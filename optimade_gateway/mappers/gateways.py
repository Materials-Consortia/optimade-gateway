from optimade.server.mappers.entries import BaseResourceMapper

__all__ = ("GatewaysMapper",)


class GatewaysMapper(BaseResourceMapper):

    ENDPOINT = "gateways"

    @classmethod
    def map_back(cls, doc: dict) -> dict:
        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))
        return super().map_back(doc)
