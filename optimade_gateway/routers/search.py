"""General /search endpoint to completely coordinate an OPTIMADE gateway query

This file describes the router for:

    /search

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
from fastapi.responses import RedirectResponse
from optimade.models import (
    EntryResponseMany,
    ErrorResponse,
    LinksResource,
    LinksResourceAttributes,
)
from optimade.models.links import LinkType
from starlette.background import BackgroundTasks

from optimade_gateway.models import (
    GatewayCreate,
    QueriesResponseSingle,
    QueryCreate,
    QueryResource,
    Search,
)
from optimade_gateway.models.queries import OptimadeQueryParameters, QueryState
from optimade_gateway.queries.params import SearchQueryParams


ROUTER = APIRouter(redirect_slashes=True)

ENDPOINT_MODELS = {
    "structures": ("optimade.models.responses", "StructureResponseMany"),
    "references": ("optimade.models.responses", "ReferenceResponseMany"),
    "links": ("optimade.models.responses", "LinksResponse"),
}


@ROUTER.post(
    "/search",
    response_model=Union[QueriesResponseSingle, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Search"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def post_search(
    request: Request, search: Search, running_queries: BackgroundTasks
) -> QueriesResponseSingle:
    """POST /search

    Coordinate a new OPTIMADE query in multiple databases through a gateway:

    1. ~Search for gateway in DB using `optimade_urls`~
    1. Create `GatewayCreate` model
    1. GET a gateway ID - calling /gateways
    1. Create new Query resource
    1. POST Query resource - calling /queries
    1. Return POST /queries response

    """
    from optimade_gateway.routers.gateways import post_gateways
    from optimade_gateway.routers.queries import post_queries

    search.optimade_urls = (
        search.optimade_urls
        if isinstance(search.optimade_urls, list)
        else [search.optimade_urls]
    )

    gateways_response = await post_gateways(
        request,
        gateway=GatewayCreate(
            databases=[
                LinksResource(
                    id=(
                        f"{url.user + '@' if url.user else ''}{url.host}"
                        f"{':' + url.port if url.port else ''}"
                        f"{url.path.rstrip('/') if url.path else ''}"
                    ),
                    type="links",
                    attributes=LinksResourceAttributes(
                        name=(
                            f"{url.user + '@' if url.user else ''}{url.host}"
                            f"{':' + url.port if url.port else ''}"
                            f"{url.path.rstrip('/') if url.path else ''}"
                        ),
                        description="",
                        base_url=url,
                        link_type=LinkType.CHILD,
                    ),
                )
                for url in search.optimade_urls
            ]
        ),
    )

    return await post_queries(
        request,
        running_queries=running_queries,
        query=QueryCreate(
            endpoint=search.endpoint,
            endpoint_model=ENDPOINT_MODELS.get(search.endpoint),
            gateway_id=(
                gateways_response.data.get("id")
                if isinstance(gateways_response.data, dict)
                else gateways_response.data.id
            ),
            query_parameters=search.query_parameters,
        ),
    )


@ROUTER.get(
    "/search",
    response_model=Union[EntryResponseMany, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Search"],
)
async def get_search(
    request: Request,
    response: Response,
    running_queries: BackgroundTasks,
    params: SearchQueryParams = Depends(),
) -> Union[EntryResponseMany, ErrorResponse, RedirectResponse]:
    """GET /search

    Coordinate a new OPTIMADE query in multiple databases through a gateway:

    1. GET a gateway ID - calling /gateways
    2. Create new Query resource
    3. POST Query resource - calling /queries
    4. Wait until query finishes - set a timeout period
    5. Return successful response

    Contingency: If the query has not succeeded within the set timeout period, the client will
    be redirected to the query instead.

    """
    from time import time
    from optimade_gateway.routers.queries import QUERIES_COLLECTION

    search = Search(
        query_parameters=OptimadeQueryParameters(
            **{
                field: getattr(params, field)
                for field in OptimadeQueryParameters.__fields_set__
                if getattr(params, field)
            }
        ),
        optimade_urls=params.optimade_urls,
        endpoint=params.endpoint,
    )

    post_response = await post_search(
        request, search=search, running_queries=running_queries
    )

    start_time = time()
    while time() < (start_time + params.timeout):
        query: QueryResource = await QUERIES_COLLECTION.get_one(
            {
                "id": {
                    "$eq": (
                        post_response.data.get("id")
                        if isinstance(post_response.data, dict)
                        else post_response.data.id
                    )
                }
            }
        )

        if query.attributes.state == QueryState.FINISHED:
            if query.attributes.response.errors:
                for error in query.attributes.response.errors:
                    if error.status:
                        response.status_code = int(error.status)
                        break
                else:
                    response.status_code = 500

            return query.attributes.response

        await asyncio.sleep(0.2)

    # The query has not yet succeeded and we're past the timeout time -> Redirect to the query
    return RedirectResponse(query.links.self)
