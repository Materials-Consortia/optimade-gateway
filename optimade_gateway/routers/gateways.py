"""/gateways/*

This file describes the router for:

    /gateways/{id}

where, `id` may be left out.
"""
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from optimade.models import ErrorResponse, ToplevelLinks
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import meta_values

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.logger import LOGGER
from optimade_gateway.common.utils import clean_python_types
from optimade_gateway.mappers import GatewaysMapper
from optimade_gateway.models import (
    GatewayCreate,
    GatewayResource,
    GatewaysResponse,
    GatewaysResponseSingle,
)
from optimade_gateway.mongo.collection import AsyncMongoCollection

from optimade_gateway.routers.utils import get_entries


ROUTER = APIRouter(redirect_slashes=True)

GATEWAYS_COLLECTION = AsyncMongoCollection(
    name=CONFIG.gateways_collection,
    resource_cls=GatewayResource,
    resource_mapper=GatewaysMapper,
)


@ROUTER.get(
    "/gateways",
    response_model=Union[GatewaysResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Gateways"],
)
async def get_gateways(
    request: Request,
    params: EntryListingQueryParams = Depends(),
) -> GatewaysResponse:
    """GET /gateways

    Return overview of all (active) gateways.
    """
    return await get_entries(
        collection=GATEWAYS_COLLECTION,
        response_cls=GatewaysResponse,
        request=request,
        params=params,
    )


@ROUTER.post(
    "/gateways",
    response_model=Union[GatewaysResponseSingle, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Gateways"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_gateways(
    request: Request, gateway: GatewayCreate
) -> GatewaysResponseSingle:
    """POST /gateways

    Create or return existing gateway according to `gateway`.
    """
    mongo_query = {
        "databases": {
            "$all": await clean_python_types(gateway.databases),
            "$size": len(gateway.databases),
        }
    }
    result, more_data_available, _ = await GATEWAYS_COLLECTION.find(
        criteria={"filter": mongo_query}
    )

    if more_data_available:
        raise HTTPException(
            status_code=500,
            detail=f"more_data_available MUST be False for a single entry response, however it is {more_data_available}",
        )

    created = False
    if not result:
        result = await GATEWAYS_COLLECTION.create_one(gateway)
        LOGGER.debug("Created new gateway: %r", result)
        created = True

    return GatewaysResponseSingle(
        links=ToplevelLinks(next=None),
        data=result,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=(
                await GATEWAYS_COLLECTION.count() + 1
                if created
                else await GATEWAYS_COLLECTION.count()
            ),
            more_data_available=more_data_available,
            **{f"_{CONFIG.provider.prefix}_created": created},
        ),
    )


@ROUTER.get(
    "/gateways/{gateway_id}",
    response_model=Union[GatewaysResponseSingle, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Gateways"],
)
async def get_gateway(request: Request, gateway_id: str) -> GatewaysResponseSingle:
    """GET /gateways/{gateway ID}

    Represent an OPTIMADE server.
    NOTE: For now, redirect to the gateway's /structures entry listing endpoint
    """
    from optimade_gateway.routers.utils import validate_resource

    await validate_resource(GATEWAYS_COLLECTION, gateway_id)
    return RedirectResponse(
        request.url.replace(path=f"{request.url.path.rstrip('/')}/structures")
    )
