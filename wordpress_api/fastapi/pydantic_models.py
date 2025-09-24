from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel, to_pascal


class LetterLanguageCode(str, Enum):
    ENG = "English"
    SVE = "Swedish"
    NOR = "Norwegian"
    DAK = "DAK"
    DANISH = "Danish"


class PascalCaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_pascal,
        populate_by_name=True,
    )


class BeneficiaryModel(PascalCaseModel):
    global_beneficiary_id: str
    local_beneficiary_id: str | None = None
    firstname: str | None = None
    preferred_name: str | None = None
    relationship_type: str | None = "Sponsor"


class SupporterModel(PascalCaseModel):
    compass_constituent_id: str
    global_supporter_id: str | None = None
    firstname: str | None = None
    preferred_name: str | None = None


class LetterPostModel(PascalCaseModel):
    supporter: SupporterModel
    beneficiary: BeneficiaryModel
    original_language: LetterLanguageCode
    pages: list[str] = Field(
        description="The content of the letter from the sponsor, split into pages. "
        "Each string in the list represents a single page of the letter."
    )
    pdf_base64: str = Field(alias="PDFBase64", description="Base64 encoded PDF.")


class SupporterInfoModel(PascalCaseModel):
    supporter: SupporterModel
    beneficiaries: list[BeneficiaryModel] = []


class AvailableChildModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    father_work_as: str | None = Field(default=None, alias="FatherWorkAs")
    fullshot: str | None = Field(default=None, alias="Fullshot")
    hiv: bool | None = Field(default=None, alias="Hiv")
    mother_work_as: str | None = Field(default=None, alias="MotherWorkAs")
    age: int | None = None
    church_activities: str | None = None
    common_language: str | None = None
    country: str | None = None
    date_of_birth: float | None = None
    denomination: str | None = None
    famaly_activities: str | None = None
    favorite_hobby_activities: str | None = None
    favorite_school_subject: str | None = None
    gender: int | None = None
    handicapped: bool | None = None
    help_with: str | None = None
    household_member: str | None = None
    key: str | None = None
    local_food: str | None = None
    local_sociaty_situated: str | None = None
    name: str | None = None
    nick_name: str | None = None
    no_of_inhabitants: int | None = None
    orphan: bool | None = None
    personal_name: str | None = None
    project_activities: str | None = None
    project_name: str | None = None
    risk_area: list[str] | None = None
    shool_level: str | None = None
    sourroundings: str | None = None
    sponsor_id: str | int | None = Field(default=None, alias="sponsor_id")
    sponsored: bool | None = None


class ConsignedChildListModel(BaseModel):
    count: int = Field(
        description="Total number of children available for sponsorship."
    )
    children: list[AvailableChildModel] = []
    range: str = Field(
        default="ALL",
        description="Indicates the paginated range of children returned "
        "in the current response, formatted as \n\n `{start}-{end}`. \n\n"
        "**Example:** `0-10`",
    )
