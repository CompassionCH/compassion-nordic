import re
import unittest
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import HttpCase, new_test_user

from odoo.addons.my_compassion.controllers.my2_sponsorships import (
    MyCompassionNewSponsorshipController,
)
from odoo.addons.my_compassion.tests.common import DigitalSeamCase
from odoo.addons.website.tools import MockRequest

from .test_thank_you_details_copy import _text

RADIO_RE = re.compile(r'<input[^>]*name="sponsorship_plus"[^>]*>')
CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')
WIZARD_ID_RE = re.compile(r'name="wizard_id"\s+value="(\d+)"')
TOTAL_RE = re.compile(r'id="ns-total-amount"[^>]*>([^<]*)<')
SUMMARY_LABEL_RE = re.compile(
    r'<span class="tiny-text text-mid-grey">\s*([^<]*?)\s*</span>'
)

# The product names of each site language, as the products carry them.
PRODUCT_NAMES = {
    "sv_SE": ("Compassionfadder", "Compassionfadder Plus"),
    "nb_NO": ("Fadder", "Fadder Pluss"),
    "da_DK": ("Fadder", "Fadder Plus"),
}

# Per country: the language of its site, prices set for the test
# (sponsorship, Plus contribution), and the copy expected from them.
SITES = {
    "SE": {
        "lang": "sv_SE",
        "prices": (361, 61),
        "standard": "Compassionfadder 361 kr/månad",
        "plus": "Compassionfadder Plus 422 kr/månad",
        "question": "Vad innebär Compassionfadder Plus?",
        "plan_error": "Välj ett av de två fadderskapsalternativen innan du"
        " fortsätter.",
        "explanation": (
            "Utöver att hjälpa ditt fadderbarn att utvecklas både fysiskt,"
            " ekonomiskt, socialt och andligt så bidrar du med 61 kronor extra"
            " till behov som inte täcks av fadderskapet.",
            "De pengarna kan användas för alla Compassions program, där det bäst"
            " behövs.",
            "Det kan till exempel vara rent vatten, sanitetsanläggningar,"
            " katastrofhjälp, hälsoprogram för mödrar och spädbarn eller"
            " registrerade barn som ännu inte fått någon fadder.",
        ),
    },
    "NO": {
        "lang": "nb_NO",
        "prices": (362, 62),
        "standard": "Fadder 362 kr/måned",
        "plus": "Fadder Pluss 424 kr/måned",
        "question": "Hva innebærer Fadder Pluss?",
        "plan_error": "Velg ett av de to fadderskapsalternativene før du fortsetter.",
        "explanation": (
            "bidrar du med 62 kroner ekstra til behov som ikke dekkes av"
            " fadderskapet.",
            "Pengene kan brukes til alle Compassions programmer, der behovet er"
            " størst.",
            "Det kan for eksempel være rent vann,",
        ),
    },
    "DK": {
        "lang": "da_DK",
        "prices": (261, 51),
        "standard": "Fadder 261 kr/måned",
        "plus": "Fadder Plus 312 kr/måned",
        "question": "Hvad indebærer Fadder Plus?",
        "plan_error": "Vælg en af de to fadderskabsmuligheder, før du fortsætter.",
        "explanation": (
            "bidrager du med 51 kroner ekstra til behov, som fadderskabet ikke"
            " dækker.",
            "Pengene kan bruges til alle Compassions programmer, hvor behovet er"
            " størst.",
            "Det kan for eksempel være rent vand,",
        ),
    },
}


