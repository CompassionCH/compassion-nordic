# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import base64
import itertools
import logging
from datetime import datetime
from decimal import Decimal
from io import StringIO
from os import path
import netsgiro
from pytz import timezone, utc

from odoo import _, api, models

_logger = logging.getLogger(__name__)

try:
    from csv import reader
except (ImportError, IOError) as err:
    _logger.error(err)


class AccountBankStatementImportPayPalParser(models.TransientModel):
    _name = "account.statement.import.netsgiro.parser"
    _description = "Account Statement Import Netsgiro Parser "

    @api.model
    def parse(self, data_file, filename):
        journal = self.env["account.journal"].browse(self.env.context.get("journal_id"))
        currency_code = (journal.currency_id or journal.company_id.currency_id).name
        account_number = journal.bank_account_id.acc_number

        name = _("%s: %s") % (
            journal.code,
            path.basename(filename),
        )
        file_data = netsgiro.parse(StringIO(data_file.decode("iso-8859-1")).read())
        lines = file_data.assignments[0].transactions
        if not lines:
            return currency_code, account_number, [{"name": name, "transactions": []}]
        balance_end = file_data.assignments[0].get_total_amount()
        date = file_data.assignments[0].date

        # lines = list(sorted(lines, key=lambda line: line["timestamp"]))
        # first_line = lines[0]
        # balance_start = first_line["balance_amount"]
        # balance_start -= first_line["gross_amount"]
        # balance_start -= first_line["fee_amount"]
        # last_line = lines[-1]
        # balance_end = last_line["balance_amount"]

        transactions = list(
            itertools.chain.from_iterable(
                map(lambda line: self._convert_line_to_transactions(line), lines)
            )
        )

        return (
            currency_code,
            account_number,
            [
                {
                    "name": name,
                    "date": date,
                    "balance_start": float(0),
                    "balance_end_real": float(balance_end),
                    "transactions": transactions,
                }
            ],
        )

    @staticmethod
    def _calculate_lines(data):
        lines = []
        for li in data.information_list:
            lines.append(li)
        return lines

    @api.model
    def _convert_line_to_transactions(self, line: netsgiro.Transaction):
        transactions = []
        details = line.reference
        gross_amount = line.amount
        res = self.env['recurring.contract.group'].search([('ref', '=', line.kid)])
        bank_account = res.partner_id.bank_ids
        transaction = {
            "partner_id": res.partner_id.id,
            "name": details or "",
            "amount": str(gross_amount),
            "date": line.date,
            "account_number": bank_account.acc_number,
            "payment_ref": details or ""
        }
        transactions.append(transaction)

        return transactions

    @api.model
    def _parse_decimal(self, value, mapping):
        thousands, decimal = mapping._get_float_separators()
        value = value.replace(thousands, "")
        value = value.replace(decimal, ".")
        return Decimal(value)

    @api.model
    def _normalize_tz(self, value):
        if value in ["PDT", "PST"]:
            return "America/Los_Angeles"
        elif value in ["CET", "CEST"]:
            return "Europe/Paris"
        return value
