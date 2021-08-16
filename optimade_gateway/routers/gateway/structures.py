"""/gateways/{id}/structures/*

This file describes the router for:

    /gateways/{id}/{version}/structures/{id}

where `version` and the last `id` may be left out.
"""
import asyncio
from datetime import datetime
import functools
from typing import Union
import urllib.parse
import warnings

from fastapi import APIRouter, Depends, Request, Response
from optimade.models import (
    ErrorResponse,
    Meta,
    StructureResponseMany,
    StructureResponseOne,
    ToplevelLinks,
)
from optimade.server.query_params import EntryListingQueryParams, SingleEntryQueryParams
from optimade.server.routers.utils import meta_values
from optimade.server.schemas import ERROR_RESPONSES

from optimade_gateway.models import QueryResource
from optimade_gateway.queries import perform_query
from optimade_gateway.routers.gateway.utils import validate_version
from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION
from optimade_gateway.warnings import OptimadeGatewayWarning, SortNotSupported


ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/gateways/{gateway_id}/structures",
    response_model=Union[StructureResponseMany, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Structures"],
    responses=ERROR_RESPONSES,
)
async def get_structures(
    request: Request,
    gateway_id: str,
    response: Response,
    params: EntryListingQueryParams = Depends(),
) -> Union[StructureResponseMany, ErrorResponse]:
    """`GET /gateways/{gateway_id}/structures`

    Return a regular `/structures` response for an OPTIMADE implementation,
    including responses from all the gateway's databases.
    """
    from optimade_gateway.routers.utils import validate_resource

    await validate_resource(GATEWAYS_COLLECTION, gateway_id)

    if getattr(params, "sort", False):
        warnings.warn(SortNotSupported())
        params.sort = ""

    gateway_response = await perform_query(
        url=request.url,
        query=QueryResource(
            **{
                "id": "temp",
                "type": "queries",
                "attributes": {
                    "last_modified": datetime.utcnow(),
                    "gateway_id": gateway_id,
                    "state": "created",
                    "query_parameters": {
                        key: value for key, value in params.__dict__.items() if value
                    },
                    "endpoint": "structures",
                },
            }
        ),
        use_query_resource=False,
    )

    if isinstance(gateway_response, ErrorResponse):
        for error in gateway_response.errors:
            if error.status:
                for part in error.status.split(" "):
                    try:
                        response.status_code = int(part)
                        break
                    except ValueError:
                        pass
                if response.status_code and response.status_code >= 300:
                    break
        else:
            response.status_code = 500
        return gateway_response
    elif isinstance(gateway_response, StructureResponseMany):
        return gateway_response
    else:
        raise TypeError(
            "The response should be either StructureResponseMany or ErrorResponse."
        )


