"""/gateways/*

This file describes the router for:

    /gateways/{id}

where, `id` may be left out.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from optimade.models import ToplevelLinks
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import meta_values
from optimade.server.schemas import ERROR_RESPONSES

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.utils import clean_python_types
from optimade_gateway.models import (
    GatewayCreate,
    GatewaysResponse,
    GatewaysResponseSingle,
)
from optimade_gateway.routers.utils import (
    collection_factory,
    get_entries,
    get_valid_resource,
    resource_factory,
)

ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/gateways",
    response_model=GatewaysResponse,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Gateways"],
    responses=ERROR_RESPONSES,
)
async def get_gateways(
    request: Request,
    params: Annotated[EntryListingQueryParams, Depends()],
) -> GatewaysResponse:
    """`GET /gateways`

    Return overview of all (active) gateways.
    """
    return await get_entries(
        collection=await collection_factory(CONFIG.gateways_collection),
        response_cls=GatewaysResponse,
        request=request,
        params=params,
    )


@ROUTER.post(
    "/gateways",
    response_model=GatewaysResponseSingle,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Gateways"],
    responses=ERROR_RESPONSES,
)
async def post_gateways(
    request: Request, gateway: GatewayCreate
) -> GatewaysResponseSingle:
    """`POST /gateways`

    Create or return existing gateway according to `gateway`.
    """
    if gateway.database_ids:
        databases_collection = await collection_factory(CONFIG.databases_collection)

        databases = await databases_collection.get_multiple(
            filter={"id": {"$in": await clean_python_types(gateway.database_ids)}}
        )

        if not isinstance(gateway.databases, list):
            gateway.databases = []

        current_database_ids = [_.id for _ in gateway.databases]
        gateway.databases.extend(
            _ for _ in databases if _.id not in current_database_ids
        )

    result, created = await resource_factory(gateway)
    collection = await collection_factory(CONFIG.gateways_collection)

    return GatewaysResponseSingle(
        links=ToplevelLinks(next=None),
        data=result,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=await collection.acount(),
            more_data_available=False,
            schema=CONFIG.schema_url,
            **{f"_{CONFIG.provider.prefix}_created": created},
        ),
    )


@ROUTER.get(
    "/gateways/{gateway_id}",
    response_model=GatewaysResponseSingle,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Gateways"],
    responses=ERROR_RESPONSES,
)
async def get_gateway(request: Request, gateway_id: str) -> GatewaysResponseSingle:
    """`GET /gateways/{gateway ID}`

    Return a single
    [`GatewayResource`][optimade_gateway.models.gateways.GatewayResource].
    """
    collection = await collection_factory(CONFIG.gateways_collection)
    result = await get_valid_resource(collection, gateway_id)

    return GatewaysResponseSingle(
        links=ToplevelLinks(next=None),
        data=result,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=await collection.acount(),
            more_data_available=False,
            schema=CONFIG.schema_url,
        ),
    )
