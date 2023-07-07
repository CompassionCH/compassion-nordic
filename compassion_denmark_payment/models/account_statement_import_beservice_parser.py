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
from .. import beservice

from odoo import _, api, models, fields

_logger = logging.getLogger(__name__)

try:
    from csv import reader
except (ImportError, IOError) as err:
    _logger.error(err)


class AccountBankStatementImportPayPalParser(models.TransientModel):
    _name = "account.statement.import.beservice.parser"
    _description = "Account Statement Import Betalingsservice Parser "

    @api.model
    def parse(self, data_file):
        file_data = beservice.parse(StringIO(data_file.decode("iso-8859-1")).read())
        Journal = self.env["account.journal"]
        journal = Journal.search([
            ("payment_mode_id.initiating_party_scheme", "=", file_data.data_supplier_number)
        ], limit=1) or Journal.browse(self.env.context.get("journal_id"))
        currency_code = (journal.currency_id or journal.company_id.currency_id).name
        account_number = journal.bank_account_id.acc_number
        name = journal.code + str(fields.Datetime.now())
        lines = [a for a in self._calculate_lines(file_data.sections[0]) if
                 a.transaction_code != beservice.TransactionCode.AUTOMATED_PAYMENT_COMPLETED]
        if not lines:
            return currency_code, account_number, [{"name": name, "transactions": []}]
        date = file_data.sections[0].section_date
        transactions = list(
            itertools.chain.from_iterable(
                map(lambda line: self._convert_line_to_transactions(line), lines)
            )
        )
        return {
            "name": name,
            "date": date,
            "account_number": account_number,
            "transactions": transactions,
        }

    @staticmethod
    def _calculate_lines(data):
        lines = []
        for li in data.information_list:
            lines.append(li)
        return lines

    @api.model
    def _convert_line_to_transactions(self, line: beservice.PaymentInformation):
        pay_ord_id, pay_trx_id, pay_trx_ref, empty = line.reference.split("_")
        payment = self.env["account.payment"].browse(int(pay_trx_id))
        gross_amount = line.amount
        res = self.env['recurring.contract.group'].search([('ref', '=', line.mandate_number)])
        return [{
            "partner_id": res.partner_id.id,
            "amount": str(gross_amount),
            "date": line.info_date,
            "concept": line.mandate_number,
            "reference": payment.move_id.name,
            "reason_code": line.transaction_code.value,
            "raw_import_data": line,
        }]
