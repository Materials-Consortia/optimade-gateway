"""Perform OPTIMADE queries"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import functools
import json
import os
from typing import Any, Dict, List, Tuple, Union
import urllib.parse

from optimade import __api_version__
from optimade.models import (
    EntryResource,
    EntryResponseMany,
    EntryResponseOne,
    ErrorResponse,
    LinksResource,
    Meta,
    ToplevelLinks,
)
from optimade.server.routers.utils import BASE_URL_PREFIXES, get_base_url, meta_values
from pydantic import ValidationError
from starlette.datastructures import URL

from optimade_gateway.common.logger import LOGGER
from optimade_gateway.common.utils import get_resource_attribute
from optimade_gateway.models import (
    GatewayQueryResponse,
    GatewayResource,
    QueryResource,
    QueryState,
)
from optimade_gateway.queries.prepare import get_query_params, prepare_query_filter
from optimade_gateway.queries.process import process_db_response
from optimade_gateway.queries.utils import update_query


async def perform_query(
    url: URL,
    query: QueryResource,
    use_query_resource: bool = True,
) -> Union[EntryResponseMany, ErrorResponse, GatewayQueryResponse]:
    """Perform OPTIMADE query with gateway.

    Parameters:
        url: Original request URL.
        query: The query to be performed.
        use_query_resource: Whether or not to update the passed
            [`QueryResource`][optimade_gateway.models.queries.QueryResource] or not.
            The URL will be changed if this is `True`, to allow for requesting the query back
            through the `/queries` endpoint.

    Returns:
        This function returns the final response; either an `ErrorResponse`, a subclass of
        `EntryResponseMany` or if `use_query_resource` is true, then a
        [`GatewayQueryResponse`][optimade_gateway.models.queries.GatewayQueryResponse].

    """
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION
    from optimade_gateway.routers.utils import get_valid_resource

    response = None

    if use_query_resource:
        await update_query(query, "state", QueryState.STARTED)

    gateway: GatewayResource = await get_valid_resource(
        GATEWAYS_COLLECTION, query.attributes.gateway_id
    )

    filter_queries = await prepare_query_filter(
        database_ids=[_.id for _ in gateway.attributes.databases],
        filter_query=query.attributes.query_parameters.filter,
    )

    if use_query_resource:
        url = url.replace(path=f"{url.path.rstrip('/')}/{query.id}")
        await update_query(
            query,
            "response",
            GatewayQueryResponse(
                data={},
                links=ToplevelLinks(next=None),
                meta=meta_values(
                    url=url,
                    data_available=0,
                    data_returned=0,
                    more_data_available=False,
                ),
            ),
            **{"$set": {"state": QueryState.IN_PROGRESS}},
        )
    else:
        response = query.attributes.endpoint.get_response_model()(
            data=[],
            links=ToplevelLinks(next=None),
            meta=meta_values(
                url=url,
                data_available=0,
                data_returned=0,
                more_data_available=False,
            ),
        )

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(
        max_workers=min(32, os.cpu_count() + 4, len(gateway.attributes.databases))
    ) as executor:
        # Run OPTIMADE DB queries in a thread pool, i.e., not using the main OS thread, where the
        # asyncio event loop is running.
        query_tasks = []
        for database in gateway.attributes.databases:
            query_params = await get_query_params(
                query_parameters=query.attributes.query_parameters,
                database_id=database.id,
                filter_mapping=filter_queries,
            )
            query_tasks.append(
                loop.run_in_executor(
                    executor=executor,
                    func=functools.partial(
                        db_find,
                        database=database,
                        endpoint=query.attributes.endpoint.value,
                        response_model=query.attributes.endpoint.get_response_model(),
                        query_params=query_params,
                    ),
                )
            )

        for query_task in query_tasks:
            (db_response, db_id) = await query_task

            results, errors, response_meta = await process_db_response(
                response=db_response,
                database_id=db_id,
                query=query,
                gateway=gateway,
                use_query_resource=use_query_resource,
            )

            if not use_query_resource:
                # Create a standard OPTIMADE response, adding the database ID to each returned
                # resource's meta field.
                database_id_meta = {"_optimade_gateway_": {"source_database_id": db_id}}
                if errors or isinstance(response, ErrorResponse):
                    # Error response
                    if isinstance(response, ErrorResponse):
                        response.errors.append(errors)
                    else:
                        response = ErrorResponse(errors=errors, meta=response.meta)
                        response.meta.data_returned = 0
                        response.meta.more_data_available = False
                elif isinstance(results, list):
                    # "Many" response
                    for resource in results:
                        if hasattr(resource, "meta") and resource.meta:
                            meta = resource.meta.dict()
                            meta.update(database_id_meta)
                            resource.meta = Meta(**meta)
                        elif isinstance(resource, dict) and resource.get("meta", {}):
                            resource["meta"] = resource["meta"].update(database_id_meta)
                        elif isinstance(resource, dict):
                            resource["meta"] = database_id_meta
                        else:
                            resource.meta = Meta(**database_id_meta)
                    response.data.extend(results)
                    response.meta.data_returned += response_meta["data_returned"]
                    if not response.meta.more_data_available:
                        # Keep it True, if set to True once.
                        response.meta.more_data_available = response_meta[
                            "more_data_available"
                        ]
                else:
                    # "One" response
                    if hasattr(results, "meta") and results.meta:
                        meta = results.meta.dict()
                        meta.update(database_id_meta)
                        results.meta = Meta(**meta)
                    elif isinstance(results, dict) and results.get("meta", {}):
                        results["meta"] = results["meta"].update(database_id_meta)
                    elif isinstance(results, dict):
                        results["meta"] = database_id_meta
                    else:
                        results.meta = Meta(**database_id_meta)
                    response.data.append(results)
                    response.meta.data_returned += response_meta["data_returned"]
                    if not response.meta.more_data_available:
                        # Keep it True, if set to True once.
                        response.meta.more_data_available = response_meta[
                            "more_data_available"
                        ]
                response.meta.data_available += response_meta["data_available"]

    if get_resource_attribute(
        query,
        "attributes.response.meta.more_data_available",
        False,
        disambiguate=False,  # Extremely minor speed-up
    ) or get_resource_attribute(
        response,
        "meta.more_data_available",
        False,
        disambiguate=False,
    ):
        # Deduce the `next` link from the current request
        query_string = urllib.parse.parse_qs(url.query)
        query_string["page_offset"] = int(
            query_string.get("page_offset", [0])[0]
        ) + len(results[: query.attributes.query_parameters.page_limit])
        urlencoded = urllib.parse.urlencode(query_string, doseq=True)
        base_url = get_base_url(url)

        links = ToplevelLinks(next=f"{base_url}{url.path}?{urlencoded}")

        if use_query_resource:
            await update_query(query, "response.links", links)
        else:
            response.links = links

    if use_query_resource:
        await update_query(query, "state", QueryState.FINISHED)
        return query.attributes.response
    return response


def db_find(
    database: Union[LinksResource, Dict[str, Any]],
    endpoint: str,
    response_model: Union[EntryResponseMany, EntryResponseOne],
    query_params: str = "",
    raw_url: str = None,
) -> Tuple[Union[ErrorResponse, EntryResponseMany, EntryResponseOne], str]:
    """Imitate `Collection.find()` for any given database for entry-resource endpoints

    Parameters:
        database: The OPTIMADE implementation to be queried. It **must** have a valid base URL and
            id.
        endpoint: The entry-listing endpoint, e.g., `"structures"`.
        response_model: The expected OPTIMADE pydantic response model, e.g.,
            `optimade.models.StructureResponseMany`.
        query_params: URL query parameters to pass to the database.
        raw_url: A raw URL to use straight up instead of deriving a URL from `database`,
            `endpoint`, and `query_params`.

    Returns:
        Response as an `optimade` pydantic model and the `database`'s ID.

    """
    import httpx

    if raw_url:
        url = raw_url
    else:
        url = (
            f"{str(get_resource_attribute(database, 'attributes.base_url')).strip('/')}"
            f"{BASE_URL_PREFIXES['major']}/{endpoint.strip('/')}?{query_params}"
        )
    response: httpx.Response = httpx.get(url, timeout=60)

    try:
        response = response.json()
    except json.JSONDecodeError:
        return (
            ErrorResponse(
                errors=[
                    {
                        "detail": f"Could not JSONify response from {url}",
                        "id": "OPTIMADE_GATEWAY_DB_FIND_MANY_JSONDECODEERROR",
                    }
                ],
                meta={
                    "query": {
                        "representation": f"/{endpoint.strip('/')}?{query_params}"
                    },
                    "api_version": __api_version__,
                    "more_data_available": False,
                },
            ),
            get_resource_attribute(database, "id"),
        )

    try:
        response = response_model(**response)
    except ValidationError:
        try:
            response = ErrorResponse(**response)
        except ValidationError as exc:
            return (
                ErrorResponse(
                    errors=[
                        {
                            "detail": f"Could not pass response from {url} as either a {response_model.__name__!r} or 'ErrorResponse'. ValidationError: {exc}",
                            "id": "OPTIMADE_GATEWAY_DB_FIND_MANY_VALIDATIONERROR",
                        }
                    ],
                    meta={
                        "query": {
                            "representation": f"/{endpoint.strip('/')}?{query_params}"
                        },
                        "api_version": __api_version__,
                        "more_data_available": False,
                    },
                ),
                get_resource_attribute(database, "id"),
            )

    return response, get_resource_attribute(database, "id")


async def db_get_all_resources(
    database: Union[LinksResource, Dict[str, Any]],
    endpoint: str,
    response_model: EntryResponseMany,
    query_params: str = "",
    raw_url: str = None,
) -> Tuple[
    List[Union[EntryResource, Dict[str, Any]]], Union[LinksResource, Dict[str, Any]]
]:
    """Recursively retrieve all resources from an entry-listing endpoint

    This function keeps pulling the `links.next` link if `meta.more_data_available` is `True` to
    ultimately retrieve *all* entries for `endpoint`.

    !!! warning
        This function can be dangerous if an endpoint with hundreds or thousands of entries is
        requested.

    Parameters:
        database: The OPTIMADE implementation to be queried. It **must** have a valid base URL and
            id.
        endpoint: The entry-listing endpoint, e.g., `"structures"`.
        response_model: The expected OPTIMADE pydantic response model, e.g.,
            `optimade.models.StructureResponseMany`.
        query_params: URL query parameters to pass to the database.
        raw_url: A raw URL to use straight up instead of deriving a URL from `database`,
            `endpoint`, and `query_params`.

    Returns:
        A collected list of successful responses' `data` value and the `database`'s ID.

    """
    resulting_resources = []

    response, _ = db_find(
        database=database,
        endpoint=endpoint,
        response_model=response_model,
        query_params=query_params,
        raw_url=raw_url,
    )

    if isinstance(response, ErrorResponse):
        # An errored response will result in no databases from a provider.
        LOGGER.error(
            "Error while querying database (id=%r). Full response: %s",
            get_resource_attribute(database, "id"),
            response.json(indent=2),
        )
        return [], database

    resulting_resources.extend(response.data)

    if response.meta.more_data_available:
        next_page = get_resource_attribute(response, "links.next")
        if next_page is None:
            LOGGER.error(
                "Could not find a 'next' link for an OPTIMADE query request to %r (id=%r). Cannot "
                "get all resources from /%s, even though this was asked and `more_data_available` "
                "is `True` in the response.",
                get_resource_attribute(database, "attributes.name", "N/A"),
                get_resource_attribute(database, "id"),
                endpoint,
            )
            return resulting_resources, database

        more_resources, _ = await db_get_all_resources(
            database=database,
            endpoint=endpoint,
            response_model=response_model,
            query_params=query_params,
            raw_url=next_page,
        )
        resulting_resources.extend(more_resources)

    return resulting_resources, database
