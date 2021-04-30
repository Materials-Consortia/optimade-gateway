"""/gateways/{id}/links

This file describes the router for:

    /gateways/{id}/{version}/links

where `version` may be left out.
"""
from typing import Union

from fastapi import APIRouter, Depends, Request
from optimade.models import (
    ErrorResponse,
    LinksResponse,
)
from optimade.server.query_params import EntryListingQueryParams

ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/gateways/{gateway_id}/links",
    response_model=Union[LinksResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Links"],
)
async def get_gateways_links(
    request: Request,
    gateway_id: str,
    params: EntryListingQueryParams = Depends(),
) -> LinksResponse:
    """`GET /gateways/{gateway_id}/links`

    Return a regular `/links` response for an OPTIMADE implementation.
    """
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION
    from optimade_gateway.routers.links import get_links
    from optimade_gateway.routers.utils import validate_resource

    await validate_resource(GATEWAYS_COLLECTION, gateway_id)
    return await get_links(request=request, params=params)


@ROUTER.get(
    "/gateways/{gateway_id}/{version}/links",
    response_model=Union[LinksResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Links"],
)
async def get_versioned_gateways_links(
    request: Request,
    gateway_id: str,
    version: str,
    params: EntryListingQueryParams = Depends(),
) -> LinksResponse:
    """`GET /gateways/{gateway_id}/{version}/links`

    Same as `GET /gateways/{gateway_id}/links`.
    """
    from optimade_gateway.routers.gateway.utils import validate_version

    await validate_version(version)
    return await get_gateways_links(request, gateway_id, params)
