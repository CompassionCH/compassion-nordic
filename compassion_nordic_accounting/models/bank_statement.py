from odoo import models


class BankStatement(models.Model):
    _inherit = "account.bank.statement"

    def create(self, values):
        if self.env.context.get("from_large_import"):
            self.with_context(from_large_import=False).with_delay().create_and_post(
                values, self.env.context.get("auto_post"))
            return self
        else:
            return super().create(values)

    def create_and_post(self, values, auto_post=False):
        statement = self.create(values)
        if auto_post:
            statement.button_post()
        return statement
