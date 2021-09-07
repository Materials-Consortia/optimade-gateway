"""Utility functions for all routers"""
from typing import Tuple, Union
import urllib.parse

from fastapi import Request
from optimade.models import (
    EntryResource,
    EntryResponseMany,
    LinksResource,
    ToplevelLinks,
)
from optimade.models.links import LinkType
from optimade.server.exceptions import NotFound
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import (
    get_base_url,
    handle_response_fields,
    meta_values,
)

from optimade_gateway.common.exceptions import OptimadeGatewayError
from optimade_gateway.common.logger import LOGGER
from optimade_gateway.models import (
    DatabaseCreate,
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
    """Generalized `/{entries}` endpoint getter"""
    (
        results,
        data_returned,
        more_data_available,
        fields,
        include_fields,
    ) = await collection.find(params=params)

    if more_data_available:
        # Deduce the `next` link from the current request
        query = urllib.parse.parse_qs(request.url.query)
        query["page_offset"] = int(query.get("page_offset", [0])[0]) + len(results)
        urlencoded = urllib.parse.urlencode(query, doseq=True)
        base_url = get_base_url(request.url)

        links = ToplevelLinks(next=f"{base_url}{request.url.path}?{urlencoded}")
    else:
        links = ToplevelLinks(next=None)

    if fields or include_fields:
        results = handle_response_fields(results, fields, include_fields)

    return response_cls(
        links=links,
        data=results,
        meta=meta_values(
            url=request.url,
            data_returned=data_returned,
            data_available=await collection.count(),
            more_data_available=more_data_available,
        ),
    )


async def aretrieve_queryable_properties(
    schema: dict, queryable_properties: list
) -> dict:
    """Asynchronous implementation of `retrieve_queryable_properties()` from `optimade`

    Reference to the function in the `optimade` API documentation:
    [`retrieve_queryable_properties()`](https://www.optimade.org/optimade-python-tools/api_reference/server/schemas/#optimade.server.schemas.retrieve_queryable_properties).

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
        raise NotFound(
            detail=f"Resource <id={entry_id}> not found in {collection}.",
        )


async def get_valid_resource(
    collection: AsyncMongoCollection, entry_id: str
) -> EntryResource:
    """Validate and retrieve a resource"""
    from optimade_gateway.routers.utils import validate_resource

    await validate_resource(collection, entry_id)
    return await collection.get_one(filter={"id": entry_id})


async def resource_factory(
    create_resource: Union[DatabaseCreate, GatewayCreate, QueryCreate]
) -> Tuple[Union[LinksResource, GatewayResource, QueryResource], bool]:
    """Get or create a resource

    Currently supported resources:

    - `"databases"` ([`DatabaseCreate`][optimade_gateway.models.databases.DatabaseCreate] ->
        [`LinksResource`](https://www.optimade.org/optimade-python-tools/api_reference/models/links/#optimade.models.links.LinksResource))
    - `"gateways"` ([`GatewayCreate`][optimade_gateway.models.gateways.GatewayCreate] ->
        [`GatewayResource`][optimade_gateway.models.gateways.GatewayResource])
    - `"queries"` ([`QueryCreate`][optimade_gateway.models.queries.QueryCreate] ->
        [`QueryResource`][optimade_gateway.models.queries.QueryResource])

    For each of the resources, "uniqueness" is determined in the following way:

    === "Databases"
        The `base_url` field is considered unique across all databases.

        If a `base_url` is provided via a
        [`Link`](https://www.optimade.org/optimade-python-tools/api_reference/models/jsonapi/#optimade.models.jsonapi.Link)
        model, the `base_url.href` value is used to query the MongoDB.

    === "Gateways"
        The collected list of `databases.attributes.base_url` values is considered unique across
        all gateways.

        In the database, the search is done as a combination of the length/size of the `databases`'
        Python list/MongoDB array and a match on all (using the MongoDB `$all` operator) of the
        [`databases.attributes.base_url`](https://www.optimade.org/optimade-python-tools/api_reference/models/links/#optimade.models.links.LinksResourceAttributes.base_url)
        element values, when compared with the `create_resource`.

        !!! important
            The `database_ids` attribute **must not** contain values that are not also included in the
            `databases` attribute, in the form of the IDs for the individual databases.
            If this should be the case an
            [`OptimadeGatewayError`][optimade_gateway.common.exceptions.OptimadeGatewayError] will be
            thrown.

    === "Queries"
        The `gateway_id`, `query_parameters`, and `endpoint` fields are collectively considered to
        define uniqueness for a [`QueryResource`][optimade_gateway.models.queries.QueryResource]
        in the MongoDB collection.

        !!! attention
            Only the `/structures` entry endpoint can be queried with multiple expected responses.

            This means the `endpoint` field defaults to `"structures"`, i.e., the
            [`StructureResource`](https://www.optimade.org/optimade-python-tools/all_models/#optimade.models.structures.StructureResource)
            resource model.

    Parameters:
        create_resource: The resource to be retrieved or created anew.

    Returns:
        Two things in a tuple:

        - Either a [`GatewayResource`][optimade_gateway.models.gateways.GatewayResource]; a
            [`QueryResource`][optimade_gateway.models.queries.QueryResource]; or a
            [`LinksResource`](https://www.optimade.org/optimade-python-tools/api_reference/models/links/#optimade.models.links.LinksResource) and
        - whether or not the resource was newly created.

    """
    from optimade_gateway.common.utils import clean_python_types, get_resource_attribute

    created = False

    if isinstance(create_resource, DatabaseCreate):
        from optimade_gateway.routers.databases import (
            DATABASES_COLLECTION as RESOURCE_COLLECTION,
        )

        base_url = get_resource_attribute(create_resource, "base_url")

        mongo_query = {
            "$or": [
                {"base_url": {"$eq": base_url}},
                {"base_url.href": {"$eq": base_url}},
            ]
        }
    elif isinstance(create_resource, GatewayCreate):
        from optimade_gateway.routers.gateways import (
            GATEWAYS_COLLECTION as RESOURCE_COLLECTION,
        )

        # One MUST have taken care of database_ids prior to calling `resource_factory()`
        database_attr_ids = {_.id for _ in create_resource.databases or []}
        unknown_ids = {
            database_id
            for database_id in create_resource.database_ids or []
            if database_id not in database_attr_ids
        }
        if unknown_ids:
            raise OptimadeGatewayError(
                "When using `resource_factory()` for `GatewayCreate`, `database_ids` MUST not "
                f"include unknown IDs. Passed unknown IDs: {unknown_ids}"
            )

        mongo_query = {
            "databases": {"$size": len(create_resource.databases)},
            "databases.attributes.base_url": {
                "$all": [_.attributes.base_url for _ in create_resource.databases or []]
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

        mongo_query = {
            "gateway_id": {"$eq": create_resource.gateway_id},
            "query_parameters": {"$eq": create_resource.query_parameters},
            "endpoint": {"$eq": create_resource.endpoint},
        }
    else:
        raise TypeError(
            "create_resource must be either a GatewayCreate or QueryCreate object not "
            f"{type(create_resource)!r}"
        )

    result, data_returned, more_data_available, _, _ = await RESOURCE_COLLECTION.find(
        criteria={"filter": await clean_python_types(mongo_query)}
    )

    if more_data_available:
        raise OptimadeGatewayError(
            "more_data_available MUST be False for a single entry response, however it is "
            f"{more_data_available}"
        )

    if result:
        if data_returned > 1:
            raise OptimadeGatewayError(
                f"More than one {result[0].type} were found. IDs of found {result[0].type}: "
                f"{[_.id for _ in result]}"
            )
        if isinstance(result, list):
            result = result[0]
    else:
        if isinstance(create_resource, DatabaseCreate):
            # Set required `LinksResourceAttributes` values if not set
            if not create_resource.description:
                create_resource.description = f"{create_resource.name} created by OPTIMADE gateway database registration."
            if not create_resource.link_type:
                create_resource.link_type = LinkType.EXTERNAL
            if not create_resource.homepage:
                create_resource.homepage = None
        elif isinstance(create_resource, GatewayCreate):
            # Do not store `database_ids`
            if "database_ids" in create_resource.__fields_set__:
                create_resource.database_ids = None
                create_resource.__fields_set__.remove("database_ids")
        elif isinstance(create_resource, QueryCreate):
            create_resource.state = QueryState.CREATED
        result = await RESOURCE_COLLECTION.create_one(create_resource)
        LOGGER.debug("Created new %s: %r", result.type, result)
        created = True

    return result, created
