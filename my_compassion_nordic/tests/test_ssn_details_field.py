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

    Optional everywhere, never a reason a sponsor cannot finish, and only
    ever stored as a valid number of the country whose tax authority
    receives the report, in the form that report uses.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["res.partner"]

    def _company(self, country_code, collect=True):
        country = self.env["res.country"].search([("code", "=", country_code)], limit=1)
        return self.env["res.company"].create(
            {
                "name": f"SSN Test {country_code} {'on' if collect else 'off'}",
                "country_id": country.id,
                "my2_collect_ssn": collect,
            }
        )

    def _signup(self, country_code, collect=True):
        return self.env["recurring.contract"].new(
            {"company_id": self._company(country_code, collect=collect).id}
        )

    # === Normalisation ===

    def test_swedish_number_takes_the_twelve_digit_form(self):
        """KU65 wants twelve digits; the tax export drops the dash."""
        for typed in (
            "811218-9876",
            "8112189876",
            "198112189876",
            "19811218-9876",
            "811218 9876",
        ):
            with self.subTest(typed=typed):
                self.assertEqual(
                    self.partner_model._my2_normalize_ssn(typed, "SE"),
                    "19811218-9876",
                )

    def test_swedish_centenarian_keeps_their_century(self):
        self.assertEqual(
            self.partner_model._my2_normalize_ssn("811218+9876", "SE"),
            "18811218-9876",
        )

    def test_norwegian_and_danish_numbers_are_compacted(self):
        self.assertEqual(
            self.partner_model._my2_normalize_ssn(f" {NO_VALID} ", "NO"), NO_VALID
        )
        self.assertEqual(
            self.partner_model._my2_normalize_ssn(DK_VALID, "DK"), "2110625629"
        )

    def test_only_the_reporting_countrys_number_is_accepted(self):
        """A Swede's personnummer on the Norwegian site could never go into
        Skatteetaten's report."""
        for ssn, country_code in (
            (SE_VALID, "NO"),
            (NO_VALID, "SE"),
            (SE_VALID, "DK"),
            (DK_VALID, "SE"),
        ):
            with self.subTest(ssn=ssn, country=country_code):
                self.assertEqual(
                    self.partner_model._my2_normalize_ssn(ssn, country_code), ""
                )

    def test_garbage_and_unknown_countries_are_refused(self):
        for value, country_code in (
            ("81121898", "SE"),
            ("8112189875", "SE"),
            ("not-a-number", "NO"),
            ("", "SE"),
            (SE_VALID, "SC"),
            (SE_VALID, "FI"),
        ):
            with self.subTest(value=value, country=country_code):
                self.assertEqual(
                    self.partner_model._my2_normalize_ssn(value, country_code), ""
                )

    # === The form's error path ===

    def _error_for(self, ssn, country_code, collect=True):
        return MyCompassionNewSponsorshipNordic._details_extra_error(
            {"social_sec_nr": ssn}, self._signup(country_code, collect=collect)
        )

    def test_empty_ssn_is_never_an_error(self):
        """The field is optional: the lawful basis for asking is the tax
        report, which the sponsor is free to forgo."""
        self.assertEqual(self._error_for("", "SE"), "")

    def test_own_country_ssn_is_accepted(self):
        for ssn, country_code in (
            (SE_VALID, "SE"),
            (NO_VALID, "NO"),
            (DK_VALID, "DK"),
        ):
            with self.subTest(country=country_code):
                self.assertEqual(self._error_for(ssn, country_code), "")

    def test_other_countrys_ssn_is_an_error_naming_the_authority(self):
        self.assertIn("Skatteetaten", self._error_for(SE_VALID, "NO"))
        self.assertIn("Skatteverket", self._error_for("81121898", "SE"))
        self.assertIn("Skattestyrelsen", self._error_for(SE_VALID, "DK"))

    def test_ssn_ignored_when_company_does_not_collect(self):
        self.assertEqual(self._error_for("81121898", "SE", collect=False), "")

    def test_flag_on_a_country_without_a_format_collects_nothing(self):
        """Switching the flag on for a company the form has no number
        format for must not make the field refuse every value."""
        signup = self._signup("SC")
        self.assertFalse(signup._my2_collects_ssn())

    # === What reaches the partner ===

    def test_partner_vals_hold_the_normalised_number(self):
        signup = self._signup("SE")
        self.assertEqual(
            signup._my2_details_extra_partner_vals({"social_sec_nr": "8112189876"}),
            {"social_sec_nr": "19811218-9876"},
        )

    def test_partner_vals_skip_an_empty_or_uncollected_number(self):
        self.assertEqual(
            self._signup("SE")._my2_details_extra_partner_vals({"social_sec_nr": ""}),
            {},
        )
        self.assertEqual(
            self._signup("SE", collect=False)._my2_details_extra_partner_vals(
                {"social_sec_nr": SE_VALID}
            ),
            {},
        )

    def test_number_is_staff_only(self):
        """Portal record rules let a sponsor read other partners, so the
        number must not be readable by portal users at all."""
        field = self.partner_model._fields["social_sec_nr"]
        self.assertEqual(field.groups, "base.group_user")

    # === Seeding ===

    def test_seed_turns_the_flag_on_only_for_reporting_countries(self):
        """Both directions: a company outside the reporting countries, such
        as the shared Norden parent, is explicitly off."""
        sweden = self._company("SE", collect=False)
        seychelles = self._company("SC", collect=True)

        self.env["res.company"]._my2_seed_collect_ssn()

        self.assertTrue(sweden.my2_collect_ssn)
        self.assertFalse(seychelles.my2_collect_ssn)
        for company in self.env["res.company"].search([]):
            with self.subTest(company=company.name):
                self.assertEqual(
                    company.my2_collect_ssn,
                    company.country_id.code in SSN_REPORTING_COUNTRIES,
                )

    def test_finland_is_not_a_reporting_country(self):
        """Finland's donation deduction covers gifts to universities only,
        so a Finnish entity has no report to file and therefore no lawful
        basis to ask for a henkilotunnus."""
        self.assertNotIn("FI", SSN_REPORTING_COUNTRIES)
