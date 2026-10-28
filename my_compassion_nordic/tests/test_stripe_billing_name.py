import json

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestStripeBillingName(TransactionCase):
    """What the Stripe Payment Element is told about the payer's name.

    A fast-checkout sponsor's partner is named "(pending)". Offered to the
    Element as the payer's name, Stripe shows it or hands it straight back;
    instead the Element is told to ask the payer.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Copy the stock record rather than create one: a bare create lacks
        # the inline form view reference, and the provider refuses to exist
        # in any state without its key pair.
        cls.provider = cls.env.ref("payment.payment_provider_stripe").copy(
            {
                "state": "test",
                "stripe_publishable_key": "pk_test_dummy",
                "stripe_secret_key": "sk_test_dummy",
            }
        )
        cls.card = cls.env.ref("payment.payment_method_card")
        cls.card.active = True

    def _inline_values_for(self, partner):
        raw = self.provider._stripe_get_inline_form_values(
            100.0,
            self.env.company.currency_id,
            partner.id,
            False,
            payment_method_sudo=self.card,
        )
        return json.loads(raw)

    def test_placeholder_is_withheld_and_the_name_asked(self):
        partner = self.env["res.partner"].create(
            {
                "lastname": self.env["res.partner"].MY2_PLACEHOLDER_NAME,
                "my2_name_placeholder": True,
                "email": "stripe-name@example.org",
            }
        )

        values = self._inline_values_for(partner)

        self.assertEqual(values["billing_details"]["name"], "")
        self.assertTrue(values["my2_ask_billing_name"])
        # everything else still goes through - only the name is withheld
        self.assertEqual(values["billing_details"]["email"], partner.email)

    def test_real_name_is_sent_and_not_asked_again(self):
        partner = self.env["res.partner"].create(
            {"firstname": "Anna", "lastname": "Svensson", "email": "anna@example.org"}
        )

        values = self._inline_values_for(partner)

        self.assertEqual(values["billing_details"]["name"], "Anna Svensson")
        self.assertNotIn("my2_ask_billing_name", values)
