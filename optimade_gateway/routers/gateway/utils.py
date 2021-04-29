from optimade.server.exceptions import BadRequest, VersionNotSupported
from optimade.server.routers.utils import BASE_URL_PREFIXES


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
