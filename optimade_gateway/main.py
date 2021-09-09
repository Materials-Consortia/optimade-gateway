"""The initialization of the ASGI FastAPI application."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse

from optimade.server.exception_handlers import OPTIMADE_EXCEPTIONS
from optimade.server.middleware import OPTIMADE_MIDDLEWARE
from optimade.server.routers.utils import BASE_URL_PREFIXES
from optimade.server.routers.versions import router as versions_router

from optimade_gateway import __version__
from optimade_gateway.exception_handlers import request_validation_exception_handler
from optimade_gateway.middleware import CheckWronglyVersionedBaseUrlsGateways
from optimade_gateway.events import EVENTS
from optimade_gateway.routers import (
    databases,
    gateways,
    info,
    links,
    queries,
    search,
)

APP = FastAPI(
    title="OPTIMADE Gateway",
    description="A gateway server to query multiple OPTIMADE databases.",
    version=__version__,
)
"""The FastAPI ASGI application."""


@APP.get("/", include_in_schema=False)
async def get_root(request: Request) -> RedirectResponse:
    """`GET /`

    Introspective overview of gateway server.

    !!! note
        Temporarily redirecting to `GET /docs`.
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
    if exception == RequestValidationError:
        handler = request_validation_exception_handler
    APP.add_exception_handler(exception, handler)

# Add the special /versions endpoint(s)
APP.include_router(versions_router)

# Add endpoints to / and /vMAJOR
for prefix in list(BASE_URL_PREFIXES.values()) + [""]:
    for router in (databases, gateways, info, links, queries, search):
        APP.include_router(
            router.ROUTER,  # type: ignore[attr-defined]
            prefix=prefix,
            include_in_schema=prefix == "",
        )

for event, func in EVENTS:
    APP.add_event_handler(event, func)
