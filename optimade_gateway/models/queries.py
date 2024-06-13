"""Pydantic models/schemas for the Queries resource."""

from __future__ import annotations

import inspect
import urllib.parse
import warnings
from copy import deepcopy
from datetime import timezone
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, Literal

from optimade.models import EntryResource as OptimadeEntryResource
from optimade.models import (
    EntryResourceAttributes,
    EntryResponseMany,
    ErrorResponse,
    OptimadeError,
    ReferenceResource,
    ReferenceResponseMany,
    ReferenceResponseOne,
    Response,
    ResponseMeta,
    StructureResource,
    StructureResponseMany,
    StructureResponseOne,
)
from optimade.models.utils import StrictField
from optimade.server.query_params import EntryListingQueryParams
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from pydantic.fields import FieldInfo
from starlette.datastructures import URL as StarletteURL

from optimade_gateway.common.config import CONFIG
from optimade_gateway.models.resources import EntryResourceCreate
from optimade_gateway.warnings import SortNotSupported

if TYPE_CHECKING:  # pragma: no cover
    from typing import TypedDict

    class QueryParameters(TypedDict):
        """Type definition for `QUERY_PARAMETERS`."""

        annotations: dict[str, FieldInfo]
        defaults: EntryListingQueryParams


class EndpointEntryType(Enum):
    """Entry endpoint resource types, mapping to their pydantic models from the
    `optimade` package."""

    REFERENCES = "references"
    STRUCTURES = "structures"

    def get_resource_model(self) -> ReferenceResource | StructureResource:
        """Get the matching pydantic model for a resource."""
        return {
            "references": ReferenceResource,
            "structures": StructureResource,
        }[self.value]

    def get_response_model(
        self, single: bool = False
    ) -> (
        ReferenceResponseMany
        | ReferenceResponseOne
        | StructureResponseMany
        | StructureResponseOne
    ):
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


QUERY_PARAMETERS: QueryParameters = {
    "annotations": {
        name: FieldInfo.from_annotation(parameter.annotation)
        for name, parameter in (
            inspect.signature(EntryListingQueryParams).parameters.items()
        )
    },
    "defaults": EntryListingQueryParams(),
}
"""Entry listing URL query parameters from the `optimade` package
([`EntryListingQueryParams`](https://www.optimade.org/optimade-python-tools/api_reference/server/query_params/#optimade.server.query_params.EntryListingQueryParams))."""


class OptimadeQueryParameters(BaseModel):
    """Common OPTIMADE entry listing endpoint query parameters."""

    filter: Annotated[
        str | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["filter"].description,
        ),
    ] = QUERY_PARAMETERS["defaults"].filter

    response_format: Annotated[
        str | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["response_format"].description,
        ),
    ] = QUERY_PARAMETERS["defaults"].response_format

    email_address: Annotated[
        EmailStr | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["email_address"].description,
        ),
    ] = QUERY_PARAMETERS["defaults"].email_address

    response_fields: Annotated[
        str | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["response_fields"].description,
            pattern=QUERY_PARAMETERS["annotations"]["response_fields"]
            .metadata[0]
            .pattern,
        ),
    ] = QUERY_PARAMETERS["defaults"].response_fields

    sort: Annotated[
        str | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["sort"].description,
            pattern=QUERY_PARAMETERS["annotations"]["sort"].metadata[0].pattern,
        ),
    ] = QUERY_PARAMETERS["defaults"].sort

    page_limit: Annotated[
        int | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["page_limit"].description,
            ge=QUERY_PARAMETERS["annotations"]["page_limit"].metadata[0].ge,
        ),
    ] = QUERY_PARAMETERS["defaults"].page_limit

    page_offset: Annotated[
        int | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["page_offset"].description,
            ge=QUERY_PARAMETERS["annotations"]["page_offset"].metadata[0].ge,
        ),
    ] = QUERY_PARAMETERS["defaults"].page_offset

    page_number: Annotated[
        int | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["page_number"].description,
        ),
    ] = QUERY_PARAMETERS["defaults"].page_number

    page_cursor: Annotated[
        int | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["page_cursor"].description,
            ge=QUERY_PARAMETERS["annotations"]["page_cursor"].metadata[0].ge,
        ),
    ] = QUERY_PARAMETERS["defaults"].page_cursor

    page_above: Annotated[
        int | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["page_above"].description,
        ),
    ] = QUERY_PARAMETERS["defaults"].page_above

    page_below: Annotated[
        int | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["page_below"].description,
        ),
    ] = QUERY_PARAMETERS["defaults"].page_below

    include: Annotated[
        str | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["include"].description,
        ),
    ] = QUERY_PARAMETERS["defaults"].include

    api_hint: Annotated[
        str | None,
        Field(
            description=QUERY_PARAMETERS["annotations"]["api_hint"].description,
            pattern=QUERY_PARAMETERS["annotations"]["api_hint"].metadata[0].pattern,
        ),
    ] = QUERY_PARAMETERS["defaults"].api_hint


