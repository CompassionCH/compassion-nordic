##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import base64
import re
import unittest
import xml.etree.ElementTree as ET
from datetime import date

from stdnum import luhn

from odoo import Command
from odoo.tests import TransactionCase, tagged

KU = "{http://xmls.skatteverket.se/se/skatteverket/ai/komponent/infoForBeskattning/%s}"


def personnummer(birth, serial):
    """Valid YYYYMMDD-NNNN personnummer (the check digit is a Luhn on YYMMDDNNN)."""
    digits = f"{birth:%y%m%d}{serial:03d}"
    return f"{birth:%Y%m%d}-{serial:03d}{luhn.calc_check_digit(digits)}"


@tagged("post_install", "-at_install")
class TestSwedenTaxFile(TransactionCase):
    """KU65 file: individuals and companies, generated as two files."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].search(
            [
                ("partner_id.country_id.code", "=", "SE"),
                ("company_registry", "!=", False),
            ],
            limit=1,
        )
        if not cls.company:
            raise unittest.SkipTest("No Swedish company with a registry number")
        cls.year = date.today().year - 1
        if cls.company.hard_lock_date and cls.company.hard_lock_date.year >= cls.year:
            raise unittest.SkipTest("The tax year is hard-locked")
        cls.company.fiscalyear_lock_date = False
        env = cls.env(
            context=dict(cls.env.context, allowed_company_ids=cls.company.ids)
        )
        cls.env = env
        accounts = env["account.account"].with_company(cls.company)
        cls.income = accounts.search(
            [
                ("company_ids", "in", cls.company.id),
                ("account_type", "=", "income"),
                ("is_off_balance", "=", False),
            ],
            limit=1,
        )
        cls.counterpart = accounts.search(
            [
                ("company_ids", "in", cls.company.id),
                ("account_type", "=", "asset_current"),
            ],
            limit=1,
        )
        cls.journal = env["account.journal"].search(
            [("company_id", "=", cls.company.id), ("type", "=", "general")], limit=1
        )
        partners = env["res.partner"].with_context(no_vat_validation=True)
        cls.adult = partners.create(
            {
                "name": "T3700 Adult",
                "ref": "T3700-1",
                "social_sec_nr": personnummer(date(1981, 12, 18), 987),
            }
        )
        cls.below_year = partners.create(
            {
                "name": "T3700 Below year",
                "ref": "T3700-2",
                "social_sec_nr": personnummer(date(1979, 5, 4), 123),
            }
        )
        cls.split_day = partners.create(
            {
                "name": "T3700 Split day",
                "ref": "T3700-3",
                "social_sec_nr": personnummer(date(1990, 3, 10), 456),
            }
        )
        cls.company_ok = partners.create(
            {
                "name": "T3700 AB",
                "ref": "T3700-11",
                "is_company": True,
                "vat": "556036-0793",
            }
        )
        cls.company_small = partners.create(
            {
                "name": "T3700 Small AB",
                "ref": "T3700-12",
                "is_company": True,
                "vat": "556036-0793",
            }
        )
        cls.company_bad = partners.create(
            {
                "name": "T3700 Bad AB",
                "ref": "T3700-13",
                "is_company": True,
                "vat": "123",
            }
        )
        # One move per day (creating moves is slow on a big database).
        # Day 1 / day 2 gifts; several lines of a day add up.
        cls._post_day(
            1,
            [
                (cls.adult, 1000),
                (cls.below_year, 900),
                (cls.split_day, 150),
                (cls.split_day, 150),  # 300 that day: above 200 only together
                (cls.company_ok, 2500),
                (cls.company_small, 1500),
                (cls.company_bad, 5000),
            ],
        )
        cls._post_day(
            2,
            [
                (cls.adult, 1100),  # 2100 a year
                (cls.below_year, 900),  # 1800 a year
                (cls.split_day, 1900),  # 2200 a year with day 1
                (cls.company_ok, 1999),  # below 2000 that day
                (cls.company_small, 1500),  # 3000 a year, never 2000 a day
            ],
        )

    @classmethod
    def _post_day(cls, day, gifts):
        """Post one move on that day, one income line per (partner, amount)."""
        lines = [
            Command.create(
                {
                    "account_id": cls.income.id,
                    "partner_id": partner.id,
                    "credit": amount,
                    "name": "T3700 gift",
                }
            )
            for partner, amount in gifts
        ]
        lines.append(
            Command.create(
                {
                    "account_id": cls.counterpart.id,
                    "debit": sum(amount for _partner, amount in gifts),
                    "name": "T3700 gifts",
                }
            )
        )
        cls.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": cls.journal.id,
                "date": date(cls.year, 1, day),
                "line_ids": lines,
            }
        ).action_post()

    def _generate(self, donor_type):
        """Run the wizard and return {field 215: gift amount} of our donors."""
        wizard = self.env["generate.tax.wizard"].create(
            {"tax_year": str(self.year), "se_donor_type": donor_type}
        )
        action = wizard.generate_tax()
        attachment = self.env["ir.attachment"].browse(
            int(re.search(r"/web/content/(\d+)", action["url"]).group(1))
        )
        root = ET.fromstring(base64.b64decode(attachment.datas))
        ku = KU % f"{wizard.xml_version:.1f}"
        result = {}
        for ku65 in root.iter(f"{ku}KU65"):
            if ku65.find(f"{ku}Specifikationsnummer").text.startswith("T3700-"):
                result[ku65.find(f"{ku}InkomsttagareKU65/{ku}Inkomsttagare").text] = (
                    ku65.find(f"{ku}MottagetGavobelopp").text
                )
        return attachment, result

    def _state(self, partner):
        return (
            self.env["res.partner.tax.file.result"]
            .search([("partner_id", "=", partner.id)])
            .state
        )

    def test_individuals(self):
        attachment, result = self._generate("individual")
        self.assertTrue(attachment.name.startswith("Tax_"))
        self.assertNotIn("companies", attachment.name)
        # 12-digit personnummer with century; companies are not in this file
        self.assertEqual(
            result,
            {
                self.adult.social_sec_nr.replace("-", ""): "2100",
                self.split_day.social_sec_nr.replace("-", ""): "2200",
            },
        )
        self.assertEqual(self._state(self.adult), "valid")
        self.assertFalse(self._state(self.below_year), "Below 2000 a year")
        self.assertFalse(self._state(self.company_ok))

    def test_companies(self):
        attachment, result = self._generate("company")
        self.assertTrue(attachment.name.startswith("Tax_companies_"))
        # 16 + organisation number, in the same field as the personnummer
        self.assertEqual(result, {"165560360793": "2500"})
        self.assertEqual(self._state(self.company_ok), "valid")
        self.assertEqual(self._state(self.company_bad), "invalid_vat")
        self.assertFalse(self._state(self.company_small), "Never 2000 in a day")
        self.assertFalse(self._state(self.adult))

    def test_latest_schema_version(self):
        wizard = self.env["generate.tax.wizard"].create({"tax_year": str(self.year)})
        self.assertEqual(wizard.xml_version, 12)

    def test_personnummer_without_century(self):
        wizard = self.env["generate.tax.wizard"]
        self.assertEqual(
            wizard._se_personnummer_identifier("811218-9876"), "198112189876"
        )
        self.assertEqual(
            wizard._se_personnummer_identifier("191218+9873"), "191912189873"
        )
        self.assertIsNone(wizard._se_personnummer_identifier("811218-9875"))

    def test_organisation_number_formats(self):
        wizard = self.env["generate.tax.wizard"]
        self.assertEqual(wizard._se_orgnr_identifier("5560360793"), "165560360793")
        self.assertEqual(wizard._se_orgnr_identifier("SE556036079301"), "165560360793")
        # Sole trader: its organisation number is the owner's personnummer
        self.assertEqual(wizard._se_orgnr_identifier("811218-9876"), "198112189876")
        self.assertIsNone(wizard._se_orgnr_identifier("123"))
