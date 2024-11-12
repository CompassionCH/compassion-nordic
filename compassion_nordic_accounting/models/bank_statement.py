from odoo import api, models


class BankStatement(models.Model):
    _inherit = "account.bank.statement"

    @api.model_create_multi
    def create(self, values):
        if self.env.context.get("from_large_import"):
            return self.with_context(from_large_import=False).create_and_post(
                values, self.env.context.get("auto_post"))
        else:
            return super().create(values)

    def create_and_post(self, values, auto_post=False):
        statement = self.create(values)
        if auto_post:
            statement.button_post()
        return statement
