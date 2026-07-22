from odoo import models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    def _adyen_make_request(
        self, endpoint, endpoint_param=None, payload=None, method="POST",
        idempotency_key=None,
    ):
        """Opt a payment request into Adyen Auto Rescue.

        The off-session charge engine delegates retries of refused charges
        to Adyen (no Odoo-side retry schedule exists). It signals this with
        the ``my2_auto_rescue`` context key; any other caller of the Adyen
        API - checkout drop-in, donations, refunds - is unaffected.
        """
        rescue = self.env.context.get("my2_auto_rescue")
        if rescue and endpoint == "/payments" and payload is not None:
            # autoRescue/maxDaysToRescue are additionalData entries (string
            # values); the Checkout API rejects them as top-level fields
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
