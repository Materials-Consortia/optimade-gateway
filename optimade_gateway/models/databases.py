"""Pydantic models/schemas for the LinksResource used in /databases"""
# pylint: disable=no-self-argument,line-too-long
from typing import Optional, Union

from optimade.models import Link, LinksResourceAttributes
from optimade.models.links import LinkType
from optimade.models.utils import StrictField
from pydantic import AnyUrl, validator

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

    description: Optional[str]
    base_url: Union[AnyUrl, Link]
    homepage: Optional[Union[AnyUrl, Link]] = StrictField(
        None,
        description=(
            "JSON API links object, pointing to a homepage URL for this implementation."
        ),
    )
    link_type: Optional[LinkType] = StrictField(
        None,
        title="Link Type",
        description=(
            "The type of the linked relation.\nMUST be one of these values: 'child', "
            "'root', 'external', 'providers'."
        ),
    )

    @validator("link_type")
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
