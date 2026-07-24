from odoo import api, models
from odoo.tools import str2bool

from ..hooks import PROVIDER_CODE


class ContractGroup(models.Model):
    _inherit = "recurring.contract.group"

    @api.model
    def _digital_charge_context(self, invoice):
        """Opt Adyen off-session charges into Auto Rescue.

        Refused charges are then retried by Adyen on its own schedule.
        The opt-in is off until my_compassion_nordic.auto_rescue_enabled
        is set to True, which must only happen once Adyen has enabled
        the feature on the merchant account.
        """
        context = super()._digital_charge_context(invoice)
        provider = (
            invoice.line_ids.contract_id.group_id.payment_mode_id.payment_provider_id
        )
        if provider.code != PROVIDER_CODE:
            return context
        params = self.env["ir.config_parameter"].sudo()
        if not str2bool(
            params.get_param("my_compassion_nordic.auto_rescue_enabled", "False")
        ):
            return context
        return {
            **context,
            "my2_auto_rescue": {
                "maxDaysToRescue": int(
                    params.get_param("my_compassion_nordic.max_days_to_rescue", "21")
                ),
                "merchantOrderReference": invoice.name,
            },
        }
