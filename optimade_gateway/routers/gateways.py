from typing import Union

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from optimade.models import ErrorResponse, ToplevelLinks
from optimade.server.config import CONFIG
from optimade.server.entry_collections import MongoCollection, client
from optimade.server.routers.utils import meta_values

from optimade_gateway.mappers import GatewaysMapper
from optimade_gateway.models import (
    GatewaysResponse,
    GatewayResource,
    GatewayResourceAttributes,
)
from optimade_gateway.routers.utils import find_create_gateway


ROUTER = APIRouter(redirect_slashes=True)

GATEWAY_COLLECTION = MongoCollection(
    collection=client[CONFIG.mongo_database]["gateways"],
    resource_cls=GatewayResource,
    resource_mapper=GatewaysMapper,
)


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
    gateways = find_create_gateway(
        providers=gateway.databases, collection=GATEWAY_COLLECTION
    )
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


@ROUTER.get(
    "/gateways/{gateway_id}",
    response_model=RedirectResponse,
    response_model_exclude_defaults=False,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
    tags=["Gateways"],
)
def get_gateway(
    request: Request, gateway_id: int
) -> Union[GatewaysResponse, ErrorResponse]:
    """GET /gateways/{gateway ID}

    Represent an OPTIMADE server.
    For now, redirect to the gateway's /structures entry listing endpoint
    """
    return RedirectResponse(f"{request.url}/structures")
