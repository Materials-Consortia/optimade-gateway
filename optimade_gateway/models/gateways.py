"""Pydantic models/schemas for the Gateway resource"""
# pylint: disable=no-self-argument
from datetime import datetime
from typing import List, Optional
import warnings

from optimade.models import EntryResource, EntryResourceAttributes, LinksResource
from optimade.models.links import LinkType
from optimade.models.utils import OptimadeField, SupportLevel
from pydantic import Field, validator

from optimade_gateway.common.exceptions import OptimadeGatewayError


class GatewayResourceAttributes(EntryResourceAttributes):
    """Attributes for an OPTIMADE gateway"""

    last_modified: Optional[datetime] = OptimadeField(
        None,
        description="""Date and time representing when the entry was last modified.

- **Type**: timestamp.

- **Requirements/Conventions**:
    - **Support**: SHOULD be supported by all implementations, i.e., SHOULD NOT be `null`.
    - **Query**: MUST be a queryable property with support for all mandatory filter features.
    - **Response**: REQUIRED in the response unless the query parameter `response_fields` is present and does not include this property.

- **Example**:
    - As part of JSON response format: `"2007-04-05T14:30:20Z"` (i.e., encoded as an [RFC 3339 Internet Date/Time Format](https://tools.ietf.org/html/rfc3339#section-5.6) string.)""",
        support=SupportLevel.SHOULD,
        queryable=SupportLevel.MUST,
    )
    databases: List[LinksResource] = Field(
        ...,
        description="List of databases (OPTIMADE 'links') to be queried in this gateway.",
    )

    @validator("databases", each_item=True)
    def no_index_databases(cls, v):
        """Ensure databases are not of type "root" and "providers"

        NOTE: Both "external" and "child" can still represent index meta-dbs,
        but "root" and "providers" can not represent "regular" dbs.
        """
        if v.attributes.link_type in (LinkType.ROOT, LinkType.PROVIDERS):
            raise ValueError(
                "Databases with 'root' or 'providers' link_type is not allowed for gateway resources. "
                f"Given database: {v}"
            )
        return v

    @validator("databases")
    def unique_base_urls(cls, v):
        """Remove extra entries with repeated base_urls"""
        db_base_urls = [_.attributes.base_url for _ in v]
        unique_base_urls = set(db_base_urls)
        if len(db_base_urls) == len(unique_base_urls):
            return v

        if len(db_base_urls) < len(unique_base_urls):
            raise OptimadeGatewayError(
                f"The number of DBs with unique base_urls should never be less than the total number of DBs. List of DBs: {v}"
            )

        repeated_base_urls = [_ for _ in unique_base_urls if db_base_urls.count(_) > 1]
        new_databases = [
            _ for _ in v if _.attributes.base_url not in repeated_base_urls
        ]
        for base_url in repeated_base_urls:
            new_databases.append([_ for _ in v if _.attributes.base_url == base_url][0])
        warnings.warn(
            "Removed extra database entries for a gateway, because the base_url was repeated. "
            "The first found database entry was kept, while the others were removed. "
            f"Original number of databases: {len(v)}. New number of databases: {len(new_databases)}"
            "Repeated base_urls (number of repeats): {}".format(
                [
                    f"{base_url} ({db_base_urls.count(base_url)})"
                    for base_url in repeated_base_urls
                ]
            )
        )
        return new_databases


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
