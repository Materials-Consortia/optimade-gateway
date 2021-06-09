"""Special /queries endpoint for a gateway to perform and list queries

This file describes the router for:

    /gateways/{id}/{version}/queries/{id}

where `version` and the last `id` may be left out.
"""
from fastapi import APIRouter, Depends, Request, status
from optimade.models.responses import EntryResponseMany
from optimade.server.exceptions import Forbidden
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.schemas import ERROR_RESPONSES

from optimade_gateway.models import (
    QueryCreate,
    QueriesResponse,
    QueriesResponseSingle,
)
from optimade_gateway.routers.utils import validate_resource


ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/gateways/{gateway_id}/queries",
    response_model=QueriesResponse,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Gateways", "Queries"],
    responses=ERROR_RESPONSES,
)
async def get_gateway_queries(
    request: Request,
    gateway_id: str,
    params: EntryListingQueryParams = Depends(),
) -> QueriesResponse:
    """`GET /gateways/{gateway_id}/queries`

    Return overview of all (active) queries for specific gateway.
    """
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION
    from optimade_gateway.routers.queries import get_queries

    await validate_resource(GATEWAYS_COLLECTION, gateway_id)

    params.filter = (
        f'( {params.filter} ) AND ( gateway="{gateway_id}" )'
        if params.filter
        else f'gateway="{gateway_id}"'
    )
    return await get_queries(request, params)


@ROUTER.post(
    "/gateways/{gateway_id}/queries",
    response_model=QueriesResponseSingle,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Gateways", "Queries"],
    status_code=status.HTTP_202_ACCEPTED,
    responses=ERROR_RESPONSES,
)
async def post_gateway_queries(
    request: Request,
    gateway_id: str,
    query: QueryCreate,
) -> QueriesResponseSingle:
    """`POST /gateways/{gateway_id}/queries`

    Create or return existing gateway query according to `query`.
    """
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION
    from optimade_gateway.routers.queries import post_queries

    await validate_resource(GATEWAYS_COLLECTION, gateway_id)

    if query.gateway_id and query.gateway_id != gateway_id:
        raise Forbidden(
            detail=(
                f"The gateway ID in the posted data (<gateway={query.gateway_id}>) does not align "
                f"with the gateway ID specified in the URL (/{gateway_id}/)."
            ),
        )

    return await post_queries(request, query)


@ROUTER.get(
    "/gateways/{gateway_id}/queries/{query_id}",
    response_model=EntryResponseMany,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Gateways", "Queries"],
    responses=ERROR_RESPONSES,
)
async def get_gateway_query(
    request: Request, gateway_id: str, query_id: str
) -> EntryResponseMany:
    """`GET /gateways/{gateway_id}/queries/{query_id}`

    Return the response from a gateway query
    ([`QueryResource.attributes.response`][optimade_gateway.models.queries.QueryResourceAttributes.response]).
    """
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION
    from optimade_gateway.routers.queries import get_query

    await validate_resource(GATEWAYS_COLLECTION, gateway_id)

    return await get_query(request, query_id)
