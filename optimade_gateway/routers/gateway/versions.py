from fastapi import APIRouter, Request
from optimade.server.routers.versions import CsvResponse

ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/gateways/{gateway_id}/versions",
    response_class=CsvResponse,
    tags=["Versions"],
)
async def get_gateway_versions(request: Request, gateway_id: str) -> CsvResponse:
    """GET /gateways/{gateway_id}/versions

    Return the result of the function used to GET /versions from the `optimade` package.
    """
    from optimade.server.routers.versions import get_versions

    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION
    from optimade_gateway.routers.utils import validate_resource

    await validate_resource(GATEWAYS_COLLECTION, gateway_id)
    return get_versions(request)
