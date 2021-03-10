import concurrent.futures
import os
import sys
from typing import Union
import urllib
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

from optimade_gateway.routers.gateway.utils import get_valid_gateway, validate_version

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
    from optimade.server.routers.utils import get_base_url
    from optimade_gateway.routers.gateway.utils import db_find

    gateway = await get_valid_gateway(gateway_id)

    more_data_available = False
    data_available = 0
    data_returned = 0
    results = []
    errors = []
    parsed_params = urllib.parse.urlencode(
        {param: value for param, value in params.__dict__.items() if value}
    )

    PY38_DEFAULT = None
    if sys.version_info.minor < 8:
        # Using Python 3.7 or below
        PY38_DEFAULT = min(32, os.cpu_count() + 4)
    with concurrent.futures.ThreadPoolExecutor(max_workers=PY38_DEFAULT) as executor:
        future_to_db_id = {
            executor.submit(
                db_find,
                db,
                "structures",
                StructureResponseMany,
                parsed_params,
            ): db.id
            for db in gateway.attributes.databases
        }
        for future in concurrent.futures.as_completed(future_to_db_id):
            db_id = future_to_db_id[future]
            response: Union[ErrorResponse, StructureResponseMany] = future.result()
            if isinstance(response, ErrorResponse):
                for error in response.errors:
                    if isinstance(error.id, str) and error.id.startswith(
                        "OPTIMADE_GATEWAY"
                    ):
                        warnings.warn(error.detail)
                    else:
                        meta = {}
                        if error.meta:
                            meta = error.meta.dict()
                        meta.update(
                            {
                                "optimade_gateway": {
                                    "gateway": gateway,
                                    "source_database_id": db_id,
                                }
                            }
                        )
                        error.meta = Meta(**meta)
                        errors.append(error)
            else:
                for datum in response.data:
                    if isinstance(datum, dict) and datum.get("id") is not None:
                        datum["id"] = f"{db_id}/{datum['id']}"
                    else:
                        datum.id = f"{db_id}/{datum.id}"
                results.extend(response.data)

                data_available += response.meta.data_available or 0
                data_returned += response.meta.data_returned or len(response.data)

                if not more_data_available:
                    # Keep it True, if set to True once.
                    more_data_available = response.meta.more_data_available

    if errors:
        return ErrorResponse(
            errors=errors,
            meta=meta_values(
                url=request.url,
                data_returned=0,
                data_available=data_available,
                more_data_available=False,
            ),
        )

    # Sort results over two steps, first by database id,
    # and then by (original) "id", since "id" MUST always be present.
    results.sort(key=lambda data: data["id"] if "id" in data else data.id)
    results.sort(
        key=lambda data: "/".join(data["id"].split("/")[1:])
        if "id" in data
        else "/".join(data.id.split("/")[1:])
    )

    if more_data_available:
        # Deduce the `next` link from the current request
        query = urllib.parse.parse_qs(request.url.query)
        query["page_offset"] = int(query.get("page_offset", [0])[0]) + len(
            results[: params.page_limit]
        )
        urlencoded = urllib.parse.urlencode(query, doseq=True)
        base_url = get_base_url(request.url)

        links = ToplevelLinks(next=f"{base_url}{request.url.path}?{urlencoded}")
    else:
        links = ToplevelLinks(next=None)

    return StructureResponseMany(
        links=links,
        data=results,
        meta=meta_values(
            url=request.url,
            data_returned=data_returned,
            data_available=data_available,
            more_data_available=more_data_available,
        ),
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
    from optimade_gateway.routers.gateway.utils import adb_find

    gateway = await get_valid_gateway(gateway_id)

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

    response: Union[ErrorResponse, StructureResponseOne] = await adb_find(
        database=database,
        endpoint=f"structures/{local_structure_id}",
        response_model=StructureResponseOne,
        query_params=parsed_params,
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
    response_model=Union[StructureResponseMany, ErrorResponse],
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
