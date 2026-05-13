import inspect
import logging

from fastapi import HTTPException

from odoo.models import AbstractModel

from .giving_platform_pydantic_models import (
    DonateResponseModel,
    DonationPostModel,
    FundListModel,
    FundModel,
)

_logger = logging.getLogger(__name__)


class GivingPlatformService(AbstractModel):
    _name = "giving.platform.service"
    _description = "Giving Platform Service"

    def get_funds(self) -> FundListModel:
        """
        Fetch available funds from the database and
        format them for the Giving Platform API.
        """
        funds = self.env["product.product"].search([("requires_thankyou", "=", True)])
        return FundListModel(
            funds=[
                FundModel(name=fund.name, odoo_id=fund.id, category=fund.categ_id.name)
                for fund in funds
            ]
        )

    def donate(self, donate_data: DonationPostModel) -> DonateResponseModel:
        """
        Process a donation submission from the Giving Platform API.
        """
        # Make sure we don't lose the information received.
        json_data = donate_data.model_dump_json()
        self.env["ir.logging"].with_delay(
            channel="root.wordpress_api",
            description="Log donation from Giving Platform",
        ).create(
            {
                "level": "info",
                "name": "giving_platform_service.donate",
                "message": f"Received donation data: {json_data}",
                "type": "server",
                "dbname": self.env.cr.dbname,
                "path": __file__,
                "func": "donate",
                "line": inspect.currentframe().f_lineno,
            }
        )
        if not donate_data.donor_phone and not donate_data.donor_email:
            raise HTTPException(
                status_code=422,
                detail="Donor email and/or phone are required.",
            )
        currency = self.env["res.currency"].search(
            [("name", "=", donate_data.currency_code.value)], limit=1
        )
        if not currency:
            raise HTTPException(
                status_code=422,
                detail=f"Currency {donate_data.currency_code.name} is not supported.",
            )
        fund = self.env["product.product"].search([("id", "=", donate_data.fund_id)])
        if not fund:
            raise HTTPException(
                status_code=422,
                detail=f"Fund with id {donate_data.fund_id} does not exist.",
            )
        if not donate_data.amount > 0:
            raise HTTPException(
                status_code=422,
                detail="Donation amount must be greater than zero.",
            )
        company = self.env["res.company"].search(
            [
                ("currency_id", "=", currency.id),
                ("company_registry", "!=", False),
            ],
            limit=1,
        )
        if not company:
            # Comapssion Sweden by default
            company = self.env["res.company"].search(
                [
                    ("currency_id", "=", self.env.ref("base.SEK").id),
                    ("company_registry", "!=", False),
                ],
                order="id ASC",
                limit=1,
            )
        journal = (
            self.env["account.journal"]
            .with_company(company)
            .search(
                [("type", "=", "sale"), ("company_id", "=", company.id)],
                order="id ASC",
                limit=1,
            )
        )
        if not journal:
            raise HTTPException(
                status_code=422,
                detail=f"No sales journal found for company {company.name} "
                f"and currency {currency.name}.",
            )
        donation = (
            self.env["account.move"]
            .with_company(company)
            .search(
                [
                    ("payment_reference", "=", donate_data.payment_request_id),
                    ("move_type", "=", "out_invoice"),
                ],
                limit=1,
            )
        )
        if not donation:
            donation = (
                self.env["account.move"]
                .with_company(company)
                .create(
                    {
                        "move_type": "out_invoice",
                        "currency_id": currency.id,
                        "journal_id": journal.id,
                        "payment_reference": donate_data.payment_request_id,
                        "ref": str(donate_data.donation_id),
                    }
                )
            )
        donation.with_delay(channel="root.wordpress_api").process_donation(json_data)
        return DonateResponseModel(success=True, odoo_id=donation.id)
