import re
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import HttpCase, new_test_user

from odoo.addons.my_compassion.tests.common import DigitalSeamCase

# The copy above the Nordic details form, per language of the sites.
TITLE = {
    "en_US": "Thank you for becoming the sponsor of",
    "sv_SE": "Tack för att du har blivit fadder till",
    "nb_NO": "Takk for at du har blitt fadder for",
    "da_DK": "Tak fordi du er blevet fadder for",
}
INTRO = {
    "en_US": "Please fill in your details so we can manage your new sponsorship.",
    "sv_SE": "Var vänlig och fyll i dina uppgifter så vi kan administrera ditt"
    " nya fadderskap.",
    "nb_NO": "Vennligst fyll inn opplysningene dine, så vi kan administrere ditt"
    " nye fadderskap.",
    "da_DK": "Udfyld venligst dine oplysninger, så vi kan administrere dit nye"
    " fadderskab.",
}
LETTER_WRITER = {
    "en_US": "If someone else will write the letters, enter their name instead.",
    "sv_SE": "Om brevskrivningen ska skötas av någon annan, fyll i det namnet i"
    " stället.",
    "nb_NO": "Hvis noen andre skal skrive brevene, skriv inn navnet deres i stedet.",
    "da_DK": "Hvis en anden skal skrive brevene, så skriv vedkommendes navn i"
    " stedet.",
}
# What my_compassion's form and page say in its place.
BASE_COPY = {
    "en_US": ("Who shall we thank?", "Thank you for sponsoring"),
    "sv_SE": ("Vem ska vi tacka?", "Tack för att du är fadder till"),
    "nb_NO": ("Hvem skal vi takke?", "Takk for at du er fadder for"),
    "da_DK": ("Who shall we thank?", "Tak, fordi du er fadder for"),
}


def _text(html):
    """The visible text of a page, one space between words."""
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", html).replace("\xa0", " ").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text)


@tagged("post_install", "-at_install")
class TestThankYouDetailsCopy(HttpCase, DigitalSeamCase):
    """While the details form is due, the thank-you page says the
    sponsorship has begun, and the form opens on what it is for instead of
    its own heading."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The test client talks to 127.0.0.1: the MyCompassion website gets
        # that domain, like the sponsors' requests in production.
        cls.website = cls.env.ref("my_compassion.my2_website")
        cls.website.domain = cls.base_url()
        for lang in TITLE:
            cls.env["res.lang"]._activate_lang(lang)
        cls.website.language_ids |= cls.env["res.lang"].search(
            [("code", "in", list(TITLE))]
        )

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
        self.child = self.env["compassion.child"].search([], limit=1)
        self.assertTrue(self.child, "the database needs a child")
        self.child.preferred_name = "Maria"
        self.signup = self._make_digital_contract(child=self.child)
        self.payer = self.signup.partner_id
        self.payer.write(
            {
                "lastname": self.env["res.partner"].MY2_PLACEHOLDER_NAME,
                "firstname": False,
                "my2_name_placeholder": True,
            }
        )
        self.signup.write(
            {"my2_signup": True, "my2_details_awaited_partner": self.payer.id}
        )

    def _open_form(self, lang):
        token = self.signup._my2_issue_details_token()
        prefix = ""
        if lang != self.website.default_lang_id.code:
            prefix = "/" + self.env["res.lang"]._get_data(code=lang).url_code
        page = self.url_open(
            f"{prefix}/my2/new-sponsorship/thank-you"
            f"?sponsorship_id={self.signup.id}&details_token={token}"
        )
        self.assertEqual(page.status_code, 200)
        self.assertIn("/my2/new-sponsorship/complete-details", page.text)
        return page.text

    def test_copy_of_the_page_in_each_language(self):
        name = self.child.preferred_name
        for lang in TITLE:
            with self.subTest(lang=lang):
                html = self._open_form(lang)
                text = _text(html)
                self.assertIn(f"{TITLE[lang]} {name}", text)
                self.assertIn(INTRO[lang], text)
                self.assertIn(LETTER_WRITER[lang], text)
                heading, title = BASE_COPY[lang]
                self.assertNotIn(heading, text)
                self.assertNotIn(title, text)

    def test_form_opens_on_the_intro_then_the_letter_writer(self):
        html = self._open_form("en_US")
        token_input = html.index('name="details_token"')
        after_token = _text(html[html.index(">", token_input) + 1 :])
        self.assertTrue(
            after_token.lstrip().startswith(
                f"{INTRO['en_US']} {LETTER_WRITER['en_US']}"
            ),
            after_token[:300],
        )
        self.assertNotIn("writes to you by name", after_token)

    def test_page_without_the_form_keeps_its_title(self):
        """Once the details are in, the page thanks the sponsor as before."""
        self.payer.write(
            {"firstname": "Anna", "lastname": "Svensson", "my2_name_placeholder": False}
        )
        self.signup.my2_details_awaited_partner = 0
        self.assertFalse(self.signup._my2_details_pending())
        login = "nordic-thank-you-copy"
        new_test_user(
            self.env, login=login, groups="base.group_portal", partner_id=self.payer.id
        )
        self.authenticate(login, login)
        page = self.url_open(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={self.signup.id}"
        )
        self.assertEqual(page.status_code, 200)
        self.assertNotIn("/my2/new-sponsorship/complete-details", page.text)
        text = _text(page.text)
        self.assertIn(f"Thank you for sponsoring {self.child.preferred_name}", text)
        self.assertNotIn(TITLE["en_US"], text)
