from optimade.models.links import LinksResource

from optimade_gateway.mappers.base import BaseResourceMapper

__all__ = ("LinksMapper",)


class LinksMapper(BaseResourceMapper):

    ENDPOINT = "links"
    ENTRY_RESOURCE_CLASS = LinksResource

    @classmethod
    def map_back(cls, doc: dict) -> dict:
        type_ = doc.get("type", None) or "links"
        newdoc = super().map_back(doc)
        newdoc["type"] = type_
        return newdoc
