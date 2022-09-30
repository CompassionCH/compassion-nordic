# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import itertools
import logging
from io import StringIO
from os import path

from odoo import _, api, models
from .. import bggiro

_logger = logging.getLogger(__name__)

try:
    from csv import reader
except (ImportError, IOError) as err:
    _logger.error(err)


class AccountBankStatementImportPayPalParser(models.TransientModel):
    _name = "account.statement.import.bggiro.parser"
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
        file_data = bggiro.parse(StringIO(data_file.decode("iso-8859-1")).read())
        lines = [p for p in file_data.payments if p.payment_status_code == bggiro.PaymentStatus.APPROVED]
        if not lines:
            return currency_code, account_number, [{"name": name, "transactions": []}]
        balance_end = file_data.get_total_amount_incoming()
        date = file_data.date_written
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

    @api.model
    def _convert_line_to_transactions(self, line: bggiro.Payment):
        transactions = []
        details = line.reference
        gross_amount = line.amount
        res = self.env['recurring.contract.group'].search([('ref', '=', line.payer_number)], limit=1)
        bank_account = res.partner_id.bank_ids
        transaction = {
            "partner_id": res.partner_id.id,
            "amount": str(gross_amount),
            "date": line.payment_date,
            "account_number": bank_account.acc_number,
            "ref": line.payer_number,
            "payment_ref": details or ""
        }
        transactions.append(transaction)

        return transactions
