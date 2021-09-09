# pylint: disable=line-too-long
"""Replicate of
[`LinksMapper`](https://www.optimade.org/optimade-python-tools/api_reference/server/mappers/links/#optimade.server.mappers.links.LinksMapper)
in OPTIMADE Python tools."""
from optimade.models.links import LinksResource

from optimade_gateway.mappers.base import BaseResourceMapper


class LinksMapper(BaseResourceMapper):
    """Replicate of
    [`LinksMapper`](https://www.optimade.org/optimade-python-tools/api_reference/server/mappers/links/#optimade.server.mappers.links.LinksMapper)
    in OPTIMADE Python tools.

    This is based on the OPTIMADE Gateway
    [`BaseResourceMapper`][optimade_gateway.mappers.base.BaseResourceMapper] however.
    """

    ENDPOINT = "links"
    ENTRY_RESOURCE_CLASS = LinksResource

    @classmethod
    def map_back(cls, doc: dict) -> dict:
        type_ = doc.get("type", None) or "links"
        newdoc = super().map_back(doc)
        newdoc["type"] = type_
        return newdoc
