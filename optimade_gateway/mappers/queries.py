"""Resource mapper for
[`QueryResource`][optimade_gateway.models.queries.QueryResource]."""
from optimade_gateway.mappers.base import BaseResourceMapper
from optimade_gateway.models import QueryResource


class QueryMapper(BaseResourceMapper):
    """[`QueryResource`][optimade_gateway.models.queries.QueryResource] mapper."""

    ENDPOINT = "queries"
    ENTRY_RESOURCE_CLASS = QueryResource
