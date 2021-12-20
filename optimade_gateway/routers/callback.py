"""/callback

This file describes the router for:

    /callback

This is an endpoint used for OAuth2 flows.
"""
from fastapi import APIRouter, Request
import httpx
from optimade.server.exceptions import UnprocessableEntity
from pydantic import ValidationError

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.exceptions import ERROR_RESPONSES
from optimade_gateway.models.security import (
    OpenIDUserInfoResponse,
    OpenIDUserInfoErrorResponse,
)


ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/callback",
    response_model=OpenIDUserInfoResponse,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Security"],
    responses=ERROR_RESPONSES,
)
async def get_callback(request: Request) -> OpenIDUserInfoResponse:
    """`GET /callback`."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        user_info = await client.get(
            f"https://{CONFIG.marketplace_host.value}/user-service/userinfo",
            headers=request.headers,
        )
    user_info_data = user_info.json()

    try:
        res = OpenIDUserInfoErrorResponse(**user_info_data)
    except ValidationError:
        res = OpenIDUserInfoResponse(**user_info_data)
    else:
        raise UnprocessableEntity(
            detail=(
                "An error occurred when trying to retrieve the user information: "
                f"{res}"
            )
        )

    return res
