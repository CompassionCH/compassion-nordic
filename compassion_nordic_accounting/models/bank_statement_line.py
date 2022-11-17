from odoo import models


class BankStatement(models.Model):
    _inherit = "account.bank.statement.line"

    def _check_invoice_state(self, invoice):
        """
        Adapt the invoice to the bank statement amount for correcting exchange rate diffs
        """
        super()._check_invoice_state(invoice)
        difference = invoice.amount_total_signed  - self.amount
        if invoice.amount_total_signed != self.amount:
            invoice_debit_line = invoice.line_ids.filtered("debit")
            self.button_undo_reconciliation()
            # Adapt the invoice amount
            invoice_credit_line = invoice.line_ids.filtered("credit")[:1]
            invoice.button_draft()
            invoice.write({
                "line_ids": [
                    (1, invoice_credit_line.id, {"credit": invoice_credit_line.credit - difference}),
                    (1, invoice_debit_line.id, {"debit": self.amount})
                ]})
            invoice.action_post()
            statement_line = self.move_id.line_ids.filtered("credit")
            statement_line.account_id = invoice_debit_line.account_id
            (invoice_debit_line | statement_line).reconcile()
