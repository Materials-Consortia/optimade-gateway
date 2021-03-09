"""Special /queries endpoint for a gateway to perform and list queries"""
from typing import Union
import urllib

from fastapi import APIRouter, Depends, HTTPException, Request
from optimade.models import ErrorResponse, ToplevelLinks
from optimade.models.responses import EntryResponseMany
from optimade.server.exceptions import BadRequest
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import (
    get_base_url,
    handle_response_fields,
    meta_values,
)

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.logger import LOGGER
from optimade_gateway.common.utils import clean_python_types
from optimade_gateway.mappers import GatewayQueryMapper
from optimade_gateway.models import (
    GatewayQueryCreate,
    GatewayQueryResource,
    GatewaysQueriesResponse,
    GatewaysQueriesResponseSingle,
)
from optimade_gateway.mongo.collection import AsyncMongoCollection
from optimade_gateway.mongo.database import MONGO_DB
from optimade_gateway.routers.utils import validate_resource


ROUTER = APIRouter(redirect_slashes=True)

QUERIES_COLLECTION = AsyncMongoCollection(
    collection=MONGO_DB[CONFIG.queries_collection],
    resource_cls=GatewayQueryResource,
    resource_mapper=GatewayQueryMapper,
    cached_properties=[],  # Don't use in-memory caching
)


@ROUTER.get(
    "/gateways/{gateway_id}/queries",
    response_model=Union[GatewaysQueriesResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Queries"],
)
async def get_queries(
    request: Request,
    gateway_id: str,
    params: EntryListingQueryParams = Depends(),
) -> Union[GatewaysQueriesResponse, ErrorResponse]:
    """GET /gateways/{gateway_id}/queries

    Return overview of all (active) queries for specific gateway.
    """
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION

    await validate_resource(GATEWAYS_COLLECTION, gateway_id)

    params.filter = (
        f'( {params.filter} ) AND ( gateway="{gateway_id}" )'
        if params.filter
        else f'gateway="{gateway_id}"'
    )
    queries, more_data_available, fields = await QUERIES_COLLECTION.find(params=params)

    if more_data_available:
        # Deduce the `next` link from the current request
        query = urllib.parse.parse_qs(request.url.query)
        query["page_offset"] = int(query.get("page_offset", [0])[0]) + len(queries)
        urlencoded = urllib.parse.urlencode(query, doseq=True)
        base_url = get_base_url(request.url)

        links = ToplevelLinks(next=f"{base_url}{request.url.path}?{urlencoded}")
    else:
        links = ToplevelLinks(next=None)

    if fields:
        queries = handle_response_fields(queries, fields)

    return GatewaysQueriesResponse(
        links=links,
        data=queries,
        meta=meta_values(
            url=request.url,
            data_returned=await QUERIES_COLLECTION.count(params=params),
            data_available=await QUERIES_COLLECTION.count(),
            more_data_available=more_data_available,
        ),
    )


@ROUTER.post(
    "/gateways/{gateway_id}/queries",
    response_model=Union[GatewaysQueriesResponseSingle, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Queries"],
)
async def post_queries(
    request: Request,
    gateway_id: str,
    gateway_query: GatewayQueryCreate,
) -> Union[GatewaysQueriesResponseSingle, ErrorResponse]:
    """POST /gateways/{gateway_id}/queries

    Create or return existing gateway query according to `gateway_query`.
    """
    if gateway_query.gateway and gateway_query.gateway != gateway_id:
        raise BadRequest(
            status_code=403,
            title="Forbidden",
            detail=f"The gateway ID in the posted data (<gateway={gateway_query.gateway}>)does not align with the gateway ID specified in the URL (/{gateway_id}/).",
        )

    mongo_query = {
        "types": {
            "$all": await clean_python_types(gateway_query.types),
            "$size": len(gateway_query.types),
        },
        "query_parameters": {
            "$all": await clean_python_types(gateway_query.query_parameters),
        },
    }
    result, more_data_available, _ = await QUERIES_COLLECTION.find(
        criteria={"filter": mongo_query}
    )

    if more_data_available:
        raise HTTPException(
            status_code=500,
            detail=f"more_data_available MUST be False for a single entry response, however it is {more_data_available}",
        )

    created = False
    if not result:
        result = await QUERIES_COLLECTION.create_one(gateway_query)
        LOGGER.debug("Created new gateway query in DB: %r", result)
        # TODO: Queue query !
        created = True

    return GatewaysQueriesResponseSingle(
        links=ToplevelLinks(next=None),
        data=result,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=await QUERIES_COLLECTION.count(),
            more_data_available=more_data_available,
            _optimade_gateway_query_created=created,
        ),
    )


@ROUTER.get(
    "/gateways/{gateway_id}/queries/{query_id}",
    response_model=Union[EntryResponseMany, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Query"],
)
async def get_gateway(
    request: Request, gateway_id: str, query_id: str
) -> Union[EntryResponseMany, ErrorResponse]:
    """GET /gateways/{gateway_id}/queries/{query_id}

    Return the response from a gateway query
    [`GatewayQueryResource.attributes.response`][optimade_gateway.models.queries.GatewayQueryResourceAttributes.response].
    """
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION
    from optimade_gateway.routers.gateway.utils import get_valid_resource

    await validate_resource(GATEWAYS_COLLECTION, gateway_id)

    query: GatewayQueryResource = await get_valid_resource(QUERIES_COLLECTION, query_id)

    if not query.attributes.response or not query.attributes.response.data:
        query.attributes.response = meta_values(
            url=request.url,
            data_returned=0,
            data_available=None,  # It is at this point unknown
            more_data_available=False,
        )

    return query.attributes.response
