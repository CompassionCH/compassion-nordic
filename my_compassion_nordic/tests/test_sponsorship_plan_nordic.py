import re
import unittest
from unittest.mock import patch

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.my_compassion.controllers.my2_sponsorships import (
    MyCompassionNewSponsorshipController,
)
from odoo.addons.my_compassion.tests.common import DigitalSeamCase
from odoo.addons.website.tools import MockRequest

from .test_thank_you_details_copy import _text

RADIO_RE = re.compile(r'<input[^>]*name="sponsorship_plus"[^>]*>')

# The product names of each site language, as the products carry them.
PRODUCT_NAMES = {
    "sv_SE": ("Compassionfadder", "Compassionfadder Plus"),
    "nb_NO": ("Fadder", "Fadder Pluss"),
    "da_DK": ("Fadder", "Fadder Plus"),
}

# Per site: its language, prices set for the test (sponsorship, Plus
# contribution), and the copy expected from them.
SITES = {
    "SE": {
        "lang": "sv_SE",
        "prices": (361, 61),
        "standard": "Compassionfadder 361 kr/månad",
        "plus": "Compassionfadder Plus 422 kr/månad",
        "question": "Vad innebär Compassionfadder Plus?",
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
        "explanation": (
            "bidrager du med 51 kroner ekstra til behov, som fadderskabet ikke"
            " dækker.",
            "Pengene kan bruges til alle Compassions programmer, hvor behovet er"
            " størst.",
            "Det kan for eksempel være rent vand,",
        ),
    },
}


@tagged("post_install", "-at_install")
class TestSponsorshipPlanNordic(DigitalSeamCase):
    """The Nordic checkout asks the sponsor to choose between the
    sponsorship and the sponsorship Plus: two required radios, neither
    checked in advance, named after the products and priced by the
    website's pricelist."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The MyCompassion websites of the Nordic countries: the checkout's
        # theme components only exist on the websites the theme is applied
        # to, so the page is rendered on those.
        cls.websites = {}
        for website in cls.env["website"].search([("is_my_compassion", "=", True)]):
            code = website.company_id.country_id.code
            if code in SITES and code not in cls.websites:
                cls.websites[code] = website
        if set(cls.websites) != set(SITES):
            raise unittest.SkipTest("needs the MyCompassion website of SE, NO and DK")
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
        for code, site in SITES.items():
            cls._set_prices(cls.websites[code], *site["prices"])
        cls.child = cls.env["compassion.child"].search([], limit=1)

    @classmethod
    def _set_prices(cls, website, amount, extra):
        """Price both products on every pricelist of the website's company,
        whichever of them the website picks. A product rule added last wins
        over the pricelist's own rules for the product."""
        pricelists = cls.env["product.pricelist"].search(
            [("company_id", "=", website.company_id.id)]
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

    def _wizard(self, code="SE", public=True, **values):
        user = self.env.ref("base.public_user") if public else self.env.user
        return self.env["new.sponsorship.wizard"].create(
            {
                "user_id": user.id,
                "child_id": self.child.id,
                "company_id": self.websites[code].company_id.id,
                **values,
            }
        )

    def _render(self, wizard, code="SE", lang=None):
        lang = lang or SITES[code]["lang"]
        website = self.websites[code]
        with MockRequest(self.env, website=website, context={"lang": lang}) as request:
            return str(
                MyCompassionNewSponsorshipController._render_form_content(
                    wizard.with_env(request.env)
                )
            )

    def _mode(self, code="SE"):
        """A published card payment mode of the site's company."""
        return self.env["account.payment.mode"].create(
            {
                "name": "Plan Choice Card",
                "company_id": self.websites[code].company_id.id,
                "bank_account_link": "variable",
                "payment_method_id": self.pay_method.id,
                "payment_order_ok": False,
                "is_published": True,
            }
        )

    def _checkout(self, email, plan=None, code="SE"):
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
        html = self._render(self._wizard("DK", public=False), "DK")
        self.assertIn('id="payment_method"', html)
        self.assertRadios(html)
        self.assertIn(SITES["DK"]["plus"], _text(html))

    def test_a_choice_survives_a_rerender(self):
        for value in ("0", "1"):
            with self.subTest(value=value):
                wizard = self._wizard()
                wizard.update({"sponsorship_plus": value})
                self.assertRadios(self._render(wizard), checked=value)

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
        wizard = self._wizard("DK", public=False, user_id=sponsor.id)
        wizard.update({"action": "next"})
        self.assertTrue(wizard.is_done)
        with self.assertRaisesRegex(ValidationError, "two sponsorship options"):
            wizard.finish_sponsorship()
        wizard.update({"sponsorship_plus": "1"})
        sponsorship = wizard.finish_sponsorship()
        self.assertIn(
            "fund_gen", sponsorship.contract_line_ids.product_id.mapped("default_code")
        )

    def test_write_and_pray_has_no_plan_to_choose(self):
        wizard = self._wizard(
            sponsorship_type="write_and_pray",
            email="plan-choice-wap@example.org",
            privacy_consent=True,
            birthdate=fields.Date.today() - relativedelta(years=20),
            wap_contribution_amount=15.0,
        )
        self.assertNotIn('name="sponsorship_plus"', self._render(wizard))
        sponsorship = wizard.finish_sponsorship()
        self.assertEqual(sponsorship.type, "SWP")
        self.assertEqual(sponsorship.total_amount, 15.0)
