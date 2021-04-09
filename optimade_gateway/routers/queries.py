"""General /queries endpoint to handle gateway queries

This file describes the router for:

    /queries/{id}

where, `id` may be left out.
"""
from typing import Tuple, Union
import urllib

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
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
from optimade_gateway.mappers import QueryMapper
from optimade_gateway.models import (
    QueryCreate,
    QueryResource,
    QueryState,
    QueriesResponse,
    QueriesResponseSingle,
)
from optimade_gateway.mongo.collection import AsyncMongoCollection


ROUTER = APIRouter(redirect_slashes=True)

QUERIES_COLLECTION = AsyncMongoCollection(
    name=CONFIG.queries_collection,
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
) -> QueriesResponse:
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


async def get_or_create_query(query: QueryCreate) -> Tuple[QueryResource, bool]:
    """Utility function to get a query

    If a query is not found in the MongoDB collection a new one will be created.

    Parameters:
        query: A gateway as presented from a POST request, i.e., a
            [`QueryCreate`][optimade_gateway.models.gateways.GatewayCreate].

    Returns:
        Two things in a tuple:

        - The [`GatewayResource`][optimade_gateway.models.queries.QueryResource]; and
        - whether or not the resource was newly created.

    """
    from optimade_gateway.common.utils import clean_python_types

    created = False

    # Currently only /structures entry endpoints can be queried with multiple expected responses.
    query.endpoint = query.endpoint if query.endpoint else "structures"
    query.endpoint_model = (
        query.endpoint_model
        if query.endpoint_model
        else ("optimade.models.responses", "StructureResponseMany")
    )

    mongo_query = {
        "gateway_id": {"$eq": query.gateway_id},
        "query_parameters": {
            "$eq": await clean_python_types(query.query_parameters),
        },
        "endpoint": {"$eq": query.endpoint},
    }
    result, more_data_available, _ = await QUERIES_COLLECTION.find(
        criteria={"filter": mongo_query}
    )

    if more_data_available:
        raise HTTPException(
            status_code=500,
            detail=(
                "more_data_available MUST be False for a single entry response, however it is "
                f"{more_data_available}"
            ),
        )

    if result:
        if isinstance(result, list) and len(result) != 1:
            raise HTTPException(
                status_code=500,
                detail=f"More than one gateway was found. IDs of found gateways: {[_.id for _ in result]}",
            )
        result = result[0]
    else:
        query.state = QueryState.CREATED
        result = await QUERIES_COLLECTION.create_one(query)
        LOGGER.debug("Created new query: %r", result)
        created = True

    return result, created


@ROUTER.post(
    "/queries",
    response_model=Union[QueriesResponseSingle, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Queries"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_queries(
    request: Request,
    query: QueryCreate,
    running_queries: BackgroundTasks,
) -> QueriesResponseSingle:
    """POST /queries

    Create or return existing gateway query according to `query`.
    """
    from optimade_gateway.queries import perform_query
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION
    from optimade_gateway.routers.utils import validate_resource

    await validate_resource(GATEWAYS_COLLECTION, query.gateway_id)

    result, created = await get_or_create_query(query)

    if created:
        running_queries.add_task(
            perform_query, url=request.url, query=result, use_query_resource=True
        )

    return QueriesResponseSingle(
        links=ToplevelLinks(next=None),
        data=result,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=await QUERIES_COLLECTION.count(),
            more_data_available=False,
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
    request: Request,
    query_id: str,
    response: Response,
) -> Union[EntryResponseMany, ErrorResponse]:
    """GET /queries/{query_id}

    Return the response from a query
    [`QueryResource.attributes.response`][optimade_gateway.models.queries.QueryResourceAttributes.response].
    """
    from optimade_gateway.routers.gateway.utils import get_valid_resource

    query: QueryResource = await get_valid_resource(QUERIES_COLLECTION, query_id)

    if query.attributes.state != QueryState.FINISHED:
        return EntryResponseMany(
            data=[],
            meta=meta_values(
                url=request.url,
                data_returned=0,
                data_available=None,  # It is at this point unknown
                more_data_available=False,
                **{f"_{CONFIG.provider.prefix}_query": query},
            ),
        )

    if query.attributes.response.errors:
        for error in query.attributes.response.errors:
            if error.status:
                response.status_code = int(error.status)
                break
        else:
            response.status_code = 500

    return query.attributes.response
