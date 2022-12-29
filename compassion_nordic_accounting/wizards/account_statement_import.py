##############################################################################
#
#    Copyright (C) 2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#
#    The licence is in the file __manifest__.py
#
##############################################################################
import logging
import numpy

from odoo import models, fields, _

_logger = logging.getLogger(__name__)


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    large_file_import = fields.Boolean(
        help="Use this for large statement files. The process will run in the background so that you can continue "
             "to work in the meantime.",
        default=True
    )
    maximum_lines = fields.Integer(
        help="Use this to split large statements into multiple smaller ones. It can be useful for speeding up "
             "the reconcile process afterwards. (use 0 for keeping it all together)",
        default=500
    )
    auto_post = fields.Boolean(
        help="Post automatically the statement after import",
        default=True)

    def import_file_button(self):
        if self.large_file_import:
            # Import in background and return a message.
            self.with_delay()._import_file_with_journal(self.env.context.get("journal_id"))
            self.env.user.notify_success(message=_(
                "Import job launched. Come back in a few minutes to check your statements."))
        else:
            return_action = super().import_file_button()
            # Lauch a job for bank statements auto reconciliations
            statements = self.env["account.bank.statement"].browse(return_action["res_id"])
            statements.with_delay().auto_reconcile()
            return return_action

    def _import_file_with_journal(self, journal_id):
        result = self.with_context(
            journal_id=journal_id, from_large_import=True, auto_post=self.auto_post)._import_file()
        # Lauch a job for bank statements auto reconciliations
        statements = self.env["account.bank.statement"].browse(result["statement_ids"])
        statements.with_delay().auto_reconcile()
        return result

    def import_single_file(self, file_data, result):
        if self.large_file_import and self.maximum_lines:
            parsing_data = self.with_context(active_id=self.ids[0])._parse_file(file_data)
            if not isinstance(parsing_data, list):  # for backward compatibility
                parsing_data = [parsing_data]

            nb_statements = 0
            for line in parsing_data:
                # Split statements that have more lines than the maximum allowed.
                to_remove = []  # statements to replace
                to_add = []  # new split statements
                statements = line[2]
                for statement in statements:
                    statement_lines = statement.get("transactions", [])
                    if len(statement_lines) > self.maximum_lines:
                        to_remove.append(statement)
                        to_add.extend(self._split_statement(statement))
                for s in to_remove:
                    statements.remove(s)
                statements.extend(to_add)
                nb_statements += len(statements)

            _logger.info(
                "Bank statement file %s is split into %d bank statements",
                self.statement_filename,
                nb_statements,
            )
            i = 0
            for single_statement_data in parsing_data:
                i += 1
                _logger.debug(
                    "account %d: single_statement_data=%s", i, single_statement_data
                )
                self.import_single_statement(single_statement_data, result)
        else:
            super().import_single_file(file_data, result)

    def _split_statement(self, stmts_vals):
        res = []
        balance_start = stmts_vals.get("balance_start", 0.0)
        # We divide the transactions into chunks for creating multiple bank stmts_valss
        lines = stmts_vals.get("transactions")
        for chunk in numpy.array_split(lines, (len(lines) // self.maximum_lines) or 1):
            new_stmts_vals = stmts_vals.copy()
            new_stmts_vals["balance_start"] = balance_start
            new_stmts_vals["transactions"] = chunk.tolist()
            balance_end = balance_start + sum(map(lambda l: float(l["amount"]), chunk))
            new_stmts_vals["balance_end_real"] = balance_end
            res.append(new_stmts_vals)
            balance_start = balance_end
        return res
