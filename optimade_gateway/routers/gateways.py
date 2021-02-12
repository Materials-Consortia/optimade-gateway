from typing import Union
import urllib

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from optimade.models import ErrorResponse, ToplevelLinks
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import (
    get_base_url,
    handle_response_fields,
    meta_values,
)

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
from optimade_gateway.mongo.database import MONGO_DB


ROUTER = APIRouter(redirect_slashes=True)

GATEWAYS_COLLECTION = AsyncMongoCollection(
    collection=MONGO_DB[CONFIG.gateways_collection],
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
    gateways, more_data_available, fields = await GATEWAYS_COLLECTION.find(
        params=params
    )

    if more_data_available:
        # Deduce the `next` link from the current request
        query = urllib.parse.parse_qs(request.url.query)
        query["page_offset"] = int(query.get("page_offset", [0])[0]) + len(gateways)
        urlencoded = urllib.parse.urlencode(query, doseq=True)
        base_url = get_base_url(request.url)

        links = ToplevelLinks(next=f"{base_url}{request.url.path}?{urlencoded}")
    else:
        links = ToplevelLinks(next=None)

    if fields:
        gateways = handle_response_fields(gateways, fields)

    return GatewaysResponse(
        links=links,
        data=gateways,
        meta=meta_values(
            url=request.url,
            data_returned=GATEWAYS_COLLECTION.data_returned,
            data_available=GATEWAYS_COLLECTION.data_available,
            more_data_available=more_data_available,
        ),
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
                GATEWAYS_COLLECTION.data_available + 1
                if created
                else GATEWAYS_COLLECTION.data_available
            ),
            more_data_available=more_data_available,
            _optimade_gateway_created=created,
        ),
    )


@ROUTER.get(
    "/gateways/{gateway_id}",
    response_model=Union[GatewaysResponseSingle, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
    tags=["Gateways"],
)
async def get_gateway(
    request: Request, gateway_id: str
) -> Union[GatewaysResponseSingle, ErrorResponse]:
    """GET /gateways/{gateway ID}

    Represent an OPTIMADE server.
    NOTE: For now, redirect to the gateway's /structures entry listing endpoint
    """
    return RedirectResponse(
        request.url.replace(path=f"{request.url.path.rstrip('/')}/structures")
    )
