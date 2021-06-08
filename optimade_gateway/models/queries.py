"""Pydantic models/schemas for the Queries resource"""
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import warnings

from optimade.models import (
    EntryResource,
    EntryResourceAttributes,
    EntryResponseMany,
    ErrorResponse,
    ReferenceResource,
    ReferenceResponseMany,
    ReferenceResponseOne,
    StructureResource,
    StructureResponseMany,
    StructureResponseOne,
)
from optimade.server.query_params import EntryListingQueryParams
from pydantic import BaseModel, EmailStr, Field, validator

from optimade_gateway.models.resources import EntryResourceCreate
from optimade_gateway.warnings import SortNotSupported


class EndpointEntryType(Enum):
    """Entry endpoint resource types, mapping to their pydantic models from the `optimade` package."""

    REFERENCES = "references"
    STRUCTURES = "structures"

    def get_resource_model(self) -> Union[ReferenceResource, StructureResource]:
        """Get the matching pydantic model for a resource."""
        return {
            "references": ReferenceResource,
            "structures": StructureResource,
        }[self.value]

    def get_response_model(
        self, single: bool = False
    ) -> Union[
        ReferenceResponseMany,
        ReferenceResponseOne,
        StructureResponseMany,
        StructureResponseOne,
    ]:
        """Get the matching pydantic model for a successful response."""
        if single:
            return {
                "references": ReferenceResponseOne,
                "structures": StructureResponseOne,
            }[self.value]
        return {
            "references": ReferenceResponseMany,
            "structures": StructureResponseMany,
        }[self.value]


QUERY_PARAMETERS = EntryListingQueryParams()
"""Entry listing URL query parameters from the `optimade` package
([`EntryListingQueryParams`](https://www.optimade.org/optimade-python-tools/api_reference/server/query_params/#optimade.server.query_params.EntryListingQueryParams))."""


class OptimadeQueryParameters(BaseModel):
    """Common OPTIMADE entry listing endpoint query parameters."""

    filter: Optional[str] = Field(
        QUERY_PARAMETERS.filter.default,
        description=QUERY_PARAMETERS.filter.description,
    )
    response_format: Optional[str] = Field(
        QUERY_PARAMETERS.response_format.default,
        description=QUERY_PARAMETERS.response_format.description,
    )
    email_address: Optional[EmailStr] = Field(
        QUERY_PARAMETERS.email_address.default,
        description=QUERY_PARAMETERS.email_address.description,
    )
    response_fields: Optional[str] = Field(
        QUERY_PARAMETERS.response_fields.default,
        description=QUERY_PARAMETERS.response_fields.description,
        regex=QUERY_PARAMETERS.response_fields.regex,
    )
    sort: Optional[str] = Field(
        QUERY_PARAMETERS.sort.default,
        description=QUERY_PARAMETERS.sort.description,
        regex=QUERY_PARAMETERS.sort.regex,
    )
    page_limit: Optional[int] = Field(
        QUERY_PARAMETERS.page_limit.default,
        description=QUERY_PARAMETERS.page_limit.description,
        ge=QUERY_PARAMETERS.page_limit.ge,
    )
    page_offset: Optional[int] = Field(
        QUERY_PARAMETERS.page_offset.default,
        description=QUERY_PARAMETERS.page_offset.description,
        ge=QUERY_PARAMETERS.page_offset.ge,
    )
    page_number: Optional[int] = Field(
        QUERY_PARAMETERS.page_number.default,
        description=QUERY_PARAMETERS.page_number.description,
        ge=QUERY_PARAMETERS.page_number.ge,
    )
    page_cursor: Optional[int] = Field(
        QUERY_PARAMETERS.page_cursor.default,
        description=QUERY_PARAMETERS.page_cursor.description,
        ge=QUERY_PARAMETERS.page_cursor.ge,
    )
    page_above: Optional[int] = Field(
        QUERY_PARAMETERS.page_above.default,
        description=QUERY_PARAMETERS.page_above.description,
        ge=QUERY_PARAMETERS.page_above.ge,
    )
    page_below: Optional[int] = Field(
        QUERY_PARAMETERS.page_below.default,
        description=QUERY_PARAMETERS.page_below.description,
        ge=QUERY_PARAMETERS.page_below.ge,
    )
    include: Optional[str] = Field(
        QUERY_PARAMETERS.include.default,
        description=QUERY_PARAMETERS.include.description,
    )
    # api_hint: Optional[str] = Field(
    #     QUERY_PARAMETERS.api_hint.default,
    #     description=QUERY_PARAMETERS.api_hint.description,
    #     regex=QUERY_PARAMETERS.api_hint.regex,
    # )


class QueryState(Enum):
    """Enumeration of possible states for a Gateway Query.

    The states are enumerated here in the expected evolvement.
    """

    CREATED = "created"
    STARTED = "started"
    IN_PROGRESS = "in progress"
    FINISHED = "finished"


class GatewayQueryResponse(EntryResponseMany):
    """Response from a Gateway Query."""

    data: Dict[str, Union[List[EntryResource], List[Dict[str, Any]]]] = Field(
        ...,
        uniqueItems=True,
    )


class QueryResourceAttributes(EntryResourceAttributes):
    """Attributes for an OPTIMADE gateway query."""

    gateway_id: str = Field(
        ...,
        description="The OPTIMADE gateway ID for this query.",
    )
    query_parameters: OptimadeQueryParameters = Field(
        ...,
        description="OPTIMADE query parameters for entry listing endpoints used for this query.",
        type="object",
    )
    state: QueryState = Field(
        QueryState.CREATED,
        description="Current state of Gateway Query.",
        title="State",
        type="enum",
    )
    response: Optional[Union[GatewayQueryResponse, ErrorResponse]] = Field(
        None,
        description="Response from gateway query.",
        type="object",
    )
    endpoint: EndpointEntryType = Field(
        EndpointEntryType.STRUCTURES,
        description="The entry endpoint queried, e.g., 'structures'.",
        title="Endpoint",
        type="enum",
    )

    @validator("endpoint")
    def only_allow_structures(cls, value: EndpointEntryType) -> EndpointEntryType:
        """Temporarily only allow queries to "structures" endpoints."""
        if value != EndpointEntryType.STRUCTURES:
            raise NotImplementedError(
                'OPTIMADE Gateway temporarily only supports queries to "structures" endpoints, '
                'i.e.: endpoint="structures"'
            )
        return value


class QueryResource(EntryResource):
    """OPTIMADE query resource for a gateway"""

    type: str = Field(
        "queries",
        const="queries",
        description="The name of the type of an entry.",
        regex="^queries$",
    )
    attributes: QueryResourceAttributes


class QueryCreate(EntryResourceCreate, QueryResourceAttributes):
    """Model for creating new Query resources in the MongoDB"""

    state: Optional[QueryState]
    endpoint: Optional[EndpointEntryType]

    @validator("query_parameters")
    def sort_not_supported(
        cls, value: OptimadeQueryParameters
    ) -> OptimadeQueryParameters:
        """Warn and reset value if `sort` is supplied."""
        if value.sort:
            warnings.warn(SortNotSupported())
            value.sort = None
        return value