class QueryState(Enum):
    """Enumeration of possible states for a Gateway Query.

    The states are enumerated here in the expected evolvement.
    """

    CREATED = "created"
    STARTED = "started"
    IN_PROGRESS = "in progress"
    FINISHED = "finished"


class EntryResource(OptimadeEntryResource):
    """Entry Resource ensuring datetimes are not naive."""

    @field_validator("attributes", mode="after")
    @classmethod
    def ensure_non_naive_datetime(
        cls, value: EntryResourceAttributes
    ) -> EntryResourceAttributes:
        """Set timezone to UTC if datetime is naive."""
        if value.last_modified and value.last_modified.tzinfo is None:
            value.last_modified = value.last_modified.replace(tzinfo=timezone.utc)
        return value


class GatewayQueryResponse(Response):
    """Response from a Gateway Query."""

    data: Annotated[
        dict[str, list[EntryResource] | list[dict[str, Any]]],
        StrictField(uniqueItems=True, description="Outputted Data."),
    ]

    meta: Annotated[
        ResponseMeta,
        StrictField(description="A meta object containing non-standard information."),
    ]

    errors: Annotated[
        list[OptimadeError] | None,
        StrictField(
            description=(
                "A list of OPTIMADE-specific JSON API error objects, where the field "
                "detail MUST be present."
            ),
            uniqueItems=True,
        ),
    ] = []  # noqa: RUF012

    included: Annotated[
        list[EntryResource] | list[dict[str, Any]] | None,
        StrictField(
            description="A list of unique included OPTIMADE entry resources.",
            uniqueItems=True,
            union_mode="left_to_right",
        ),
    ] = None

    @model_validator(mode="after")
    def either_data_meta_or_errors_must_be_set(self) -> GatewayQueryResponse:
        """Overwrite `either_data_meta_or_errors_must_be_set`.

        `errors` should be allowed to be present always for this special response.
        """
        return self


class QueryResourceAttributes(EntryResourceAttributes):
    """Attributes for an OPTIMADE gateway query."""

    gateway_id: Annotated[
        str,
        Field(
            description="The OPTIMADE gateway ID for this query.",
        ),
    ]

    query_parameters: Annotated[
        OptimadeQueryParameters,
        Field(
            description=(
                "OPTIMADE query parameters for entry listing endpoints used for this "
                "query."
            ),
            json_schema_extra={
                "type": "object",
            },
        ),
    ]

    state: Annotated[
        QueryState,
        Field(
            description="Current state of Gateway Query.",
            title="State",
            json_schema_extra={
                "type": "enum",
            },
        ),
    ] = QueryState.CREATED

    response: Annotated[
        GatewayQueryResponse | None,
        Field(
            description="Response from gateway query.",
        ),
    ] = None

    endpoint: Annotated[
        EndpointEntryType,
        Field(
            description="The entry endpoint queried, e.g., 'structures'.",
            title="Endpoint",
            json_schema_extra={
                "type": "enum",
            },
        ),
    ] = EndpointEntryType.STRUCTURES

    @field_validator("endpoint", mode="after")
    @classmethod
    def only_allow_structures(cls, value: EndpointEntryType) -> EndpointEntryType:
        """Temporarily only allow queries to "structures" endpoints."""
        if value != EndpointEntryType.STRUCTURES:
            raise NotImplementedError(
                'OPTIMADE Gateway temporarily only supports queries to "structures" '
                'endpoints, i.e.: endpoint="structures"'
            )
        return value


