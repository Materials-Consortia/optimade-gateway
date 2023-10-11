"""Pydantic models/schemas for the API responses."""
from typing import List, Optional

from optimade.models import EntryResponseMany, EntryResponseOne, LinksResource
from pydantic import Field

from optimade_gateway.models.gateways import GatewayResource
from optimade_gateway.models.queries import QueryResource


class DatabasesResponse(EntryResponseMany):
    """Successful response for `GET /databases`

    This model is essentially equal to
    [`LinksResponse`](https://www.optimade.org/optimade-python-tools/api_reference/models/responses/#optimade.models.responses.LinksResponse)
    with the exception of the `data´ field's description.
    """

    data: List[LinksResource] = Field(
        ...,
        description=(
            "List of unique OPTIMADE links resource objects.\nThese links resource "
            "objects represents OPTIMADE databases that can be used for queries in "
            "gateways."
        ),
        uniqueItems=True,
    )


class DatabasesResponseSingle(EntryResponseOne):
    """Successful response for `POST /databases` and `GET /databases/{database_id}`"""

    data: Optional[LinksResource] = Field(
        ...,
        description=(
            "A unique OPTIMADE links resource object.\nThe OPTIMADE links resource object"
            " has just been created or found according to the specific query parameter(s)"
            " or URL id.\nIt represents an OPTIMADE database that can be used for queries"
            " in gateways."
        ),
    )


class GatewaysResponse(EntryResponseMany):
    """Successful response for `GET /gateways`"""

    data: List[GatewayResource] = Field(
        ...,
        description="""List of unique OPTIMADE gateway resource objects.""",
        uniqueItems=True,
    )


class GatewaysResponseSingle(EntryResponseOne):
    """Successful response for `POST /gateways` and `GET /gateways/{gateway_id}`."""

    data: Optional[GatewayResource] = Field(
        ...,
        description=(
            "A unique OPTIMADE gateway resource object.\nThe OPTIMADE gateway resource "
            "object has just been created or found according to the specific query "
            "parameter(s) or URL id."
        ),
    )


class QueriesResponse(EntryResponseMany):
    """Successful response for `GET /gateways/{gateway_ID}/queries`."""

    data: List[QueryResource] = Field(
        ...,
        description="List of unique OPTIMADE gateway query resource objects.",
        uniqueItems=True,
    )


class QueriesResponseSingle(EntryResponseOne):
    """Successful response for `POST /gateways/{gateway_ID}/queries`
    and `GET /gateways/{gateway_ID}/queries/{query_id}`."""

    data: Optional[QueryResource] = Field(
        ...,
        description=(
            "A unique OPTIMADE gateway query resource object.\nThe OPTIMADE gateway query"
            " resource object has just been created or found according to the specific "
            "query parameter(s) or URL id."
        ),
    )
