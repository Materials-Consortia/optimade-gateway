from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from optimade.server.exception_handlers import OPTIMADE_EXCEPTIONS
from optimade.server.middleware import OPTIMADE_MIDDLEWARE
from optimade.server.routers.utils import BASE_URL_PREFIXES
from optimade.server.routers.versions import router as versions_router

from optimade_gateway import __version__
from optimade_gateway.middleware import CheckWronglyVersionedBaseUrlsGateways
from optimade_gateway.routers import (
    databases,
    gateways,
    info,
    links,
    queries,
    search,
)
from optimade_gateway.routers.gateway import (
    info as gateway_info,
    links as gateway_links,
    queries as gateway_queries,
    structures,
    versions,
)

APP = FastAPI(
    title="OPTIMADE Gateway",
    description="A gateway server to query multiple OPTIMADE databases.",
    version=__version__,
)


@APP.get("/", include_in_schema=False)
async def get_root(request: Request) -> RedirectResponse:
    """Get /

    Introspective overview of gateway server.

    NOTE: Temporarily redirecting to GET /docs
    """
    return RedirectResponse(
        request.url.replace(path=f"{request.url.path.strip('/')}/docs")
    )


# Add middleware
APP.add_middleware(CheckWronglyVersionedBaseUrlsGateways)
for middleware in OPTIMADE_MIDDLEWARE:
    APP.add_middleware(middleware)

# Add exception handlers
for exception, handler in OPTIMADE_EXCEPTIONS:
    APP.add_exception_handler(exception, handler)

# Add the special /versions endpoint(s)
APP.include_router(versions_router)
APP.include_router(versions.ROUTER)

# Add endpoints to / and /vMAJOR
for prefix in list(BASE_URL_PREFIXES.values()) + [""]:
    for router in (databases, gateways, info, links, queries, search) + (
        gateway_info,
        gateway_links,
        gateway_queries,
        structures,
    ):
        APP.include_router(router.ROUTER, prefix=prefix, include_in_schema=prefix == "")


@APP.on_event("startup")
async def ci_dev_startup():
    """Function to run at app startup - only relevant for CI or development to add test data"""
    import os
    from optimade_gateway.common.logger import LOGGER

    if bool(os.getenv("CI", False)):
        LOGGER.info(
            "CI detected - Will load test gateways (after dropping the collection)!"
        )
    elif os.getenv("OPTIMADE_MONGO_DATABASE", "") == "optimade_gateway_dev":
        LOGGER.info(
            "Running in development mode - Will load test gateways (after dropping the collection)!"
        )
    else:
        LOGGER.debug("Not in CI or development mode - will start normally.")
        return

    # Add test gateways
    import json
    from optimade_gateway.mongo.database import MONGO_DB
    from pathlib import Path

    collection = "gateways"
    test_data = (
        Path(__file__).parent.parent.joinpath(".ci/test_gateways.json").resolve()
    )

    await MONGO_DB[collection].drop()

    assert await MONGO_DB[collection].count_documents({}) == 0
    assert test_data.exists()

    with open(test_data) as handle:
        data = json.load(handle)

    await MONGO_DB[collection].insert_many(data)
