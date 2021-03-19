"""Utility functions for all routers"""
import asyncio
import importlib
import sys
from typing import Tuple, Union
import urllib.parse

if sys.version_info >= (3, 7):
    # Python 3.7+
    from asyncio import create_task
else:
    # See https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
    from asyncio import ensure_future as create_task

try:
    import simplejson as json
except ImportError:
    import json

from fastapi import Request
import httpx
from optimade import __api_version__
from optimade.models import (
    EntryResponseMany,
    EntryResponseOne,
    ErrorResponse,
    LinksResource,
    Meta,
    ToplevelLinks,
)
from optimade.server.exceptions import BadRequest
from optimade.server.schemas import retrieve_queryable_properties
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import (
    BASE_URL_PREFIXES,
    get_base_url,
    handle_response_fields,
    meta_values,
)
from pydantic import ValidationError
from starlette.datastructures import URL

from optimade_gateway.common.logger import LOGGER
from optimade_gateway.models import QueryResource
from optimade_gateway.models.queries import QueryState
from optimade_gateway.mongo.collection import AsyncMongoCollection


async def get_entries(
    collection: AsyncMongoCollection,
    response_cls: EntryResponseMany,
    request: Request,
    params: EntryListingQueryParams,
) -> EntryResponseMany:
    """Generalized /{entries} endpoint getter"""
    results, more_data_available, fields = await collection.find(params=params)

    if more_data_available:
        # Deduce the `next` link from the current request
        query = urllib.parse.parse_qs(request.url.query)
        query["page_offset"] = int(query.get("page_offset", [0])[0]) + len(results)
        urlencoded = urllib.parse.urlencode(query, doseq=True)
        base_url = get_base_url(request.url)

        links = ToplevelLinks(next=f"{base_url}{request.url.path}?{urlencoded}")
    else:
        links = ToplevelLinks(next=None)

    if fields:
        results = handle_response_fields(results, fields)

    return response_cls(
        links=links,
        data=results,
        meta=meta_values(
            url=request.url,
            data_returned=await collection.count(params=params),
            data_available=await collection.count(),
            more_data_available=more_data_available,
        ),
    )


async def aretrieve_queryable_properties(
    schema: dict, queryable_properties: list
) -> Tuple[dict, dict]:
    """Asynchronous implementation of `optimade.server.schemas.retrieve_queryable_properties()`

    Recurisvely loops through the schema of a pydantic model and resolves all references, returning
    a dictionary of all the OPTIMADE-queryable properties of that model.

    Parameters:
        schema: The schema of the pydantic model.
        queryable_properties: The list of properties to find in the schema.

    Returns:
        A flat dictionary with properties as keys, containing the field description, unit,
        sortability, support level, queryability and type, where provided.

    """
    return retrieve_queryable_properties(
        schema=schema,
        queryable_properties=queryable_properties,
    )


async def validate_resource(collection: AsyncMongoCollection, entry_id: str) -> None:
    """Validate whether a resource exists in a collection"""
    if not await collection.exists(entry_id):
        raise BadRequest(
            title="Not Found",
            status_code=404,
            detail=f"Resource <id={entry_id}> not found in {collection}.",
        )


