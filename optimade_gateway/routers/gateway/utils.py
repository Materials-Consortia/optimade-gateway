from typing import Union

try:
    import simplejson as json
except ImportError:
    import json

from optimade import __api_version__
from optimade.models import (
    EntryResource,
    EntryResponseMany,
    EntryResponseOne,
    ErrorResponse,
    LinksResource,
)
from optimade.server.exceptions import BadRequest, VersionNotSupported
from optimade.server.routers.utils import BASE_URL_PREFIXES
from pydantic import ValidationError
import requests

from optimade_gateway.mongo.collection import AsyncMongoCollection


def db_find(
    database: LinksResource,
    endpoint: str,
    response_model: Union[EntryResponseMany, EntryResponseOne],
    query_params: str = "",
) -> Union[ErrorResponse, EntryResponseMany, EntryResponseOne]:
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
    response = requests.get(url, timeout=60)

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

    return response


async def adb_find(
    database: LinksResource,
    endpoint: str,
    response_model: Union[EntryResponseMany, EntryResponseOne],
    query_params: str = "",
) -> Union[ErrorResponse, EntryResponseMany, EntryResponseOne]:
    """The asynchronous version of `optimade_gateway.routers.structures:db_find()`.

    Parameters:
        database: The OPTIMADE implementation to be queried.
        endpoint: The entry-listing endpoint, e.g., `"structures"`.
        response_model: The expected OPTIMADE pydantic response model, e.g., `optimade.models.StructureResponseMany`.
        query_params: URL query parameters to pass to the database.

    Results:
        Response as an OPTIMADE pydantic model, depending on whether it was a successful or unsuccessful response.

    """
    return db_find(database, endpoint, response_model, query_params)


async def validate_version(version: str) -> None:
    """Validate version according to `optimade` package"""
    valid_versions = [_[1:] for _ in BASE_URL_PREFIXES.values()]

    if version not in valid_versions:
        if version.startswith("v"):
            raise VersionNotSupported(
                detail=f"version {version} is not supported. Supported versions: {valid_versions}"
            )
        else:
            raise BadRequest(
                title="Not Found",
                status_code=404,
                detail=f"version MUST be one of {valid_versions}",
            )


async def get_valid_resource(
    collection: AsyncMongoCollection, entry_id: str
) -> EntryResource:
    """Validate and retrieve a resource"""
    from optimade_gateway.routers.utils import validate_resource

    await validate_resource(collection, entry_id)
    return await collection.get_one(filter={"id": entry_id})
