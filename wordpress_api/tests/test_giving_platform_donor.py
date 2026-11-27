from odoo.tests import TransactionCase, tagged

from ..fastapi.giving_platform_pydantic_models import DonationPostModel

# Swedish numbers reserved for fiction (PTS): 070-174 06 05 to 070-174 06 99
NUMBER = "+46701740605"
OTHER_NUMBER = "+46701740606"


@tagged("post_install", "-at_install")
class TestGivingPlatformDonor(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sweden = cls.env.ref("base.se")
        cls.company = cls.env["res.company"].create(
            {"name": "Test Compassion Sverige", "country_id": cls.sweden.id}
        )
        cls.Partner = cls.env["res.partner"].with_company(cls.company)

    def _donation(self, **values):
        return DonationPostModel(
            donation_id=1,
            payment_request_id="pi_test",
            currency_code="SEK",
            amount=100,
            payment_provider="Swish",
            fund_id=1,
            **values,
        )

    def _donor(self, **values):
        move = self.env["account.move"].new({"company_id": self.company.id})
        return move._giving_platform_partner(self._donation(**values))

    def test_phone_in_any_format_finds_the_partner(self):
        partner = self.Partner.create(
            {"name": "Anna Svensson", "phone": "+46 70 174 06 05"}
        )
        for phone in (
            "0701740605",
            "070-174 06 05",
            "+46701740605",
            "0046701740605",
            "46701740605",
        ):
            with self.subTest(phone=phone):
                self.assertEqual(
                    self.Partner.match_create_partner(phone=phone), partner
                )

    def test_partner_with_a_local_number_is_found(self):
        partner = self.Partner.create(
            {"name": "Anna Svensson", "phone": "070-174 06 05"}
        )
        self.assertEqual(self.Partner.match_create_partner(phone=NUMBER), partner)

    def test_two_donations_with_a_local_number_make_one_partner(self):
        """T3732: the partner created by the first donation stores the
        international number; the second donation must find it."""
        first = self.Partner.match_create_partner(phone="0701740605")
        self.assertEqual(first.phone, NUMBER)
        second = self.Partner.match_create_partner(phone="0701740605")
        self.assertEqual(second, first)

    def test_number_found_in_mobile_or_phone(self):
        partner = self.Partner.create(
            {
                "name": "Anna Svensson",
                "mobile": "+46 70 174 06 05",
                "phone": "0701740606",
            }
        )
        self.assertEqual(self.Partner.match_create_partner(phone=NUMBER), partner)
        self.assertEqual(self.Partner.match_create_partner(phone=OTHER_NUMBER), partner)

    def test_part_of_a_number_does_not_match(self):
        partner = self.Partner.create({"name": "Anna Svensson", "phone": NUMBER})
        self.assertNotEqual(self.Partner.match_create_partner(phone="1740605"), partner)

    def test_new_donor_with_names_and_address(self):
        donor = self._donor(
            donor_name="Feffe",
            donor_first_name="Fredrik",
            donor_last_name=" Testsson ",
            donor_phone="0701740605",
            donor_email="fredrik@example.com",
            donor_street="Kalendervägen 1",
            donor_zip="352 60",
            donor_city="Växjö",
            donor_country_code="se",
        )
        self.assertEqual(
            (donor.firstname, donor.lastname, donor.phone, donor.email),
            ("Fredrik", "Testsson", NUMBER, "fredrik@example.com"),
        )
        self.assertEqual(
            (donor.street, donor.zip, donor.city, donor.country_id),
            ("Kalendervägen 1", "352 60", "Växjö", self.sweden),
        )

    def test_new_donor_with_a_full_name_only(self):
        donor = self._donor(donor_name="Anna Svensson", donor_phone=NUMBER)
        self.assertEqual((donor.firstname, donor.lastname), ("Anna", "Svensson"))

    def test_known_donor_keeps_name_and_gets_missing_address(self):
        partner = self.Partner.create({"name": "Anna Svensson", "phone": NUMBER})
        donor = self._donor(
            donor_first_name="Annie",
            donor_last_name="S",
            donor_phone="0701740605",
            donor_street="Storgatan 1",
            donor_zip="111 22",
            donor_city="Stockholm",
            donor_country_code="SE",
        )
        self.assertEqual(donor, partner)
        self.assertEqual(partner.name, "Anna Svensson")
        self.assertEqual(
            (partner.street, partner.zip, partner.city, partner.country_id),
            ("Storgatan 1", "111 22", "Stockholm", self.sweden),
        )

    def test_known_donor_keeps_its_address(self):
        partner = self.Partner.create(
            {
                "name": "Anna Svensson",
                "phone": NUMBER,
                "street": "Storgatan 1",
                "zip": "111 22",
                "city": "Stockholm",
            }
        )
        self._donor(
            donor_phone=NUMBER,
            donor_street="Lillgatan 2",
            donor_zip="222 33",
            donor_city="Lund",
        )
        self.assertEqual(
            (partner.street, partner.zip, partner.city),
            ("Storgatan 1", "111 22", "Stockholm"),
        )

    def test_country_code_reads_a_national_number(self):
        donor = self._donor(donor_phone="412 34 567", donor_country_code="NO")
        self.assertEqual(donor.phone, "+4741234567")
        self.assertEqual(donor.country_id, self.env.ref("base.no"))

    def test_unknown_country_code_is_ignored(self):
        donor = self._donor(donor_phone="0701740605", donor_country_code="XX")
        self.assertFalse(donor.country_id)
        # the company's country reads the number
        self.assertEqual(donor.phone, NUMBER)

    def test_known_donor_with_only_a_second_line_keeps_it(self):
        """A second address line alone is an address: the new one is not
        mixed with it."""
        partner = self.Partner.create(
            {"name": "Anna Svensson", "phone": NUMBER, "street2": "c/o Berg"}
        )
        self._donor(
            donor_phone=NUMBER,
            donor_street="Storgatan 1",
            donor_zip="111 22",
            donor_city="Stockholm",
        )
        self.assertEqual(
            (partner.street, partner.street2, partner.zip, partner.city),
            (False, "c/o Berg", False, False),
        )
