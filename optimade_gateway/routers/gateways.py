from typing import Union

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from optimade.models import ErrorResponse, ToplevelLinks
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import meta_values

from optimade_gateway.mappers import GatewaysMapper
from optimade_gateway.models import (
    GatewayCreate,
    GatewayResource,
    GatewaysResponse,
    GatewaysResponseSingle,
)
from optimade_gateway.mongo.collection import AsyncMongoCollection
from optimade_gateway.mongo.database import MONGO_CLIENT


ROUTER = APIRouter(redirect_slashes=True)

GATEWAY_COLLECTION = AsyncMongoCollection(
    collection=MONGO_CLIENT["optimade_gateway"]["gateways"],
    resource_cls=GatewayResource,
    resource_mapper=GatewaysMapper,
    cached_properties=[],  # Don't use in-memory caching
)


@ROUTER.get(
    "/gateways",
    response_model=Union[GatewaysResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
    tags=["Gateways"],
)
async def get_gateways(
    request: Request,
    params: EntryListingQueryParams = Depends(),
) -> Union[GatewaysResponse, ErrorResponse]:
    """GET /gateways

    Return overview of all (active) gateways.
    """
    gateways = []  # get_all_gateways()
    included = []

    return GatewaysResponse(
        links=ToplevelLinks(next=None),
        data=gateways,
        meta=meta_values(
            url=request.url,
            data_returned=len(gateways),
            data_available=len(gateways),
            more_data_available=False,
        ),
        included=included,
    )


@ROUTER.post(
    "/gateways",
    response_model=Union[GatewaysResponseSingle, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
    tags=["Gateways"],
)
async def post_gateways(
    request: Request, gateway: GatewayCreate
) -> Union[GatewaysResponseSingle, ErrorResponse]:
    """POST /gateways

    Create or return existing gateway according to `gateway`.
    """
    mongo_query = {
        "databases": {"$all": gateway.databases, "$size": len(gateway.databases)}
    }
    result, more_data_available, _ = await GATEWAY_COLLECTION.find(
        criteria={"filter": mongo_query}
    )

    if more_data_available:
        raise HTTPException(
            status_code=500,
            detail=f"more_data_available MUST be False for a single entry response, however it is {more_data_available}",
        )

    created = False
    if result is None:
        result = await GATEWAY_COLLECTION.create_one(gateway)
        created = True

    return GatewaysResponseSingle(
        links=ToplevelLinks(next=None),
        data=result,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=GATEWAY_COLLECTION.data_available + 1
            if created
            else GATEWAY_COLLECTION.data_available,
            more_data_available=more_data_available,
            _optimade_gateway_created=created,
        ),
    )


@ROUTER.get(
    "/gateways/{gateway_id}",
    response_model=RedirectResponse,
    response_model_exclude_defaults=False,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
    tags=["Gateways"],
)
async def get_gateway(
    request: Request, gateway_id: int
) -> Union[GatewaysResponseSingle, ErrorResponse]:
    """GET /gateways/{gateway ID}

    Represent an OPTIMADE server.
    For now, redirect to the gateway's /structures entry listing endpoint
    """
    return RedirectResponse(f"{request.url}/structures")
