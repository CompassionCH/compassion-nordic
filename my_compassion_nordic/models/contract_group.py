##############################################################################
#
#    Copyright (C) 2026 Compassion CH (http://www.compassion.ch)
#    @author: Noé Berdoz <nberdoz@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
"""Adyen Auto Rescue hooks of the off-session charge engine.

Everything in this file is Adyen-specific despite the generic model name.
It opts eligible charges into provider-side retries and stretches the
pending timeout to Adyen's rescue window. Charges through any other
provider, Stripe included, fall through every branch untouched and use
the base engine's dunning flow instead.
"""

from odoo import api, models

from ..hooks import ADYEN_CODE


class ContractGroup(models.Model):
    _inherit = "recurring.contract.group"

    @api.model
    def _digital_charge_context(self, invoice):
        """Opt Adyen off-session charges into Auto Rescue.

        Refused charges are then retried by Adyen on its own schedule. The
        opt-in lives on the payment provider because Adyen enables the
        feature per merchant account, and one provider is one account.
        """
        context = super()._digital_charge_context(invoice)
        provider = (
            invoice.line_ids.contract_id.group_id.payment_mode_id.payment_provider_id
        )
        if provider.code != ADYEN_CODE or not provider.adyen_auto_rescue_enabled:
            return context
        return {
            **context,
            "my2_auto_rescue": {
                "maxDaysToRescue": provider.adyen_max_days_to_rescue,
                "merchantOrderReference": invoice.name,
            },
        }

    @api.model
    def _my2_pending_charge_timeout_days(self, provider):
        """Give Adyen its whole rescue window before giving up.

        The extra days cover a late webhook.
        """
        if provider.code == ADYEN_CODE and provider.adyen_auto_rescue_enabled:
            return provider.adyen_max_days_to_rescue + 7
        return super()._my2_pending_charge_timeout_days(provider)
