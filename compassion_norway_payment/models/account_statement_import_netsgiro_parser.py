##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#    The licence is in the file __manifest__.py
#
##############################################################################

import itertools
import logging
from decimal import Decimal
from io import StringIO
from os import path

import netsgiro

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
        date = file_data.assignments[0].date
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
                    "balance_start": float(-file_data.assignments[0].get_total_amount()),
                    "balance_end_real": float(0),
                    "transactions": transactions,
                }
            ],
        )

    @api.model
    def _convert_line_to_transactions(self, line: netsgiro.Transaction):
        transactions = []
        details = line.reference
        gross_amount = line.amount
        res = self.env['recurring.contract.group'].search([('ref', '=', line.kid)])
        bank_account = res.partner_id.bank_ids
        transaction = {
            "partner_id": res.partner_id.id,
            "amount": str(gross_amount),
            "date": line.date,
            "ref": line.kid,
            "account_number": bank_account.acc_number,
            "payment_ref":  details or ""
        }
        transactions.append(transaction)

        return transactions
