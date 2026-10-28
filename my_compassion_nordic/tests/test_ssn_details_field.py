from odoo.tests import TransactionCase, tagged

from odoo.addons.my_compassion_nordic.controllers.my2_sponsorships import (
    MyCompassionNewSponsorshipNordic,
)
from odoo.addons.my_compassion_nordic.models.res_company import (
    SSN_REPORTING_COUNTRIES,
)

# Valid specimens, checked against the stdnum validators the form uses.
SE_VALID = "811218-9876"
NO_VALID = "01129900160"
DK_VALID = "211062-5629"


@tagged("post_install", "-at_install")
class TestSsnDetailsField(TransactionCase):
    """The national identity number of the post-payment details form.

    Optional everywhere, never a reason a sponsor cannot finish, and stored
    even when it belongs to another Nordic country than the one whose tax
    authority would receive the report.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["res.partner"]

    def _company(self, country_code, collect=True):
        country = self.env["res.country"].search(
            [("code", "=", country_code)], limit=1
        )
        return self.env["res.company"].create(
            {
                "name": f"SSN Test {country_code}",
                "country_id": country.id,
                "my2_collect_ssn": collect,
            }
        )

    # === Classification ===

    def test_own_country_number_is_ok(self):
        for code, ssn in (("SE", SE_VALID), ("NO", NO_VALID), ("DK", DK_VALID)):
            with self.subTest(country=code):
                outcome, matched = self.partner_model._my2_check_ssn(ssn, code)
                self.assertEqual(outcome, "ok")
                self.assertEqual(matched, code)

    def test_other_nordic_number_is_foreign_not_invalid(self):
        """A Swede sponsoring on the Norwegian site. Their personnummer is
        no use to Skatteetaten, but it is still their number and is kept."""
        outcome, matched = self.partner_model._my2_check_ssn(SE_VALID, "NO")
        self.assertEqual(outcome, "foreign")
        self.assertEqual(matched, "SE")

    def test_garbage_is_invalid(self):
        for value in ("81121898", "not-a-number", "0000000000"):
            with self.subTest(value=value):
                outcome, _matched = self.partner_model._my2_check_ssn(value, "SE")
                self.assertEqual(outcome, "invalid")

    def test_company_without_reporting_country_accepts_any_nordic(self):
        """The shared Norden parent company has no report of its own to
        file, so there is nothing for a number to be foreign to."""
        outcome, _matched = self.partner_model._my2_check_ssn(SE_VALID, "SC")
        self.assertEqual(outcome, "ok")

    # === The form's error path ===

    def _error_for(self, ssn, country_code, collect=True):
        company = self._company(country_code, collect=collect)
        sponsorship = self.env["recurring.contract"].new(
            {"company_id": company.id}
        )
        return MyCompassionNewSponsorshipNordic._details_extra_error(
            {"social_sec_nr": ssn}, sponsorship
        )

    def test_empty_ssn_is_never_an_error(self):
        """The field is optional: the lawful basis for asking is the tax
        report, which the sponsor is free to forgo."""
        self.assertEqual(self._error_for("", "SE"), "")

    def test_foreign_ssn_is_never_an_error(self):
        self.assertEqual(self._error_for(SE_VALID, "NO"), "")

    def test_invalid_ssn_is_an_error(self):
        self.assertTrue(self._error_for("81121898", "SE"))

    def test_invalid_ssn_ignored_when_company_does_not_collect(self):
        self.assertEqual(self._error_for("81121898", "SE", collect=False), "")

    # === Seeding ===

    def test_seed_turns_the_flag_on_only_for_reporting_countries(self):
        """Both directions. Asserting only the positive would have missed
        the real bug: a ("country_id.code", "in", ...) domain does not
        filter res.company at all, so every company was seeded on -
        including the Norden parent, whose country is Seychelles."""
        self.env["res.company"]._my2_seed_collect_ssn()
        for company in self.env["res.company"].search([]):
            with self.subTest(company=company.name):
                self.assertEqual(
                    company.my2_collect_ssn,
                    company.country_id.code in SSN_REPORTING_COUNTRIES,
                )

    def test_country_code_domain_does_not_filter_companies(self):
        """Guards the reason the seeder filters in Python. If this ever
        starts filtering, the workaround can go - until then, a domain here
        silently matches everything."""
        all_companies = self.env["res.company"].search([])
        by_domain = self.env["res.company"].search(
            [("country_id.code", "in", list(SSN_REPORTING_COUNTRIES))]
        )
        non_reporting = all_companies.filtered(
            lambda c: c.country_id.code not in SSN_REPORTING_COUNTRIES
        )
        if non_reporting:
            self.assertTrue(
                by_domain & non_reporting,
                "the domain now filters - drop the Python filter in"
                " _my2_seed_collect_ssn",
            )

    def test_finland_is_not_a_reporting_country(self):
        """Finland's donation deduction covers gifts to universities only,
        so a Finnish entity has no report to file and therefore no lawful
        basis to ask for a henkilotunnus."""
        self.assertNotIn("FI", SSN_REPORTING_COUNTRIES)
