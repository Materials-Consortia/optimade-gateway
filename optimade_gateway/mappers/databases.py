"""Resource mapper for resources under `/databases`.

These resources are [`LinksResource`](https://www.optimade.org/optimade-python-tools/api_reference/models/links/#optimade.models.links.LinksResource)s.
"""
from optimade_gateway.mappers.links import LinksMapper


class DatabasesMapper(LinksMapper):
    """`/databases`-endpoint resources mapper."""

    ENDPOINT = "databases"
