import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    # CP-207 This reduces the depends of the field payment_state in order to reduce computation frequency
    # resulting in increased performance. However it might introduce cases where the
    # fields are not computed and have inconsistent states.
    _inherit = "account.move"

    payment_state = fields.Selection(compute="_compute_amount_custom")
    amount_untaxed = fields.Monetary(compute="_compute_amount_custom")
    amount_tax = fields.Monetary(compute="_compute_amount_custom")
    amount_total = fields.Monetary(compute="_compute_amount_custom")
    amount_residual = fields.Monetary(compute="_compute_amount_custom")
    amount_untaxed_signed = fields.Monetary(compute="_compute_amount_custom")
    amount_tax_signed = fields.Monetary(compute="_compute_amount_custom")
    amount_total_signed = fields.Monetary(compute="_compute_amount_custom")
    amount_residual_signed = fields.Monetary(compute="_compute_amount_custom")
    is_late_payment = fields.Boolean(compute="_compute_is_late_payment", store=True)

    # Reduce the depends list of original source code which was producing the compute
    # of a lot of unrelated move lines when reconciling two items.
    @api.depends(
        "line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched",
        # 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        # 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        "line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched",
        # 'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        # 'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        "line_ids.debit",
        "line_ids.credit",
        "line_ids.currency_id",
        "line_ids.amount_currency",
        "line_ids.amount_residual",
        "line_ids.amount_residual_currency",
        "line_ids.payment_id.state",
        "line_ids.full_reconcile_id",
    )
    def _compute_amount_custom(self):
        self._compute_amount()

    def _compute_is_late_payment(self):
        for record in self:
            if record.last_payment:
                one_month_from_date = record.date + relativedelta(months=1)
                record.is_late_payment = (
                    one_month_from_date.replace(day=1) <= record.last_payment
                )

    def _prepare_rate_change(self, rate_change_date="2023-05-01"):
        balance_product = self.env.ref("recurring_contract.product_balance_migr")
        invoices = self.search(
            [
                ("invoice_category", "=", "sponsorship"),
                ("state", "=", "posted"),
                ("payment_state", "!=", "paid"),
                ("invoice_date_due", ">=", rate_change_date),
                ("line_ids.product_id", "=", balance_product.id),
            ]
        )
        invoices.button_draft()
        for inv in invoices:
            balance_lines = inv.mapped("invoice_line_ids").filtered(
                lambda l: l.product_id == balance_product
            )
            inv.write(
                {"invoice_line_ids": [(2, line_id) for line_id in balance_lines.ids]}
            )
        invoices.action_post()
        _logger.info("Removed balance on %s invoices", str(len(invoices)))
        return invoices.ids

    def update_open_invoices(self, updt_val):
        """
        It updates the invoices in self with the value of updt_val.
        The function acts as a filter to make sure we perform valid updates
        on open invoices in the past, present or future.

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
                # Perform update
                invoice.update(val_to_updt)
                if invoice.amount_total:
                    invoice.action_post()
                else:
                    invoice.button_cancel()
