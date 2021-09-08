from datetime import datetime
from typing import TYPE_CHECKING
import warnings

from optimade.filterparser import LarkParser
from optimade.filtertransformers.mongo import MongoTransformer
from optimade.models import EntryResource
from optimade.server.entry_collections.entry_collections import EntryCollection
from optimade.server.exceptions import BadRequest, NotFound
from optimade.server.mappers.entries import BaseResourceMapper
from optimade.server.query_params import EntryListingQueryParams, SingleEntryQueryParams
from optimade.server.warnings import UnknownProviderProperty
from pymongo.collection import Collection as MongoCollection

from optimade_gateway.common.logger import LOGGER
from optimade_gateway.common.utils import clean_python_types
from optimade_gateway.models import EntryResourceCreate
from optimade_gateway.warnings import OptimadeGatewayWarning

if TYPE_CHECKING:
    from typing import Any, Dict, List, Set, Tuple, Union


__all__ = ("AsyncMongoCollection",)


class AsyncMongoCollection(EntryCollection):
    """MongoDB Collection for use with `asyncio`

    The asynchronicity is implemented using [`motor`](https://motor.readthedocs.io) and [`asyncio`](https://asyncio.readthedocs.io/).
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
        """Standard printing result for an instance."""
        return f"<{self.__class__.__name__}: resource={self.resource_cls.__name__} endpoint(mapper)={self.resource_mapper.ENDPOINT} DB_collection={self.collection.name}>"

    def __repr__(self) -> str:
        """Representation of instance."""
        return f"{self.__class__.__name__}(name={self.collection.name!r}, resource_cls={self.resource_cls!r}, resource_mapper={self.resource_mapper!r})"

    def __len__(self) -> int:
        import warnings

        warnings.warn(
            OptimadeGatewayWarning(
                detail="Cannot calculate length of collection using `len()`. Use `count()` instead."
            )
        )
        return 0

    async def insert(self, data: "List[EntryResource]") -> None:
        await self.collection.insert_many(await clean_python_types(data))

    async def count(
        self,
        params: "Union[EntryListingQueryParams, SingleEntryQueryParams]" = None,
        **kwargs,
    ) -> int:
        """Count documents in Collection

        Parameters:
            params: URL query parameters, either from a general entry endpoint or a single-entry endpoint.
            kwargs (dict): Query parameters as keyword arguments. Valid keys will be passed
                to the
                [`AsyncIOMotorCollection.count_documents`](https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_collection.html#motor.motor_asyncio.AsyncIOMotorCollection.count_documents)
                method.

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

    async def find(
        self,
        params: "Union[EntryListingQueryParams, SingleEntryQueryParams]" = None,
        criteria: "Dict[str, Any]" = None,
    ) -> "Tuple[Union[List[EntryResource], EntryResource, None], int, bool, Set[str], Set[str]]":
        """Perform the query on the underlying MongoDB Collection, handling projection
        and pagination of the output.

        Either provide `params` or `criteria`. Not both, but at least one.

        Parameters:
            params: URL query parameters, either from a general entry endpoint or a single-entry endpoint.
            criteria: Already handled/parsed URL query parameters.

        Returns:
            A list of entry resource objects, how much data was returned for the query,
            whether more data is available with pagination, and fields (excluded, included).

        """
        if (params is None and criteria is None) or (
            params is not None and criteria is not None
        ):
            raise ValueError(
                "Exacly one of either `params` and `criteria` must be specified."
            )

        # Set single_entry to False, this is done since if criteria is defined,
        # this is an unknown factor - better to then get a list of results.
        single_entry = False
        if criteria is None:
            criteria = await self.handle_query_params(params)
        else:
            single_entry = isinstance(params, SingleEntryQueryParams)

        response_fields = criteria.pop("fields", self.all_fields)

        results, data_returned, more_data_available = await self._run_db_query(
            criteria=criteria,
            single_entry=single_entry,
        )

        if single_entry:
            results = results[0] if results else None  # type: ignore[assignment]

            if data_returned > 1:
                raise NotFound(
                    detail=f"Instead of a single entry, {data_returned} entries were found",
                )

        include_fields = (
            response_fields - self.resource_mapper.TOP_LEVEL_NON_ATTRIBUTES_FIELDS
        )
        bad_optimade_fields = set()
        bad_provider_fields = set()
        for field in include_fields:
            if field not in self.resource_mapper.ALL_ATTRIBUTES:
                if field.startswith("_"):
                    if any(
                        field.startswith(f"_{prefix}_")
                        for prefix in self.resource_mapper.SUPPORTED_PREFIXES
                    ):
                        bad_provider_fields.add(field)
                else:
                    bad_optimade_fields.add(field)

        if bad_provider_fields:
            warnings.warn(
                UnknownProviderProperty(
                    detail=f"Unrecognised field(s) for this provider requested in `response_fields`: {bad_provider_fields}."
                )
            )

        if bad_optimade_fields:
            raise BadRequest(
                detail=f"Unrecognised OPTIMADE field(s) in requested `response_fields`: {bad_optimade_fields}."
            )

        if results:
            results = await self.resource_mapper.deserialize(results)

        return (  # type: ignore[return-value]
            results,
            data_returned,
            more_data_available,
            self.all_fields - response_fields,
            include_fields,
        )

    async def handle_query_params(
        self, params: "Union[EntryListingQueryParams, SingleEntryQueryParams]"
    ) -> "Dict[str, Any]":
        return super().handle_query_params(params)

    async def _run_db_query(
        self, criteria: "Dict[str, Any]", single_entry: bool
    ) -> "Tuple[List[Dict[str, Any]], int, bool]":
        results = []
        async for document in self.collection.find(**self._valid_find_keys(**criteria)):
            if criteria.get("projection", {}).get("_id"):
                document["_id"] = str(document["_id"])
            results.append(document)

        if single_entry:
            data_returned = len(results)
            more_data_available = False
        else:
            criteria_nolimit = criteria.copy()
            criteria_nolimit.pop("limit", None)
            data_returned = await self.count(params=None, **criteria_nolimit)
            more_data_available = len(results) < data_returned

        return results, data_returned, more_data_available

    def _check_aliases(self, aliases: "Tuple[Tuple[str, str]]") -> None:
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

    async def get_one(self, **criteria: "Dict[str, Any]") -> EntryResource:
        """Get one resource based on criteria

        Warning:
            This is not to be used for creating a REST API response,
            but is rather a utility function to easily retrieve a single resource.

        Parameters:
            criteria: Already handled/parsed URL query parameters.

        Returns:
            A single resource from the MongoDB (mapped to pydantic models).

        """
        criteria = criteria or {}

        return self.resource_cls(
            **self.resource_mapper.map_back(
                await self.collection.find_one(**self._valid_find_keys(**criteria))
            )
        )

    async def get_multiple(self, **criteria: "Dict[str, Any]") -> "List[EntryResource]":
        """Get a list of resources based on criteria

        Warning:
            This is not to be used for creating a REST API response,
            but is rather a utility function to easily retrieve a list of resources.

        Parameters:
            criteria: Already handled/parsed URL query parameters.

        Returns:
            A list of resources from the MongoDB (mapped to pydantic models).

        """
        criteria = criteria or {}

        results = []
        async for document in self.collection.find(**self._valid_find_keys(**criteria)):
            results.append(self.resource_cls(**self.resource_mapper.map_back(document)))

        return results

    async def create_one(self, resource: EntryResourceCreate) -> EntryResource:
        """Create a new document in the MongoDB collection based on query parameters.

        Update the newly created document with an `"id"` field.
        The value will be the string representation of the `"_id"` field.
        This will only be done if `"id"` is not already present in `resource`.

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
        """Assert whether entry_id exists in the collection (value of `"id"`)

        Parameters:
            entry_id: The `"id"` value of the entry.

        """
        return bool(await self.collection.count_documents({"id": entry_id}))

    @staticmethod
    def _valid_find_keys(**kwargs: "Dict[str, Any]") -> "Dict[str, Any]":
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
