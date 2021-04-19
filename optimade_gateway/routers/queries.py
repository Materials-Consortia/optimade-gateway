"""General /queries endpoint to handle gateway queries

This file describes the router for:

    /queries/{id}

where, `id` may be left out.
"""
import asyncio
from typing import Union

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    status,
)
from optimade.models import ErrorResponse, ToplevelLinks
from optimade.models.responses import EntryResponseMany
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import meta_values

from optimade_gateway.common.logger import LOGGER
from optimade_gateway.common.config import CONFIG
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
    from optimade_gateway.routers.utils import get_entries

    return await get_entries(
        collection=QUERIES_COLLECTION,
        response_cls=QueriesResponse,
        request=request,
        params=params,
    )


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
) -> QueriesResponseSingle:
    """POST /queries

    Create or return existing gateway query according to `query`.
    """
    from optimade_gateway.queries import perform_query
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION
    from optimade_gateway.routers.utils import resource_factory, validate_resource

    await validate_resource(GATEWAYS_COLLECTION, query.gateway_id)

    result, created = await resource_factory(query)

    if created:
        asyncio.create_task(
            perform_query(url=request.url, query=result, use_query_resource=True)
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
    "/queries/{query_id:path}",
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
    from optimade_gateway.routers.utils import get_valid_resource

    LOGGER.debug("At /queries/<id> with id=%s", query_id)
    query: QueryResource = await get_valid_resource(QUERIES_COLLECTION, query_id)
    LOGGER.debug("Found query (in /queries/<id>): %s", query)

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
