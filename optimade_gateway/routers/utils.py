"""Utility functions for all routers"""
from typing import Tuple, Union
import urllib.parse

from fastapi import Request
from optimade.models import EntryResponseMany, ToplevelLinks
from optimade.server.exceptions import BadRequest
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import (
    get_base_url,
    handle_response_fields,
    meta_values,
)

from optimade_gateway.common.exceptions import OptimadeGatewayError
from optimade_gateway.common.logger import LOGGER
from optimade_gateway.models import (
    GatewayCreate,
    GatewayResource,
    QueryCreate,
    QueryResource,
)
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
) -> dict:
    """Asynchronous implementation of `retrieve_queryable_properties()` from `optimade`

    Reference to the function in the `optimade` API documentation:
    [`retrieve_queryable_properties()](https://www.optimade.org/optimade-python-tools/api_reference/server/schemas/#optimade.server.schemas.retrieve_queryable_properties).

    Recursively loops through the schema of a pydantic model and resolves all references, returning
    a dictionary of all the OPTIMADE-queryable properties of that model.

    Parameters:
        schema: The schema of the pydantic model.
        queryable_properties: The list of properties to find in the schema.

    Returns:
        A flat dictionary with properties as keys, containing the field description, unit,
        sortability, support level, queryability and type, where provided.

    """
    from optimade.server.schemas import retrieve_queryable_properties

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


async def resource_factory(
    create_resource: Union[GatewayCreate, QueryCreate]
) -> Tuple[Union[GatewayResource, QueryResource], bool]:
    """Get or create a resource

    Currently supported resources:

    - `"gateways"` ([`GatewayCreate`][optimade_gateway.models.gateways.GatewayCreate] ->
        [`GatewayResource`][optimade_gateway.models.gateways.GatewayResource])
    - `"queries"` ([`QueryyCreate`][optimade_gateway.models.queries.QueryCreate] ->
        [`QueryResource`][optimade_gateway.models.queries.QueryResource])

    Parameters:
        create_resource: The resource to be retrieved or created anew.

    Returns:
        Two things in a tuple:

        - Either a [`GatewayResource`][optimade_gateway.models.gateways.GatewayResource] or a
            [`QueryResource`][optimade_gateway.models.queries.QueryResource]; and
        - whether or not the resource was newly created.

    """
    from optimade_gateway.common.utils import clean_python_types

    created = False

    if isinstance(create_resource, GatewayCreate):
        from optimade_gateway.routers.gateways import (
            GATEWAYS_COLLECTION as RESOURCE_COLLECTION,
        )

        mongo_query = {
            "databases": {"$size": len(create_resource.databases)},
            "databases.attributes.base_url": {
                "$all": await clean_python_types(
                    [_.attributes.base_url for _ in create_resource.databases]
                )
            },
        }
    elif isinstance(create_resource, QueryCreate):
        from optimade_gateway.models.queries import QueryState
        from optimade_gateway.routers.queries import (
            QUERIES_COLLECTION as RESOURCE_COLLECTION,
        )

        # Currently only /structures entry endpoints can be queried with multiple expected responses.
        create_resource.endpoint = (
            create_resource.endpoint if create_resource.endpoint else "structures"
        )
        create_resource.endpoint_model = (
            create_resource.endpoint_model
            if create_resource.endpoint_model
            else ("optimade.models.responses", "StructureResponseMany")
        )

        mongo_query = {
            "gateway_id": {"$eq": create_resource.gateway_id},
            "query_parameters": {
                "$eq": await clean_python_types(create_resource.query_parameters),
            },
            "endpoint": {"$eq": create_resource.endpoint},
        }
    else:
        raise TypeError(
            "create_resource must be either a GatewayCreate or QueryCreate object not "
            f"{type(create_resource)!r}"
        )

    result, more_data_available, _ = await RESOURCE_COLLECTION.find(
        criteria={"filter": mongo_query}
    )

    if more_data_available:
        raise OptimadeGatewayError(
            "more_data_available MUST be False for a single entry response, however it is "
            f"{more_data_available}"
        )

    if result:
        if len(result) > 1:
            raise OptimadeGatewayError(
                f"More than one {result[0].type} was found. IDs of found {result[0].type}: "
                f"{[_.id for _ in result]}"
            )
        result = result[0]
    else:
        if isinstance(create_resource, QueryCreate):
            create_resource.state = QueryState.CREATED
        result = await RESOURCE_COLLECTION.create_one(create_resource)
        LOGGER.debug("Created new %s: %r", result.type, result)
        created = True

    return result, created
