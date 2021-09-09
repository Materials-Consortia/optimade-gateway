"""/links/*

This file describes the router for:

    /links

"""
from fastapi import APIRouter, Depends, Request

from optimade.models import LinksResponse
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.schemas import ERROR_RESPONSES

from optimade_gateway.common.config import CONFIG
from optimade_gateway.routers.utils import collection_factory, get_entries


ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/links",
    response_model=LinksResponse,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Links"],
    responses=ERROR_RESPONSES,
)
async def get_links(
    request: Request, params: EntryListingQueryParams = Depends()
) -> LinksResponse:
    """`GET /links`

    Return a regular `/links` response for an OPTIMADE implementation.
    """
    return await get_entries(
        collection=await collection_factory(CONFIG.links_collection),
        response_cls=LinksResponse,
        request=request,
        params=params,
    )
