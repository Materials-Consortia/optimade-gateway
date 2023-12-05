"""/info/*

This file describes the router for:

    /info/{entry}

where, `entry` may be left out.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from optimade import __api_version__
from optimade.models import (
    BaseInfoAttributes,
    BaseInfoResource,
    EntryInfoResource,
    EntryInfoResponse,
    EntryResource,
    InfoResponse,
    LinksResource,
)
from optimade.server.exceptions import NotFound
from optimade.server.routers.utils import get_base_url, meta_values
from optimade.server.schemas import ERROR_RESPONSES

from optimade_gateway.common.config import CONFIG
from optimade_gateway.models import GatewayResource, QueryResource
from optimade_gateway.routers.utils import aretrieve_queryable_properties

ROUTER = APIRouter(redirect_slashes=True)

ENTRY_INFO_SCHEMAS: dict[str, type[EntryResource]] = {
    "databases": LinksResource,
    "gateways": GatewayResource,
    "queries": QueryResource,
}
"""This dictionary is used to define the `/info/<entry_type>` endpoints."""


@ROUTER.get(
    "/info",
    response_model=InfoResponse,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Info"],
    responses=ERROR_RESPONSES,
)
async def get_info(request: Request) -> InfoResponse:
    """`GET /info`

    An introspective endpoint for the gateway service.
    """
    return InfoResponse(
        data=BaseInfoResource(
            id=BaseInfoResource.model_fields["id"].default,
            type=BaseInfoResource.model_fields["type"].default,
            attributes=BaseInfoAttributes(
                api_version=__api_version__,
                available_api_versions=[
                    {
                        "url": (
                            f"{get_base_url(request.url)}"
                            f"/v{__api_version__.split('.', maxsplit=1)[0]}"
                        ),
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
                        *list(ENTRY_INFO_SCHEMAS.keys()),
                    ]
                ),
                is_index=False,
            ),
        ),
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=1,
            more_data_available=False,
            schema=CONFIG.schema_url,
        ),
    )


@ROUTER.get(
    "/info/{entry}",
    response_model=EntryInfoResponse,
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Info"],
    responses=ERROR_RESPONSES,
)
async def get_entry_info(request: Request, entry: str) -> EntryInfoResponse:
    """`GET /info/{entry}`

    Get information about the gateway service's entry-listing endpoints.
    """
    valid_entry_info_endpoints = ENTRY_INFO_SCHEMAS.keys()
    if entry not in valid_entry_info_endpoints:
        raise NotFound(
            detail=(
                f"Entry info not found for {entry}, valid entry info endpoints are: "
                f"{', '.join(valid_entry_info_endpoints)}"
            ),
        )

    schema = ENTRY_INFO_SCHEMAS[entry]
    queryable_properties = {"id", "type", "attributes"}
    properties = await aretrieve_queryable_properties(schema, queryable_properties, entry_type=entry)

    output_fields_by_format = {"json": list(properties)}

    return EntryInfoResponse(
        data=EntryInfoResource(
            formats=list(output_fields_by_format),
            description=getattr(schema, "__doc__", "Entry Resources"),
            properties=properties,
            output_fields_by_format=output_fields_by_format,
        ),
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=1,
            more_data_available=False,
            schema=CONFIG.schema_url,
        ),
    )
