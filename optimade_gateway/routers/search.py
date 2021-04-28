"""General /search endpoint to completely coordinate an OPTIMADE gateway query

This file describes the router for:

    /search

"""
import asyncio
from typing import Union

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from optimade.server.exceptions import BadRequest
from optimade.models import (
    EntryResponseMany,
    ErrorResponse,
    LinksResource,
    LinksResourceAttributes,
    ToplevelLinks,
)
from optimade.models.links import LinkType
from optimade.models import StructureResponseMany, ReferenceResponseMany, LinksResponse
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import meta_values
from pydantic import AnyUrl, ValidationError

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.logger import LOGGER
from optimade_gateway.common.utils import clean_python_types, get_resource_attribute
from optimade_gateway.models import (
    GatewayCreate,
    QueriesResponseSingle,
    QueryCreate,
    QueryResource,
    Search,
)
from optimade_gateway.models.queries import OptimadeQueryParameters, QueryState
from optimade_gateway.queries import perform_query, SearchQueryParams


ROUTER = APIRouter(redirect_slashes=True)

ENDPOINT_MODELS = {
    "structures": (StructureResponseMany.__module__, StructureResponseMany.__name__),
    "references": (ReferenceResponseMany.__module__, ReferenceResponseMany.__name__),
    "links": (LinksResponse.__module__, LinksResponse.__name__),
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
async def post_search(request: Request, search: Search) -> QueriesResponseSingle:
    """POST /search

    Coordinate a new OPTIMADE query in multiple databases through a gateway:

    1. Search for gateway in DB using `optimade_urls` and `database_ids`
    1. Create `GatewayCreate` model
    1. POST gateway resource to get ID - using functionality of POST /gateways
    1. Create new Query resource
    1. POST Query resource - using functionality of POST /queries
    1. Return POST /queries response -
        [`QueriesResponseSingle`][optimade_gateway.models.responses.QueriesResponseSingle]

    """
    from optimade_gateway.routers.databases import DATABASES_COLLECTION
    from optimade_gateway.routers.queries import QUERIES_COLLECTION
    from optimade_gateway.routers.utils import resource_factory

    # NOTE: It may be that the final list of base URLs (`base_urls`) contains the same provider(s),
    # but with differring base URLS, if, for example, a versioned base URL is supplied.
    base_urls = set()

    if search.database_ids:
        databases = await DATABASES_COLLECTION.get_multiple(
            filter={"id": {"$in": await clean_python_types(search.database_ids)}}
        )
        base_urls |= set(
            [
                get_resource_attribute(database, "attributes.base_url")
                for database in databases
                if get_resource_attribute(database, "attributes.base_url") is not None
            ]
        )

    if search.optimade_urls:
        base_urls |= set([_ for _ in search.optimade_urls if _ is not None])

    if not base_urls:
        msg = "No (valid) OPTIMADE URLs with:"
        if search.database_ids:
            msg += (
                f"\n  Database IDs: {search.database_ids} and corresponding found URLs: "
                f"{[get_resource_attribute(database, 'attributes.base_url') for database in databases]}"
            )
        if search.optimade_urls:
            msg += f"\n  Passed OPTIMADE URLs: {search.optimade_urls}"
        raise BadRequest(detail=msg)

    # Ensure all URLs are `pydantic.AnyUrl`s
    if not all([isinstance(_, AnyUrl) for _ in base_urls]):
        raise HTTPException(
            status_code=500,
            detail="Could unexpectedly not get all base URLs as `pydantic.AnyUrl`s.",
        )

    gateway = GatewayCreate(
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
                    homepage=None,
                ),
            )
            for url in base_urls
        ]
    )
    gateway, created = await resource_factory(gateway)

    if created:
        LOGGER.debug("A new gateway was created for a query (id=%r)", gateway.id)
    else:
        LOGGER.debug("A gateway was found and reused for a query (id=%r)", gateway.id)

    query = QueryCreate(
        endpoint=search.endpoint,
        endpoint_model=ENDPOINT_MODELS.get(search.endpoint),
        gateway_id=gateway.id,
        query_parameters=search.query_parameters,
    )
    query, created = await resource_factory(query)

    if created:
        asyncio.create_task(
            perform_query(url=request.url, query=query, use_query_resource=True)
        )

    return QueriesResponseSingle(
        links=ToplevelLinks(next=None),
        data=query,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=await QUERIES_COLLECTION.count(),
            more_data_available=False,
            **{f"_{CONFIG.provider.prefix}_created": created},
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
    search_params: SearchQueryParams = Depends(),
    entry_params: EntryListingQueryParams = Depends(),
) -> Union[EntryResponseMany, ErrorResponse, RedirectResponse]:
    """GET /search

    Coordinate a new OPTIMADE query in multiple databases through a gateway:

    1. Create a [`Search`][optimade_gateway.models.search.Search] POST data - calling POST /search
    1. Wait [`search_params.timeout`][optimade_gateway.queries.params.SearchQueryParams.timeout]
        seconds until the query has finished
    1. Return successful response

    Contingency: If the query has not finished within the set timeout period, the client will be
    redirected to the query's URL instead.

    """
    from time import time
    from optimade_gateway.routers.queries import QUERIES_COLLECTION

    try:
        search = Search(
            query_parameters=OptimadeQueryParameters(
                **{
                    field: getattr(entry_params, field)
                    for field in OptimadeQueryParameters.__fields__
                    if getattr(entry_params, field)
                }
            ),
            optimade_urls=search_params.optimade_urls,
            endpoint=search_params.endpoint,
            database_ids=search_params.database_ids,
        )
    except ValidationError as exc:
        raise BadRequest(
            detail=(
                "A Search object could not be created from the given URL query parameters. "
                f"Error(s): {[exc.errors]}"
            )
        )

    queries_response = await post_search(request, search=search)

    once = True
    start_time = time()
    while time() < (start_time + search_params.timeout) or once:
        # Make sure to run this at least once (e.g., if timeout=0)
        once = False

        query: QueryResource = await QUERIES_COLLECTION.get_one(
            **{"filter": {"id": queries_response.data.id}}
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

        await asyncio.sleep(0.1)

    # The query has not yet succeeded and we're past the timeout time -> Redirect to /queries/<id>
    return RedirectResponse(query.links.self)
