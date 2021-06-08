from optimade.models import LinksResource
from optimade.server.mappers.links import LinksMapper
from pydantic import AnyUrl  # pylint: disable=no-name-in-module

from optimade_gateway.common.config import CONFIG

__all__ = ("DatabasesMapper",)


class DatabasesMapper(LinksMapper):

    ENDPOINT = "databases"
    ENTRY_RESOURCE_CLASS = LinksResource

    @classmethod
    def map_back(cls, doc: dict) -> dict:
        from optimade.server.routers.utils import BASE_URL_PREFIXES

        if "_id" in doc:
            _id = str(doc.pop("_id"))
            if "id" not in doc:
                doc["id"] = _id

        doc["links"] = {
            "self": AnyUrl(
                url=f"{CONFIG.base_url.strip('/')}{BASE_URL_PREFIXES['major']}/{cls.ENDPOINT}/{doc['id']}",
                scheme=CONFIG.base_url.split("://")[0],
                host=CONFIG.base_url.split("://")[1].split("/")[0],
            )
        }

        # Ensure the type does not change to "databases"
        # The `LinksMapper.map_back()` method ensures the value for doc["type"] is kept.
        doc["type"] = "links"

        return super().map_back(doc)
