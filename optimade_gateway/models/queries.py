from typing import List, Optional

from optimade.models import EntryResource, EntryResourceAttributes
from optimade.server.query_params import EntryListingQueryParams
from pydantic import BaseModel, EmailStr, Field


query_parameters = EntryListingQueryParams()


class OptimadeQueryParameters(BaseModel):
    """Common OPTIMADE entry listing endpoint query parameters."""

    filter: Optional[str] = Field(
        query_parameters.filter.default,
        description=query_parameters.filter.description,
    )
    response_format: Optional[str] = Field(
        query_parameters.response_format.default,
        description=query_parameters.response_format.description,
    )
    email_address: Optional[EmailStr] = Field(
        query_parameters.email_address.default,
        description=query_parameters.email_address.description,
    )
    response_fields: Optional[str] = Field(
        query_parameters.response_fields.default,
        description=query_parameters.response_fields.description,
        regex=query_parameters.response_fields.regex,
    )
    sort: Optional[str] = Field(
        query_parameters.sort.default,
        description=query_parameters.sort.description,
        regex=query_parameters.sort.regex,
    )
    page_limit: Optional[int] = Field(
        query_parameters.page_limit.default,
        description=query_parameters.page_limit.description,
        ge=query_parameters.page_limit.ge,
    )
    page_offset: Optional[int] = Field(
        query_parameters.page_offset.default,
        description=query_parameters.page_offset.description,
        ge=query_parameters.page_offset.ge,
    )
    page_number: Optional[int] = Field(
        query_parameters.page_number.default,
        description=query_parameters.page_number.description,
        ge=query_parameters.page_number.ge,
    )
    page_cursor: Optional[int] = Field(
        query_parameters.page_cursor.default,
        description=query_parameters.page_cursor.description,
        ge=query_parameters.page_cursor.ge,
    )
    page_above: Optional[int] = Field(
        query_parameters.page_above.default,
        description=query_parameters.page_above.description,
        ge=query_parameters.page_above.ge,
    )
    page_below: Optional[int] = Field(
        query_parameters.page_below.default,
        description=query_parameters.page_below.description,
        ge=query_parameters.page_below.ge,
    )
    include: Optional[str] = Field(
        query_parameters.include.default,
        description=query_parameters.include.description,
    )
    # api_hint: Optional[str] = Field(
    #     query_parameters.api_hint.default,
    #     description=query_parameters.api_hint.description,
    #     regex=query_parameters.api_hint.regex,
    # )


class GatewayQueryResourceAttributes(EntryResourceAttributes):
    """Attributes for an OPTIMADE gateway query"""

    types: List[str] = Field(
        ...,
        description="""List of OPTIMADE entry resource types.
These are the OPTIMADE entry resource types that are queried for.""",
    )
    gateway: int = Field(
        ...,
        description="The OPTIMADE gateway ID for this query.",
    )
    query_parameters: OptimadeQueryParameters = Field(
        ...,
        description="OPTIMADE query parameters for entry listing endpoints used for this query.",
    )


class GatewayQueryResource(EntryResource):
    """OPTIMADE gateway query"""

    type: str = Field(
        "gateway_queries",
        const="gateway_queries",
        description="The name of the type of an entry.",
        regex="^gateway_queries$",
    )
    attributes: GatewayQueryResourceAttributes
