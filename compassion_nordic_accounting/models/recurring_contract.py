##############################################################################
#
#    Copyright (C) 2014-2022 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Robin Berguerand
#
#    The licence is in the file __manifest__.py
#
##############################################################################

from odoo import api, fields, models, _

class RecurringContract(models.Model):
    _inherit = "recurring.contract"

    company_id = fields.Many2one(
        # Show selection of all companies except Norden (id = 1)
        domain="[('id', '!=', 1)]",
    )

    @api.onchange('partner_id')
    def change_price(self):
        if self.partner_id.property_product_pricelist.exists():
            for f in self.contract_line_ids:
                f.recompute_price(self.partner_id.property_product_pricelist)

    def _filter_open_invoices_to_cancel(self):
        """
        Exclude Direct Debit Order invoices, to avoid cancelling invoices that are being paid.
        :return: <account.move.line> recordset
        """
        invoice_lines = super()._filter_open_invoices_to_cancel()
        modified_orders = self.env["account.payment.order"]
        for move_line in invoice_lines:
            payment_line = self.env["account.payment.line"].search([
                ("move_line_id.move_id", "=", move_line.move_id.id),
                ("amount_currency", ">=", -move_line.amount_currency),
                ("state", "!=", "cancel")
            ], order="amount_currency ASC", limit=1)
            if payment_line.state == "draft":
                # As the order is not yet validated, we can simply cancel the payment
                modified_orders |= payment_line.order_id
                if abs(payment_line.amount_currency) > abs(move_line.amount_currency):
                    payment_line.amount_currency -= abs(move_line.amount_currency)
                else:
                    payment_line.unlink()
            elif payment_line:
                invoice_lines -= move_line
        for order in modified_orders:
            for contract in self:
                order.message_post(
                    body=f"Contract "
                         f"<a href='{contract._notify_get_action_link('view')}'>{contract.name}</a> was terminated. "
                         f"Payment lines were adapted.")
        return invoice_lines
