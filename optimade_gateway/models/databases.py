"""Pydantic models/schemas for the LinksResource used in /databases"""
from __future__ import annotations

from typing import Annotated

from optimade.models import LinksResourceAttributes
from optimade.models.links import JsonLinkType, LinkType
from optimade.models.utils import StrictField
from pydantic import field_validator

from optimade_gateway.models.resources import EntryResourceCreate


class DatabaseCreate(EntryResourceCreate, LinksResourceAttributes):
    """Model for creating new LinksResources representing `/databases` resources in the
    MongoDB.

    Required fields:

    - `name`
    - `base_url`

    Original required fields for a
    [`LinksResourceAttributes`](https://www.optimade.org/optimade-python-tools/api_reference/models/links/#optimade.models.links.LinksResourceAttributes)
    model:

    - `name`
    - `description`
    - `link_type`

    """

    description: Annotated[
        str | None,
        StrictField(
            description=LinksResourceAttributes.model_fields["description"].description
        ),
    ] = None

    base_url: Annotated[
        JsonLinkType,
        StrictField(
            description=LinksResourceAttributes.model_fields["base_url"].description
        ),
    ]

    homepage: Annotated[
        JsonLinkType | None,
        StrictField(
            description=LinksResourceAttributes.model_fields["homepage"].description,
        ),
    ] = None

    link_type: Annotated[
        LinkType | None,
        StrictField(
            title=LinksResourceAttributes.model_fields["link_type"].title,
            description=LinksResourceAttributes.model_fields["link_type"].description,
        ),
    ] = None

    @field_validator("link_type", mode="after")
    @classmethod
    def ensure_database_link_type(cls, value: LinkType) -> LinkType:
        """Ensure databases are not index meta-database-only types

        I.e., ensure they're not of type `"root"` or `"providers"`.

        !!! note
            Both `"external"` and `"child"` can still represent index meta-dbs,
            but `"root"` and `"providers"` can not represent "regular" dbs.

        """
        if value in (LinkType.ROOT, LinkType.PROVIDERS):
            raise ValueError(
                "Databases with 'root' or 'providers' link_type is not allowed for "
                f"gateway-usable database resources. Given link_type: {value}"
            )
        return value
