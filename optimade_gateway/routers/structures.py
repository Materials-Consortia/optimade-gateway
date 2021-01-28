from typing import Union

from fastapi import APIRouter, Depends, Request
from optimade.models import (
    ErrorResponse,
    StructureResource,
    StructureResponseMany,
    StructureResponseOne,
)
from optimade.server.mappers import StructureMapper
from optimade.server.query_params import EntryListingQueryParams, SingleEntryQueryParams

from optimade_gateway.common.config import CONFIG
from optimade_gateway.mongo.collection import AsyncMongoCollection
from optimade_gateway.mongo.database import MONGO_DB


ROUTER = APIRouter(redirect_slashes=True)

STRUCTURES_COLLECTION = AsyncMongoCollection(
    collection=MONGO_DB[CONFIG.structures_collection],
    resource_cls=StructureResource,
    resource_mapper=StructureMapper,
)


@ROUTER.get(
    "/gateways/{gateway_id}/structures",
    response_model=Union[StructureResponseMany, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
    tags=["Structures"],
)
async def get_structures(
    request: Request, gateway_id: int, params: EntryListingQueryParams = Depends()
):
    """GET /gateways/{gateway_id}/structures

    Retrieve and serve structure entries from the gateway's providers.
    Store entries in DB.
    """
    return StructureResponseMany(data=[])


@ROUTER.get(
    "/gateways/{gateway_id}/structures/{entry_id:path}",
    response_model=Union[StructureResponseOne, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
    tags=["Structures"],
)
async def get_single_structure(
    request: Request, entry_id: str, params: SingleEntryQueryParams = Depends()
):
    return StructureResponseOne(data={})
