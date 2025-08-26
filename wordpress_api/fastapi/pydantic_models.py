from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_pascal


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
    original_language: str
    pages: list[str]
    pdf_base64: str = Field(alias="PDFBase64")


class SupporterInfoModel(PascalCaseModel):
    supporter: SupporterModel
    beneficiaries: list[BeneficiaryModel] = []
