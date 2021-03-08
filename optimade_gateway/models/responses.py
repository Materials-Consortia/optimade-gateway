from typing import Any, Dict, List, Union

from optimade.models import EntryResponseMany, EntryResponseOne
from pydantic import Field

from optimade_gateway.models.gateways import GatewayResource
from optimade_gateway.models.queries import GatewayQueryResource


class GatewaysResponse(EntryResponseMany):
    """Successful response for GET /gateways"""

    data: Union[List[GatewayResource], List[Dict[str, Any]]] = Field(
        ...,
        description="""List of unique OPTIMADE gateway resource objects.""",
        uniqueItems=True,
    )


class GatewaysResponseSingle(EntryResponseOne):
    """Successful response for POST /gateways and GET /gateways/{gateway_id}"""

    data: Union[GatewayResource, Dict[str, Any], None] = Field(
        ...,
        description="""A unique OPTIMADE gateway resource object.
The OPTIMADE gateway resource object has just been created or found according to the specific query parameter(s) or URL id.""",
    )


class GatewaysQueriesResponse(EntryResponseOne):
    """Successful response for GET /gateways/{gateway_ID}/queries"""

    data: Union[GatewayQueryResource, Dict[str, Any], None] = Field(
        ..., description="A unique OPTIMADE gateway query resource object."
    )
