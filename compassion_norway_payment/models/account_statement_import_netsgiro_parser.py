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
        assignement_dict_list = []
        for assignement in file_data.assignments:
            lines = assignement.transactions
            if not lines:
                assignement_dict_list.append({"name": name, "transactions": []})
                continue
            date = assignement.date
            transactions = list(
                itertools.chain.from_iterable(
                    map(lambda line: self._convert_line_to_transactions(line), lines)
                )
            )
            assignement_dict_list.append(
                    {
                        "name": name,
                        "date": date,
                        "balance_start": float(-assignement.get_total_amount()),
                        "balance_end_real": float(0),
                        "transactions": transactions,
                    })
        return (
            currency_code,
            account_number,
            [assignement_dict for assignement_dict in assignement_dict_list],
        )

    @api.model
    def _convert_line_to_transactions(self, line: netsgiro.Transaction):
        pay_opt = self.env['recurring.contract.group'].search([('ref', '=', line.kid)])
        transaction = {
            "partner_id": pay_opt.partner_id.id,
            "amount": str(line.amount),
            "date": line.date,
            "ref": line.kid,
            "account_number": pay_opt.partner_id.bank_ids[:1].acc_number,
            "payment_ref": line.reference or ""
        }
        return [transaction]
