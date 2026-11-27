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
    """A donation. Partner details are only used to create the partner, or to
    give an address to a partner found (by phone, then email) that has none:
    send them only when the donor agreed to share them."""

    model_config = ConfigDict(**CamelCaseModel.model_config, str_strip_whitespace=True)

    donation_id: int = Field(description="Giving Platform donation ID")
    payment_request_id: str = Field(
        description="Unique identifier from the payment provider"
    )
    currency_code: CurrencyEnum
    amount: float
    donor_email: str | None = None
    donor_name: str | None = None
    donor_phone: str | None = None
    donor_first_name: str | None = Field(
        default=None,
        description="Donor first name. With donorLastName, used instead of "
        "donorName for a new partner.",
    )
    donor_last_name: str | None = Field(default=None, description="Donor last name")
    donor_street: str | None = Field(
        default=None, description="Address line 1 (e.g. Stripe address.line1)"
    )
    donor_street2: str | None = Field(
        default=None, description="Address line 2 (e.g. Stripe address.line2)"
    )
    donor_zip: str | None = Field(default=None, description="Postal code")
    donor_city: str | None = Field(default=None, description="City")
    donor_country_code: str | None = Field(
        default=None,
        description="Country, ISO 3166-1 alpha-2 code (e.g. SE). Also used to "
        "read a national phone number. An unknown code is ignored.",
    )
    payment_provider: ProviderEnum
    fund_id: int = Field(description="Odoo ID of the fund the donation is for")


class DonateResponseModel(CamelCaseModel):
    success: bool
    odoo_id: int = Field(
        description="Odoo ID of the created donation record, if successful"
    )
