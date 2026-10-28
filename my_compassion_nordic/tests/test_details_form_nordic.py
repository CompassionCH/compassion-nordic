import re
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.my_compassion.tests.common import DigitalSeamCase

CSRF_RE = re.compile(r'name="csrf_token"\s+value="([^"]+)"')
SE_VALID = "811218-9876"


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
        self.signup.write(
            {"my2_signup": True, "my2_details_awaited_partner": self.payer.id}
        )

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

    def test_details_emailed_flag_does_not_hide_the_form(self):
        """The flag is a query parameter: anyone holding the page can add it,
        and a required form must not be put off by it."""
        token = self.signup._my2_issue_details_token()

        page = self.url_open(
            f"/my2/new-sponsorship/thank-you?sponsorship_id={self.signup.id}"
            f"&details_token={token}&details_emailed=1"
        )

        self.assertIn("/my2/new-sponsorship/complete-details", page.text)

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
        # the payer keeps the sponsorship and its letters in their portal
        self.assertEqual(self.payer.portal_sponsorships, "all_info")
        # the correspondent change waits in a job, never in the request
        self.assertEqual(self.signup.correspondent_id, self.payer)
        job_model = "queue.job" if "queue.job" in self.env else "queue.job.replacement"
        self.assertTrue(
            self.env[job_model].search(
                [
                    (
                        "identity_key",
                        "=",
                        f"recurring.contract._my2_assign_letter_writer.{self.signup.id}",
                    )
                ]
            )
        )

    def test_completing_a_card_name_is_the_same_person(self):
        """A card name is often only part of the name. Adding the surname is
        not naming someone else."""
        self._name_from_stripe("Pekka", False)
        partners_before = self.env["res.partner"].search([])

        self._submit(firstname="Pekka", lastname="Virtanen")

        self.assertEqual(
            (self.payer.firstname, self.payer.lastname), ("Pekka", "Virtanen")
        )
        self.assertFalse(self.env["res.partner"].search([]) - partners_before)
        self.assertEqual(self.signup.correspondent_id, self.payer)

    def test_restoring_the_accents_is_the_same_person(self):
        self._name_from_stripe("ASA", "OSTERGAARD")

        self._submit(firstname="Åsa", lastname="Østergaard")

        self.assertEqual(
            (self.payer.firstname, self.payer.lastname), ("Åsa", "Østergaard")
        )
        self.assertEqual(self.signup.correspondent_id, self.payer)

    def test_stripe_name_not_yet_on_the_payer_still_makes_them_the_payer(self):
        """Stripe reported the payer's name, but post-processing has not
        written it on the partner yet (the payment is still pending). A
        different name on the form is still the letter writer's."""
        invoice = self.signup._ensure_first_invoice()
        transaction = self.env["payment.transaction"].create(
            {
                "provider_id": self.signup.payment_mode_id.payment_provider_id.id,
                "payment_method_id": self.env["payment.method"].search([], limit=1).id,
                "partner_id": self.payer.id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "reference": "nordic-details-authorised",
                "operation": "online_direct",
                "invoice_ids": [(6, 0, invoice.ids)],
                "state": "pending",
            }
        )
        transaction.my2_cardholder_name = "Anna Svensson"
        partners_before = self.env["res.partner"].search([])

        self._submit(firstname="Erik", lastname="Svensson", social_sec_nr=SE_VALID)

        self.assertEqual(
            (self.payer.firstname, self.payer.lastname), ("Anna", "Svensson")
        )
        self.assertEqual(self.payer.sudo().social_sec_nr, "19811218-9876")
        letter_writer = self.env["res.partner"].search([]) - partners_before
        self.assertEqual(letter_writer.name, "Erik Svensson")

    def test_foreign_number_sends_the_form_back_without_saving(self):
        response = self._submit(social_sec_nr="01129900160")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Skatteverket", response.text)
        self.assertIn('value="01129900160"', response.text)
        self.assertTrue(self.payer.my2_name_placeholder)
        self.assertFalse(self.payer.phone)
        self.assertTrue(self.signup._my2_details_pending())

    # === The letter writer job ===

    def _letter_writer(self):
        return self.env["res.partner"].create(
            {"firstname": "Erik", "lastname": "Svensson"}
        )

    def _gmc_upsert(self, registers):
        """Stand in for GMC's constituent upsert, which never raises: a
        rejected one only leaves the partner without a global_id."""

        def upsert(partners):
            if registers:
                partners.global_id = f"T3465-{partners.id}"
            return self.env["gmc.message"]

        return patch.object(
            type(self.env["res.partner"]),
            "upsert_constituent",
            autospec=True,
            side_effect=upsert,
        )

    def test_letter_writer_job_makes_them_the_correspondent(self):
        """Queued from the public form, so it runs as the public user."""
        letter_writer = self._letter_writer()
        public = self.env.ref("base.public_user")

        with self._gmc_upsert(registers=True):
            self.signup.with_user(public)._my2_assign_letter_writer(letter_writer.id)

        self.assertEqual(self.signup.correspondent_id, letter_writer)
        self.assertEqual(self.signup.partner_id, self.payer)

    def test_letter_writer_job_updates_an_existing_commitment(self):
        """Once GMC has the sponsorship, the ordinary correspondent change
        takes care of it, constituent included."""
        letter_writer = self._letter_writer()
        self.signup.gmc_commitment_id = "T3465-COMMITMENT"
        contract_class = type(self.env["recurring.contract"])

        with (
            self._gmc_upsert(registers=True) as upsert,
            patch.object(
                contract_class, "_change_correspondent", return_value=True
            ) as change,
        ):
            # the fixture contract carries no_upsert, a queued job does not
            self.signup.with_context(no_upsert=False)._my2_assign_letter_writer(
                letter_writer.id
            )

        upsert.assert_not_called()
        change.assert_called_once()
        self.assertEqual(self.signup.correspondent_id, letter_writer)

    def test_letter_writer_job_fails_when_gmc_does_not_register_them(self):
        """The pending sponsorship upsert would name a correspondent GMC
        does not know: the job fails instead, and nothing changes."""
        letter_writer = self._letter_writer()

        with self._gmc_upsert(registers=False), self.assertRaises(UserError):
            self.signup._my2_assign_letter_writer(letter_writer.id)

        self.assertEqual(self.signup.correspondent_id, self.payer)
