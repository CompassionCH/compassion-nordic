from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_aml_default_display_name_list(self):
        # Communication is useful for reconciling the bank return
        communication = self.payment_line_ids.mapped("communication")
        if len(communication) == 1:
            return [("label", communication[0])]
        return super()._get_aml_default_display_name_list()
