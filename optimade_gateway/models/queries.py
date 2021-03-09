from datetime import datetime
from enum import Enum
from typing import List, Optional

from optimade.models import EntryResource, EntryResourceAttributes, EntryResponseMany
from optimade.server.query_params import EntryListingQueryParams
from pydantic import BaseModel, EmailStr, Field, validator


QUERY_PARAMETERS = EntryListingQueryParams()


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
    """Enumeration of possible states for a Gateway Query"""

    CREATED = "created"
    STARTED = "started"
    IN_PROGRESS = "in progress"
    FINISHED = "finished"


class QueryResourceAttributes(EntryResourceAttributes):
    """Attributes for an OPTIMADE gateway query"""

    types: List[str] = Field(
        ...,
        description="""List of OPTIMADE entry resource types.
These are the OPTIMADE entry resource types that are queried for.""",
    )
    gateway_id: str = Field(
        ...,
        description="The OPTIMADE gateway ID for this query.",
    )
    query_parameters: OptimadeQueryParameters = Field(
        ...,
        description="OPTIMADE query parameters for entry listing endpoints used for this query.",
    )
    state: QueryState = Field(
        QueryState.CREATED, description="Current state of Gateway Query.", title="State"
    )
    response: Optional[EntryResponseMany] = Field(
        None, description="Response from gateway query."
    )

    @validator("types")
    def only_allow_structures(cls, value: List[str]) -> List[str]:
        """Temporarily only allow "structures" as type."""
        if value != ["structures"]:
            raise NotImplementedError(
                'OPTIMADE Gateway temporarily only supports "structures" type, i.e.: types=["structures"]'
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


class QueryCreate(QueryResourceAttributes):
    """Model for creating new Gateway resources in the MongoDB"""

    last_modified: Optional[datetime]

    class Config:
        extra = "ignore"
