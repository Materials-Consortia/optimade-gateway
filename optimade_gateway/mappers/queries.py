"""Resource mapper for
[`QueryResource`][optimade_gateway.models.queries.QueryResource]."""

from __future__ import annotations

from optimade_gateway.mappers.base import BaseResourceMapper
from optimade_gateway.models import QueryResource


class QueryMapper(BaseResourceMapper):
    """[`QueryResource`][optimade_gateway.models.queries.QueryResource] mapper."""

    ENDPOINT = "queries"
    ENTRY_RESOURCE_CLASS = QueryResource
