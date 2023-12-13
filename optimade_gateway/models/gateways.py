"""Pydantic models/schemas for the Gateways resource."""
from __future__ import annotations

import warnings
from typing import Annotated, Literal

from optimade.models import EntryResource, EntryResourceAttributes, LinksResource
from optimade.models.links import LinkType
from optimade.models.utils import OptimadeField
from pydantic import Field, field_validator, model_validator

from optimade_gateway.models.resources import EntryResourceCreate
from optimade_gateway.warnings import OptimadeGatewayWarning


class GatewayResourceAttributes(EntryResourceAttributes):
    """Attributes for an OPTIMADE gateway"""

    databases: Annotated[
        list[LinksResource],
        Field(
            description=(
                "List of databases (OPTIMADE 'links') to be queried in this gateway."
            ),
        ),
    ]

    @field_validator("databases", mode="after")
    @classmethod
    def unique_base_urls(cls, value: list[LinksResource]) -> list[LinksResource]:
        """Remove extra entries with repeated base_urls.

        Also, ensure databases are not of type `"root"` or `"providers"`

        !!! note
            Both `"external"` and `"child"` can still represent index meta-dbs,
            but `"root"` and `"providers"` can not represent "regular" dbs.

        """
        for resource in value:
            if resource.attributes.link_type in (LinkType.ROOT, LinkType.PROVIDERS):
                raise ValueError(
                    "Databases with 'root' or 'providers' link_type is not allowed for "
                    f"gateway resources. Given database: {resource}"
                )

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
                next(_ for _ in value if _.attributes.base_url == base_url)
            )
        warnings.warn(
            "Removed extra database entries for a gateway, because the base_url was "
            "repeated. The first found database entry was kept, while the others were "
            f"removed. Original number of databases: {len(value)}. New number of "
            f"databases: {len(new_databases)} Repeated base_urls (number of repeats): "
            "{}".format(
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
    The gateway can be treated as any other OPTIMADE gateway, but the entries are an
    aggregate of multiple databases. The `id` of each aggregated resource will reflect
    the originating database.
    """

    id: Annotated[
        str,
        OptimadeField(
            description=EntryResource.model_fields["id"].description,
            support=EntryResource.model_fields["id"].json_schema_extra[
                "x-optimade-support"
            ],
            queryable=EntryResource.model_fields["id"].json_schema_extra[
                "x-optimade-queryable"
            ],
            pattern=r"^[^/]*$",
        ),
    ]

    type: Annotated[
        Literal["gateways"],
        Field(description="The name of the type of an entry."),
    ] = "gateways"

    attributes: Annotated[
        GatewayResourceAttributes,
        Field(description=EntryResource.model_fields["attributes"].description),
    ]


class GatewayCreate(EntryResourceCreate, GatewayResourceAttributes):
    """Model for creating new Gateway resources in the MongoDB"""

    id: Annotated[
        str | None,
        OptimadeField(
            description=EntryResource.model_fields["id"].description,
            support=EntryResource.model_fields["id"].json_schema_extra[
                "x-optimade-support"
            ],
            queryable=EntryResource.model_fields["id"].json_schema_extra[
                "x-optimade-queryable"
            ],
            pattern=r"^[^/]*$",  # This pattern is the special addition
        ),
    ] = None

    database_ids: Annotated[
        set[str] | None,
        Field(description="A unique list of database IDs for registered databases."),
    ] = None

    databases: Annotated[
        list[LinksResource] | None,
        Field(
            description=GatewayResourceAttributes.model_fields["databases"].description
        ),
    ] = None  # type: ignore[assignment]

    @model_validator(mode="after")
    def specify_databases(self) -> GatewayCreate:
        """Either `database_ids` or `databases` must be non-empty.
        Both together is also fine.
        """
        if not any(getattr(self, field) for field in ("database_ids", "databases")):
            raise ValueError("Either 'database_ids' or 'databases' MUST be specified")
        return self
