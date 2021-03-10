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
    "/gateways/{gateway_id}/info",
    response_model=Union[InfoResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Info"],
)
async def get_gateways_info(
    request: Request,
    gateway_id: str,
) -> InfoResponse:
    """GET /gateways/{gateway_id}/info

    Return a regular /info response for an OPTIMADE implementation,
    including extra information from all the gateway's databases.
    The general information will be a minimum set from the gateway's databases.
    """
    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.routers.gateway.utils import get_valid_gateway

    gateway = await get_valid_gateway(gateway_id)

    return InfoResponse(
        data=BaseInfoResource(
            id=BaseInfoResource.schema()["properties"]["id"]["const"],
            type=BaseInfoResource.schema()["properties"]["type"]["const"],
            attributes=BaseInfoAttributes(
                api_version=__api_version__,
                available_api_versions=[
                    {
                        "url": f"{get_base_url(request.url)}/v{__api_version__.split('.')[0]}/gateways/{gateway_id}/v{__api_version__.split('.')[0]}",
                        "version": __api_version__,
                    }
                ],
                formats=["json"],
                entry_types_by_format={"json": ["structures"]},
                available_endpoints=["info", "links", "structures"],
                is_index=False,
            ),
        ),
        meta=meta_values(
            request.url,
            data_returned=1,
            data_available=1,
            more_data_available=False,
            **{
                f"_{CONFIG.provider.prefix}_gateway": {
                    "databases": [
                        {"id": _.id, "type": _.type}
                        for _ in gateway.attributes.databases
                    ],
                }
            },
        ),
    )


@ROUTER.get(
    "/gateways/{gateway_id}/{version}/info",
    response_model=Union[InfoResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Info"],
)
async def get_versioned_gateways_info(
    request: Request,
    gateway_id: str,
    version: str,
) -> InfoResponse:
    """GET /gateways/{gateway_id}/{version}/info

    Same as GET /gateways/{gateway_id}/info.
    """
    from optimade_gateway.routers.gateway.utils import validate_version

    await validate_version(version)
    return await get_gateways_info(request, gateway_id)
