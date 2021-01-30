from fastapi import FastAPI
from fastapi.responses import JSONResponse

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


@APP.get("/optimade")
async def get_root() -> JSONResponse:
    """Introspective overview of gateway server."""
    return JSONResponse(content={"data": {}}, status_code=200)


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