async def perform_query(
    url: URL,
    query: QueryResource,
    update_query_resource: bool = True,
) -> Union[EntryResponseMany, ErrorResponse]:
    """Perform OPTIMADE query with gateway.

    Parameters:
        query: The query to be performed.
        gateway: The gateway for which the query will be performed.
        update_query_resource: Whether or not to update the passed
            [`QueryResource`][optimade_gateway.models.queries.QueryResource] or not.

    Returns:
        This function returns the final response; either an `ErrorResponse` or a subclass of
        `EntryResponseMany`.

    """
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION
    from optimade_gateway.routers.gateway.utils import get_valid_resource

    data_available = data_returned = 0
    errors = []
    more_data_available = False
    results = []

    response_model_module = importlib.import_module(query.attributes.endpoint_model[0])
    response_model = getattr(response_model_module, query.attributes.endpoint_model[1])

    query_params = urllib.parse.urlencode(
        {
            param: value
            for param, value in query.attributes.query_parameters.dict().items()
            if value
        }
    )

    gateway = await get_valid_resource(GATEWAYS_COLLECTION, query.attributes.gateway_id)

    query_tasks = [
        create_task(
            db_find(
                database=database,
                endpoint=query.attributes.endpoint,
                response_model=response_model,
                query_params=query_params,
            )
        )
        for database in gateway.attributes.databases
    ]

    if update_query_resource:
        await update_query_state(query, QueryState.CREATED)

    for query_task in asyncio.as_completed(query_tasks):
        (response, db_id) = await query_task

        if update_query_resource and query.attributes.state != QueryState.IN_PROGRESS:
            await update_query_state(query, QueryState.IN_PROGRESS)

        if isinstance(response, ErrorResponse):
            for error in response.errors:
                if isinstance(error.id, str) and error.id.startswith(
                    "OPTIMADE_GATEWAY"
                ):
                    import warnings

                    warnings.warn(error.detail)
                else:
                    meta = {}
                    if error.meta:
                        meta = error.meta.dict()
                    meta.update(
                        {
                            "optimade_gateway": {
                                "gateway": gateway,
                                "source_database_id": db_id,
                            }
                        }
                    )
                    error.meta = Meta(**meta)
                    errors.append(error)
        else:
            for datum in response.data:
                if isinstance(datum, dict) and datum.get("id") is not None:
                    datum["id"] = f"{db_id}/{datum['id']}"
                else:
                    datum.id = f"{db_id}/{datum.id}"
            results.extend(response.data)

            data_available += response.meta.data_available or 0
            data_returned += response.meta.data_returned or len(response.data)

            if not more_data_available:
                # Keep it True, if set to True once.
                more_data_available = response.meta.more_data_available

    meta = meta_values(
        url=url,
        data_available=data_available,
        data_returned=data_returned,
        more_data_available=more_data_available,
    )

    if errors:
        response = ErrorResponse(errors=errors, meta=meta)
    else:
        # Sort results over two steps, first by database id,
        # and then by (original) "id", since "id" MUST always be present.
        # NOTE: Possbly remove this sorting?
        results.sort(key=lambda data: data["id"] if "id" in data else data.id)
        results.sort(
            key=lambda data: "/".join(data["id"].split("/")[1:])
            if "id" in data
            else "/".join(data.id.split("/")[1:])
        )

        if more_data_available:
            # Deduce the `next` link from the current request
            query_string = urllib.parse.parse_qs(url.query)
            query_string["page_offset"] = int(
                query_string.get("page_offset", [0])[0]
            ) + len(results[: query.attributes.query_parameters.page_limit])
            urlencoded = urllib.parse.urlencode(query_string, doseq=True)
            base_url = get_base_url(url)

            links = ToplevelLinks(next=f"{base_url}{url.path}?{urlencoded}")
        else:
            links = ToplevelLinks(next=None)

        response = response_model(
            links=links,
            data=results,
            meta=meta,
        )

    if update_query_resource:
        query.attributes.response = response
        await update_query_state(query, QueryState.FINISHED)

    return response


async def db_find(
    database: LinksResource,
    endpoint: str,
    response_model: Union[EntryResponseMany, EntryResponseOne],
    query_params: str = "",
) -> Tuple[Union[ErrorResponse, EntryResponseMany, EntryResponseOne], str]:
    """Imitate Collection.find for any given database for entry-resource endpoints

    Parameters:
        database: The OPTIMADE implementation to be queried.
        endpoint: The entry-listing endpoint, e.g., `"structures"`.
        response_model: The expected OPTIMADE pydantic response model, e.g., `optimade.models.StructureResponseMany`.
        query_params: URL query parameters to pass to the database.

    Results:
        Response as an OPTIMADE pydantic model, depending on whether it was a successful or unsuccessful response.

    """
    url = f"{str(database.attributes.base_url).strip('/')}{BASE_URL_PREFIXES['major']}/{endpoint.strip('/')}?{query_params}"
    async with httpx.AsyncClient() as client:
        response: httpx.Response = await client.get(url, timeout=60)

    try:
        response = response.json()
    except json.JSONDecodeError:
        return ErrorResponse(
            errors=[
                {
                    "detail": f"Could not JSONify response from {url}",
                    "id": "OPTIMADE_GATEWAY_DB_FIND_MANY_JSONDECODEERROR",
                }
            ],
            meta={
                "query": {"representation": f"/{endpoint.strip('/')}?{query_params}"},
                "api_version": __api_version__,
                "more_data_available": False,
            },
        )

    try:
        response = response_model(**response)
    except ValidationError:
        try:
            response = ErrorResponse(**response)
        except ValidationError as exc:
            return ErrorResponse(
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
            )

    return response, database.id


async def update_query_state(query: QueryResource, state: QueryState) -> None:
    """Update a query's state in the MongoDB.

    Parameters:
        query: The query to be updated.
        state: The (possibly) new state to be set.

    """
    from datetime import datetime

    from optimade_gateway.routers.queries import QUERIES_COLLECTION

    update_time = datetime.utcnow()

    # MongoDB
    result = await QUERIES_COLLECTION.collection.update_one(
        filter={"id": {"$eq": query.id}},
        update={"$set": {"last_modified": update_time, "state": state.value}},
    )
    if result.matched_count != 1:
        LOGGER.error(
            "matched_count should have been exactly 1, it was: %s. Returned update_one result: %s",
            result.matched_count,
            result,
        )

    # Pydantic model instance
    query.attributes.last_modified = update_time
    query.attributes.state = state