class PlanChoiceCase(DigitalSeamCase):
    """The Nordic companies, with both products named per language and
    priced on the companies' pricelists.

    Every Nordic database has the companies of SE, NO and DK, so the tests of
    the model run on them alone. The checkout's theme components only exist
    on the MyCompassion websites the theme is applied to, so a rendering test
    runs on each such site of SE, NO and DK, and skips the site the database
    lacks (stage, for one, has Sverige only): the gap shows in the log.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.companies = {}
        for company in cls.env["res.company"].search([]):
            code = company.country_id.code
            if code in SITES and code not in cls.companies:
                cls.companies[code] = company
        if not cls.companies:
            raise unittest.SkipTest("needs a company of SE, NO or DK")
        # the country of the tests that work on any of them
        cls.code = next(code for code in SITES if code in cls.companies)
        cls.websites = {}
        for website in cls.env["website"].search(
            [("is_my_compassion", "=", True), ("theme_id", "!=", False)]
        ):
            code = website.company_id.country_id.code
            if code in SITES and code not in cls.websites:
                cls.websites[code] = website
        for lang in ("en_US", *PRODUCT_NAMES):
            cls.env["res.lang"]._activate_lang(lang)
        product_model = cls.env["product.template"]
        cls.sponsorship_product = product_model.search(
            [("default_code", "=", "sponsorship")]
        )
        cls.plus_product = product_model.search([("default_code", "=", "fund_gen")])
        for lang, (standard, plus) in PRODUCT_NAMES.items():
            cls.sponsorship_product.with_context(lang=lang).name = standard
            cls.plus_product.with_context(lang=lang).name = plus
        for code, company in cls.companies.items():
            cls._set_prices(company, *SITES[code]["prices"])

    @classmethod
    def _set_prices(cls, company, amount, extra):
        """Price both products on every pricelist of the company, whichever
        of them a website or a contract picks. A product rule added last wins
        over the pricelist's own rules for the product."""
        pricelists = cls.env["product.pricelist"].search(
            [("company_id", "=", company.id)]
        )
        pricelists.item_ids = [
            Command.create(
                {
                    "applied_on": "1_product",
                    "product_tmpl_id": product.id,
                    "compute_price": "fixed",
                    "fixed_price": price,
                }
            )
            for product, price in (
                (cls.sponsorship_product, amount),
                (cls.plus_product, extra),
            )
        ]

    def _site(self, code):
        """The themed MyCompassion website of the country, else skip."""
        if code not in self.websites:
            self.skipTest(f"needs the MyCompassion website of {code}")
        return self.websites[code]

    def _mode(self, code=None):
        """A published payment mode of the country's company, without a
        provider: finishing creates the contract, no payment page."""
        return self.env["account.payment.mode"].create(
            {
                "name": "Plan Choice Mode",
                "company_id": self.companies[code or self.code].id,
                "bank_account_link": "variable",
                "payment_method_id": self.pay_method.id,
                "payment_order_ok": False,
                "is_published": True,
            }
        )


