from dateutil.relativedelta import relativedelta

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    is_late_payment = fields.Boolean(compute="_compute_is_late_payment", store=True)

    def _compute_is_late_payment(self):
        for record in self:
            if record.last_payment:
                one_month_from_date = record.date + relativedelta(months=1)
                record.is_late_payment = (
                    one_month_from_date.replace(day=1) <= record.last_payment
                )

    def update_open_invoices(self, updt_val):
        """
        It updates the invoices in self with the value of updt_val.
        The function acts as a filter to make sure we perform valid updates
        on open invoices in the past , present or future.

        :param updt_val: a dictionary of invoices values with the invoice name
        which refer to another dictionary of values for that invoice name
        """

        # Filter out unpaid invoices.
        for invoice in self.filtered(
            lambda i: i.state != "cancel"
            and i.payment_state != "paid"
            and (
                i.payment_order_id.state in ["draft", "open"] or not i.payment_order_id
            )
        ):
            if updt_val.get(invoice.name):
                val_to_updt = updt_val[invoice.name]
                if (
                    "partner_id" in val_to_updt
                    and val_to_updt["partner_id"] == invoice.partner_id.id
                ):
                    del val_to_updt["partner_id"]
                    if not val_to_updt:
                        continue
                # In case we modify the amount we want to test if the amount is zero
                invoice.button_draft()
                # Perform th update
                invoice.update(val_to_updt)
                if invoice.amount_total:
                    invoice.action_post()
                else:
                    invoice.button_cancel()
