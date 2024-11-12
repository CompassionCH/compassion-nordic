from odoo import models, fields


class AccountPaymentOrder(models.Model):
    _inherit = 'account.payment.order'

    skip_payment_line = fields.Boolean(string="Skip payment lines",
                                       help="This field is retrieved from the payment mode associated with this payment order.",
                                       related='payment_mode_id.skip_payment_line',
                                       readonly=True)

    def draft2open(self):
        return super(AccountPaymentOrder, self.with_context(skip_payment_line=self.skip_payment_line)).draft2open()
