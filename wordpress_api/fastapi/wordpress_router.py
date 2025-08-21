from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from odoo.addons.child_compassion.models.child_compassion import CompassionChild
from odoo.addons.fastapi.dependencies import odoo_env
from odoo.addons.sponsorship_compassion.models.res_partner import ResPartner

from .pydantic_models import (
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
}


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


def _fetch_child(global_id: str, env: odoo_env = Depends(odoo_env)) -> CompassionChild:
    return _fetch_record("compassion.child", global_id, env)


def _fetch_sponsor(global_id: str, env: odoo_env = Depends(odoo_env)) -> ResPartner:
    return _fetch_record("res.partner", global_id, env)


# ruff: noqa: B008
@router.get("/consignment", dependencies=[Depends(_validate_api_key)])
def get_consigned_children(
    env: odoo_env = Depends(odoo_env),
    limit: int = Query(0, ge=0),
    offset: int = Query(0, ge=0),
    language_code: str = Query("ENG", min_length=2, max_length=3),
):
    lang = LANG_MAPPING.get(language_code, "en_US")
    return env["wordpress.service"].get_consigned_children(lang, limit, offset)


# ruff: noqa: B008
@router.get(
    "/consignment/{global_id}/sponsor", dependencies=[Depends(_validate_api_key)]
)
def sponsor_child(
    child: CompassionChild = Depends(_fetch_child), env: odoo_env = Depends(odoo_env)
):
    return env["wordpress.service"].wordpress_sponsor_child(child)


# ruff: noqa: B008
@router.post("/letters/write", dependencies=[Depends(_validate_api_key)])
def write_letter(letter_data: LetterPostModel, env: odoo_env = Depends(odoo_env)):
    return env["wordpress.service"].write_letter(letter_data)


# ruff: noqa: B008
@router.get("/supporter/{global_id}", dependencies=[Depends(_validate_api_key)])
def get_sponsor_info(
    sponsor: ResPartner = Depends(_fetch_sponsor), env: odoo_env = Depends(odoo_env)
) -> SupporterInfoModel:
    return env["wordpress.service"].get_sponsor_info(sponsor)
