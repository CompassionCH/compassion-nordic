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

from odoo import Command
from odoo.tests import TransactionCase, tagged

NS = "{urn:ske:fastsetting:innsamling:gavefrivilligorganisasjon:v2}"


@tagged("post_install", "-at_install")
class TestNorwayTaxFile(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].search(
            [
                ("partner_id.country_id.code", "=", "NO"),
                ("company_registry", "!=", False),
            ],
            limit=1,
        )
        if not cls.company:
            raise unittest.SkipTest("No Norwegian company with a registry number")
        cls.year = date.today().year - 1
        if cls.company.hard_lock_date and cls.company.hard_lock_date.year >= cls.year:
            raise unittest.SkipTest("The tax year is hard-locked")
        cls.company.fiscalyear_lock_date = False
        cls.env = cls.env(
            context=dict(cls.env.context, allowed_company_ids=cls.company.ids)
        )
        accounts = cls.env["account.account"]
        income = accounts.search(
            [
                ("company_ids", "in", cls.company.id),
                ("account_type", "=", "income"),
                ("is_off_balance", "=", False),
            ],
            limit=1,
        )
        counterpart = accounts.search(
            [
                ("company_ids", "in", cls.company.id),
                ("account_type", "=", "asset_current"),
            ],
            limit=1,
        )
        journal = cls.env["account.journal"].search(
            [("company_id", "=", cls.company.id), ("type", "=", "general")], limit=1
        )
        partners = cls.env["res.partner"].with_context(no_vat_validation=True)
        cls.person = partners.create(
            {"name": "T3700 Ola", "social_sec_nr": "15108695088"}
        )
        cls.organisation = partners.create(
            {"name": "T3700 AS", "is_company": True, "vat": "988 077 917"}
        )
        gifts = [(cls.person, 600), (cls.organisation, 9000)]
        lines = [
            Command.create(
                {
                    "account_id": income.id,
                    "partner_id": partner.id,
                    "credit": amount,
                    "name": "T3700 gift",
                }
            )
            for partner, amount in gifts
        ]
        lines.append(
            Command.create(
                {"account_id": counterpart.id, "debit": 9600, "name": "T3700 gifts"}
            )
        )
        cls.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": journal.id,
                "date": date(cls.year, 1, 2),
                "line_ids": lines,
            }
        ).action_post()

    def test_donor_identifier_tags(self):
        """A company goes in organisasjonsnummer, a person in foedselsnummer."""
        wizard = self.env["generate.tax.wizard"].create({"tax_year": str(self.year)})
        action = wizard.generate_tax()
        attachment = self.env["ir.attachment"].browse(
            int(re.search(r"/web/content/(\d+)", action["url"]).group(1))
        )
        root = ET.fromstring(base64.b64decode(attachment.datas))
        owners = {
            owner.find(f"{NS}navn").text: [
                (child.tag.replace(NS, ""), child.text)
                for child in owner
                if child.tag != f"{NS}navn"
            ]
            for owner in root.iter(f"{NS}oppgaveeier")
            if owner.find(f"{NS}navn").text.startswith("T3700")
        }
        self.assertEqual(
            owners,
            {
                "T3700 Ola": [("foedselsnummer", "15108695088")],
                "T3700 AS": [("organisasjonsnummer", "988077917")],
            },
        )
