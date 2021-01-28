from typing import List

from optimade.models import EntryResource, EntryResourceAttributes, LinksResource
from optimade.models.links import LinkType
from pydantic import Field, validator


class GatewayResourceAttributes(EntryResourceAttributes):
    """Attributes for an OPTIMADE gateway"""

    databases: List[LinksResource] = Field(
        ...,
        description="List of databases (OPTIMADE 'links') to be queried in this gateway.",
    )

    @validator("databases")
    def no_index_databases(cls, v):
        """Ensure databases are not of type "root" and "providers"

        NOTE: Both "external" and "child" can still represent index meta-dbs,
        but "root" and "providers" can not represent "regular" dbs.
        """
        for db in v:
            if db.attributes.link_type in (LinkType.ROOT, LinkType.PROVIDERS):
                raise ValueError(
                    "Databases with 'root' or 'providers' link_type is not allowed for gateway resources. "
                    f"Given database: {db}"
                )
        return v


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
