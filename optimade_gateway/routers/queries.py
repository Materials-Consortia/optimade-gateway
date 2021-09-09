"""General /queries endpoint to handle gateway queries

This file describes the router for:

    /queries/{id}

where, `id` may be left out.
"""
# pylint: disable=import-outside-toplevel
import asyncio

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
    status,
)
from optimade.models import ToplevelLinks
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import meta_values
from optimade.server.schemas import ERROR_RESPONSES

from optimade_gateway.common.config import CONFIG
from optimade_gateway.models import (
    QueryCreate,
    QueryResource,
    QueriesResponse,
    QueriesResponseSingle,
)
from optimade_gateway.queries.perform import perform_query
from optimade_gateway.routers.utils import (
    collection_factory,
    get_entries,
    get_valid_resource,
    resource_factory,
    validate_resource,
)


ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/queries",
    response_model=QueriesResponse,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Queries"],
    responses=ERROR_RESPONSES,
)
async def get_queries(
    request: Request,
    params: EntryListingQueryParams = Depends(),
) -> QueriesResponse:
    """`GET /queries`

    Return overview of all (active) queries.
    """
    return await get_entries(
        collection=await collection_factory(CONFIG.queries_collection),
        response_cls=QueriesResponse,
        request=request,
        params=params,
    )


@ROUTER.post(
    "/queries",
    response_model=QueriesResponseSingle,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Queries"],
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
)
async def post_queries(
    request: Request,
    query: QueryCreate,
) -> QueriesResponseSingle:
    """`POST /queries`

    Create or return existing gateway query according to `query`.
    """
    await validate_resource(
        await collection_factory(CONFIG.gateways_collection), query.gateway_id
    )

    result, created = await resource_factory(query)

    if created:
        asyncio.create_task(perform_query(url=request.url, query=result))

    collection = await collection_factory(CONFIG.queries_collection)

    return QueriesResponseSingle(
        links=ToplevelLinks(next=None),
        data=result,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=await collection.acount(),
            more_data_available=False,
            **{f"_{CONFIG.provider.prefix}_created": created},
        ),
    )


@ROUTER.get(
    "/queries/{query_id}",
    response_model=QueriesResponseSingle,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Queries"],
    responses=ERROR_RESPONSES,
)
async def get_query(
    request: Request,
    query_id: str,
    response: Response,
) -> QueriesResponseSingle:
    """`GET /queries/{query_id}`

    Return a single [`QueryResource`][optimade_gateway.models.queries.QueryResource].
    """
    collection = await collection_factory(CONFIG.queries_collection)
    query: QueryResource = await get_valid_resource(collection, query_id)

    if query.attributes.response and query.attributes.response.errors:
        for error in query.attributes.response.errors:
            if error.status:
                for part in error.status.split(" "):
                    try:
                        response.status_code = int(part)
                        break
                    except ValueError:
                        pass
                if response.status_code and response.status_code >= 300:
                    break
        else:
            response.status_code = 500

    return QueriesResponseSingle(
        links=ToplevelLinks(next=None),
        data=query,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=await collection.acount(),
            more_data_available=False,
        ),
    )
