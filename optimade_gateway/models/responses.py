from typing import Any, Dict, List, Union

from optimade.models import EntryResponseMany, EntryResponseOne
from pydantic import Field

from optimade_gateway.models.gateways import GatewayResource
from optimade_gateway.models.queries import GatewayQueryResource


class GatewaysResponse(EntryResponseMany):
    """Successful response for GET /gateways"""

    data: Union[List[GatewayResource], List[Dict[str, Any]]] = Field(
        ...,
        description="""List of unique OPTIMADE gateway resource objects.
This may also be a list of a single OPTIMADE gateway resource object that has just been created or found according to the specific query parameter(s).""",
        uniqueItems=True,
    )


class GatewayStructuresResponse(EntryResponseOne):
    """Successful response for GET /gateways/{gateway_ID}/structures"""

    data: Union[GatewayQueryResource, Dict[str, Any], None] = Field(
        ..., description="A unique OPTIMADE gateway query resource object."
    )
