"""The initialization of the ASGI FastAPI application."""
from typing import TYPE_CHECKING

import fastapi.applications
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse

from optimade.server.exception_handlers import OPTIMADE_EXCEPTIONS
from optimade.server.middleware import OPTIMADE_MIDDLEWARE
from optimade.server.routers.utils import BASE_URL_PREFIXES, JSONAPIResponse
from optimade.server.routers.versions import router as versions_router

from optimade_gateway import __version__
from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.utils import gateway_get_swagger_ui_html
from optimade_gateway.exception_handlers import request_validation_exception_handler
from optimade_gateway.middleware import CheckWronglyVersionedBaseUrlsGateways
from optimade_gateway.events import EVENTS
from optimade_gateway.routers import ROUTERS
from optimade_gateway.security.oauth2 import get_marketplace_user


if TYPE_CHECKING:
    from typing import Any, Dict

fastapi.applications.get_swagger_ui_html = gateway_get_swagger_ui_html
APP = FastAPI(
    title="OPTIMADE Gateway",
    description="A gateway server to query multiple OPTIMADE databases.",
    version=__version__,
    root_path=CONFIG.root_path,
    default_response_class=JSONAPIResponse,
    servers=[{"url": CONFIG.base_url or ""}],
    **{
        "x-application-name": "OPTIMADE Gateway",
        "x-application-id": CONFIG.hydra_application_id,
        "x-external-hostname": CONFIG.base_url,
        "x-image": (
            "https://raw.githubusercontent.com/Materials-Consortia"
            "/optimade-python-tools/master/images/optimade_logo_180x180.svg"
        ),
        "x-products": [
            {
                "name": "OPTIMADE Gateway",
                "productId": "22e6e756-7179-47c9-8f37-1ee06c7b38ae",
            },
        ],
    },
    swagger_ui_init_oauth={
        "clientId": CONFIG.hydra_application_id,
        "clientSecret": CONFIG.hydra_client_secret,
        "scopes": [_.value for _ in CONFIG.hydra_scopes],
    },
    swagger_ui_oauth2_redirect_url="/callback",
)
"""The FastAPI ASGI application."""


@APP.get("/", include_in_schema=False)
async def get_root(request: Request) -> RedirectResponse:
    """`GET /`

    Introspective overview of gateway server.

    !!! note
        Redirecting to `GET /redoc`.

    """
    return RedirectResponse(
        request.url.replace(path=f"{request.url.path.strip('/')}/redoc")
    )


def marketplace_openapi() -> "Dict[str, Any]":
    """Add all `**extra` values from the `APP` to the OpenAPI schema's `info` value."""
    if APP.openapi_schema:
        return APP.openapi_schema
    APP.openapi_schema = get_openapi(
        title=APP.title,
        version=APP.version,
        openapi_version=APP.openapi_version,
        description=APP.description,
        routes=APP.routes,
        tags=APP.openapi_tags,
        servers=APP.servers,
    )
    APP.openapi_schema["info"].update(APP.extra)
    return APP.openapi_schema


APP.openapi = marketplace_openapi  # type: ignore[assignment]

# Add CORS middleware first
# cors_origins = [f"https://{CONFIG.marketplace_host.value}"]
# if CONFIG.debug:
#     cors_origins.append("*")
APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["Content-Type", "api_key", "Authorization"],
    allow_methods=["*"],
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
    for router in ROUTERS.routers():
        APP.include_router(
            router,
            prefix=prefix,
            include_in_schema=prefix == "",
            dependencies=[Depends(get_marketplace_user)],
        )

for event, func in EVENTS:
    APP.add_event_handler(event, func)
