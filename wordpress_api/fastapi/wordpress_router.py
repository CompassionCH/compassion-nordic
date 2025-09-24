from enum import Enum
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from odoo.addons.child_compassion.models.child_compassion import CompassionChild
from odoo.addons.fastapi.dependencies import odoo_env
from odoo.addons.sponsorship_compassion.models.res_partner import ResPartner

from .pydantic_models import (
    ConsignedChildListModel,
    LetterPostModel,
    SupporterInfoModel,
)

router = APIRouter()

LANG_MAPPING = {
    "ENG": "en_US",
    "English": "en_US",
    "SVE": "sv_SE",
    "Swedish": "sv_SE",
    "NOR": "nb_NO",
    "Norwegian": "nb_NO",
    "DAK": "da_DK",
    "Danish": "da_DK",
}


class LanguageCode(str, Enum):
    ENG = "ENG"
    SVE = "SVE"
    NOR = "NOR"
    DAK = "DAK"


# ruff: noqa: B008
def _validate_api_key(
    api_key: Annotated[str, Query()], env: odoo_env = Depends(odoo_env)
):
    """
    Validate the API key against the Odoo environment.
    """
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required.")
    if api_key != env["res.config.settings"].get_param("wordpress_api_key"):
        raise HTTPException(status_code=403, detail="Invalid API key.")


def _fetch_record(model_name: str, global_id: str, env: odoo_env):
    """
    Fetch a record by global ID from the Odoo environment.
    """
    record = (
        env[model_name]
        .with_context(active_test=False)
        .search([("global_id", "=", global_id)])
    )
    if not record:
        model_display_name = model_name.replace(".", " ").title()
        raise HTTPException(
            status_code=404,
            detail=f"{model_display_name} with global ID {global_id} not found.",
        )
    return record


def _fetch_child(
    global_id: Annotated[
        str,
        Path(
            description="The unique identifier for the child. "
            "This ID is obtained from the `key` field for each child object returned "
            "by the `GET /consignment` endpoint."
        ),
    ],
    env: odoo_env = Depends(odoo_env),
) -> CompassionChild:
    return _fetch_record("compassion.child", global_id, env)


def _fetch_sponsor(
    global_id: Annotated[
        str,
        Path(
            description="The unique identifier for the sponsor. It is provided "
            "by the sponsor directly."
        ),
    ],
    env: odoo_env = Depends(odoo_env),
) -> ResPartner:
    return _fetch_record("res.partner", global_id, env)


# ruff: noqa: B008
@router.get("/consignment", dependencies=[Depends(_validate_api_key)])
def get_consigned_children(
    env: odoo_env = Depends(odoo_env),
    limit: int = Query(0, ge=0),
    offset: int = Query(0, ge=0),
    language_code: LanguageCode = Query(LanguageCode.ENG, min_length=2, max_length=3),
) -> ConsignedChildListModel:
    """
    ### Retrieves a paginated list of children who are available for sponsorship.
    This data is intended for display on the *"Sponsor a Child"* page.

    - Use the `limit` and `offset` parameters for pagination.
    - Use the `language_code` parameter to receive the data in a specific language.
    """
    lang = LANG_MAPPING.get(language_code.value, "en_US")
    return env["wordpress.service"].get_consigned_children(lang, limit, offset)


# ruff: noqa: B008
@router.get(
    "/consignment/{global_id}/sponsor", dependencies=[Depends(_validate_api_key)]
)
def sponsor_child(
    child: CompassionChild = Depends(_fetch_child), env: odoo_env = Depends(odoo_env)
):
    """
    ### Basic service for notifying Odoo that a child has been sponsored.
    At the moment it's only used for removing the child from the consignment list.
    In the future it could be extended to create a sponsorship directly from here.
    """
    return env["wordpress.service"].wordpress_sponsor_child(child)


# ruff: noqa: B008
@router.get("/supporter/{global_id}", dependencies=[Depends(_validate_api_key)])
def get_sponsor_info(
    sponsor: ResPartner = Depends(_fetch_sponsor), env: odoo_env = Depends(odoo_env)
) -> SupporterInfoModel:
    """
    ### Retrieves information about a sponsor and their sponsored children.
    This data is intended for the *"Write a Letter"* page, so that the sponsor can
    select which child they want to write to.
    """
    return env["wordpress.service"].get_sponsor_info(sponsor)


# ruff: noqa: B008
@router.post("/letters/write", dependencies=[Depends(_validate_api_key)])
def write_letter(letter_data: LetterPostModel, env: odoo_env = Depends(odoo_env)):
    """
    ### Endpoint for submitting letters.
    `Supporter` and `Beneficiary` values in the request body are provided
    by the `GET /supporter/{global_id}` endpoint.
    """
    return env["wordpress.service"].write_letter(letter_data)
