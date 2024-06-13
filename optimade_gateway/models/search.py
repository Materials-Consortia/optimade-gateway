"""Pydantic models/schemas for the Search resource."""

from __future__ import annotations

import warnings
from typing import Annotated

from pydantic import AnyUrl, BaseModel, Field, field_validator, model_validator

from optimade_gateway.models.queries import OptimadeQueryParameters
from optimade_gateway.warnings import SortNotSupported


class Search(BaseModel):
    """A general coordinated OPTIMADE search

    !!! important
        Either `database_ids` or `optimade_urls` MUST be specified.

    """

    query_parameters: Annotated[
        OptimadeQueryParameters,
        Field(
            description=(
                "OPTIMADE query parameters for entry listing endpoints used for this "
                "query."
            ),
        ),
    ] = OptimadeQueryParameters()

    database_ids: Annotated[
        set[str],
        Field(
            description=(
                "A list of registered database IDs. Go to `/databases` to get all "
                "registered databases."
            ),
        ),
    ] = set()

    optimade_urls: Annotated[
        set[AnyUrl],
        Field(
            description=(
                "A list of OPTIMADE base URLs. If a versioned base URL is supplied it "
                "will be used as is, as long as it represents a supported version. If "
                "an un-versioned base URL, standard version negotiation will be "
                "conducted to get the versioned base URL, which will be used as long "
                "as it represents a supported version. Note, a single URL can be "
                "supplied as well, and it will automatically be wrapped in a list in "
                "the server logic."
            ),
        ),
    ] = set()

    endpoint: Annotated[
        str,
        Field(
            description=(
                "The entry endpoint queried. According to the OPTIMADE specification, "
                "this is the same as the resource's type."
            ),
        ),
    ] = "structures"

    @model_validator(mode="after")
    def either_ids_or_urls(self) -> Search:
        """Either `database_ids` or `optimade_urls` must be defined"""
        if not any(getattr(self, field) for field in ("database_ids", "optimade_urls")):
            raise ValueError(
                "Either 'database_ids' or 'optimade_urls' MUST be specified."
            )
        return self

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
