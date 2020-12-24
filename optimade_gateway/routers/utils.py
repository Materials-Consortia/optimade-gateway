from typing import List

from optimade.models import LinksResource
from optimade.server.entry_collections import MongoCollection

from optimade_gateway.exceptions import OptimadeGatewayError
from optimade_gateway.models import GatewayResource
from optimade_gateway.mappers import GatewaysMapper


def find_create_gateway(
    providers: List[LinksResource], collection: MongoCollection
) -> GatewayResource:
    """Find or create gateway

    Try to find gateway according to desired providers.
    If the gateway does not exist, create it.
    """
    create = False
    result = None
    filter = {"databases": {"$in": [_.dict() for _ in providers]}}

    if len(providers) != collection.collection.count_documents(filter):
        create = True
    else:
        for gateway in collection.collection.find(filter):
            if sorted([_["id"] for _ in gateway["databases"]]) == sorted(
                [_.id for _ in providers]
            ):
                result = GatewayResource(**GatewaysMapper.map_back(gateway))
                break
        else:
            create = True

    if not create:
        if result is None:
            raise OptimadeGatewayError(
                "Reasoned that a gateway should NOT be created, while still being unable to find an existing gateway."
            )
        return result

    # Create gateway
