from odoo import models


class RecurringContract(models.Model):
    _inherit = "recurring.contract"

    def _my2_fixit_configs(self):
        """Supply the Nordic charge-failure emails to the generic engine."""
        first = self.env.ref(
            "my_compassion_nordic.config_digital_payment_fixit_first",
            raise_if_not_found=False,
        )
        final = self.env.ref(
            "my_compassion_nordic.config_digital_payment_fixit_final",
            raise_if_not_found=False,
        )
        if not first or not final:
            return super()._my2_fixit_configs()
        return {"first": first, "final": final}

    def _my2_portal_invitation_config(self):
        config = self.env.ref(
            "my_compassion_nordic.config_portal_invitation",
            raise_if_not_found=False,
        )
        return config or super()._my2_portal_invitation_config()
