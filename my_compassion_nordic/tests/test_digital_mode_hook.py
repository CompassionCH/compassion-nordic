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
            self.assertEqual(
                mode.company_id, mode.payment_provider_id.company_id
            )

    def test_archived_mode_is_not_recreated(self):
        modes = _ensure_digital_modes(self.env)
        if not modes:
            self.skipTest("no digital payment provider on this database")
        modes[0].active = False
        again = _ensure_digital_modes(self.env)
        self.assertEqual(modes, again)
