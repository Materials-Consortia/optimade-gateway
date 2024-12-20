"""General /search endpoint to completely coordinate an OPTIMADE gateway query

This file describes the router for:

    /search

"""

from __future__ import annotations

import asyncio
from time import time
from typing import Annotated, Union

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import RedirectResponse
from optimade.models import LinksResource, LinksResourceAttributes, ToplevelLinks
from optimade.models.links import LinkType
from optimade.models.responses import (
    EntryResponseMany as OptimadeEntryResponseMany,
)
from optimade.models.responses import (
    ErrorResponse,
    LinksResponse,
    ReferenceResponseMany,
    StructureResponseMany,
)
from optimade.server.exceptions import BadRequest, InternalServerError
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import meta_values
from optimade.server.schemas import ERROR_RESPONSES
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
from optimade_gateway.queries.params import SearchQueryParams
from optimade_gateway.queries.perform import perform_query
from optimade_gateway.routers.utils import collection_factory, resource_factory

ROUTER = APIRouter(redirect_slashes=True)

EntryResponseMany = Union[
    StructureResponseMany,
    ReferenceResponseMany,
    LinksResponse,
    OptimadeEntryResponseMany,
]


@ROUTER.post(
    "/search",
    response_model=QueriesResponseSingle,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Search"],
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
)
async def post_search(request: Request, search: Search) -> QueriesResponseSingle:
    """`POST /search`

    Coordinate a new OPTIMADE query in multiple databases through a gateway:

    1. Search for gateway in DB using `optimade_urls` and `database_ids`
    1. Create [`GatewayCreate`][optimade_gateway.models.gateways.GatewayCreate] model
    1. `POST` gateway resource to get ID - using functionality of `POST /gateways`
    1. Create new [Query][optimade_gateway.models.queries.QueryCreate] resource
    1. `POST` Query resource - using functionality of `POST /queries`
    1. Return `POST /queries` response -
        [`QueriesResponseSingle`][optimade_gateway.models.responses.QueriesResponseSingle]

    """
    databases_collection = await collection_factory(CONFIG.databases_collection)
    # NOTE: It may be that the final list of base URLs (`base_urls`) contains the same
    # provider(s), but with differring base URLS, if, for example, a versioned base URL
    # is supplied.
    base_urls: list[AnyUrl] = []

    if search.database_ids:
        databases = await databases_collection.get_multiple(
            filter={"id": {"$in": await clean_python_types(search.database_ids)}}
        )
        base_urls.extend(
            [
                get_resource_attribute(database, "attributes.base_url")
                for database in databases
                if get_resource_attribute(database, "attributes.base_url") is not None
            ]
        )

    if search.optimade_urls:
        base_urls.extend([_ for _ in search.optimade_urls if _ is not None])

    if not base_urls:
        msg = "No (valid) OPTIMADE URLs with:"
        if search.database_ids:
            msg += (
                f"\n  Database IDs: {search.database_ids} and corresponding found "
                "URLs: "
                f"{[get_resource_attribute(database, 'attributes.base_url') for database in databases]}"  # noqa: E501
            )
        if search.optimade_urls:
            msg += f"\n  Passed OPTIMADE URLs: {search.optimade_urls}"
        raise BadRequest(detail=msg)

    # Ensure all URLs are `pydantic.AnyUrl`s
    if not all(isinstance(_, AnyUrl) for _ in base_urls):
        raise InternalServerError(
            "Could unexpectedly not validate all base URLs as proper URLs."
        )

    databases = await databases_collection.get_multiple(
        filter={"base_url": {"$in": await clean_python_types(base_urls)}}
    )

    if len(databases) == len(base_urls):
        # At this point it is expected that the list of databases in `databases`
        # is a complete set of databases requested.
        pass

    elif len(databases) < len(base_urls):
        # There are unregistered databases, i.e., databases not in the local collection
        current_base_urls: list[AnyUrl] = [
            get_resource_attribute(database, "attributes.base_url")
            for database in databases
        ]
        diff_base_urls = [
            base_url for base_url in base_urls if base_url not in current_base_urls
        ]
        databases.extend(
            [
                LinksResource(
                    id=str(url)
                    .replace(".", "__")[len(url.scheme) + 3 :]
                    .split("?", maxsplit=1)[0]
                    .split("#", maxsplit=1)[0],
                    type="links",
                    attributes=LinksResourceAttributes(
                        name=str(url)[len(url.scheme) + 3 :]
                        .split("?", maxsplit=1)[0]
                        .split("#", maxsplit=1)[0],
                        description="",
                        base_url=url,
                        link_type=LinkType.CHILD,
                        homepage=None,
                    ),
                )
                for url in diff_base_urls
            ]
        )
    else:
        LOGGER.error(
            "Found more database entries in MongoDB than then number of passed base "
            "URLs. This suggests ambiguity in the base URLs of databases stored in "
            "MongoDB.\n  base_urls: %s\n  databases %s",
            base_urls,
            databases,
        )
        raise InternalServerError("Unambiguous base URLs. See logs for more details.")

    gateway = GatewayCreate(databases=databases)
    gateway, created = await resource_factory(gateway)

    if created:
        LOGGER.debug("A new gateway was created for a query (id=%r)", gateway.id)
    else:
        LOGGER.debug("A gateway was found and reused for a query (id=%r)", gateway.id)

    query = QueryCreate(
        endpoint=search.endpoint,
        gateway_id=gateway.id,
        query_parameters=search.query_parameters,
    )
    query, created = await resource_factory(query)

    background_tasks: set[asyncio.Task] = set()

    if created:
        task = asyncio.create_task(perform_query(url=request.url, query=query))

        # Add task to the set. This creates a strong reference.
        background_tasks.add(task)

        # To prevent keeping references to finished tasks forever,
        # make each task remove its own reference from the set after
        # completion:
        task.add_done_callback(background_tasks.discard)

    collection = await collection_factory(CONFIG.queries_collection)

    return QueriesResponseSingle(
        links=ToplevelLinks(next=None),
        data=query,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=await collection.acount(),
            more_data_available=False,
            schema=CONFIG.schema_url,
            **{f"_{CONFIG.provider.prefix}_created": created},
        ),
    )


