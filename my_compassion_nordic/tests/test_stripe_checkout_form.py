import json

from lxml import html as lxml_html

from odoo.tests import TransactionCase, tagged

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.website.tools import MockRequest


@tagged("post_install", "-at_install")
class TestStripeCheckoutForm(TransactionCase):
    """The rendered Stripe inline form must declare tokenization when the
    my2 checkout context is set.

    Stripe Elements reads is_tokenization_required at init to declare
    setup_future_usage. The server puts off_session on the PaymentIntent
    when the transaction tokenizes. Stripe rejects the payment when the
    two disagree. The my2 pages send the flag through the environment of
    the recordsets given to the form rendering, and this test locks that
    propagation down end to end through the real QWeb templates.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # the stock card method ships archived and only wakes up on a
        # provider state write, force it so the fixture works on any DB
        cls.card = cls.env.ref("payment.payment_method_card")
        cls.card.active = True
        # copy the stock record like ops does, a bare create would lack
        # the inline form view reference the template needs. The copy
        # trips the provider create hook, so it also creates an
        # account.payment.mode as a side effect.
        cls.provider = cls.env.ref("payment.payment_provider_stripe").copy(
            {
                "name": "Stripe Render Test",
                "company_id": cls.env.company.id,
                "state": "test",
                "stripe_publishable_key": "pk_test_dummy",
                "stripe_secret_key": "sk_test_dummy",
                "payment_method_ids": [(6, 0, cls.card.ids)],
            }
        )
        cls.website = cls.env["website"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        ) or cls.env["website"].search([], limit=1)

    def _render_form_values(self, extra_context):
        methods = self.card.with_context(**extra_context)
        providers = self.provider.with_context(**extra_context)
        # the form template reads request.env for its debug notices and
        # the website qweb environment needs a current website
        with MockRequest(self.env, website=self.website):
            rendered = self.env["ir.qweb"]._render(
                "payment.form",
                {
                    "providers_sudo": providers,
                    "payment_methods_sudo": methods,
                    "tokens_sudo": self.env["payment.token"],
                    "amount": 200.0,
                    "currency": self.env.company.currency_id,
                    "partner_id": self.env.user.partner_id.id,
                    "reference_prefix": "TEST",
                    "transaction_route": "/test/transaction",
                    "landing_route": "/test/landing",
                    "access_token": "dummy",
                    # computed like the real pages so the checkbox
                    # visibility follows the context under test
                    "show_tokenize_input_mapping": (
                        payment_portal.PaymentPortal._compute_show_tokenize_input_mapping(
                            providers
                        )
                    ),
                    "availability_report": {},
                },
            )
        tree = lxml_html.fromstring(str(rendered))
        containers = tree.xpath("//div[@name='o_stripe_element_container']")
        self.assertTrue(containers, "the Stripe inline form container is missing")
        return json.loads(containers[0].get("data-stripe-inline-form-values"))

    def test_form_declares_tokenization_with_my2_context(self):
        values = self._render_form_values({"my2_sponsorship": True})
        self.assertTrue(values["is_tokenization_required"])

    def test_form_leaves_tokenization_optional_without_context(self):
        values = self._render_form_values({})
        self.assertFalse(values["is_tokenization_required"])
