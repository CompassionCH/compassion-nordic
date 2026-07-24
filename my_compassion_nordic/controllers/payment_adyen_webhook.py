import logging
import pprint

from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment_adyen.controllers.main import AdyenController

_logger = logging.getLogger(__name__)


class MyCompassionAdyenController(AdyenController):
    @http.route()
    def adyen_webhook(self):
        """Also process AUTORESCUE events.

        The stock webhook only handles AUTHORISATION-class events and skips
        everything else; the terminal outcome of a provider-side rescue
        (see the off-session charge engine) arrives as an AUTORESCUE event.
        The stock pass runs first so a batch carrying both the winning
        retry's AUTHORISATION and the rescue outcome settles in order.
        """
        try:
            data = request.get_json_data()
        except ValueError as e:
            # Malformed webhook body. Reject before the stock handler indexes it.
            raise BadRequest() from e
        if not isinstance(data, dict) or not isinstance(
            data.get("notificationItems"), list
        ):
            raise BadRequest()
        res = super().adyen_webhook()
        for notification_item in data["notificationItems"]:
            notification_data = notification_item.get("NotificationRequestItem") or {}
            if notification_data.get("eventCode") != "AUTORESCUE":
                continue
            _logger.info(
                "rescue outcome received from Adyen with data:\n%s",
                pprint.pformat(notification_data),
            )
            try:
                tx_sudo = request.env[
                    "payment.transaction"
                ].sudo()._get_tx_from_notification_data("adyen", notification_data)
            except ValidationError:
                _logger.warning(
                    "unable to find the transaction of the rescue outcome;"
                    " skipping to acknowledge"
                )
                continue
            self._verify_notification_signature(notification_data, tx_sudo)
            try:
                tx_sudo._my2_process_autorescue(notification_data)
            except ValidationError:
                _logger.exception(
                    "unable to process the rescue outcome;"
                    " skipping to acknowledge"
                )
        return res
