"""General /queries endpoint to handle gateway queries"""
from typing import Union
import urllib

from fastapi import APIRouter, Depends, HTTPException, Request
from optimade.models import ErrorResponse, ToplevelLinks
from optimade.models.responses import EntryResponseMany
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import (
    get_base_url,
    handle_response_fields,
    meta_values,
)

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.logger import LOGGER
from optimade_gateway.common.utils import clean_python_types
from optimade_gateway.mappers import QueryMapper
from optimade_gateway.models import (
    QueryCreate,
    QueryResource,
    QueriesResponse,
    QueriesResponseSingle,
)
from optimade_gateway.mongo.collection import AsyncMongoCollection
from optimade_gateway.mongo.database import MONGO_DB
from optimade_gateway.routers.utils import validate_resource


ROUTER = APIRouter(redirect_slashes=True)

QUERIES_COLLECTION = AsyncMongoCollection(
    collection=MONGO_DB[CONFIG.queries_collection],
    resource_cls=QueryResource,
    resource_mapper=QueryMapper,
)


@ROUTER.get(
    "/queries",
    response_model=Union[QueriesResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Queries"],
)
async def get_queries(
    request: Request,
    params: EntryListingQueryParams = Depends(),
) -> Union[QueriesResponse, ErrorResponse]:
    """GET /queries

    Return overview of all (active) queries.
    """
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

    return QueriesResponse(
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
    "/queries",
    response_model=Union[QueriesResponseSingle, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Queries"],
)
async def post_queries(
    request: Request,
    query: QueryCreate,
) -> Union[QueriesResponseSingle, ErrorResponse]:
    """POST /queries

    Create or return existing gateway query according to `query`.
    """
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION

    await validate_resource(GATEWAYS_COLLECTION, query.gateway_id)

    mongo_query = {
        "types": {
            "$all": await clean_python_types(query.types),
            "$size": len(query.types),
        },
        "query_parameters": {
            "$eq": await clean_python_types(query.query_parameters),
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
        result = await QUERIES_COLLECTION.create_one(query)
        LOGGER.debug("Created new query in DB: %r", result)
        # TODO: Queue query !
        created = True

    return QueriesResponseSingle(
        links=ToplevelLinks(next=None),
        data=result,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=await QUERIES_COLLECTION.count(),
            more_data_available=more_data_available,
            **{f"_{CONFIG.provider.prefix}_created": created},
        ),
    )


@ROUTER.get(
    "/queries/{query_id}",
    response_model=Union[EntryResponseMany, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Queries"],
)
async def get_query(
    request: Request, query_id: str
) -> Union[EntryResponseMany, ErrorResponse]:
    """GET /queries/{query_id}

    Return the response from a query
    [`QueryResource.attributes.response`][optimade_gateway.models.queries.QueryResourceAttributes.response].
    """
    from optimade_gateway.routers.gateway.utils import get_valid_resource

    query: QueryResource = await get_valid_resource(QUERIES_COLLECTION, query_id)

    if not query.attributes.response or not query.attributes.response.data:
        query.attributes.response = meta_values(
            url=request.url,
            data_returned=0,
            data_available=None,  # It is at this point unknown
            more_data_available=False,
        )

    return query.attributes.response
