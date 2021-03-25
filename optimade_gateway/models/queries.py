from datetime import datetime
from enum import Enum
from typing import Optional, Tuple, Union

from optimade.models import (
    EntryResource,
    EntryResourceAttributes,
    EntryResponseMany,
    ErrorResponse,
)
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
    response: Optional[Union[EntryResponseMany, ErrorResponse]] = Field(
        None, description="Response from gateway query."
    )
    endpoint: str = Field(
        ..., description="The entry endpoint queried, e.g., 'structures'."
    )
    endpoint_model: Tuple[str, str] = Field(
        ...,
        description=(
            "The full importable path to the pydantic response model class (not an instance of "
            "the class). It should be a tuple of the Python module and the Class name."
        ),
    )

    @validator("endpoint")
    def remove_endpoints_slashes(cls, value: str) -> str:
        """Remove prep-/appended slashes (`/`)"""
        org_value = value
        value = value.strip()
        while value.startswith("/"):
            value = value[1:]
        while value.endswith("/"):
            value = value[:-1]
        if not value:
            raise ValueError(
                "endpoint must not be an empty string or be prep-/appended with slashes (`/`). "
                f"Original value: {org_value!r}. Final value (after removing prep-/appended "
                f"slashes): {value!r}"
            )

        # Temporarily only allow queries to "structures" endpoints.
        if value != "structures":
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


class QueryCreate(QueryResourceAttributes):
    """Model for creating new Gateway resources in the MongoDB"""

    last_modified: Optional[datetime]
    state: Optional[QueryState]
    endpoint: Optional[str]
    endpoint_model: Optional[Tuple[str, str]]

    class Config:
        extra = "ignore"