class QueryResource(EntryResource):
    """OPTIMADE query resource for a gateway"""

    type: Annotated[
        Literal["queries"],
        Field(
            description="The name of the type of an entry.",
        ),
    ] = "queries"

    attributes: QueryResourceAttributes

    async def response_as_optimade(
        self,
        url: None | (
            urllib.parse.ParseResult | urllib.parse.SplitResult | StarletteURL | str
        ) = None,
    ) -> EntryResponseMany | ErrorResponse:
        """Return `attributes.response` as a valid OPTIMADE entry listing response.

        Note, this method disregards the state of the query and will simply return the
        query results as they currently are (if there are any at all).

        Parameters:
            url: Optionally, update the `meta.query.representation` value with this.

        Returns:
            A valid OPTIMADE entry-listing response according to the
            [OPTIMADE specification](https://github.com/Materials-Consortia/OPTIMADE/blob/master/optimade.rst#entry-listing-endpoints)
            or an error response, if errors were returned or occurred during the query.

        """
        from optimade.server.routers.utils import (
            meta_values,
        )

        async def _update_id(
            entry_: EntryResource | dict[str, Any], database_provider_: str
        ) -> EntryResource | dict[str, Any]:
            """Internal utility function to prepend the entries' `id` with
            `provider/database/`.

            Parameters:
                entry_: The entry as a model or a dictionary.
                database_provider_: `provider/database` string.

            Returns:
                The entry with an updated `id` value.

            """
            if isinstance(entry_, dict):
                _entry = deepcopy(entry_)
                _entry["id"] = f"{database_provider_}/{entry_['id']}"
                return _entry

            return entry_.model_copy(
                update={"id": f"{database_provider_}/{entry_.id}"},
                deep=True,
            ).model_dump(exclude_unset=True, exclude_none=True)

        if not self.attributes.response:
            # The query has not yet been initiated
            return ErrorResponse(
                errors=[
                    {
                        "detail": (
                            "Can not return as a valid OPTIMADE response as the query "
                            "has not yet been initialized."
                        ),
                        "id": "OPTIMADE_GATEWAY_QUERY_NOT_INITIALIZED",
                    }
                ],
                meta=meta_values(
                    url=url or f"/queries/{self.id}?",
                    data_returned=0,
                    data_available=0,
                    more_data_available=False,
                    schema=CONFIG.schema_url,
                ),
            )

        meta_ = self.attributes.response.meta

        if url:
            meta_ = meta_.model_dump(exclude_unset=True)
            for repeated_key in (
                "query",
                "api_version",
                "time_stamp",
                "provider",
                "implementation",
            ):
                meta_.pop(repeated_key, None)
            meta_ = meta_values(url=url, **meta_)

        # Error response
        if self.attributes.response.errors:
            return ErrorResponse(
                errors=self.attributes.response.errors,
                meta=meta_,
            )

        # Data response
        results = []
        for database_provider, entries in self.attributes.response.data.items():
            results.extend(
                [await _update_id(entry, database_provider) for entry in entries]
            )

        return self.attributes.endpoint.get_response_model()(
            data=results,
            meta=meta_,
            links=self.attributes.response.links,
        )


class QueryCreate(EntryResourceCreate, QueryResourceAttributes):
    """Model for creating new Query resources in the MongoDB"""

    state: Annotated[
        QueryState | None,
        Field(
            title=QueryResourceAttributes.model_fields["state"].title,
            description=QueryResourceAttributes.model_fields["state"].description,
            json_schema_extra=QueryResourceAttributes.model_fields[
                "state"
            ].json_schema_extra,
        ),
    ] = None  # type: ignore[assignment]
    endpoint: Annotated[
        EndpointEntryType | None,
        Field(
            title=QueryResourceAttributes.model_fields["endpoint"].title,
            description=QueryResourceAttributes.model_fields["endpoint"].description,
            json_schema_extra=QueryResourceAttributes.model_fields[
                "endpoint"
            ].json_schema_extra,
        ),
    ] = None  # type: ignore[assignment]

    @field_validator("query_parameters", mode="after")
    @classmethod
    def sort_not_supported(
        cls, value: OptimadeQueryParameters
    ) -> OptimadeQueryParameters:
        """Warn and reset value if `sort` is supplied."""
        if value.sort:
            warnings.warn(SortNotSupported())
            value.sort = None
        return value
