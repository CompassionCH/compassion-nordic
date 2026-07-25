from odoo.tests import tagged

from odoo.addons.my_compassion.tests.common import DigitalSeamCase


@tagged("post_install", "-at_install")
class TestDigitalFixitNordic(DigitalSeamCase):
    """The Nordic configs plug the generic dunning engine in."""

    def test_hooks_resolve_nordic_configs(self):
        contract = self.env["recurring.contract"]
        configs = contract._my2_fixit_configs()
        self.assertEqual(
            configs["first"],
            self.env.ref("my_compassion_nordic.config_digital_payment_fixit_first"),
        )
        self.assertEqual(
            configs["final"],
            self.env.ref("my_compassion_nordic.config_digital_payment_fixit_final"),
        )
        self.assertEqual(
            contract._my2_portal_invitation_config(),
            self.env.ref("my_compassion_nordic.config_portal_invitation"),
        )

    def test_charge_failure_creates_fixit_email(self):
        """A definitive charge failure creates ONE auto-send job whose body
        carries the signed update-card link of the right group."""
        contract, invoice, _token = self._make_chargeable_invoice()
        contract.contract_active()
        contract.partner_id.email = "nordic-fixit@example.com"
        contract._on_digital_charge_failed(invoice, "Refused")
        job = self.env["partner.communication.job"].search(
            [
                (
                    "config_id",
                    "=",
                    self.env.ref(
                        "my_compassion_nordic.config_digital_payment_fixit_first"
                    ).id,
                ),
                ("partner_id", "=", contract.partner_id.id),
            ]
        )
        self.assertEqual(len(job), 1)
        self.assertTrue(job.auto_send)
        self.assertIn(
            f"/my2/update-card?group_id={contract.group_id.id}&amp;access_token=",
            job.body_html,
        )
        # same broken card next month: no second first-notice
        contract._on_digital_charge_failed(invoice, "Refused again")
        self.assertEqual(
            self.env["partner.communication.job"].search_count(
                [
                    ("config_id", "=", job.config_id.id),
                    ("partner_id", "=", contract.partner_id.id),
                ]
            ),
            1,
        )

    def test_portal_invitation_renders_signup_link(self):
        contract = self._make_digital_contract()
        contract.partner_id.email = "nordic-invite@example.com"
        contract._my2_send_portal_invitation()
        job = self.env["partner.communication.job"].search(
            [
                (
                    "config_id",
                    "=",
                    self.env.ref("my_compassion_nordic.config_portal_invitation").id,
                ),
                ("partner_id", "=", contract.partner_id.id),
            ]
        )
        self.assertEqual(len(job), 1)
        self.assertEqual(job.partner_id, contract.partner_id)
        self.assertIn("/web/signup", job.body_html)
