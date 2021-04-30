"""Pydantic models/schemas for the Gateways resource"""
# pylint: disable=no-self-argument
from typing import List, Optional, Set
import warnings

from optimade.models import EntryResource, EntryResourceAttributes, LinksResource
from optimade.models.links import LinkType
from optimade.models.utils import OptimadeField, SupportLevel
from pydantic import Field, validator
from pydantic.class_validators import root_validator

from optimade_gateway.models.resources import EntryResourceCreate
from optimade_gateway.warnings import OptimadeGatewayWarning


class GatewayResourceAttributes(EntryResourceAttributes):
    """Attributes for an OPTIMADE gateway"""

    databases: List[LinksResource] = Field(
        ...,
        description="List of databases (OPTIMADE 'links') to be queried in this gateway.",
    )

    @validator("databases", each_item=True)
    def no_index_databases(cls, value: LinksResource) -> LinksResource:
        """Ensure databases are not of type `"root"` or `"providers"`

        !!! note
            Both `"external"` and `"child"` can still represent index meta-dbs,
            but `"root"` and `"providers"` can not represent "regular" dbs.
        """
        if value.attributes.link_type in (LinkType.ROOT, LinkType.PROVIDERS):
            raise ValueError(
                "Databases with 'root' or 'providers' link_type is not allowed for gateway "
                f"resources. Given database: {value}"
            )
        return value

    @validator("databases")
    def unique_base_urls(cls, value: List[LinksResource]) -> List[LinksResource]:
        """Remove extra entries with repeated base_urls"""
        db_base_urls = [_.attributes.base_url for _ in value]
        unique_base_urls = set(db_base_urls)
        if len(db_base_urls) == len(unique_base_urls):
            return value

        repeated_base_urls = [_ for _ in unique_base_urls if db_base_urls.count(_) > 1]
        new_databases = [
            _ for _ in value if _.attributes.base_url not in repeated_base_urls
        ]
        for base_url in repeated_base_urls:
            new_databases.append(
                [_ for _ in value if _.attributes.base_url == base_url][0]
            )
        warnings.warn(
            "Removed extra database entries for a gateway, because the base_url was repeated. The "
            "first found database entry was kept, while the others were removed. Original number "
            f"of databases: {len(value)}. New number of databases: {len(new_databases)} Repeated "
            "base_urls (number of repeats): {}".format(
                [
                    f"{base_url} ({db_base_urls.count(base_url)})"
                    for base_url in repeated_base_urls
                ]
            ),
            OptimadeGatewayWarning,
        )
        return new_databases


class GatewayResource(EntryResource):
    """OPTIMADE gateway

    A resource representing a dynamic collection of OPTIMADE databases.
    The gateway can be treated as any other OPTIMADE gateway, but the entries are an aggregate of
    multiple databases. The `id` of each aggregated resource will reflect the originating database.
    """

    id: str = OptimadeField(
        ...,
        description="""An entry's ID as defined in section Definition of Terms.

- **Type**: string.

- **Requirements/Conventions**:
    - **Support**: MUST be supported by all implementations, MUST NOT be `null`.
    - **Query**: MUST be a queryable property with support for all mandatory filter features.
    - **Response**: REQUIRED in the response.
    - **Gateway-specific**: MUST NOT contain a forward slash (`/`).

- **Examples**:
    - `"db_1234567"`
    - `"cod_2000000"`
    - `"cod_2000000@1234567"`
    - `"nomad_L1234567890"`
    - `"42"`""",
        support=SupportLevel.MUST,
        queryable=SupportLevel.MUST,
        regex=r"^[^/]*$",
    )
    type: str = Field(
        "gateways",
        const="gateways",
        description="The name of the type of an entry.",
        regex="^gateways$",
    )
    attributes: GatewayResourceAttributes


class GatewayCreate(EntryResourceCreate, GatewayResourceAttributes):
    """Model for creating new Gateway resources in the MongoDB"""

    id: Optional[str] = OptimadeField(
        None,
        description="""An entry's ID as defined in section Definition of Terms.

- **Type**: string.

- **Requirements/Conventions**:
    - **Support**: MUST be supported by all implementations, MUST NOT be `null`.
    - **Query**: MUST be a queryable property with support for all mandatory filter features.
    - **Response**: REQUIRED in the response.
    - **Gateway-specific**: MUST NOT contain a forward slash (`/`).

- **Examples**:
    - `"db_1234567"`
    - `"cod_2000000"`
    - `"cod_2000000@1234567"`
    - `"nomad_L1234567890"`
    - `"42"`""",
        support=SupportLevel.MUST,
        queryable=SupportLevel.MUST,
        regex=r"^[^/]*$",  # This regex is the special addition
    )

    database_ids: Optional[Set[str]] = Field(
        None, description="A unique list of database IDs for registered databases."
    )

    databases: Optional[List[LinksResource]]

    @root_validator
    def specify_databases(cls, values: dict) -> dict:
        """Either `database_ids` or `databases` must be non-empty"""
        if not any(values.get(field) for field in ("database_ids", "databases")):
            raise ValueError("Either 'database_ids' or 'databases' MUST be specified")
        return values
