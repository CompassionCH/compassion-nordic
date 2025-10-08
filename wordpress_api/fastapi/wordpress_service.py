import logging

from fastapi import HTTPException

from odoo import fields
from odoo.models import AbstractModel

from odoo.addons.child_compassion.models.child_compassion import CompassionChild
from odoo.addons.child_compassion.models.compassion_hold import HoldType
from odoo.addons.sbc_compassion.models.correspondence_page import PAGE_SEPARATOR
from odoo.addons.sponsorship_compassion.models.res_partner import ResPartner

from .pydantic_models import (
    AvailableChildModel,
    BeneficiaryModel,
    ConsignedChildListModel,
    LetterPostModel,
    PeterChildListModel,
    SupporterInfoModel,
    SupporterModel,
)
from .wordpress_router import LANG_MAPPING

_logger = logging.getLogger(__name__)


class WordpressService(AbstractModel):
    _name = "wordpress.service"
    _description = "WordPress Service"

    def get_consigned_children(
        self, lang: str, limit: int = 0, offset: int = 0
    ) -> PeterChildListModel:
        """
        Fetch consigned children from the database and
        format them for the WordPress API.
        """
        count = self.env["compassion.child"].search_count(
            [
                ("state", "=", "N"),
                ("hold_channel", "=", "web"),
                ("hold_type", "=", HoldType.E_COMMERCE_HOLD.value),
                ("hold_expiration", ">=", fields.Datetime.now()),
            ]
        )
        children = (
            self.env["compassion.child"]
            .with_context(lang=lang)
            .search(
                [
                    ("state", "=", "N"),
                    ("hold_channel", "=", "web"),
                    ("hold_type", "=", HoldType.E_COMMERCE_HOLD.value),
                    ("hold_expiration", ">=", fields.Datetime.now()),
                ],
                limit=limit,
                offset=offset,
            )
        )
        data = children.data_to_json("Wordpress Consignment Child")
        if not isinstance(data, list):
            data = [data]
        for child_vals in data:
            try:
                child_vals["localSociatySituated"] = (
                    child_vals["localSociatySituated"]
                    + ", "
                    + child_vals.pop("country_name")
                )
                member_ids = child_vals["householdMember"]
                caregivers = (
                    children.env["compassion.household.member"]
                    .browse(member_ids)
                    .filtered("is_caregiver")
                )
                child_vals["householdMember"] = caregivers.get_list("role")
            except (KeyError, TypeError):
                continue
        return PeterChildListModel(
            child_list=ConsignedChildListModel(
                count=count,
                range=f"{offset}-{offset + (limit - 1)}" if limit else "ALL",
                children=[AvailableChildModel(**vals) for vals in data],
            )
        )

    def wordpress_sponsor_child(self, child: CompassionChild):
        child.hold_id.write(
            {
                "type": HoldType.NO_MONEY_HOLD.value,
                "expiration_date": child.hold_id.get_default_hold_expiration(
                    HoldType.NO_MONEY_HOLD
                ),
            }
        )
        return {"message": f"Child {child.global_id} is sponsored"}

    def write_letter(self, letter_data: LetterPostModel) -> str:
        """
        Process a letter submission from the WordPress API.
        """
        original_text = PAGE_SEPARATOR.join(letter_data.pages)
        original_language = LANG_MAPPING.get(letter_data.original_language, "sv_SE")
        sponsorship = self.env["recurring.contract"].search(
            [
                "|",
                (
                    "correspondent_id.global_id",
                    "=",
                    letter_data.supporter.global_supporter_id,
                ),
                (
                    "correspondent_id.ref",
                    "=",
                    letter_data.supporter.compass_constituent_id,
                ),
                (
                    "child_id.global_id",
                    "=",
                    letter_data.beneficiary.global_beneficiary_id,
                ),
                ("state", "not in", ["terminated", "cancelled"]),
            ]
        )
        if not sponsorship or len(sponsorship) > 1:
            raise HTTPException(
                status_code=404,
                detail="Sponsorship not found or multiple matches found.",
            )
        language = sponsorship.env["res.lang.compassion"].search(
            [("lang_id.code", "=", original_language)], limit=1
        )
        new_letter = self.env["correspondence"].create(
            [
                {
                    "original_text": original_text,
                    "original_language_id": language.id,
                    "sponsor_letter_scan": letter_data.pdf_base64,
                    "sponsorship_id": sponsorship.id,
                    "direction": "Supporter To Beneficiary",
                    "template_id": self.env.ref("wordpress_api.webletter_template").id,
                }
            ]
        )
        new_letter.validate()
        return f"New letter created with id {new_letter.id}"

    def get_sponsor_info(self, sponsor: ResPartner) -> SupporterInfoModel:
        children = sponsor.sponsored_child_ids
        beneficiaries = [
            BeneficiaryModel(
                global_beneficiary_id=child.global_id,
                local_beneficiary_id=child.local_id,
                firstname=child.firstname,
                preferred_name=child.preferred_name,
            )
            for child in children
        ]
        supporter = SupporterModel(
            global_supporter_id=sponsor.global_id,
            compass_constituent_id=sponsor.ref,
            firstname=sponsor.firstname,
            preferred_name=sponsor.preferred_name or sponsor.firstname,
        )
        return SupporterInfoModel(supporter=supporter, beneficiaries=beneficiaries)