@ROUTER.get(
    "/search",
    response_model=Union[QueriesResponseSingle, ErrorResponse, EntryResponseMany],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Search"],
    responses=ERROR_RESPONSES,
)
async def get_search(
    request: Request,
    response: Response,
    search_params: Annotated[SearchQueryParams, Depends()],
    entry_params: Annotated[EntryListingQueryParams, Depends()],
) -> QueriesResponseSingle | EntryResponseMany | ErrorResponse | RedirectResponse:
    """`GET /search`

    Coordinate a new OPTIMADE query in multiple databases through a gateway:

    1. Create a [`Search`][optimade_gateway.models.search.Search] `POST` data - calling
        `POST /search`.
    1. Wait [`search_params.timeout`][optimade_gateway.queries.params.SearchQueryParams]
        seconds before returning the query, if it has not finished before.
    1. Return query - similar to `GET /queries/{query_id}`.

    This endpoint works similarly to `GET /queries/{query_id}`, where one passes the
    query parameters directly in the URL, instead of first POSTing a query and then
    going to its URL. Hence, a
    [`QueryResponseSingle`][optimade_gateway.models.responses.QueriesResponseSingle] is
    the standard response model for this endpoint.

    If the timeout time is reached and the query has not yet finished, the user is
    redirected to the specific URL for the query.

    If the `as_optimade` query parameter is `True`, the response will be parseable as a
    standard OPTIMADE entry listing endpoint like, e.g., `/structures`.
    For more information see the
    [OPTIMADE specification](https://github.com/Materials-Consortia/OPTIMADE/blob/master/optimade.rst#entry-listing-endpoints).

    """
    try:
        search = Search(
            query_parameters=OptimadeQueryParameters(
                **{
                    field: getattr(entry_params, field)
                    for field in OptimadeQueryParameters.model_fields
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
                "A Search object could not be created from the given URL query "
                f"parameters. Error(s): {exc.errors}"
            )
        ) from exc

    queries_response = await post_search(request, search=search)

    if not queries_response.data:
        LOGGER.error(
            "QueryResource not found in POST /search response:\n%s", queries_response
        )
        raise RuntimeError(
            "Expected the response from POST /search to return a QueryResource, it did "
            "not"
        )

    once = True
    start_time = time()
    while time() < (start_time + search_params.timeout) or once:
        # Make sure to run this at least once (e.g., if timeout=0)
        once = False

        collection = await collection_factory(CONFIG.queries_collection)

        query: QueryResource = await collection.get_one(
            filter={"id": queries_response.data.id}
        )

        if query.attributes.state == QueryState.FINISHED:
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

            if search_params.as_optimade:
                response = await query.response_as_optimade(url=request.url)
                LOGGER.debug(
                    "Returning response as OPTIMADE entry listing:\n%s", response
                )
                return response

            return QueriesResponseSingle(
                links=ToplevelLinks(next=None),
                data=query,
                meta=meta_values(
                    url=request.url,
                    data_returned=1,
                    data_available=await collection.acount(),
                    more_data_available=False,
                    schema=CONFIG.schema_url,
                ),
            )

        await asyncio.sleep(0.1)

    # The query has not yet succeeded and we're past the timeout time -> Redirect to
    # /queries/<id>
    return RedirectResponse(query.links.self)
