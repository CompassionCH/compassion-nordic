from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CurrencyEnum(str, Enum):
    SWEDISH_KRONA = "SEK"
    US_DOLLAR = "USD"
    NORWEGIAN_KRONE = "NOK"
    EURO = "EUR"
    DANISH_KRONE = "DKK"


class ProviderEnum(str, Enum):
    STRIPE = "Stripe"
    SWISH = "Swish"
    VIPPS = "Vipps"


class CamelCaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class FundModel(CamelCaseModel):
    name: str
    odoo_id: int
    category: str | None = None


class FundListModel(CamelCaseModel):
    funds: list[FundModel] = []


class DonationPostModel(CamelCaseModel):
    donation_id: int = Field(description="Giving Platform donation ID")
    payment_request_id: str = Field(
        description="Unique identifier from the payment provider"
    )
    currency_code: CurrencyEnum
    amount: float
    donor_email: str | None = None
    donor_name: str | None = None
    donor_phone: str | None = None
    payment_provider: ProviderEnum
    fund_id: int = Field(description="Odoo ID of the fund the donation is for")


class DonateResponseModel(CamelCaseModel):
    success: bool
    odoo_id: int = Field(
        description="Odoo ID of the created donation record, if successful"
    )
