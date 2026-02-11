import json

from odoo import models

from ..fastapi.giving_platform_pydantic_models import DonationPostModel


class AccountMove(models.Model):
    _inherit = "account.move"

    def process_donation(self, donation_data_str):
        """Process the donation by filling in the details and posting the move."""
        self.ensure_one()
        if self.state != "draft":
            self._notify_managers_error(
                f"Attempted to process donation for move, but it is not in draft state."
                f" Here is the data received: {donation_data_str}"
            )
            return "Processing error: Move is not in draft state."
        donation_data = DonationPostModel(**json.loads(donation_data_str))
        partner = self.env["res.partner"].match_create_partner(
            email=donation_data.donor_email,
            name=donation_data.donor_name,
            phone=donation_data.donor_phone,
        )
        self.partner_id = partner.id
        self.line_ids = [
            (
                0,
                0,
                {
                    "product_id": donation_data.fund_id,
                    "quantity": 1,
                    "price_unit": donation_data.amount,
                },
            ),
            (
                0,
                0,
                {
                    "account_id": self.env["account.account"]
                    .search(
                        [
                            ("account_type", "=", "asset_receivable"),
                            ("company_id", "=", self.company_id.id),
                            ("is_off_balance", "=", False),
                        ],
                        order="id asc",
                        limit=1,
                    )
                    .id,
                    "debit": donation_data.amount,
                },
            ),
        ]
        self.action_post()
        journal = self.env["account.journal"].search(
            [
                ("name", "ilike", donation_data.payment_provider.value),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
            order="id asc",
        )
        if not journal:
            self._notify_managers_error(
                f"No journal found for {donation_data.payment_provider.value}. "
                f"Invoice cannot be processed automatically."
            )
            return False
        self.env["account.payment.register"].with_context(
            active_model="account.move.line", active_ids=self.line_ids.ids
        ).create(
            {
                "communication": (
                    f"Donation {self.payment_reference} (Giving Platform ID: "
                    f"{self.ref})"
                ),
                "amount": donation_data.amount,
                "currency_id": self.currency_id.id,
                "partner_id": partner.id,
                "journal_id": journal.id,
            }
        ).action_create_payments()
        return "Successfully processed donation and created payment."

    def _notify_managers_error(self, error_message):
        user = self.env["res.config.settings"].get_param("mandate_notif_id")
        accounting_manager = self.env["res.partner"].search([("user_ids", "=", user)])
        self.message_post(body=error_message, partner_ids=accounting_manager.ids)
