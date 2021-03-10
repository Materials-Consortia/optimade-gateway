from typing import Union

from fastapi import APIRouter, Request
from optimade import __api_version__
from optimade.models import (
    BaseInfoAttributes,
    BaseInfoResource,
    ErrorResponse,
    InfoResponse,
)
from optimade.server.routers.utils import get_base_url, meta_values

ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/info",
    response_model=Union[InfoResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Info"],
)
async def get_info(request: Request) -> InfoResponse:
    """GET /info

    An introspective endpoint for the gateway service.
    """
    return InfoResponse(
        data=BaseInfoResource(
            id=BaseInfoResource.schema()["properties"]["id"]["const"],
            type=BaseInfoResource.schema()["properties"]["type"]["const"],
            attributes=BaseInfoAttributes(
                api_version=__api_version__,
                available_api_versions=[
                    {
                        "url": f"{get_base_url(request.url)}/v{__api_version__.split('.')[0]}",
                        "version": __api_version__,
                    }
                ],
                formats=["json"],
                entry_types_by_format={"json": ["gateways"]},
                available_endpoints=[
                    "docs",
                    "gateways",
                    "info",
                    "links",
                    "openapi.json",
                    "redoc",
                ],
                is_index=False,
            ),
        ),
        meta=meta_values(
            request.url,
            data_returned=1,
            data_available=1,
            more_data_available=False,
        ),
    )
