from datetime import datetime
from typing import Any, Dict, List, Tuple, Union

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorCollection
from optimade.filterparser import LarkParser
from optimade.filtertransformers.mongo import MongoTransformer
from optimade.models import EntryResource, EntryResourceAttributes
from optimade.server.entry_collections.entry_collections import EntryCollection
from optimade.server.mappers.entries import BaseResourceMapper
from optimade.server.query_params import EntryListingQueryParams, SingleEntryQueryParams

from optimade_gateway.common.logger import LOGGER


class AsyncMongoCollection(EntryCollection):
    """MongoDB Collection for use with asyncio

    The asynchronicity is implemented using motor and asyncio.
    """

    def __init__(
        self,
        collection: AsyncIOMotorCollection,
        resource_cls: EntryResource,
        resource_mapper: BaseResourceMapper,
        cached_properties: List[str] = None,
    ):
        """Initialize the AsyncMongoCollection for the given parameters.

        Parameters:
            collection: The backend-specific collection.
            resource_cls: The `EntryResource` model that is stored by the collection.
            resource_mapper: A resource mapper object that handles aliases and format changes between deserialization and response.
            cached_properties: List of the properties to be cached.

        """
        super().__init__(
            collection=collection,
            resource_cls=resource_cls,
            resource_mapper=resource_mapper,
            transformer=MongoTransformer(mapper=resource_mapper),
        )

        self.parser = LarkParser(version=(1, 0, 0), variant="default")

        # Check aliases do not clash with mongo operators
        self._check_aliases(self.resource_mapper.all_aliases())
        self._check_aliases(self.resource_mapper.all_length_aliases())

        # "Cache"
        self._caching: List[str] = (
            cached_properties
            if cached_properties is not None
            else [
                "data_available",
                "data_returned",
            ]
        )

        self._data_available: int = None
        self._data_returned: int = None
        self._latest_filter: dict = None

        LOGGER.debug("Caching properties %s for %s", self._caching, self)

        for cache_property in self._caching:
            if cache_property not in dir(self):
                import warnings

                warnings.warn(
                    f"A property ({cache_property}) passed for caching does not exist for {self}."
                )

    def _check_aliases(self, aliases: Tuple[Tuple(str, str)]) -> None:
        """Check that aliases do not clash with mongo keywords.

        Parameters:
            aliases: Tuple of tuple of aliases to be checked.

        Raises:
            RuntimeError: If any alias starts with the dollar (`$`) character.

        """
        if any(
            alias[0].startswith("$") or alias[1].startswith("$") for alias in aliases
        ):
            raise RuntimeError(f"Cannot define an alias starting with a '$': {aliases}")

    def _valid_find_keys(self, **kwargs) -> Dict[str, Any]:
        """Return valid MongoDB find() keys with values from kwargs

        Note, not including deprecated flags
        (see https://pymongo.readthedocs.io/en/3.11.0/api/pymongo/collection.html#pymongo.collection.Collection.find).
        """
        valid_method_keys = (
            "filter",
            "projection",
            "session",
            "skip",
            "limit",
            "no_cursor_timeout",
            "cursor_type",
            "sort",
            "allow_partial_results",
            "batch_size",
            "collation",
            "return_key",
            "show_record_id",
            "hint",
            "max_time_ms",
            "min",
            "max",
            "comment",
            "allow_disk_use",
        )
        criteria = {key: kwargs[key] for key in valid_method_keys if key in kwargs}

        if criteria["filter"] is None:
            # Ensure documents are included in the result set
            criteria["filter"] = {}

        return criteria

    async def count(self, **kwargs) -> int:
        """Count documents in Collection

        Parameters:
            kwargs (dict): Query parameters as keyword arguments. Valid keys will be passed
                to the `motor.motor_asyncio.AsyncIOMotorCollection.count_documents` method.

        Returns:
            int: The number of entries matching the query specified by the keyword arguments.

        """
        valid_method_keys = (
            "filter",
            "skip",
            "limit",
            "hint",
            "maxTimeMS",
            "collation",
            "session",
        )
        criteria = {key: kwargs[key] for key in valid_method_keys if key in kwargs}

        if criteria["filter"] is None:
            criteria["filter"] = {}

        return await self.collection.count_documents(**criteria)

    async def find(
        self,
        params: Union[EntryListingQueryParams, SingleEntryQueryParams] = None,
        criteria: Dict[str, Any] = None,
    ) -> Tuple[List[EntryResource], bool, set]:
        """Perform the query on the underlying MongoDB Collection, handling projection
        and pagination of the output.

        Either provide `params` or `criteria`. Not both, but at least one.

        Parameters:
            params: URL query parameters, either from a general entry endpoint or a single-entry endpoint.
            criteria: Already handled/parsed URL query parameters.

        Returns:
            A list of entry resource objects, the number of returned entries, whether more are available with pagination, fields.

        """
        if (params is None and criteria is None) or (
            params is not None and criteria is not None
        ):
            raise ValueError(
                "Exacly one of either `params` and `criteria` must be specified."
            )

        await self.set_data_available()

        if criteria is None:
            criteria = await self.handle_query_params(params)

        fields = criteria.get("fields", self.all_fields)

        await self.set_data_returned(**criteria)

        results = []
        async for doc in self.collection.find(**self._valid_find_keys(criteria)):
            if criteria.get("projection", {}).get("_id"):
                doc["_id"] = str(doc["_id"])
            results.append(self.resource_cls(**self.resource_mapper.map_back(doc)))

        if params is None or isinstance(params, EntryListingQueryParams):
            criteria_nolimit = criteria.copy()
            criteria_nolimit.pop("limit", None)
            more_data_available = len(results) < await self.count(**criteria_nolimit)
        else:
            # SingleEntryQueryParams, e.g., /structures/{entry_id}
            more_data_available = False
            if len(results) > 1:
                raise HTTPException(
                    status_code=404,
                    detail=f"Instead of a single entry, {len(results)} entries were found",
                )
            results = results[0] if results else None

        return results, more_data_available, self.all_fields - fields

    async def handle_query_params(
        self, params: Union[EntryListingQueryParams, SingleEntryQueryParams]
    ) -> dict:
        cursor_kwargs = super().handle_query_params(params)

        if getattr(params, "response_fields", False):
            fields = set(params.response_fields.split(","))
            fields |= self.resource_mapper.get_required_fields()
            cursor_kwargs["fields"] = fields
        else:
            # cursor_kwargs["fields"] is already set to self.all_fields
            pass

        return cursor_kwargs

    @property
    def data_available(self) -> int:
        """Get amount of data available under endpoint"""
        if self._data_available is None:
            raise ValueError("data_available MUST be set before it can be retrieved.")
        return self._data_available

    async def set_data_available(self) -> None:
        """Set _data_available if it has not yet been set"""
        if "data_available" in self._caching:
            if not self._data_available:
                self._data_available = await self.collection.estimated_document_count()
        else:
            self._data_available = await self.collection.estimated_document_count()

    @property
    def data_returned(self) -> int:
        """Get amount of data returned for query"""
        if self._data_returned is None:
            raise ValueError("data_returned MUST be set before it can be retrieved.")
        return self._data_returned

    async def set_data_returned(self, **criteria) -> None:
        """Set _data_returned if it has not yet been set or new filter does not equal
        latest filter.

        NB! Nested lists in filters are not accounted for.
        """
        if "data_returned" in self._caching:
            if self._data_returned is None or (
                self._latest_filter is not None
                and criteria.get("filters", {}) != self._latest_filter
            ):
                for key in ["limit", "offset"]:
                    if key in list(criteria.keys()):
                        del criteria[key]

                self._latest_filter = criteria.get("filters", {}).copy()
                LOGGER.debug(
                    "Setting data_returned using filter: %s", self._latest_filter
                )
                self._data_returned = await self.count(**criteria)
        else:
            self._data_returned = await self.count(**criteria)

    async def create_one(self, resource: EntryResourceAttributes) -> EntryResource:
        """Create a new document in the MongoDB collection based on query parameters.

        Parameters:
            resource: The resource to be created.

        Returns:
            The newly created document as a pydantic model entry resource.

        """
        resource.last_modified = datetime.now()
        result = await self.collection.insert_one(resource.dict())
        LOGGER.debug(
            "Inserted resource %s in DB collection %s with ID %s",
            resource,
            self.collection.name,
            result.inserted_id,
        )
        return await self.resource_cls(
            **self.resource_mapper.map_back(
                self.collection.find_one({"_id": result.inserted_id})
            )
        )
