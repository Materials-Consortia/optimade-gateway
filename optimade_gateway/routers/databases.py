"""/databases/*

This file describes the router for:

    /databases/{id}

where, `id` may be left out.

Database resources represent the available databases that may be used for the gateways.

One can register a new database (by using `POST /databases`) or look through the available
databases (by using `GET /databases`) using standard OPTIMADE filtering.
"""
from typing import Union

from fastapi import APIRouter, Depends, Request
from optimade.models import ErrorResponse, LinksResource, ToplevelLinks
from optimade.server.query_params import EntryListingQueryParams, SingleEntryQueryParams
from optimade.server.routers.utils import handle_response_fields, meta_values

from optimade_gateway.common.config import CONFIG
from optimade_gateway.mappers import DatabasesMapper
from optimade_gateway.models import (
    DatabaseCreate,
    DatabasesResponse,
    DatabasesResponseSingle,
)
from optimade_gateway.mongo.collection import AsyncMongoCollection


ROUTER = APIRouter(redirect_slashes=True)

DATABASES_COLLECTION = AsyncMongoCollection(
    name=CONFIG.databases_collection,
    resource_cls=LinksResource,
    resource_mapper=DatabasesMapper,
)


@ROUTER.get(
    "/databases",
    response_model=Union[DatabasesResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Databases"],
)
async def get_databases(
    request: Request,
    params: EntryListingQueryParams = Depends(),
) -> DatabasesResponse:
    """GET /databases

    Return overview of all (active) databases.
    """
    from optimade_gateway.routers.utils import get_entries

    return await get_entries(
        collection=DATABASES_COLLECTION,
        response_cls=DatabasesResponse,
        request=request,
        params=params,
    )


@ROUTER.post(
    "/databases",
    response_model=Union[DatabasesResponseSingle, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Databases"],
)
async def post_databases(
    request: Request, database: DatabaseCreate
) -> DatabasesResponseSingle:
    """POST /databases

    Create/Register or return an existing `LinksResource´, representing a database resource object,
    according to `database`.
    """
    from optimade_gateway.routers.utils import resource_factory

    result, created = await resource_factory(database)

    return DatabasesResponseSingle(
        links=ToplevelLinks(next=None),
        data=result,
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=await DATABASES_COLLECTION.count(),
            more_data_available=False,
            **{f"_{CONFIG.provider.prefix}_created": created},
        ),
    )


@ROUTER.get(
    "/databases/{database_id:path}",
    response_model=Union[DatabasesResponseSingle, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Databases"],
)
async def get_database(
    request: Request,
    database_id: str,
    params: SingleEntryQueryParams = Depends(),
) -> DatabasesResponseSingle:
    """GET /databases/{database ID}

    Return a single `LinksResource` representing the database resource object with id=`database_id`.
    """
    params.filter = f'id="{database_id}"'
    result, _, fields = await DATABASES_COLLECTION.find(params=params)

    if fields and result is not None:
        result = handle_response_fields(result, fields)[0]

    return DatabasesResponseSingle(
        links=ToplevelLinks(next=None),
        data=result,
        meta=meta_values(
            url=request.url,
            data_returned=0 if result is None else 1,
            data_available=await DATABASES_COLLECTION.count(),
            more_data_available=False,
        ),
    )
