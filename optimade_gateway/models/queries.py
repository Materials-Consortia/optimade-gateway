"""Pydantic models/schemas for the Queries resource."""
# pylint: disable=line-too-long,too-few-public-methods,no-self-argument
from copy import deepcopy
from datetime import timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import urllib.parse
import warnings

from optimade.models import (
    EntryResource as OptimadeEntryResource,
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
from pydantic import BaseModel, EmailStr, Field, validator
from starlette.datastructures import URL as StarletteURL

from optimade_gateway.common.config import CONFIG
from optimade_gateway.models.resources import EntryResourceCreate
from optimade_gateway.warnings import SortNotSupported


class EndpointEntryType(Enum):
    """Entry endpoint resource types, mapping to their pydantic models from the
    `optimade` package."""

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


class EntryResource(OptimadeEntryResource):
    """Entry Resource ensuring datetimes are not naive."""

    @validator("attributes")
    def ensure_non_naive_datetime(
        cls, value: EntryResourceAttributes
    ) -> EntryResourceAttributes:
        """Set timezone to UTC if datetime is naive."""
        if value.last_modified and value.last_modified.tzinfo is None:
            value.last_modified = value.last_modified.replace(tzinfo=timezone.utc)
        return value


class GatewayQueryResponse(Response):
    """Response from a Gateway Query."""

    data: Dict[str, Union[List[EntryResource], List[Dict[str, Any]]]] = StrictField(
        ..., uniqueItems=True, description="Outputted Data."
    )
    meta: ResponseMeta = StrictField(
        ..., description="A meta object containing non-standard information."
    )
    errors: Optional[List[OptimadeError]] = StrictField(
        [],
        description=(
            "A list of OPTIMADE-specific JSON API error objects, where the field detail "
            "MUST be present."
        ),
        uniqueItems=True,
    )
    included: Optional[Union[List[EntryResource], List[Dict[str, Any]]]] = Field(
        None, uniqueItems=True
    )

    @classmethod
    def _remove_pre_root_validators(cls):
        """Remove `either_data_meta_or_errors_must_be_set` pre root_validator.
        This will always be available through `meta`, and more importantly,
        `errors` should be allowed to be present always for this special response.
        """
        pre_root_validators = []
        for validator_ in cls.__pre_root_validators__:
            if not str(validator_).startswith(
                "<function Response.either_data_meta_or_errors_must_be_set"
            ):
                pre_root_validators.append(validator_)
        cls.__pre_root_validators__ = pre_root_validators

    def __init__(self, **data: Any) -> None:
        """Remove root_validator `either_data_meta_or_errors_must_be_set`."""
        self._remove_pre_root_validators()
        super().__init__(**data)


class QueryResourceAttributes(EntryResourceAttributes):
    """Attributes for an OPTIMADE gateway query."""

    gateway_id: str = Field(
        ...,
        description="The OPTIMADE gateway ID for this query.",
    )
    query_parameters: OptimadeQueryParameters = Field(
        ...,
        description=(
            "OPTIMADE query parameters for entry listing endpoints used for this query."
        ),
        type="object",
    )
    state: QueryState = Field(
        QueryState.CREATED,
        description="Current state of Gateway Query.",
        title="State",
        type="enum",
    )
    response: Optional[GatewayQueryResponse] = Field(
        None,
        description="Response from gateway query.",
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
                'OPTIMADE Gateway temporarily only supports queries to "structures" '
                'endpoints, i.e.: endpoint="structures"'
            )
        return value


class QueryResource(EntryResource):
    """OPTIMADE query resource for a gateway"""

    type: str = Field(
        "queries",
        const=True,
        description="The name of the type of an entry.",
        regex="^queries$",
    )
    attributes: QueryResourceAttributes

    async def response_as_optimade(
        self,
        url: Optional[
            Union[urllib.parse.ParseResult, urllib.parse.SplitResult, StarletteURL, str]
        ] = None,
    ) -> Union[EntryResponseMany, ErrorResponse]:
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
        from optimade.server.routers.utils import (  # pylint: disable=import-outside-toplevel
            meta_values,
        )

        async def _update_id(
            entry_: Union[EntryResource, Dict[str, Any]], database_provider_: str
        ) -> Union[EntryResource, Dict[str, Any]]:
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
            else:
                _entry = entry_.copy(deep=True)
                _entry.id = f"{database_provider_}/{entry_.id}"  # type: ignore[union-attr]
            return _entry

        if not self.attributes.response:
            # The query has not yet been initiated
            return ErrorResponse(
                errors=[
                    {
                        "detail": (
                            "Can not return as a valid OPTIMADE response as the query has"
                            " not yet been initialized."
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
        print(meta_)
        if url:
            meta_ = meta_.dict(exclude_unset=True)
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

    state: Optional[QueryState]  # type: ignore[assignment]
    endpoint: Optional[EndpointEntryType]  # type: ignore[assignment]

    @validator("query_parameters")
    def sort_not_supported(
        cls, value: OptimadeQueryParameters
    ) -> OptimadeQueryParameters:
        """Warn and reset value if `sort` is supplied."""
        if value.sort:
            warnings.warn(SortNotSupported())
            value.sort = None
        return value
