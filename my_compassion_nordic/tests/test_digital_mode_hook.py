from odoo.tests import TransactionCase, tagged

from ..hooks import _ensure_digital_modes


@tagged("post_install", "-at_install")
class TestDigitalModeHook(TransactionCase):
    def test_ensure_digital_modes_is_idempotent(self):
        first = _ensure_digital_modes(self.env)
        again = _ensure_digital_modes(self.env)
        self.assertEqual(first, again)
        for mode in first:
            self.assertFalse(mode.payment_order_ok)
            self.assertEqual(mode.company_id, mode.payment_provider_id.company_id)

    def test_archived_mode_is_not_recreated(self):
        modes = _ensure_digital_modes(self.env)
        if not modes:
            self.skipTest("no digital payment provider on this database")
        modes[0].active = False
        again = _ensure_digital_modes(self.env)
        self.assertEqual(modes, again)

    def test_new_stripe_provider_gets_a_mode_on_create(self):
        provider = self.env["payment.provider"].create(
            {
                "name": "Stripe Hook Test",
                "code": "stripe",
                "company_id": self.env.company.id,
                "state": "test",
                "stripe_publishable_key": "pk_test_dummy",
                "stripe_secret_key": "sk_test_dummy",
            }
        )
        mode = self.env["account.payment.mode"].search(
            [("payment_provider_id", "=", provider.id)]
        )
        self.assertEqual(len(mode), 1)
        self.assertEqual(mode.name, "Card (Stripe)")
        self.assertFalse(mode.payment_order_ok)
        self.assertEqual(mode.company_id, provider.company_id)

    def test_non_digital_provider_gets_no_mode(self):
        provider = self.env["payment.provider"].create(
            {
                "name": "Wire Hook Test",
                "code": "none",
                "company_id": self.env.company.id,
            }
        )
        mode = self.env["account.payment.mode"].search(
            [("payment_provider_id", "=", provider.id)]
        )
        self.assertFalse(mode)
