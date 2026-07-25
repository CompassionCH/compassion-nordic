from odoo import fields, models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    adyen_auto_rescue_enabled = fields.Boolean(
        string="Auto Rescue",
        help="Let Adyen retry refused off-session charges on its own"
        " schedule. Only enable this once Adyen has switched the feature on"
        " for this merchant account.",
    )
    adyen_max_days_to_rescue = fields.Integer(
        string="Max Days To Rescue",
        default=21,
        help="How long Adyen keeps retrying a refused charge before it"
        " reports a final failure.",
    )

    def _adyen_make_request(
        self, endpoint, endpoint_param=None, payload=None, method="POST",
        idempotency_key=None,
    ):
        """Opt a payment request into Adyen Auto Rescue.

        The off-session charge engine delegates retries of refused charges
        to Adyen. No Odoo-side retry schedule exists. It signals this with
        the ``my2_auto_rescue`` context key. Any other caller of the Adyen
        API is unaffected. That covers the checkout drop-in, donations and
        refunds.
        """
        rescue = self.env.context.get("my2_auto_rescue")
        if rescue and endpoint == "/payments" and payload is not None:
            # autoRescue and maxDaysToRescue are additionalData entries with
            # string values. The Checkout API rejects them as top-level
            # fields.
            payload = {
                **payload,
                "additionalData": {
                    **payload.get("additionalData", {}),
                    "autoRescue": "true",
                    "maxDaysToRescue": str(rescue["maxDaysToRescue"]),
                },
                "merchantOrderReference": rescue["merchantOrderReference"],
            }
        return super()._adyen_make_request(
            endpoint,
            endpoint_param=endpoint_param,
            payload=payload,
            method=method,
            idempotency_key=idempotency_key,
        )
