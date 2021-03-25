from typing import Any, Dict, List, Union

from optimade.models import EntryResponseMany, EntryResponseOne
from pydantic import Field

from optimade_gateway.models.gateways import GatewayResource
from optimade_gateway.models.queries import QueryResource


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


class QueriesResponse(EntryResponseMany):
    """Successful response for GET /gateways/{gateway_ID}/queries"""

    data: Union[List[QueryResource], List[Dict[str, Any]]] = Field(
        ...,
        description="List of unique OPTIMADE gateway query resource objects.",
        uniqueItems=True,
    )


class QueriesResponseSingle(EntryResponseOne):
    """Successful response for POST /gateways/{gateway_ID}/queries and GET /gateways/{gateway_ID}/queries/{query_id}"""

    data: Union[QueryResource, Dict[str, Any], None] = Field(
        ...,
        description="""A unique OPTIMADE gateway query resource object.
The OPTIMADE gateway query resource object has just been created or found according to the specific query parameter(s) or URL id.""",
    )
