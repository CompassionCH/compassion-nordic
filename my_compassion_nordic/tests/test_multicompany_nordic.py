from odoo.tests import tagged

from odoo.addons.my_compassion.tests.common import DigitalSeamCase


@tagged("post_install", "-at_install")
class TestAdyenMultiCompany(DigitalSeamCase):
    """The Adyen charge context is resolved per invoice, so a batch across
    several companies never leaks one company's opt-in onto another's
    charge."""

    def _two_sale_companies(self):
        companies = (
            self.env["account.journal"].search([("type", "=", "sale")]).company_id
        )
        self.assertGreaterEqual(
            len(companies), 2, "the database needs two companies with sale accounting"
        )
        return companies[0], companies[1]

    def test_charge_context_is_per_invoice_company(self):
        company_a, company_b = self._two_sale_companies()
        _ca, invoice_a, _ta = self._make_chargeable_invoice(company=company_a)
        _cb, invoice_b, _tb = self._make_chargeable_invoice(company=company_b)
        # company A collects through Adyen, in its own company
        adyen_a = self.env["payment.provider"].create(
            {
                "name": "Multi Co Adyen A",
                "code": "adyen",
                "company_id": company_a.id,
                "state": "test",
                "adyen_merchant_account": "MultiCoECOM",
                "adyen_api_key": "multi-co-api-key",
                "adyen_client_key": "multi-co-client-key",
                "adyen_hmac_key": "4d554c5449434f4d554c5449434f4d55",
                "adyen_api_url_prefix": "checkout-test",
            }
        )
        invoice_a.line_ids.contract_id.group_id.payment_mode_id.write(
            {"payment_provider_id": adyen_a.id}
        )
        # company B collects through Adyen too, on its own merchant account.
        # Adyen enables Auto Rescue per merchant account, so B must be able
        # to stay out while A is in.
        # Values here are dummy strings.
        adyen_b = self.env["payment.provider"].create(
            {
                "name": "Multi Co Adyen B",
                "code": "adyen",
                "company_id": company_b.id,
                "state": "test",
                "adyen_merchant_account": "MultiCoECOMB",
                "adyen_api_key": "multi-co-api-key-b",
                "adyen_client_key": "multi-co-client-key-b",
                "adyen_hmac_key": "4d554c5449434f4d554c5449434f4d56",
                "adyen_api_url_prefix": "checkout-test",
            }
        )
        invoice_b.line_ids.contract_id.group_id.payment_mode_id.write(
            {"payment_provider_id": adyen_b.id}
        )
        # only A's merchant account has the feature switched on
        adyen_a.adyen_auto_rescue_enabled = True
        self.assertFalse(adyen_b.adyen_auto_rescue_enabled)
        Group = self.env["recurring.contract.group"]
        ctx_a = Group._digital_charge_context(invoice_a)
        ctx_b = Group._digital_charge_context(invoice_b)
        # company A gets the Adyen Auto Rescue opt-in, keyed to its invoice
        self.assertIn("my2_auto_rescue", ctx_a)
        self.assertEqual(
            ctx_a["my2_auto_rescue"]["merchantOrderReference"], invoice_a.name
        )
        # company B runs the same provider code and is still left out
        self.assertEqual(ctx_b, {})
