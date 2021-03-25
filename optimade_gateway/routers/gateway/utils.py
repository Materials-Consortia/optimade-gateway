from optimade.models import EntryResource
from optimade.server.exceptions import BadRequest, VersionNotSupported
from optimade.server.routers.utils import BASE_URL_PREFIXES

from optimade_gateway.mongo.collection import AsyncMongoCollection


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
