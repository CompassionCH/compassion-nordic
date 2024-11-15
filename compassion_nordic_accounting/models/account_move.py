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
