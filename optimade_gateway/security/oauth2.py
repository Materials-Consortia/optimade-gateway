"""OAuth2 functionality."""
from fastapi import Depends
from fastapi.security import OAuth2AuthorizationCodeBearer
import httpx
from pydantic import EmailStr

from optimade_gateway.common.config import CONFIG, AvailableOAuthScopes
from optimade_gateway.common.logger import LOGGER
from optimade_gateway.models.security import (
    OpenIDUserInfoErrorResponse,
    OpenIDUserInfoResponse,
)


OAUTH2_SCHEME = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"https://{CONFIG.marketplace_host.value}/oauth/oauth2/auth",
    tokenUrl=(
        f"https://cors-anywhere.herokuapp.com/https://{CONFIG.marketplace_host.value}"
        "/oauth/oauth2/token"
    ),
    # tokenUrl=f"https://{CONFIG.marketplace_host.value}/oauth/oauth2/token",
    auto_error=False,
    scopes={_.value: _.name for _ in AvailableOAuthScopes},
)

USER_INFO_URL = f"https://{CONFIG.marketplace_host.value}/user-service/userinfo"


async def get_marketplace_user(token: str = Depends(OAUTH2_SCHEME)) -> None:
    """Validate and retrieve the MarketPlace user."""
    if not token:
        LOGGER.warning("No MarketPlace auth token was provided.")
        return None
        # raise Unauthorized(
        #     detail="Invalid authentication credentials",
        #     headers={"WWW-Authenticate": "Bearer"},
        # )

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}
    ) as client:
        user_info_response = await client.get(USER_INFO_URL)

    if user_info_response.is_success:
        user_info = OpenIDUserInfoResponse(**user_info_response.json())
        if user_info.email:
            CONFIG.marketplace_user = EmailStr(user_info.email)
    else:
        user_info_error = OpenIDUserInfoErrorResponse(**user_info_response.json())
        LOGGER.error(
            "Error during retrieving user info data from MarketPlace:\n%s",
            user_info_error.json(indent=2),
        )
