from optimade.server.mappers.entries import BaseResourceMapper
from pydantic import AnyUrl  # pylint: disable=no-name-in-module

from optimade_gateway.common.config import CONFIG

__all__ = ("QueryMapper",)


class QueryMapper(BaseResourceMapper):

    ENDPOINT = "queries"

    @classmethod
    def map_back(cls, doc: dict) -> dict:
        from optimade.server.routers.utils import BASE_URL_PREFIXES

        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))

        doc["links"] = {
            "self": AnyUrl(
                url=f"{CONFIG.base_url.strip('/')}{BASE_URL_PREFIXES['major']}/{cls.ENDPOINT}/{doc['id']}",
                scheme=CONFIG.base_url.split("://")[0],
                host=CONFIG.base_url.split("://")[1].split("/")[0],
            )
        }
        return super().map_back(doc)
