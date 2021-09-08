from pydantic import AnyUrl

from optimade_gateway.common.config import CONFIG

from optimade_gateway.mappers.links import LinksMapper

__all__ = ("DatabasesMapper",)


class DatabasesMapper(LinksMapper):

    ENDPOINT = "databases"

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
        return super().map_back(doc)
