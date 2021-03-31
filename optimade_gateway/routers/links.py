"""/links/*

This file describes the router for:

    /links

"""
from typing import Union

from fastapi import APIRouter, Depends, Request

from optimade.models import ErrorResponse, LinksResponse, LinksResource
from optimade.server.mappers import LinksMapper
from optimade.server.query_params import EntryListingQueryParams

from optimade_gateway.common.config import CONFIG
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
    response_model=Union[LinksResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Links"],
)
async def get_links(
    request: Request, params: EntryListingQueryParams = Depends()
) -> LinksResponse:
    """GET /links

    Return a regular /links response for an OPTIMADE implementation.
    """
    return await get_entries(
        collection=LINKS_COLLECTION,
        response_cls=LinksResponse,
        request=request,
        params=params,
    )
