import re
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.my_compassion.tests.common import DigitalSeamCase

CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')


@tagged("post_install", "-at_install")
class TestDetailsFormNordic(HttpCase, DigitalSeamCase):
    """The Nordic post-payment details form, through its public routes.

    A required step: it stays after Stripe named the payer, it cannot be put
    off, and the name typed on it is the letter writer's, which only
    replaces the payer's when it is the same person.
    """

    def setUp(self):
        super().setUp()
        self.signup = self._make_digital_contract()
        company = self.signup.company_id
        company.partner_id.country_id = self.env.ref("base.se")
        company.my2_collect_ssn = True
        self.payer = self.signup.partner_id
        self.payer.write(
            {
                "lastname": self.env["res.partner"].MY2_PLACEHOLDER_NAME,
                "firstname": False,
                "my2_name_placeholder": True,
                "email": "nordic-details@example.org",
                "phone": False,
            }
        )
        self.signup.write({"my2_signup": True, "my2_details_awaited": True})

    def _name_from_stripe(self, firstname, lastname):
        """What _my2_apply_cardholder_name does once Stripe sent a name."""
        self.payer._my2_replace_placeholder_name(firstname, lastname)

    def _open_form(self):
        token = self.signup._my2_issue_details_token()
        page = self.url_open(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={self.signup.id}"
            f"&details_token={token}"
        )
        self.assertEqual(page.status_code, 200)
        return page.text, CSRF_RE.search(page.text).group(1), token

    def _submit(self, route="complete-details", **fields_):
        _html, csrf, token = self._open_form()
        values = {
            "csrf_token": csrf,
            "sponsorship_id": self.signup.id,
            "details_token": token,
            "firstname": "Anna",
            "lastname": "Svensson",
            "phone": "+46 70 123 45 67",
            **fields_,
        }
        return self.url_open(
            f"/my2/new-sponsorship/{route}", data=values, allow_redirects=False
        )

    # === The form ===

    def test_form_stays_after_stripe_named_the_payer(self):
        self._name_from_stripe("Anna", "Svensson")

        html, _csrf, _token = self._open_form()

        self.assertIn("/my2/new-sponsorship/complete-details", html)
        self.assertIn('value="Anna"', html)
        self.assertIn("Personnummer (for gift reporting to Skatteverket)", html)
        self.assertNotIn("All set", html)

    def test_form_has_no_later_and_no_address(self):
        html, _csrf, _token = self._open_form()

        self.assertNotIn("/my2/new-sponsorship/details-later", html)
        self.assertNotIn('name="street"', html)

    def test_identity_field_sits_above_the_phone(self):
        html, _csrf, _token = self._open_form()

        self.assertLess(html.index('name="social_sec_nr"'), html.index('name="phone"'))

    def test_details_later_sends_back_to_the_form(self):
        response = self._submit(route="details-later")

        self.assertEqual(response.status_code, 303)
        self.assertNotIn("details_emailed", response.headers["Location"])
        self.assertTrue(self.signup._my2_details_pending())

    # === Saving ===

    def test_payer_without_a_stripe_name_takes_the_form_name(self):
        response = self._submit(social_sec_nr="8112189876")

        self.assertEqual(response.status_code, 303)
        self.assertEqual(
            (self.payer.firstname, self.payer.lastname), ("Anna", "Svensson")
        )
        self.assertEqual(self.payer.phone, "+46 70 123 45 67")
        self.assertEqual(self.payer.sudo().social_sec_nr, "19811218-9876")
        self.assertEqual(self.signup.correspondent_id, self.payer)
        self.assertFalse(self.signup._my2_details_pending())

    def test_same_name_split_differently_is_corrected_on_the_payer(self):
        self._name_from_stripe("Anna Maria", "Svensson")

        self._submit(firstname="Anna", lastname="Maria Svensson")

        self.assertEqual(
            (self.payer.firstname, self.payer.lastname), ("Anna", "Maria Svensson")
        )
        self.assertEqual(self.signup.correspondent_id, self.payer)

    def test_another_name_becomes_the_letter_writer(self):
        """The payer keeps the name Stripe charged and gets the identity
        number; the person named on the form writes the letters."""
        self._name_from_stripe("Anna", "Svensson")
        partners_before = self.env["res.partner"].search([])

        response = self._submit(
            firstname="Erik", lastname="Svensson", social_sec_nr=" 811218-9876 "
        )

        self.assertEqual(response.status_code, 303)
        self.assertEqual(
            (self.payer.firstname, self.payer.lastname), ("Anna", "Svensson")
        )
        self.assertFalse(self.payer.phone)
        self.assertEqual(self.payer.sudo().social_sec_nr, "19811218-9876")
        letter_writer = self.env["res.partner"].search([]) - partners_before
        self.assertEqual(len(letter_writer), 1)
        self.assertEqual(
            (letter_writer.firstname, letter_writer.lastname, letter_writer.phone),
            ("Erik", "Svensson", "+46 70 123 45 67"),
        )
        self.assertFalse(letter_writer.sudo().social_sec_nr)
        self.assertFalse(self.signup._my2_details_pending())

    def test_foreign_number_sends_the_form_back_without_saving(self):
        response = self._submit(social_sec_nr="01129900160")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Skatteverket", response.text)
        self.assertIn('value="01129900160"', response.text)
        self.assertTrue(self.payer.my2_name_placeholder)
        self.assertFalse(self.payer.phone)
        self.assertTrue(self.signup._my2_details_pending())

    # === The letter writer job ===

    def test_letter_writer_job_makes_them_the_correspondent(self):
        letter_writer = self.env["res.partner"].create(
            {"firstname": "Erik", "lastname": "Svensson"}
        )
        partner_class = type(self.env["res.partner"])
        with patch.object(
            partner_class,
            "upsert_constituent",
            return_value=self.env["gmc.message"],
        ) as upsert:
            self.signup._my2_assign_letter_writer(letter_writer.id)

        upsert.assert_called_once()
        self.assertEqual(self.signup.correspondent_id, letter_writer)
        self.assertEqual(self.signup.partner_id, self.payer)
