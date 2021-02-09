from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from optimade.server.exception_handlers import OPTIMADE_EXCEPTIONS
from optimade.server.middleware import OPTIMADE_MIDDLEWARE
from optimade.server.routers.utils import BASE_URL_PREFIXES

from optimade_gateway import __version__
from optimade_gateway.routers import gateways, structures

APP = FastAPI(
    title="OPTIMADE Gateway",
    description="A gateway server to query multiple OPTIMADE databases.",
    version=__version__,
)


@APP.get("/")
async def get_root(request: Request) -> RedirectResponse:
    """Get /

    Introspective overview of gateway server.

    NOTE: Temporarily redirecting to GET /docs
    """
    return RedirectResponse(
        request.url.replace(path=f"{request.url.path.strip('/')}/docs")
    )


# Add OPTIMADE middleware
for middleware in OPTIMADE_MIDDLEWARE:
    APP.add_middleware(middleware)

# Add exception handlers
for exception, handler in OPTIMADE_EXCEPTIONS:
    APP.add_exception_handler(exception, handler)

# Add endpoints to / and /vMAJOR
for prefix in ("", BASE_URL_PREFIXES["major"]):
    for endpoint in (gateways, structures):
        APP.include_router(endpoint.ROUTER, prefix=prefix)


@APP.on_event("startup")
async def ci_startup():
    """Function to run at app startup - only relevant for CI to add test data"""
    import os
    from optimade_gateway.common.logger import LOGGER

    if not bool(os.getenv("CI", False)):
        LOGGER.debug("Not in CI - will start normally.")
        return

    # Add test gateways
    import json
    from optimade_gateway.mongo.database import MONGO_DB
    from pathlib import Path

    LOGGER.info(
        "CI detected - Will load test gateways (after dropping the collection)!"
    )

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
