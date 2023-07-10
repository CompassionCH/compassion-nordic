##############################################################################
#
#    Copyright (C) 2015-2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Robin Berguerand <robin.berguerand@gmail.com>
#
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging
from io import StringIO
from os import path

from odoo import _, api, models, fields
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
    def parse(self, data_file):
        file_data = bggiro.parse(StringIO(data_file.decode("iso-8859-1")).read())
        Journal = self.env["account.journal"]
        journal = Journal.search([
            ("payment_mode_id.initiating_party_identifier", "=", file_data.customer_number)
        ], limit=1) or Journal.browse(self.env.context.get("journal_id"))
        currency_code = (journal.currency_id or journal.company_id.currency_id).name
        account_number = journal.bank_account_id.acc_number
        name = journal.code + str(fields.Datetime.now())
        lines = [p for p in file_data.payments if p.payment_status_code != bggiro.PaymentStatus.APPROVED]
        if not lines:
            return currency_code, account_number, [{"name": name, "transactions": []}]
        date = file_data.date_written
        transactions = list(map(lambda line: self._convert_line_to_transactions(line), lines))
        return {
            "name": name,
            "date": date,
            "account_number": account_number,
            "transactions": transactions,
        }

    @api.model
    def _convert_line_to_transactions(self, line: bggiro.Payment):
        pay_opt = self.env['recurring.contract.group'].search([('ref', '=', line.payer_number)], limit=1)
        payment = self.env["account.payment"].browse(int(line.reference))
        return {
            "partner_id": pay_opt.partner_id.id,
            "amount": str(line.amount),
            "date": line.payment_date,
            "concept": line.reference,
            "reference": payment.move_id.name,
            "reason_code": line.payment_status_code.value,
            "raw_import_data": line
        }
