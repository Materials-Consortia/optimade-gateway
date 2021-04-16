from datetime import datetime
from typing import Any, Dict, List, Tuple, Union

from fastapi import HTTPException
from optimade.filterparser import LarkParser
from optimade.filtertransformers.mongo import MongoTransformer
from optimade.models import EntryResource
from optimade.server.entry_collections.entry_collections import EntryCollection
from optimade.server.mappers.entries import BaseResourceMapper
from optimade.server.query_params import EntryListingQueryParams, SingleEntryQueryParams
from pymongo.collection import Collection as MongoCollection

from optimade_gateway.common.logger import LOGGER
from optimade_gateway.common.utils import clean_python_types
from optimade_gateway.models import EntryResourceCreate


__all__ = ("AsyncMongoCollection",)


class AsyncMongoCollection(EntryCollection):
    """MongoDB Collection for use with asyncio

    The asynchronicity is implemented using motor and asyncio.
    """

    def __init__(
        self,
        name: str,
        resource_cls: EntryResource,
        resource_mapper: BaseResourceMapper,
    ):
        """Initialize the AsyncMongoCollection for the given parameters.

        Parameters:
            name: The name of the collection.
            resource_cls: The `EntryResource` model that is stored by the collection.
            resource_mapper: A resource mapper object that handles aliases and format changes between deserialization and response.

        """
        from optimade_gateway.mongo.database import MONGO_DB

        super().__init__(
            resource_cls=resource_cls,
            resource_mapper=resource_mapper,
            transformer=MongoTransformer(mapper=resource_mapper),
        )

        self.parser = LarkParser(version=(1, 0, 0), variant="default")
        self.collection: MongoCollection = MONGO_DB[name]

        # Check aliases do not clash with mongo operators
        self._check_aliases(self.resource_mapper.all_aliases())
        self._check_aliases(self.resource_mapper.all_length_aliases())

    def __str__(self) -> str:
        """Standard printing result for an instance"""
        return f"<{self.__class__.__name__}: resource={self.resource_cls.__name__} endpoint(mapper)={self.resource_mapper.ENDPOINT} DB_collection={self.collection.name}>"

    def __repr__(self) -> str:
        """Representation of instance"""
        return f"{self.__class__.__name__}(name={self.collection.name!r}, resource_cls={self.resource_cls!r}, resource_mapper={self.resource_mapper!r}"

    def __len__(self) -> int:
        """Length of collection"""
        import warnings

        warnings.warn(
            "Cannot calculate length of collection using `len()`. Use `count()` instead."
        )
        return 0

    def _check_aliases(self, aliases: Tuple[Tuple[str, str]]) -> None:
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

    @staticmethod
    def _valid_find_keys(**kwargs) -> Dict[str, Any]:
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

        if criteria.get("filter") is None:
            # Ensure documents are included in the result set
            criteria["filter"] = {}

        return criteria

    async def count(
        self,
        params: Union[EntryListingQueryParams, SingleEntryQueryParams] = None,
        **kwargs,
    ) -> int:
        """Count documents in Collection

        Parameters:
            params: URL query parameters, either from a general entry endpoint or a single-entry endpoint.
            kwargs (dict): Query parameters as keyword arguments. Valid keys will be passed
                to the `motor.motor_asyncio.AsyncIOMotorCollection.count_documents` method.

        Returns:
            int: The number of entries matching the query specified by the keyword arguments.

        """
        if params is not None and kwargs:
            raise ValueError(
                "When 'params' is supplied, no other parameters can be supplied."
            )

        if params is not None:
            kwargs = await self.handle_query_params(params)

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

        if criteria.get("filter") is None:
            criteria["filter"] = {}

        return await self.collection.count_documents(**criteria)

    async def get_one(self, **criteria: Dict[str, Any]) -> EntryResource:
        """Get one resource based on criteria

        NOTE: This is not to be used for creating a REST API response,
        but is rather a utility function to easily retrieve a single resource.

        Parameters:
            criteria: Already handled/parsed URL query parameters.

        Returns:
            A single resource from the MongoDB.

        """
        criteria = criteria or {}

        return self.resource_cls(
            **self.resource_mapper.map_back(
                await self.collection.find_one(**self._valid_find_keys(**criteria))
            )
        )

    async def find(
        self,
        params: Union[EntryListingQueryParams, SingleEntryQueryParams] = None,
        criteria: Dict[str, Any] = None,
    ) -> Tuple[Union[List[EntryResource], EntryResource], bool, set]:
        """Perform the query on the underlying MongoDB Collection, handling projection
        and pagination of the output.

        Either provide `params` or `criteria`. Not both, but at least one.

        Parameters:
            params: URL query parameters, either from a general entry endpoint or a single-entry endpoint.
            criteria: Already handled/parsed URL query parameters.

        Returns:
            A list of entry resource objects, whether more data is available with pagination, and fields.

        """
        if (params is None and criteria is None) or (
            params is not None and criteria is not None
        ):
            raise ValueError(
                "Exacly one of either `params` and `criteria` must be specified."
            )

        if criteria is None:
            criteria = await self.handle_query_params(params)

        fields = criteria.get("fields", self.all_fields)

        results = []
        async for doc in self.collection.find(**self._valid_find_keys(**criteria)):
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

    async def create_one(self, resource: EntryResourceCreate) -> EntryResource:
        """Create a new document in the MongoDB collection based on query parameters.

        Update the newly created document with an "id" field.
        The value will be the string representation of the "_id" field.
        This will only be done if `id` is not already present in `resource`.

        Parameters:
            resource: The resource to be created.

        Returns:
            The newly created document as a pydantic model entry resource.

        """
        resource.last_modified = datetime.utcnow()
        result = await self.collection.insert_one(
            await clean_python_types(resource.dict(exclude_unset=True))
        )
        LOGGER.debug(
            "Inserted resource %r in DB collection %s with ID %s",
            resource,
            self.collection.name,
            result.inserted_id,
        )

        if not resource.id:
            LOGGER.debug("Updating resource with an `id` field equal to str(id_).")
            await self.collection.update_one(
                {"_id": result.inserted_id}, {"$set": {"id": str(result.inserted_id)}}
            )

        return self.resource_cls(
            **self.resource_mapper.map_back(
                await self.collection.find_one({"_id": result.inserted_id})
            )
        )

    async def exists(self, entry_id: str) -> bool:
        """Assert whether entry_id exists in the collection (value of `id`)

        Parameters:
            entry_id: The `id` value of the entry.

        """
        return bool(await self.collection.count_documents({"id": entry_id}))

    async def insert(self, data: List[EntryResource]) -> None:
        """Add the given entries to the underlying database.

        Warning:
            No validation is performed on the incoming data.

        Parameters:
            data: The entry resource objects to add to the database.

        """
        await self.collection.insert_many(await clean_python_types(data))

    def _run_db_query(
        self, criteria: Dict[str, Any], single_entry: bool
    ) -> Tuple[List[Dict[str, Any]], int, bool]:
        """Abstract class - not implemented"""
        return super()._run_db_query(criteria, single_entry=single_entry)
