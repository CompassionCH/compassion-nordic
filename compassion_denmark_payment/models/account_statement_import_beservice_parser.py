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
from io import StringIO
from os import path

from odoo import _, api, models

from . import beservice

_logger = logging.getLogger(__name__)


class AccountBankStatementImportPayPalParser(models.TransientModel):
    _name = "account.statement.import.beservice.parser"
    _description = "Account Statement Import Betalingsservice Parser "

    @api.model
    def parse(self, data_file, filename):
        file_data = beservice.parse(StringIO(data_file.decode("iso-8859-1")).read())

        journal = self.env["account.journal"].browse(self.env.context.get("journal_id"))

        currency_code = (journal.currency_id or journal.company_id.currency_id).name

        account_number = journal.bank_account_id.acc_number

        name = _("%s: %s") % (
            journal.code,
            path.basename(filename),
        )
        lines = [
            a
            for a in self._calculate_lines(file_data.sections[0])
            if a.transaction_code
            == beservice.TransactionCode.AUTOMATED_PAYMENT_COMPLETED
        ]
        if not lines:
            return currency_code, account_number, [{"name": name, "transactions": []}]

        date = file_data.sections[0].section_date

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
                    "balance_start": float(-file_data.sections[0].get_net_amount()),
                    "balance_end_real": float(0),
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
        details = line.reference
        gross_amount = line.amount
        #
        res = self.env["recurring.contract.group"].search(
            [("ref", "=", line.mandate_number)]
        )
        transaction = {
            "partner_id": res.partner_id.id,
            "amount": str(gross_amount),
            "date": line.info_date,
            "ref": line.mandate_number,
            "payment_ref": details,
        }
        transactions.append(transaction)

        return transactions
