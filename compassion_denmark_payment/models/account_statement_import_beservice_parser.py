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
from .. import beservice
from pytz import timezone, utc

from odoo import _, api, models

_logger = logging.getLogger(__name__)

try:
    from csv import reader
except (ImportError, IOError) as err:
    _logger.error(err)


def _data_dict_constructor(header):
    required_list = [
        "date_column",
        "time_column",
        "tz_column",
        "name_column",
        "currency_column",
        "gross_column",
        "fee_column",
        "balance_column",
        "transaction_id_column!",
    ]
    optional_list = [
        "description_column",
        "type_column",
        "from_email_address_column",
        "to_email_address_column",
        "invoice_id_column",
        "subject_column",
        "note_column",
        "bank_name_column",
        "bank_account_column",
    ]
    data_dict = {}
    for key in required_list:
        data_dict[key] = header.index(getattr(mapping, key))
    for key in optional_list:
        try:
            data_dict[key] = header.index(getattr(mapping, key))
        except ValueError:
            data_dict[key] = None
    return data_dict


class AccountBankStatementImportPayPalParser(models.TransientModel):
    _name = "account.statement.import.beservice.parser"
    _description = "Account Statement Import Betalingsservice Parser "

    @api.model
    def parse(self, data_file, filename):
        journal = self.env["account.journal"].browse(self.env.context.get("journal_id"))
        currency_code = (journal.currency_id or journal.company_id.currency_id).name
        account_number = journal.bank_account_id.acc_number

        name = _("%s: %s") % (
            journal.code,
            path.basename(filename),
        )
        file_data = beservice.parse(StringIO(data_file.decode("iso-8859-1")).read())
        lines = self._calculate_lines(file_data.sections[0])
        sec = file_data.sections[0]
        if not lines:
            return currency_code, account_number, [{"name": name, "transactions": []}]
        balance_end = file_data.sections[0].get_net_amount()
        date = file_data.sections[0].section_date

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
    def _convert_line_to_transactions(self, line: beservice.PaymentInformation):
        transactions = []
        transaction_id = line.debtor_group_number
        details = line.reference
        gross_amount = line.amount
        #
        bank_account = self.env['res.partner.bank'].search([('acc_number', '=', str(line.mandate_number))])
        transaction = {
            "name": details or "",
            "amount": str(gross_amount),
            "date": line.info_date,
            "payment_ref": line.mandate_number,
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
