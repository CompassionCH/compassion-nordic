from odoo import models, api


class AccountPayment(models.Model):
    _name = 'account.payment'
    _inherit = 'account.payment'

    @api.model
    def create(self, vals_list):
        if self.env.context.get('skip_payment_line', False):
            return self
        else:
            return super().create(vals_list)
