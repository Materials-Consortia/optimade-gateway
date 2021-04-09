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

from fastapi import APIRouter, Depends, Request
from optimade.models import (
    ErrorResponse,
    Meta,
    StructureResponseMany,
    StructureResponseOne,
    ToplevelLinks,
)
from optimade.server.exceptions import BadRequest
from optimade.server.query_params import EntryListingQueryParams, SingleEntryQueryParams
from optimade.server.routers.utils import meta_values

from optimade_gateway.models import QueryResource
from optimade_gateway.routers.gateway.utils import get_valid_resource, validate_version
from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION


ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/gateways/{gateway_id}/structures",
    response_model=Union[StructureResponseMany, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Structures"],
)
async def get_structures(
    request: Request,
    gateway_id: str,
    params: EntryListingQueryParams = Depends(),
) -> StructureResponseMany:
    """GET /gateways/{gateway_id}/structures

    Return a regular /structures response for an OPTIMADE implementation,
    including responses from all the gateway's databases.
    """
    from optimade_gateway.queries import perform_query
    from optimade_gateway.routers.utils import validate_resource

    await validate_resource(GATEWAYS_COLLECTION, gateway_id)

    return await perform_query(
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
                    "endpoint_model": (
                        StructureResponseMany.__module__,
                        StructureResponseMany.__name__,
                    ),
                },
            }
        ),
        use_query_resource=False,
    )


@ROUTER.get(
    "/gateways/{gateway_id}/structures/{structure_id:path}",
    response_model=Union[StructureResponseOne, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Structures"],
)
async def get_single_structure(
    request: Request,
    gateway_id: str,
    structure_id: str,
    params: SingleEntryQueryParams = Depends(),
) -> StructureResponseOne:
    """GET /gateways/{gateway_id}/structures/{structure_id}

    Return a regular /structures/{id} response for an OPTIMADE implementation.
    The structure_id must be of the type {database}/{id}.
    """
    from optimade_gateway.models import GatewayResource
    from optimade_gateway.queries import db_find

    gateway: GatewayResource = await get_valid_resource(GATEWAYS_COLLECTION, gateway_id)

    local_structure_id = None
    for database in gateway.attributes.databases:
        if structure_id.startswith(f"{database.id}/"):
            # Database found
            local_structure_id = structure_id[len(f"{database.id}/") :]
            break
    else:
        raise BadRequest(
            detail=(
                f"Structures entry <id={structure_id}> not found. To get a specific structures entry "
                "one needs to prepend the ID with a database ID belonging to the gateway, e.g., "
                f"'{gateway.attributes.databases[0].id}/<local_database_ID>'. Available databases for "
                f"gateway {gateway_id!r}: {[_.id for _ in gateway.attributes.databases]}"
            )
        )

    errors = []
    result = None
    parsed_params = urllib.parse.urlencode(
        {param: value for param, value in params.__dict__.items() if value}
    )

    (response, _) = await asyncio.get_running_loop().run_in_executor(
        executor=None,  # Run in thread with the event loop
        func=functools.partial(
            db_find,
            database=database,
            endpoint=f"structures/{local_structure_id}",
            response_model=StructureResponseOne,
            query_params=parsed_params,
        ),
    )

    if isinstance(response, ErrorResponse):
        for error in response.errors:
            if isinstance(error.id, str) and error.id.startswith("OPTIMADE_GATEWAY"):
                warnings.warn(error.detail)
            else:
                meta = {}
                if error.meta:
                    meta = error.meta.dict()
                meta.update(
                    {
                        "optimade_gateway": {
                            "gateway": gateway,
                            "source_database_id": database.id,
                        }
                    }
                )
                error.meta = Meta(**meta)
                errors.append(error)
    else:
        result = response.data
        if isinstance(result, dict) and result.get("id") is not None:
            result["id"] = f"{database.id}/{result['id']}"
        elif result is None:
            pass
        else:
            result.id = f"{database.id}/{result.id}"

    meta = meta_values(
        url=request.url,
        data_returned=response.meta.data_returned,
        data_available=None,  # Don't set this, as we'd have to request ALL gateway databases
        more_data_available=response.meta.more_data_available,
    )
    del meta.data_available

    if errors:
        return ErrorResponse(errors=errors, meta=meta)

    return StructureResponseOne(links=ToplevelLinks(next=None), data=result, meta=meta)


@ROUTER.get(
    "/gateways/{gateway_id}/{version}/structures",
    response_model=Union[StructureResponseMany, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Structures"],
    include_in_schema=False,
)
async def get_versioned_structures(
    request: Request,
    gateway_id: str,
    version: str,
    params: EntryListingQueryParams = Depends(),
) -> StructureResponseMany:
    """GET /gateways/{gateway_id}/{version}/structures

    Same as GET /gateways/{gateway_id}/structures.
    """
    await validate_version(version)
    return await get_structures(request, gateway_id, params)


@ROUTER.get(
    "/gateways/{gateway_id}/{version}/structures/{structure_id:path}",
    response_model=Union[StructureResponseOne, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Structures"],
    include_in_schema=False,
)
async def get_versioned_single_structure(
    request: Request,
    gateway_id: str,
    version: str,
    structure_id: str,
    params: SingleEntryQueryParams = Depends(),
) -> StructureResponseOne:
    """GET /gateways/{gateway_id}/{version}/structures/{structure_id}

    Same as GET /gateways/{gateway_id}/structures/{structure_id}.
    """
    await validate_version(version)
    return await get_single_structure(request, gateway_id, structure_id, params)
