from typing import Union

from fastapi import APIRouter, Request
from optimade import __api_version__
from optimade.models import (
    BaseInfoAttributes,
    BaseInfoResource,
    ErrorResponse,
    InfoResponse,
)
from optimade.server.exceptions import BadRequest, VersionNotSupported
from optimade.server.routers.utils import get_base_url, meta_values, BASE_URL_PREFIXES

from optimade_gateway.models import GatewayResource

ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/info",
    response_model=Union[InfoResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Info"],
)
async def get_info(request: Request) -> Union[InfoResponse, ErrorResponse]:
    """GET /info

    An intro-spective endpoint for the gateway service.
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
) -> Union[InfoResponse, ErrorResponse]:
    """GET /gateways/{gateway_id}/info

    Return a regular /info response for an OPTIMADE implementation,
    including extra information from all the gateway's databases.
    The general information will be a minimum set from the gateway's databases.
    """
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION

    if not await GATEWAYS_COLLECTION.exists(gateway_id):
        raise BadRequest(
            title="Not Found",
            status_code=404,
            detail=f"gateway <id={gateway_id}> not found.",
        )

    gateway: GatewayResource = await GATEWAYS_COLLECTION.get_one(
        filter={"id": gateway_id}
    )

    return InfoResponse(
        data=BaseInfoResource(
            id=BaseInfoResource.schema()["properties"]["id"]["const"],
            type=BaseInfoResource.schema()["properties"]["type"]["const"],
            attributes=BaseInfoAttributes(
                api_version=__api_version__,
                available_api_versions=[
                    {
                        "url": f"{get_base_url(request.url)}/v{__api_version__.split('.')[0]}/gateways/{gateway_id}",
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
            optimade_gateway={
                "databases": [
                    {"id": _.id, "type": _.type} for _ in gateway.attributes.databases
                ],
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
) -> Union[InfoResponse, ErrorResponse]:
    """GET /gateways/{gateway_id}/{version}/info

    Same as GET /gateways/{gateway_id}/info.
    """
    valid_versions = [_[1:] for _ in BASE_URL_PREFIXES.values()]

    if version not in valid_versions:
        if version.startswith("v"):
            raise VersionNotSupported(
                detail=f"version {version} is not supported. Supported versions: {valid_versions}"
            )
        else:
            raise BadRequest(
                title="Not Found",
                status_code=404,
                detail=f"version MUST be one of {valid_versions}",
            )

    return await get_gateways_info(request, gateway_id)
