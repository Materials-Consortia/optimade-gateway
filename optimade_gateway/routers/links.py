"""/links/*

This file describes the router for:

    /links

"""
from fastapi import APIRouter, Depends, Request

from optimade.models import LinksResponse, LinksResource
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.schemas import ERROR_RESPONSES

from optimade_gateway.common.config import CONFIG
from optimade_gateway.mappers.links import LinksMapper
from optimade_gateway.mongo.collection import AsyncMongoCollection
from optimade_gateway.routers.utils import get_entries

ROUTER = APIRouter(redirect_slashes=True)

LINKS_COLLECTION = AsyncMongoCollection(
    name=CONFIG.links_collection,
    resource_cls=LinksResource,
    resource_mapper=LinksMapper,
)


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
        collection=LINKS_COLLECTION,
        response_cls=LinksResponse,
        request=request,
        params=params,
    )
