from typing import Union

from fastapi import APIRouter, Depends, Request

from optimade.models import ErrorResponse, LinksResponse, LinksResource
from optimade.server.mappers import LinksMapper
from optimade.server.query_params import EntryListingQueryParams
from optimade.server.routers.utils import get_entries

from optimade_gateway.common.config import CONFIG
from optimade_gateway.mongo.collection import AsyncMongoCollection
from optimade_gateway.mongo.database import MONGO_DB

ROUTER = APIRouter(redirect_slashes=True)

LINKS_COLLECTION = AsyncMongoCollection(
    collection=MONGO_DB[CONFIG.links_collection],
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
def get_links(request: Request, params: EntryListingQueryParams = Depends()):
    return get_entries(
        collection=LINKS_COLLECTION,
        response=LinksResponse,
        request=request,
        params=params,
    )
