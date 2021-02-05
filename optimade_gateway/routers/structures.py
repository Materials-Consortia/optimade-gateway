import concurrent.futures
import os
import requests
import sys
from typing import Union
import urllib
import warnings

try:
    import simplejson as json
except ImportError:
    import json

from fastapi import APIRouter, Depends, Request
from optimade.models import (
    EntryResponseMany,
    ErrorResponse,
    LinksResource,
    StructureResponseMany,
    StructureResponseOne,
    ToplevelLinks,
)
from optimade.server.query_params import EntryListingQueryParams, SingleEntryQueryParams
from optimade.server.routers.utils import meta_values, BASE_URL_PREFIXES

from optimade_gateway.models import GatewayResource

ROUTER = APIRouter(redirect_slashes=True)


@ROUTER.get(
    "/gateways/{gateway_id}/structures",
    response_model=Union[StructureResponseMany, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=True,
    response_model_exclude_unset=False,
    tags=["Structures"],
)
async def get_structures(
    request: Request,
    gateway_id: str,
    params: EntryListingQueryParams = Depends(),
) -> Union[StructureResponseMany, ErrorResponse]:
    """GET /gateways/{gateway_id}/structures

    Return a regular /structures response for an OPTIMADE implementation,
    including responses from all the gateway's databases.
    """
    from optimade.models import Meta
    from optimade.server.routers.utils import get_base_url
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION

    gateway: GatewayResource = await GATEWAYS_COLLECTION.get_one(
        filter={"id": gateway_id}
    )

    more_data_available = False
    data_available = 0
    data_returned = 0
    results = []
    errors = []

    PY38_DEFAULT = None
    if sys.version_info.minor < 8:
        # Using Python 3.7 or below
        PY38_DEFAULT = min(32, os.cpu_count() + 4)
    with concurrent.futures.ThreadPoolExecutor(max_workers=PY38_DEFAULT) as executor:
        future_to_db_id = {
            executor.submit(
                db_find_many, db, "structures", StructureResponseMany, request.url.query
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

    if not results and errors:
        return ErrorResponse(
            errors=errors,
            meta=meta_values(
                url=request.url,
                data_returned=0,
                data_available=data_available,
                more_data_available=False,
            ),
        )

    # Sort results by (original) "id", since "id" MUST always be present.
    if getattr(params, "response_fields", False):
        results = sorted(results, key=lambda data: "/".join(data["id"].split("/")[1:]))
    else:
        results = sorted(results, key=lambda data: "/".join(data.id.split("/")[1:]))

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


def db_find_many(
    database: LinksResource,
    endpoint: str,
    response_model: EntryResponseMany,
    query_params: str = "",
) -> Union[ErrorResponse, EntryResponseMany]:
    """Imitate Collection.find for any given database for entry-resource endpoints

    Parameters:
        database: The OPTIMADE implementation to be queried.
        endpoint: The entry-listing endpoint, e.g., "structures".
        response_model: The expected OPTIMADE pydantic response model, e.g., optimade.models.StructureResponseMany.
        query_params: URL Query parameters to pass to the database.

    Results:
        Response as an OPTIMADE pydantic model, depending on whether it was a successful or unsuccessful response.

    """
    from optimade import __api_version__
    from pydantic import ValidationError

    url = f"{str(database.attributes.base_url).strip('/')}{BASE_URL_PREFIXES['major']}/{endpoint.strip('/')}?{query_params}"
    response = requests.get(url, timeout=60)

    try:
        response = response.json()
    except json.JSONDecodeError:
        return ErrorResponse(
            errors=[
                {
                    "detail": f"Could not JSONify response from {url}",
                    "id": "OPTIMADE_GATEWAY_DB_FIND_MANY_JSONDECODEERROR",
                }
            ],
            meta={
                "query": {"representation": f"/{endpoint.strip('/')}?{query_params}"},
                "api_version": __api_version__,
                "more_data_available": False,
            },
        )

    try:
        response = response_model(**response)
    except ValidationError:
        try:
            response = ErrorResponse(**response)
        except ValidationError as exc:
            return ErrorResponse(
                errors=[
                    {
                        "detail": f"Could not pass response from {url} as either a {response_model.__name__!r} or 'ErrorResponse'. ValidationError: {exc}",
                        "id": "OPTIMADE_GATEWAY_DB_FIND_MANY_VALIDATIONERROR",
                    }
                ],
                meta={
                    "query": {
                        "representation": f"/{endpoint.strip('/')}?{query_params}"
                    },
                    "api_version": __api_version__,
                    "more_data_available": False,
                },
            )

    return response
