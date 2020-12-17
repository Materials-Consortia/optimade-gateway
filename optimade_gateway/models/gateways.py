from optimade.models import EntryResource, SupportLevel
from pydantic import BaseModel, Field


class GatewayResourceAttributes(BaseModel):
    """Attributes for an OPTIMADE gateway"""


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
        pattern="^gateways$",
        support=SupportLevel.MUST,
        queryable=SupportLevel.MUST,
    )

    attributes: GatewayResourceAttributes
