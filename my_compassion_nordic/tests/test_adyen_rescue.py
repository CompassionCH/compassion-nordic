from unittest.mock import Mock, patch

from odoo.tests import tagged

from odoo.addons.my_compassion.tests.common import DigitalSeamCase


@tagged("post_install", "-at_install")
class TestAdyenRescue(DigitalSeamCase):
    def _make_adyen_provider(self):
        """A minimally configured Adyen provider (never contacted: tests
        mock the HTTP layer or feed notification data directly)."""
        journal = self.env["account.journal"].search([("type", "=", "sale")], limit=1)
        return self.env["payment.provider"].create(
            {
                "name": "Digital Seam Adyen",
                "code": "adyen",
                "company_id": journal.company_id.id,
                "state": "test",
                "adyen_merchant_account": "DigitalSeamECOM",
                "adyen_api_key": "digital-seam-api-key",
                "adyen_client_key": "digital-seam-client-key",
                "adyen_hmac_key": "4449474954414c5345414d5445535431",
                "adyen_api_url_prefix": "checkout-test",
            }
        )

    def _make_adyen_tx(self, provider, reference, **extra):
        method = self.env["payment.method"].search([("code", "=", "card")], limit=1)
        if not method:
            method = self.env["payment.method"].search([], limit=1)
        return self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": method.id,
                "partner_id": self.partner.id,
                "amount": 100,
                "currency_id": provider.company_id.currency_id.id,
                "reference": reference,
                "operation": "offline",
                **extra,
            }
        )

    def _make_rescued_charge(self):
        """A pending off-session charge whose refusal was taken over by the
        provider's rescue process."""
        contract, invoice, _token = self._make_chargeable_invoice()

        def send_rescued(tx_self):
            tx_self.write(
                {
                    "my2_rescue_reference": "DIGITALSEAMRESCUE02",
                    "my2_rescue_state": "scheduled",
                }
            )
            tx_self._set_pending()

        self._run_charge_cron(send_rescued)
        tx = self.env["payment.transaction"].search(
            [("invoice_ids", "in", invoice.ids)]
        )
        self.assertEqual(tx.state, "pending")
        return contract, invoice, tx

    def test_adyen_rescue_payload_injection(self):
        provider = self._make_adyen_provider()
        captured = {}

        def fake_request(method, url, json=None, headers=None, timeout=None):
            captured["json"] = json
            response = Mock()
            response.json.return_value = {}
            response.raise_for_status.return_value = None
            return response

        rescue = {"maxDaysToRescue": 21, "merchantOrderReference": "digital-seam-cycle"}
        with patch(
            "odoo.addons.payment_adyen.models.payment_provider.requests.request",
            side_effect=fake_request,
        ):
            provider.with_context(my2_auto_rescue=rescue)._adyen_make_request(
                "/payments", payload={"reference": "r1"}
            )
            self.assertEqual(captured["json"]["additionalData"]["autoRescue"], "true")
            self.assertEqual(
                captured["json"]["additionalData"]["maxDaysToRescue"], "21"
            )
            self.assertEqual(
                captured["json"]["merchantOrderReference"], "digital-seam-cycle"
            )
            self.assertEqual(captured["json"]["reference"], "r1")
            # without the context key the payload is untouched
            provider._adyen_make_request("/payments", payload={"reference": "r2"})
            self.assertNotIn("autoRescue", captured["json"])
            # other endpoints are untouched even with the context key
            provider.with_context(my2_auto_rescue=rescue)._adyen_make_request(
                "/payments/details", payload={"reference": "r3"}
            )
            self.assertNotIn("autoRescue", captured["json"])

    def test_rescued_refusal_keeps_tx_pending(self):
        provider = self._make_adyen_provider()
        tx = self._make_adyen_tx(provider, "digital-seam-rescued-refusal")
        tx._process_notification_data(
            {
                "resultCode": "Refused",
                "refusalReason": "Expired Card",
                "pspReference": "DIGITALSEAMPSP01",
                "additionalData": {
                    "retry.rescueScheduled": "true",
                    "retry.rescueReference": "DIGITALSEAMRESCUE01",
                },
            }
        )
        self.assertEqual(tx.state, "pending")
        self.assertEqual(tx.my2_rescue_state, "scheduled")
        self.assertEqual(tx.my2_rescue_reference, "DIGITALSEAMRESCUE01")
        self.assertEqual(tx.provider_reference, "DIGITALSEAMPSP01")

    def test_plain_refusal_still_errors(self):
        provider = self._make_adyen_provider()
        tx = self._make_adyen_tx(provider, "digital-seam-plain-refusal")
        tx._process_notification_data(
            {
                "resultCode": "Refused",
                "refusalReason": "Refused",
                "pspReference": "DIGITALSEAMPSP02",
            }
        )
        self.assertEqual(tx.state, "error")
        self.assertFalse(tx.my2_rescue_state)

    def test_autorescue_matching_never_creates_child_tx(self):
        # an unknown event code falls into the stock matcher's refund branch,
        # which can create a spurious child transaction from
        # originalReference: AUTORESCUE must match by merchantReference
        provider = self._make_adyen_provider()
        tx = self._make_adyen_tx(provider, "digital-seam-autorescue-match")
        tx.provider_reference = "DIGITALSEAMPSP03"
        matched = self.env["payment.transaction"]._get_tx_from_notification_data(
            "adyen",
            {
                "eventCode": "AUTORESCUE",
                "merchantReference": tx.reference,
                "pspReference": "DIGITALSEAMRESCUE03",
                "originalReference": "DIGITALSEAMPSP03",
                "amount": {"value": 10000, "currency": "SEK"},
                "success": "false",
            },
        )
        self.assertEqual(matched, tx)
        self.assertFalse(
            self.env["payment.transaction"].search(
                [("source_transaction_id", "=", tx.id)]
            )
        )

    def test_autorescue_success_closes_pending_charge(self):
        contract, invoice, tx = self._make_rescued_charge()
        tx._my2_process_autorescue(
            {
                "eventCode": "AUTORESCUE",
                "merchantReference": tx.reference,
                "success": "true",
            }
        )
        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.my2_rescue_state, "succeeded")
        self.assertIn(invoice.payment_state, ("paid", "in_payment"))
        self.assertEqual(contract.state, "active")

    def test_autorescue_failure_errors_tx_and_hands_off(self):
        contract, invoice, tx = self._make_rescued_charge()
        handoffs = []

        def record_handoff(contract_self, failed_invoice, reason):
            handoffs.append((contract_self, failed_invoice, reason))

        with patch.object(
            self.registry["recurring.contract"],
            "_on_digital_charge_failed",
            record_handoff,
        ):
            tx._my2_process_autorescue(
                {
                    "eventCode": "AUTORESCUE",
                    "merchantReference": tx.reference,
                    "success": "false",
                    "reason": "maxRetryAttemptsReached",
                }
            )
        self.assertEqual(tx.state, "error")
        self.assertEqual(tx.my2_rescue_state, "failed")
        self.assertEqual(handoffs, [(contract, invoice, "maxRetryAttemptsReached")])
        self.assertEqual(invoice.payment_state, "not_paid")
        # webhook redelivery must not re-trigger the dunning handoff
        with patch.object(
            self.registry["recurring.contract"],
            "_on_digital_charge_failed",
            record_handoff,
        ):
            tx._my2_process_autorescue(
                {
                    "eventCode": "AUTORESCUE",
                    "merchantReference": tx.reference,
                    "success": "false",
                    "reason": "maxRetryAttemptsReached",
                }
            )
        self.assertEqual(len(handoffs), 1)
        # the definitive failure is E's case now: the next cron run must
        # not blindly re-charge the same card
        self._run_charge_cron(lambda tx_self: tx_self._set_done())
        self.assertEqual(
            self.env["payment.transaction"].search_count(
                [("invoice_ids", "in", invoice.ids)]
            ),
            1,
        )

    def test_charge_context_respects_params(self):
        # the chargeable fixture uses a non-Adyen provider: no opt-in
        _contract, invoice, _token = self._make_chargeable_invoice()
        Group = self.env["recurring.contract.group"]
        params = self.env["ir.config_parameter"].sudo()
        self.assertEqual(Group._digital_charge_context(invoice), {})
        # re-point the mode to an Adyen provider. With no parameter set at
        # all there is still no opt-in: the feature stays off until Adyen
        # enables it on the merchant account.
        adyen = self._make_adyen_provider()
        invoice.line_ids.contract_id.group_id.payment_mode_id.write(
            {"payment_provider_id": adyen.id}
        )
        params.search(
            [("key", "=", "my_compassion_nordic.auto_rescue_enabled")]
        ).unlink()
        self.assertEqual(Group._digital_charge_context(invoice), {})
        # turning the parameter on is what opts the charges in
        params.set_param("my_compassion_nordic.auto_rescue_enabled", "True")
        context = Group._digital_charge_context(invoice)
        self.assertEqual(context["my2_auto_rescue"]["maxDaysToRescue"], 21)
        self.assertEqual(
            context["my2_auto_rescue"]["merchantOrderReference"], invoice.name
        )
        params.set_param("my_compassion_nordic.max_days_to_rescue", "10")
        context = Group._digital_charge_context(invoice)
        self.assertEqual(context["my2_auto_rescue"]["maxDaysToRescue"], 10)
        params.set_param("my_compassion_nordic.auto_rescue_enabled", "False")
        self.assertEqual(Group._digital_charge_context(invoice), {})
