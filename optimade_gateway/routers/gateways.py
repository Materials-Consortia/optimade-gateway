"""/gateways/*

This file describes the router for:

    /gateways/{id}

where, `id` may be left out.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from optimade.models import ToplevelLinks
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import meta_values
from optimade.server.schemas import ERROR_RESPONSES

from optimade_gateway.common.config import CONFIG
from optimade_gateway.mappers import GatewaysMapper
from optimade_gateway.models import (
    GatewayCreate,
    GatewayResource,
    GatewaysResponse,
    GatewaysResponseSingle,
)
from optimade_gateway.mongo.collection import AsyncMongoCollection


ROUTER = APIRouter(redirect_slashes=True)

GATEWAYS_COLLECTION = AsyncMongoCollection(
    name=CONFIG.gateways_collection,
    resource_cls=GatewayResource,
    resource_mapper=GatewaysMapper,
)


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
    params: EntryListingQueryParams = Depends(),
) -> GatewaysResponse:
    """`GET /gateways`

    Return overview of all (active) gateways.
    """
    from optimade_gateway.routers.utils import get_entries

    return await get_entries(
        collection=GATEWAYS_COLLECTION,
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
    from optimade_gateway.common.utils import clean_python_types
    from optimade_gateway.routers.utils import resource_factory

    if gateway.database_ids:
        from optimade_gateway.routers.databases import DATABASES_COLLECTION

        databases = await DATABASES_COLLECTION.get_multiple(
            filter={"id": {"$in": await clean_python_types(gateway.database_ids)}}
        )

        if not isinstance(gateway.databases, list):
            gateway.databases = []

        current_database_ids = [_.id for _ in gateway.databases]
        gateway.databases.extend(
            (_ for _ in databases if _.id not in current_database_ids)
        )

    result, created = await resource_factory(gateway)

    return GatewaysResponseSingle(
        links=ToplevelLinks(next=None),
        data=result,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=await GATEWAYS_COLLECTION.count(),
            more_data_available=False,
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

    Represent an OPTIMADE server.

    !!! note
        For now, redirect to the gateway's `/structures` entry listing endpoint.

    """
    from optimade_gateway.routers.utils import validate_resource

    await validate_resource(GATEWAYS_COLLECTION, gateway_id)
    return RedirectResponse(
        request.url.replace(path=f"{request.url.path.rstrip('/')}/structures")
    )