@ROUTER.get(
    "/gateways/{gateway_id}/structures/{structure_id:path}",
    response_model=Union[StructureResponseOne, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Structures"],
    responses=ERROR_RESPONSES,
)
async def get_single_structure(
    request: Request,
    gateway_id: str,
    structure_id: str,
    response: Response,
    params: SingleEntryQueryParams = Depends(),
) -> Union[StructureResponseOne, ErrorResponse]:
    """`GET /gateways/{gateway_id}/structures/{structure_id}`

    Return a regular `/structures/{id}` response for an OPTIMADE implementation.

    !!! important
        There are two options for the `structure_id`.

        Either one supplies an entry ID similar to what is given in the local databases.
        This will result in this endpoint returning the first entry it finds from any database that
        matches the given ID.

        Example: `GET /gateway/some_gateway/structures/some_structure`.

        Otherwise, one can supply the database ID (call `GET /databases` to see all available
        databases and their IDs), and then the local entry ID, separated by a forward slash.

        Example: `GET /gateways/some_gateway/structures/some_database/some_structure`.

    """
    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.models import GatewayResource
    from optimade_gateway.queries import db_find
    from optimade_gateway.routers.utils import get_valid_resource

    gateway: GatewayResource = await get_valid_resource(GATEWAYS_COLLECTION, gateway_id)

    local_structure_id = None
    database_id = None

    for database in gateway.attributes.databases:
        if structure_id.startswith(f"{database.id}/"):
            # Database found
            database_id = database.id
            local_structure_id = structure_id[len(f"{database_id}/") :]
            break
    else:
        # Assume the given ID is already a local database ID - find and return the first one
        # available.
        local_structure_id = structure_id

    errors = []
    parsed_params = urllib.parse.urlencode(
        {param: value for param, value in params.__dict__.items() if value}
    )

    if database_id:
        (gateway_response, _) = await asyncio.get_running_loop().run_in_executor(
            executor=None,  # Run in thread with the event loop
            func=functools.partial(
                db_find,
                database=database,
                endpoint=f"structures/{local_structure_id}",
                response_model=StructureResponseOne,
                query_params=parsed_params,
            ),
        )
        if isinstance(gateway_response, ErrorResponse):
            for error in gateway_response.errors:
                if isinstance(error.id, str) and error.id.startswith(
                    "OPTIMADE_GATEWAY"
                ):
                    warnings.warn(error.detail, OptimadeGatewayWarning)
                else:
                    meta = {}
                    if error.meta:
                        meta = error.meta.dict()
                    meta.update(
                        {
                            f"_{CONFIG.provider.prefix}_source_gateway": {
                                "id": gateway.id,
                                "type": gateway.type,
                                "links": {"self": gateway.links.self},
                            },
                            f"_{CONFIG.provider.prefix}_source_database": {
                                "id": database.id,
                                "type": database.type,
                                "links": {"self": database.links.self},
                            },
                        }
                    )
                    error.meta = Meta(**meta)
                    errors.append(error)

        meta = meta_values(
            url=request.url,
            data_returned=gateway_response.meta.data_returned,
            data_available=None,  # Don't set this, as we'd have to request ALL gateway databases
            more_data_available=gateway_response.meta.more_data_available,
        )
        del meta.data_available

        if errors:
            gateway_response = ErrorResponse(errors=errors, meta=meta)
        else:
            gateway_response = StructureResponseOne(
                links=ToplevelLinks(next=None), data=gateway_response.data, meta=meta
            )

    else:
        params.filter = f'id="{local_structure_id}"'
        gateway_response = await perform_query(
            url=request.url,
            query=QueryResource(
                **{
                    "id": "temp",
                    "type": "queries",
                    "attributes": {
                        "last_modified": datetime.utcnow(),
                        "gateway_id": gateway_id,
                        "state": "created",
                        "query_parameters": {
                            key: value
                            for key, value in params.__dict__.items()
                            if value
                        },
                        "endpoint": "structures",
                    },
                }
            ),
            use_query_resource=False,
        )
        if isinstance(gateway_response, StructureResponseMany):
            gateway_response = gateway_response.dict(exclude_unset=True)
            gateway_response["data"] = (
                gateway_response["data"][0] if gateway_response["data"] else None
            )
            gateway_response = StructureResponseOne(**gateway_response)

    if isinstance(gateway_response, ErrorResponse):
        for error in errors or gateway_response.errors:
            if error.status:
                for part in error.status.split(" "):
                    try:
                        response.status_code = int(part)
                        break
                    except ValueError:
                        pass
                if response.status_code and response.status_code >= 300:
                    break
        else:
            response.status_code = 500

    return gateway_response


@ROUTER.get(
    "/gateways/{gateway_id}/{version}/structures",
    response_model=Union[StructureResponseMany, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Structures"],
    include_in_schema=False,
    responses=ERROR_RESPONSES,
)
async def get_versioned_structures(
    request: Request,
    gateway_id: str,
    version: str,
    response: Response,
    params: EntryListingQueryParams = Depends(),
) -> Union[StructureResponseMany, ErrorResponse]:
    """`GET /gateways/{gateway_id}/{version}/structures`

    Same as `GET /gateways/{gateway_id}/structures`.
    """
    await validate_version(version)
    return await get_structures(request, gateway_id, response, params)


@ROUTER.get(
    "/gateways/{gateway_id}/{version}/structures/{structure_id:path}",
    response_model=Union[StructureResponseOne, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Structures"],
    include_in_schema=False,
    responses=ERROR_RESPONSES,
)
async def get_versioned_single_structure(
    request: Request,
    gateway_id: str,
    version: str,
    structure_id: str,
    response: Response,
    params: SingleEntryQueryParams = Depends(),
) -> Union[StructureResponseOne, ErrorResponse]:
    """`GET /gateways/{gateway_id}/{version}/structures/{structure_id}`

    Same as `GET /gateways/{gateway_id}/structures/{structure_id}`.
    """
    await validate_version(version)
    return await get_single_structure(
        request, gateway_id, structure_id, response, params
    )
