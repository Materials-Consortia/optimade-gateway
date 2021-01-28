from typing import List

from optimade.models import EntryResource, EntryResourceAttributes, LinksResource
from pydantic import Field


class GatewayResourceAttributes(EntryResourceAttributes):
    """Attributes for an OPTIMADE gateway"""

    databases: List[LinksResource] = Field(
        ...,
        description="List of databases (OPTIMADE 'links') to be queried in this gateway.",
    )


class GatewayResource(EntryResource):
    """OPTIMADE gateway

    A resource representing a dynamic collection of OPTIMADE databases.
    The gateway can be treated as any other OPTIMADE gateway, but the entries are an aggregate of multiple databases.
    The `id` of each aggregated resource will reflect the originating database.
    """

    type: str = Field(
        "gateways",
        const="gateways",
        description="The name of the type of an entry.",
        regex="^gateways$",
    )
    attributes: GatewayResourceAttributes


class GatewayCreate(GatewayResourceAttributes):
    """Model for creating new Gateway resources in the MongoDB"""

    class Config:
        extra = "ignore"
