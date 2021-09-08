from typing import TYPE_CHECKING

from optimade.server.mappers.entries import (
    BaseResourceMapper as OptimadeBaseResourceMapper,
)

if TYPE_CHECKING:
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
    async def deserialize(
        cls, results: "Union[dict, Iterable[dict]]"
    ) -> "Union[List[EntryResource], EntryResource]":
        return super(BaseResourceMapper, cls).deserialize(results)
