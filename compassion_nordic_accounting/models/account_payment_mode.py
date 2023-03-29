from odoo import models, fields


class AccountPaymentMode(models.Model):
    _inherit = 'account.payment.mode'

    skip_payment_line = fields.Boolean(string="Skip payment lines (payment order)",
                                       help="This field defines if we should generate or not the payment transactions in the payment order with this payment mode.",
                                       default=True)
