import logging

from odoo import _, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    my2_rescue_reference = fields.Char(
        string="Rescue Reference",
        readonly=True,
        help="Adyen Auto Rescue identifier of a refused charge the provider"
        " retries on its own schedule.",
    )
    my2_rescue_state = fields.Selection(
        [
            ("scheduled", "Rescue Scheduled"),
            ("succeeded", "Rescue Succeeded"),
            ("failed", "Rescue Failed"),
        ],
        string="Rescue State",
        readonly=True,
    )

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Match AUTORESCUE webhooks by merchant reference.

        The stock Adyen matcher routes unknown event codes through its
        refund branch, which may create a spurious child transaction from
        originalReference; a rescue outcome concerns the original charge
        itself.
        """
        if (
            provider_code == "adyen"
            and notification_data.get("eventCode") == "AUTORESCUE"
        ):
            reference = notification_data.get("merchantReference")
            tx = self.search(
                [("reference", "=", reference), ("provider_code", "=", "adyen")]
            )
            if not tx:
                raise ValidationError(
                    "Adyen: "
                    + _("No transaction found matching reference %s.", reference)
                )
            return tx
        return super()._get_tx_from_notification_data(provider_code, notification_data)

    def _my2_process_autorescue(self, notification_data):
        """Settle a charge from the terminal outcome of the provider's
        rescue process.

        Success: the winning retry's AUTHORISATION webhook normally already
        confirmed the transaction through the stock handler; confirm it here
        when that webhook was missed, and post-process (no shopper session
        exists to do it).
        Failure: the pending charge is definitively lost - error the
        transaction and hand the invoice's contracts to the dunning hook.
        """
        self.ensure_one()
        if str(notification_data.get("success")).lower() == "true":
            self.my2_rescue_state = "succeeded"
            if self.state != "done":
                self._set_done()
            if not self.is_post_processed:
                try:
                    with self.env.cr.savepoint():
                        self._post_process()
                except Exception:
                    # never fail the webhook (the whole batch would be
                    # retried into the same error): the transaction is
                    # safely done, the stock retrying cron reconciles it
                    _logger.exception(
                        "Post-processing of transaction %s failed; the"
                        " payment post-processing cron will retry it.",
                        self.reference,
                    )
                    self.env.ref("payment.cron_post_process_payment_tx")._trigger()
        elif self.my2_rescue_state == "failed":
            # webhooks are delivered at least once: this failure is
            # already settled, a duplicate must not re-trigger dunning
            pass
        elif self.state == "done":
            _logger.error(
                "Transaction %s received a failed rescue outcome but is"
                " already done; leaving it untouched.",
                self.reference,
            )
        else:
            reason = notification_data.get("reason") or ""
            self.my2_rescue_state = "failed"
            self._set_error(_("The provider gave up retrying the payment: %s", reason))
            for invoice in self.invoice_ids:
                invoice.line_ids.contract_id._on_digital_charge_failed(invoice, reason)

    def _process_notification_data(self, notification_data):
        """Keep refused-but-rescued Adyen charges alive.

        When a charge request opted into Auto Rescue is refused, Adyen
        answers Refused with retry.rescueScheduled and keeps retrying
        server-side. The stock handler would error the transaction; instead
        it stays pending, holding the one-charge-per-invoice guard closed,
        until the terminal AUTORESCUE webhook settles the case.
        """
        if (
            self.provider_code == "adyen"
            and notification_data.get("resultCode") == "Refused"
        ):
            additional_data = notification_data.get("additionalData") or {}
            rescue_scheduled = (
                str(additional_data.get("retry.rescueScheduled")).lower() == "true"
            )
            if rescue_scheduled:
                if notification_data.get("pspReference"):
                    self.provider_reference = notification_data["pspReference"]
                self.write(
                    {
                        "my2_rescue_reference": additional_data.get(
                            "retry.rescueReference"
                        ),
                        "my2_rescue_state": "scheduled",
                    }
                )
                self._set_pending(
                    state_message=_(
                        "The payment was refused (%s); the provider scheduled"
                        " automatic retries.",
                        notification_data.get("refusalReason") or "",
                    )
                )
                return
        return super()._process_notification_data(notification_data)
