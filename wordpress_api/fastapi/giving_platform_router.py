import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from odoo.addons.fastapi.dependencies import odoo_env

from .giving_platform_pydantic_models import (
    DonateResponseModel,
    DonationPostModel,
    FundListModel,
)

router = APIRouter()


# ruff: noqa: B008
def _validate_api_key(
    api_key: Annotated[str, Query()], env: odoo_env = Depends(odoo_env)
):
    """
    Validate the API key against the Odoo environment.
    """
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required.")
    if not hmac.compare_digest(
        api_key, env["res.config.settings"].get_param("giving_platform_api_key", "")
    ):
        raise HTTPException(status_code=403, detail="Invalid API key.")


# ruff: noqa: B008
@router.get("/funds", dependencies=[Depends(_validate_api_key)])
def get_funds(
    env: odoo_env = Depends(odoo_env),
) -> FundListModel:
    """
    ### Retrieves the available funds for donations.
    """
    return env["giving.platform.service"].get_funds()


# ruff: noqa: B008
@router.post("/donate", dependencies=[Depends(_validate_api_key)])
def donate(
    donate_data: DonationPostModel, env: odoo_env = Depends(odoo_env)
) -> DonateResponseModel:
    """
    ### Endpoint for submitting donations.
    """
    return env["giving.platform.service"].donate(donate_data)
