"""Special /queries endpoint for a gateway to perform and list queries"""
from typing import Union
import urllib

from fastapi import APIRouter, Depends, Request
from optimade.models import ErrorResponse, ToplevelLinks
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import (
    get_base_url,
    handle_response_fields,
    meta_values,
)

from optimade_gateway.common.config import CONFIG
from optimade_gateway.mappers import GatewayQueryMapper
from optimade_gateway.models import GatewayQueryResource, GatewaysQueriesResponse
from optimade_gateway.mongo.collection import AsyncMongoCollection
from optimade_gateway.mongo.database import MONGO_DB


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
    from optimade_gateway.routers.utils import validate_resource

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