@tagged("post_install", "-at_install")
class TestSponsorshipPlanNordic(PlanChoiceCase):
    """The Nordic checkout asks the sponsor to choose between the
    sponsorship and the sponsorship Plus: two required radios, neither
    checked in advance, named after the products and priced by the
    website's pricelist."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.child = cls.env["compassion.child"].search([], limit=1)

    def setUp(self):
        super().setUp()
        # child_sponsored drives the GMC hold state, outside of what is
        # tested here.
        patcher = patch.object(
            self.registry["compassion.child"],
            "child_sponsored",
            lambda child_self, sponsor_id: None,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def _wizard(self, code=None, public=True, **values):
        user = self.env.ref("base.public_user") if public else self.env.user
        return self.env["new.sponsorship.wizard"].create(
            {
                "user_id": user.id,
                "child_id": self.child.id,
                "company_id": self.companies[code or self.code].id,
                **values,
            }
        )

    def _render(self, wizard, code, lang=None):
        lang = lang or SITES[code]["lang"]
        website = self._site(code)
        with MockRequest(self.env, website=website, context={"lang": lang}) as request:
            return str(
                MyCompassionNewSponsorshipController._render_form_content(
                    wizard.with_env(request.env)
                )
            )

    def _render_all_set(self, sponsorship, code, lang=None):
        """The summary of the thank-you page once the sponsor's name is in."""
        lang = lang or SITES[code]["lang"]
        website = self._site(code)
        with MockRequest(self.env, website=website, context={"lang": lang}) as request:
            return str(
                request.env["ir.qweb"]._render(
                    "my_compassion.my2_new_sponsorship_all_set",
                    {
                        "sponsorship": sponsorship.with_env(request.env),
                        "sponsor_identity_visible": True,
                        "first_letter_url": "/my2/letter",
                    },
                )
            )

    def _plus_sponsorship(self, code):
        """A sponsorship of the country's company with the Plus line."""
        wizard = self._checkout(f"plan-choice-plus-{code}@example.org", "1", code)
        return wizard.finish_sponsorship()

    def _checkout(self, email, plan=None, code=None):
        """A public fast checkout, answered as the page posts it."""
        wizard = self._wizard(code)
        post = {
            "sponsorship_type": "standard",
            "email": email,
            "privacy_consent": "on",
            "payment_method": str(self._mode(code).id),
            "action": "next",
        }
        if plan is not None:
            post["sponsorship_plus"] = plan
        wizard.update(post)
        return wizard

    def assertRadios(self, html, checked=None):
        radios = RADIO_RE.findall(html)
        self.assertEqual(len(radios), 2, radios)
        for radio, value in zip(radios, ("0", "1"), strict=True):
            self.assertIn('type="radio"', radio)
            self.assertIn(f'value="{value}"', radio)
            self.assertIn("required", radio)
            self.assertEqual("checked" in radio, value == checked, radio)
        self.assertNotIn('id="sponsorship_plus"', html)
        self.assertNotIn('type="checkbox" id="sponsorship_plus"', html)
        self.assertIn('id="sponsorship-plus-info-modal"', html)

    # === The page ===

    def test_plans_named_and_priced_per_site(self):
        for code, site in SITES.items():
            with self.subTest(site=code):
                html = self._render(self._wizard(code), code)
                self.assertRadios(html)
                text = _text(html)
                self.assertIn(site["standard"], text)
                self.assertIn(site["plus"], text)
                # the link, and the title of the explanation it opens
                self.assertEqual(text.count(site["question"]), 2)
                for paragraph in site["explanation"]:
                    self.assertIn(paragraph, text)

    def test_english_page_never_shows_the_back_office_names(self):
        html = self._render(self._wizard("SE"), "SE", lang="en_US")
        text = _text(html)
        self.assertIn("Sponsorship 361 kr/month", text)
        self.assertIn("Sponsorship Plus 422 kr/month", text)
        self.assertIn("What does Sponsorship Plus mean?", text)
        self.assertIn("you give 61 kronor extra", text)
        self.assertIn("This money can be used for all of Compassion's programmes", text)
        for product in (self.sponsorship_product, self.plus_product):
            self.assertNotIn(product.with_context(lang="en_US").name, text)

    def test_logged_in_payment_step_offers_the_same_choice(self):
        for code, site in SITES.items():
            with self.subTest(site=code):
                html = self._render(self._wizard(code, public=False), code)
                self.assertIn('id="payment_method"', html)
                self.assertRadios(html)
                self.assertIn('<legend class="visually-hidden">', html)
                self.assertIn(site["plus"], _text(html))

    def test_a_choice_survives_a_rerender(self):
        for code in SITES:
            for value in ("0", "1"):
                with self.subTest(site=code, value=value):
                    wizard = self._wizard(code)
                    wizard.update({"sponsorship_plus": value})
                    self.assertRadios(self._render(wizard, code), checked=value)

    def test_missing_plan_message_under_the_radios(self):
        for code, site in SITES.items():
            with self.subTest(site=code):
                html = self._render(self._wizard(code), code)
                error = re.search(r'<div\s+id="ns-plan-error"[^>]*>([^<]*)<', html)
                self.assertTrue(error, "the message is rendered, hidden")
                self.assertIn("d-none", error.group(0))
                self.assertIn('role="alert"', error.group(0))
                self.assertEqual(error.group(1).strip(), site["plan_error"])

    def test_total_waits_for_a_plan(self):
        for code, site in SITES.items():
            amount, extra = site["prices"]
            with self.subTest(site=code):
                wizard = self._wizard(code)
                total = TOTAL_RE.search(self._render(wizard, code)).group(1)
                self.assertEqual(total, "–")
                for value, expected in (("0", amount), ("1", amount + extra)):
                    wizard.update({"sponsorship_plus": value})
                    total = TOTAL_RE.search(self._render(wizard, code)).group(1)
                    self.assertIn(f"{expected}.-", total)

    def test_summary_names_the_plus_plan_as_its_radio(self):
        for code, site in SITES.items():
            with self.subTest(site=code):
                self._site(code)
                html = self._render_all_set(self._plus_sponsorship(code), code)
                plus_name = PRODUCT_NAMES[site["lang"]][1]
                self.assertIn(plus_name, SUMMARY_LABEL_RE.findall(html))

    def test_english_summary_never_shows_the_back_office_name(self):
        self._site("SE")
        html = self._render_all_set(self._plus_sponsorship("SE"), "SE", "en_US")
        labels = SUMMARY_LABEL_RE.findall(html)
        self.assertIn("Sponsorship Plus", labels)
        self.assertNotIn(self.plus_product.with_context(lang="en_US").name, labels)

    # === Reading the radios ===

    def test_radio_values(self):
        wizard = self._wizard()
        self.assertFalse(wizard.sponsorship_plan)
        wizard.update({"sponsorship_plus": "0"})
        self.assertEqual(wizard.sponsorship_plan, "standard")
        self.assertFalse(wizard.sponsorship_plus)
        wizard.update({"sponsorship_plus": "1"})
        self.assertEqual(wizard.sponsorship_plan, "plus")
        self.assertTrue(wizard.sponsorship_plus)
        # a post without the radios, or with anything else, keeps the choice
        for post in ({}, {"sponsorship_plus": ""}, {"sponsorship_plus": "on"}):
            wizard.update(post)
            self.assertEqual(wizard.sponsorship_plan, "plus")
            self.assertTrue(wizard.sponsorship_plus)

    # === Finishing ===

    def test_finishing_without_a_plan_is_refused_before_anything_is_written(self):
        email = "plan-choice-none@example.org"
        wizard = self._checkout(email)
        self.assertTrue(wizard.is_done)
        contracts_before = self.env["recurring.contract"].search_count([])
        with self.assertRaisesRegex(ValidationError, "two sponsorship options"):
            wizard.finish_sponsorship()
        self.assertFalse(self.env["res.partner"].search([("email", "=", email)]))
        self.assertEqual(
            self.env["recurring.contract"].search_count([]), contracts_before
        )

    def test_refusal_is_in_the_sponsors_language(self):
        wizard = self._checkout("plan-choice-sv@example.org")
        with self.assertRaisesRegex(ValidationError, "fadderskapsalternativen"):
            wizard.with_context(lang="sv_SE").finish_sponsorship()

    def test_plan_decides_the_plus_line(self):
        for plan, has_plus in (("0", False), ("1", True)):
            with self.subTest(plan=plan):
                wizard = self._checkout(f"plan-choice-{plan}@example.org", plan)
                sponsorship = wizard.finish_sponsorship()
                codes = sponsorship.contract_line_ids.product_id.mapped("default_code")
                self.assertIn("sponsorship", codes)
                self.assertEqual("fund_gen" in codes, has_plus)

    def test_logged_in_flow_needs_a_plan_too(self):
        sponsor = new_test_user(
            self.env, login="plan-choice-sponsor", groups="base.group_portal"
        )
        wizard = self._wizard(public=False, user_id=sponsor.id)
        wizard.update({"action": "next"})
        self.assertTrue(wizard.is_done)
        with self.assertRaisesRegex(ValidationError, "two sponsorship options"):
            wizard.finish_sponsorship()
        wizard.update({"sponsorship_plus": "1"})
        sponsorship = wizard.finish_sponsorship()
        self.assertIn(
            "fund_gen", sponsorship.contract_line_ids.product_id.mapped("default_code")
        )

    def test_write_and_pray_is_refused_before_anything_is_written(self):
        """A posted form can switch the checkout to Write&Pray, which the
        Nordic countries do not offer."""
        email = "plan-choice-wap@example.org"
        for plan in (None, "1"):
            with self.subTest(plan=plan):
                wizard = self._wizard(
                    sponsorship_type="write_and_pray",
                    email=email,
                    privacy_consent=True,
                    birthdate=fields.Date.today() - relativedelta(years=20),
                    wap_contribution_amount=15.0,
                )
                if plan:
                    wizard.update({"sponsorship_plus": plan})
                contracts_before = self.env["recurring.contract"].search_count([])
                with self.assertRaisesRegex(ValidationError, "Write&Pray"):
                    wizard.finish_sponsorship()
                self.assertFalse(
                    self.env["res.partner"].search([("email", "=", email)])
                )
                self.assertEqual(
                    self.env["recurring.contract"].search_count([]), contracts_before
                )

    def test_write_and_pray_refusal_is_in_the_sponsors_language(self):
        wizard = self._wizard(sponsorship_type="write_and_pray")
        for lang, text in (
            ("sv_SE", "Write&Pray erbjuds inte"),
            ("nb_NO", "Write&Pray tilbys ikke"),
            ("da_DK", "Write&Pray tilbydes ikke"),
        ):
            with self.subTest(lang=lang):
                with self.assertRaisesRegex(ValidationError, text):
                    wizard.with_context(lang=lang).finish_sponsorship()

    # === Without the plan choice ===

    def _plan_optional(self):
        """Switch the plan choice off, as the base checkout tests do."""
        patcher = patch.object(
            type(self.env["new.sponsorship.wizard"]),
            "_my2_plan_required",
            return_value=False,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_switched_off_the_page_keeps_the_base_checkbox(self):
        self._plan_optional()
        for code, site in SITES.items():
            with self.subTest(site=code):
                html = self._render(self._wizard(code), code)
                self.assertNotIn('type="radio" id="sponsorship_plan', html)
                self.assertNotIn('<legend class="visually-hidden">', html)
                self.assertIn('id="sponsorship_plus"', html)
                self.assertIn('id="sponsorship-plus-info-modal"', html)
                self.assertNotIn(site["question"], _text(html))

    def test_switched_off_the_total_and_summary_are_the_base_ones(self):
        self._site("SE")
        sponsorship = self._plus_sponsorship("SE")
        self._plan_optional()
        amount = SITES["SE"]["prices"][0]
        total = TOTAL_RE.search(self._render(self._wizard("SE"), "SE")).group(1)
        self.assertIn(f"{amount}.-", total)
        labels = SUMMARY_LABEL_RE.findall(self._render_all_set(sponsorship, "SE"))
        self.assertNotIn(PRODUCT_NAMES["sv_SE"][1], labels)

    def test_switched_off_a_sponsorship_finishes_without_a_plan(self):
        self._plan_optional()
        wizard = self._checkout("plan-choice-optional@example.org")
        self.assertFalse(wizard.sponsorship_plan)
        sponsorship = wizard.finish_sponsorship()
        codes = sponsorship.contract_line_ids.product_id.mapped("default_code")
        self.assertIn("sponsorship", codes)
        self.assertNotIn("fund_gen", codes)

    def test_switched_off_the_checkbox_is_read_as_before(self):
        self._plan_optional()
        wizard = self._wizard()
        wizard.update({"sponsorship_plus": "on"})
        self.assertTrue(wizard.sponsorship_plus)
        self.assertFalse(wizard.sponsorship_plan)


@tagged("post_install", "-at_install")
class TestPlanChoiceRoutes(HttpCase, PlanChoiceCase):
    """The plan check holds over HTTP: a checkout posted without a plan is
    refused at /submit, and nothing is created."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        code = next((code for code in SITES if code in cls.websites), None)
        if not code:
            raise unittest.SkipTest("needs a MyCompassion website of SE, NO or DK")
        cls.code = code
        # The test client talks to 127.0.0.1: the website gets that domain,
        # like the sponsors' requests in production.
        cls.website = cls.websites[code]
        cls.website.domain = cls.base_url()

    def setUp(self):
        super().setUp()
        # An available, unreserved child: the checkout refuses any other.
        self.child = self.env["compassion.child"].search([], limit=1)
        self.child.write(
            {
                "state": self.env["compassion.child"]._available_states()[0],
                "website_reservation_date": False,
                "website_reservation_id": False,
            }
        )
        # The GMC hold state and messages are outside of what is tested here.
        for model, method, stub in (
            ("compassion.child", "child_sponsored", lambda records, sponsor_id: None),
            ("gmc.message", "_perform_outgoing_action", lambda records: None),
        ):
            patcher = patch.object(self.registry[model], method, stub)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _checkout(self, email, **post):
        """Start the checkout, post its one step, then /submit."""
        page = self.url_open(f"/my2/new-sponsorship/{self.child.id}")
        self.assertEqual(page.status_code, 200)
        csrf = CSRF_RE.search(page.text).group(1)
        wizard_id = int(WIZARD_ID_RE.search(page.text).group(1))
        step = self.make_jsonrpc_request(
            "/my2/new-sponsorship/step",
            {
                "wizard_id": wizard_id,
                "email": email,
                "privacy_consent": "true",
                "payment_method": str(self._mode().id),
                "action": "next",
                **post,
            },
        )
        self.assertEqual(step, {"finish": True})
        return self.url_open(
            "/my2/new-sponsorship/submit",
            data={"csrf_token": csrf, "wizard_id": wizard_id},
            allow_redirects=False,
        )

    def _contracts(self):
        return self.env["recurring.contract"].search([("child_id", "=", self.child.id)])

    def test_submit_without_a_plan_is_refused(self):
        email = "plan-choice-route-none@example.org"
        before = self._contracts()
        response = self._checkout(email)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._contracts(), before)
        self.assertFalse(self.env["res.partner"].search([("email", "=", email)]))

    def test_submit_with_a_plan_creates_the_contract(self):
        before = self._contracts()
        response = self._checkout(
            "plan-choice-route-plus@example.org", sponsorship_plus="1"
        )
        self.assertEqual(response.status_code, 303, response.text[:500])
        sponsorship = self._contracts() - before
        self.assertEqual(len(sponsorship), 1)
        self.assertIn(
            "fund_gen", sponsorship.contract_line_ids.product_id.mapped("default_code")
        )
