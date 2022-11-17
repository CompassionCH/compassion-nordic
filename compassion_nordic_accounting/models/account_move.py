from odoo import api, models, fields


class AccountMove(models.Model):
    # CP-207 This reduces the depends of the field payment_state in order to reduce computation frequency
    # resulting in increased performance. However it might introduce cases where the
    # fields are not computed and have inconsistent states.
    _inherit = "account.move"

    payment_state = fields.Selection(compute="_compute_amount_custom")
    amount_untaxed = fields.Monetary(compute='_compute_amount_custom')
    amount_tax = fields.Monetary(compute='_compute_amount_custom')
    amount_total = fields.Monetary(compute='_compute_amount_custom')
    amount_residual = fields.Monetary(compute='_compute_amount_custom')
    amount_untaxed_signed = fields.Monetary(compute='_compute_amount_custom')
    amount_tax_signed = fields.Monetary(compute='_compute_amount_custom')
    amount_total_signed = fields.Monetary(compute='_compute_amount_custom')
    amount_residual_signed = fields.Monetary(compute='_compute_amount_custom')

    # Reduce the depends list of original source code which was producing the compute
    # of a lot of unrelated move lines when reconciling two items.
    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        # 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        # 'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        # 'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        # 'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount_custom(self):
        self._compute_amount()
