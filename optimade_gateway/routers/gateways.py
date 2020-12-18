from optimade_gateway.models.gateways import GatewayResourceAttributes
from typing import Union

from fastapi import APIRouter, Request
from optimade.models import ErrorResponse, ToplevelLinks
from optimade.server.routers.utils import meta_values

from optimade_gateway.models import GatewaysResponse


ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/gateways",
    response_model=Union[GatewaysResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
    tags=["Gateways"],
)
def get_gateways(request: Request) -> Union[GatewaysResponse, ErrorResponse]:
    """GET /gateways

    Return overview of all (active) gateways.
    """
    gateways = []  # get_all_gateways()
    included = []

    return GatewaysResponse(
        links=ToplevelLinks(next=None),
        data=gateways,
        meta=meta_values(
            url=request.url,
            data_returned=len(gateways),
            data_available=len(gateways),
            more_data_available=False,
        ),
        included=included,
    )


@ROUTER.post(
    "/gateways",
    response_model=Union[GatewaysResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
    tags=["Gateways"],
)
def post_gateways(
    request: Request, gateway: GatewayResourceAttributes
) -> Union[GatewaysResponse, ErrorResponse]:
    """POST /gateways

    Create or return existing gateway according to `gateway`.
    """
    gateways = []  # find_create_gateway(**gateway)
    included = []

    return GatewaysResponse(
        links=ToplevelLinks(next=None),
        data=gateways,
        meta=meta_values(
            url=request.url,
            data_returned=len(gateways),
            data_available=len(gateways),
            more_data_available=False,
        ),
        included=included,
    )
