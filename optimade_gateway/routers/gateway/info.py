from typing import Union

from fastapi import APIRouter, Request
from optimade import __api_version__
from optimade.models import (
    BaseInfoAttributes,
    BaseInfoResource,
    EntryInfoResponse,
    ErrorResponse,
    InfoResponse,
    StructureResource,
)
from optimade.server.routers.utils import get_base_url, meta_values

ROUTER = APIRouter(redirect_slashes=True)

ENTRY_INFO_SCHEMAS = {"structures": StructureResource.schema}


@ROUTER.get(
    "/gateways/{gateway_id}/info",
    response_model=Union[InfoResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Info"],
)
async def get_gateways_info(
    request: Request,
    gateway_id: str,
) -> InfoResponse:
    """GET /gateways/{gateway_id}/info

    Return a regular /info response for an OPTIMADE implementation,
    including extra information from all the gateway's databases.
    The general information will be a minimum set from the gateway's databases.
    """
    from optimade_gateway.common.config import CONFIG
    from optimade_gateway.routers.gateway.utils import get_valid_resource
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION

    gateway = await get_valid_resource(GATEWAYS_COLLECTION, gateway_id)

    return InfoResponse(
        data=BaseInfoResource(
            id=BaseInfoResource.schema()["properties"]["id"]["const"],
            type=BaseInfoResource.schema()["properties"]["type"]["const"],
            attributes=BaseInfoAttributes(
                api_version=__api_version__,
                available_api_versions=[
                    {
                        "url": f"{get_base_url(request.url)}/v{__api_version__.split('.')[0]}/gateways/{gateway_id}/v{__api_version__.split('.')[0]}",
                        "version": __api_version__,
                    }
                ],
                formats=["json"],
                entry_types_by_format={"json": list(ENTRY_INFO_SCHEMAS.keys())},
                available_endpoints=sorted(
                    ["info", "links"] + list(ENTRY_INFO_SCHEMAS.keys())
                ),
                is_index=False,
            ),
        ),
        meta=meta_values(
            url=request.url,
            data_returned=1,
            data_available=1,
            more_data_available=False,
            **{
                f"_{CONFIG.provider.prefix}_gateway": {
                    "databases": [
                        {"id": _.id, "type": _.type}
                        for _ in gateway.attributes.databases
                    ],
                }
            },
        ),
    )


@ROUTER.get(
    "/gateways/{gateway_id}/info/{entry}",
    response_model=Union[EntryInfoResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Info"],
)
async def get_gateways_entry_info(
    request: Request, gateway_id: str, entry: str
) -> EntryInfoResponse:
    """GET /gateways/{gateway_id}/info/{entry}

    Get information about the gateway {gateway_id}'s entry-listing endpoints.
    """
    from optimade.models import EntryInfoResource
    from optimade.server.exceptions import BadRequest

    from optimade_gateway.routers.gateway.utils import validate_resource
    from optimade_gateway.routers.gateways import GATEWAYS_COLLECTION
    from optimade_gateway.routers.utils import aretrieve_queryable_properties

    await validate_resource(GATEWAYS_COLLECTION, gateway_id)

    valid_entry_info_endpoints = ENTRY_INFO_SCHEMAS.keys()
    if entry not in valid_entry_info_endpoints:
        raise BadRequest(
            title="Not Found",
            status_code=404,
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


@ROUTER.get(
    "/gateways/{gateway_id}/{version}/info",
    response_model=Union[InfoResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Info"],
)
async def get_versioned_gateways_info(
    request: Request,
    gateway_id: str,
    version: str,
) -> InfoResponse:
    """GET /gateways/{gateway_id}/{version}/info

    Same as GET /gateways/{gateway_id}/info.
    """
    from optimade_gateway.routers.gateway.utils import validate_version

    await validate_version(version)
    return await get_gateways_info(request, gateway_id)


@ROUTER.get(
    "/gateways/{gateway_id}/{version}/info/{entry}",
    response_model=Union[EntryInfoResponse, ErrorResponse],
    response_model_exclude_defaults=False,
    response_model_exclude_none=False,
    response_model_exclude_unset=True,
    tags=["Info"],
)
async def get_versioned_gateways_entry_info(
    request: Request,
    gateway_id: str,
    version: str,
    entry: str,
) -> EntryInfoResponse:
    """GET /gateways/{gateway_id}/{version}/info/{entry}

    Same as GET /gateways/{gateway_id}/info/{entry}.
    """
    from optimade_gateway.routers.gateway.utils import validate_version

    await validate_version(version)
    return await get_gateways_entry_info(request, gateway_id, entry)
