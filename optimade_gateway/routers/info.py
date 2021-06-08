"""/info/*

This file describes the router for:

    /info/{entry}

where, `entry` may be left out.
"""
from typing import Union

from fastapi import APIRouter, Request
from optimade import __api_version__
from optimade.models import (
    BaseInfoAttributes,
    BaseInfoResource,
    EntryInfoResponse,
    ErrorResponse,
    InfoResponse,
    LinksResource,
)
from optimade.server.routers.utils import get_base_url, meta_values

from optimade_gateway.models import GatewayResource, QueryResource

ROUTER = APIRouter(redirect_slashes=True)

ENTRY_INFO_SCHEMAS = {
    "databases": LinksResource.schema,
    "gateways": GatewayResource.schema,
    "queries": QueryResource.schema,
}


@ROUTER.get(
    "/info",
    response_model=Union[InfoResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Info"],
)
async def get_info(request: Request) -> InfoResponse:
    """`GET /info`

    An introspective endpoint for the gateway service.
    """
    return InfoResponse(
        data=BaseInfoResource(
            id=BaseInfoResource.schema()["properties"]["id"]["const"],
            type=BaseInfoResource.schema()["properties"]["type"]["const"],
            attributes=BaseInfoAttributes(
                api_version=__api_version__,
                available_api_versions=[
                    {
                        "url": f"{get_base_url(request.url)}/v{__api_version__.split('.')[0]}",
                        "version": __api_version__,
                    }
                ],
                formats=["json"],
                entry_types_by_format={"json": list(ENTRY_INFO_SCHEMAS.keys())},
                available_endpoints=sorted(
                    [
                        "docs",
                        "info",
                        "links",
                        "openapi.json",
                        "redoc",
                        "search",
                    ]
                    + list(ENTRY_INFO_SCHEMAS.keys())
                ),
                is_index=False,
            ),
        ),
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=1,
            more_data_available=False,
        ),
    )


@ROUTER.get(
    "/info/{entry}",
    response_model=Union[EntryInfoResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Info"],
)
async def get_entry_info(request: Request, entry: str) -> EntryInfoResponse:
    """`GET /info/{entry}`

    Get information about the gateway service's entry-listing endpoints.
    """
    from optimade.models import EntryInfoResource
    from optimade.server.exceptions import NotFound

    from optimade_gateway.routers.utils import aretrieve_queryable_properties

    valid_entry_info_endpoints = ENTRY_INFO_SCHEMAS.keys()
    if entry not in valid_entry_info_endpoints:
        raise NotFound(
            detail=(
                f"Entry info not found for {entry}, valid entry info endpoints are: "
                f"{', '.join(valid_entry_info_endpoints)}"
            ),
        )

    schema = ENTRY_INFO_SCHEMAS[entry]()
    queryable_properties = {"id", "type", "attributes"}
    properties = await aretrieve_queryable_properties(schema, queryable_properties)

    output_fields_by_format = {"json": list(properties.keys())}

    return EntryInfoResponse(
        data=EntryInfoResource(
            formats=list(output_fields_by_format.keys()),
            description=schema.get("description", "Entry Resources"),
            properties=properties,
            output_fields_by_format=output_fields_by_format,
        ),
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=1,
            more_data_available=False,
        ),
    )
