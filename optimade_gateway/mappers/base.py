"""Base resource mapper.

Based on the
[`BaseResourceMapper`](https://www.optimade.org/optimade-python-tools/api_reference/server/mappers/entries/#optimade.server.mappers.entries.BaseResourceMapper)
in OPTIMADE Python tools.
"""
from os import getenv
from typing import TYPE_CHECKING

from optimade.server.mappers.entries import (
    BaseResourceMapper as OptimadeBaseResourceMapper,
)
from pydantic import AnyUrl

from optimade_gateway.common.config import CONFIG

if TYPE_CHECKING or bool(getenv("MKDOCS_BUILD", "")):  # pragma: no cover
    from typing import Iterable, List, Union

    from optimade.models import EntryResource


class BaseResourceMapper(OptimadeBaseResourceMapper):
    """
    Generic Resource Mapper that defines and performs the mapping
    between objects in the database and the resource objects defined by
    the specification.

    Note:
        This is a "wrapped" sub-class to make certain methods asynchronous.

    Attributes:
        ALIASES: a tuple of aliases between
            OPTIMADE field names and the field names in the database ,
            e.g. `(("elements", "custom_elements_field"))`.
        LENGTH_ALIASES: a tuple of aliases between
            a field name and another field that defines its length, to be used
            when querying, e.g. `(("elements", "nelements"))`.
            e.g. `(("elements", "custom_elements_field"))`.
        ENTRY_RESOURCE_CLASS: The entry type that this mapper corresponds to.
        PROVIDER_FIELDS: a tuple of extra field names that this
            mapper should support when querying with the database prefix.
        TOP_LEVEL_NON_ATTRIBUTES_FIELDS: the set of top-level
            field names common to all endpoints.
        SUPPORTED_PREFIXES: The set of prefixes registered by this mapper.
        ALL_ATTRIBUTES: The set of attributes defined across the entry
            resource class and the server configuration.
        ENTRY_RESOURCE_ATTRIBUTES: A dictionary of attributes and their definitions
            defined by the schema of the entry resource class.
        ENDPOINT: The expected endpoint name for this resource, as defined by
            the `type` in the schema of the entry resource class.

    """

    @classmethod
    async def adeserialize(
        cls, results: "Union[dict, Iterable[dict]]"
    ) -> "Union[List[EntryResource], EntryResource]":
        """Asynchronous version of the `deserialize()` class method.

        Parameters:
            results: A list of or a single dictionary, representing an entry-endpoint
                resource.

        Returns:
            The deserialized list of or single pydantic resource model for the input
            `results`.

        """
        return super(BaseResourceMapper, cls).deserialize(results)

    @classmethod
    def map_back(cls, doc: dict) -> dict:
        from optimade.server.routers.utils import BASE_URL_PREFIXES

        if "_id" in doc:
            _id = str(doc.pop("_id"))
            if "id" not in doc:
                doc["id"] = _id

        doc["links"] = {
            "self": AnyUrl(
                url=(
                    f"{CONFIG.base_url.strip('/')}{BASE_URL_PREFIXES['major']}"
                    f"/{cls.ENDPOINT}/{doc['id']}"
                ),
                scheme=CONFIG.base_url.split("://", maxsplit=1)[0],
                host=CONFIG.base_url.split("://", maxsplit=2)[1].split("/")[0],
            )
        }
        return super().map_back(doc)
