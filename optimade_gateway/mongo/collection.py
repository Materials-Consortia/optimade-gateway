"""MongoDB collection for entry-endpoint resources.

The [`AsyncMongoCollection`][optimade_gateway.mongo.collection.AsyncMongoCollection]
represents an asynchronous version of the equivalent MongoDB collection in `optimade`:
[`MongoCollection`](https://www.optimade.org/optimade-python-tools/api_reference/server/entry_collections/mongo/#optimade.server.entry_collections.mongo.MongoCollection).
"""
from __future__ import annotations

from datetime import datetime, timezone
from os import getenv
from typing import TYPE_CHECKING
from warnings import warn

from optimade.filterparser import LarkParser
from optimade.filtertransformers.mongo import MongoTransformer
from optimade.server.entry_collections.entry_collections import EntryCollection
from optimade.server.exceptions import BadRequest, NotFound
from optimade.server.query_params import SingleEntryQueryParams
from optimade.server.warnings import UnknownProviderProperty
from pymongo.collection import Collection as MongoCollection

from optimade_gateway.common.logger import LOGGER
from optimade_gateway.common.utils import clean_python_types
from optimade_gateway.warnings import OptimadeGatewayWarning

if TYPE_CHECKING or bool(getenv("MKDOCS_BUILD", "")):  # pragma: no cover
    from typing import Any

    from optimade.models import EntryResource
    from optimade.server.mappers.entries import BaseResourceMapper
    from optimade.server.query_params import EntryListingQueryParams

    from optimade_gateway.models import EntryResourceCreate


__all__ = ("AsyncMongoCollection",)


class AsyncMongoCollection(EntryCollection):
    """MongoDB Collection for use with `asyncio`

    The asynchronicity is implemented using [`motor`](https://motor.readthedocs.io) and
    [`asyncio`](https://asyncio.readthedocs.io/).
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
            resource_mapper: A resource mapper object that handles aliases and format
                changes between deserialization and response.

        """
        from optimade_gateway.mongo.database import (
            MONGO_DB,
        )

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
        return (
            f"<{self.__class__.__name__}: resource={self.resource_cls.__name__} "
            f"endpoint(mapper)={self.resource_mapper.ENDPOINT} "
            f"DB_collection={self.collection.name}>"
        )

    def __repr__(self) -> str:
        """Representation of instance."""
        return (
            f"{self.__class__.__name__}(name={self.collection.name!r}, "
            f"resource_cls={self.resource_cls!r}, "
            f"resource_mapper={self.resource_mapper!r})"
        )

    def __len__(self) -> int:
        warn(
            OptimadeGatewayWarning(
                detail=(
                    "Cannot calculate length of collection using `len()`. Use "
                    "`count()` instead."
                )
            )
        )
        return 0

    def insert(self, data: list[EntryResource]) -> None:
        raise NotImplementedError(
            "This method cannot be used with this class and is a remnant from the "
            "parent class. Use instead the asynchronous method `ainsert(data: "
            "List[EntryResource])`."
        )

    async def ainsert(self, data: list[EntryResource]) -> None:
        """Add the given entries to the underlying database.

        This is the asynchronous version of the parent class method named `insert()`.

        Arguments:
            data: The entry resource objects to add to the database.

        """
        await self.collection.insert_many(await clean_python_types(data))

    def count(self, **kwargs) -> int:
        raise NotImplementedError(
            "This method cannot be used with this class and is a remnant from the "
            "parent class. Use instead the asynchronous method `acount(params: "
            "Optional[Union[EntryListingQueryParams, SingleEntryQueryParams]], "
            "**kwargs)`."
        )

    async def acount(
        self,
        params: None | (EntryListingQueryParams | SingleEntryQueryParams) = None,
        **kwargs: Any,
    ) -> int:
        """Count documents in Collection.

        This is the asynchronous version of the parent class method named `count()`.

        Parameters:
            params: URL query parameters, either from a general entry endpoint or a
                single-entry endpoint.
            **kwargs: Query parameters as keyword arguments. Valid keys will be passed
                to the
                [`AsyncIOMotorCollection.count_documents`](https://motor.readthedocs.io/en/stable/api-asyncio/asyncio_motor_collection.html#motor.motor_asyncio.AsyncIOMotorCollection.count_documents)
                method.

        Returns:
            int: The number of entries matching the query specified by the keyword
                arguments.

        """
        if params is not None and kwargs:
            raise ValueError(
                "When 'params' is supplied, no other parameters can be supplied."
            )

        if params is not None:
            kwargs = await self.ahandle_query_params(params)

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

    def find(
        self, params: EntryListingQueryParams | SingleEntryQueryParams
    ) -> tuple[
        list[EntryResource] | EntryResource | None, int, bool, set[str], set[str]
    ]:
        """
        Fetches results and indicates if more data is available.

        Also gives the total number of data available in the absence of `page_limit`.
        See
        [`EntryListingQueryParams`](https://www.optimade.org/optimade-python-tools/api_reference/server/query_params/#optimade.server.query_params.EntryListingQueryParams)
        for more information.

        Parameters:
            params: Entry listing URL query params.

        Returns:
            A tuple of various relevant values:
            (`results`, `data_returned`, `more_data_available`, `exclude_fields`,
            `include_fields`).

        """
        raise NotImplementedError(
            "This method cannot be used with this class and is a remnant from the "
            "parent class. Use instead the asynchronous method `afind(params: "
            "Optional[Union[EntryListingQueryParams, SingleEntryQueryParams]], "
            "criteria: Optional[Dict[str, Any]])`."
        )

    async def afind(
        self,
        params: None | (EntryListingQueryParams | SingleEntryQueryParams) = None,
        criteria: dict[str, Any] | None = None,
    ) -> tuple[
        list[EntryResource] | EntryResource | None, int, bool, set[str], set[str]
    ]:
        """Perform the query on the underlying MongoDB Collection, handling projection
        and pagination of the output.

        This is the asynchronous version of the parent class method named `count()`.

        Either provide `params` or `criteria`. Not both, but at least one.

        Parameters:
            params: URL query parameters, either from a general entry endpoint or a
                single-entry endpoint.
            criteria: Already handled/parsed URL query parameters.

        Returns:
            A list of entry resource objects, how much data was returned for the query,
            whether more data is available with pagination, and fields (excluded,
            included).

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
            criteria = await self.ahandle_query_params(params)
        else:
            single_entry = isinstance(params, SingleEntryQueryParams)

        response_fields = criteria.pop("fields", self.all_fields)

        results, data_returned, more_data_available = await self._arun_db_query(
            criteria=criteria,
            single_entry=single_entry,
        )

        if single_entry:
            results = results[0] if results else None  # type: ignore[assignment]

            if data_returned > 1:
                raise NotFound(
                    detail=(
                        f"Instead of a single entry, {data_returned} entries were found"
                    ),
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
            warn(
                UnknownProviderProperty(
                    detail=(
                        "Unrecognised field(s) for this provider requested in "
                        f"`response_fields`: {bad_provider_fields}."
                    )
                )
            )

        if bad_optimade_fields:
            raise BadRequest(
                detail=(
                    "Unrecognised OPTIMADE field(s) in requested `response_fields`: "
                    f"{bad_optimade_fields}."
                )
            )

        if results:
            results = await self.resource_mapper.adeserialize(results)

        return (  # type: ignore[return-value]
            results,
            data_returned,
            more_data_available,
            self.all_fields - response_fields,
            include_fields,
        )

    def handle_query_params(
        self, params: EntryListingQueryParams | SingleEntryQueryParams
    ) -> dict[str, Any]:
        """Parse and interpret the backend-agnostic query parameter models into a
        dictionary that can be used by the specific backend.

        Note:
            Currently this method returns the pymongo interpretation of the parameters,
            which will need modification for modified for other backends.

        Parameters:
            params: The initialized query parameter model from the server.

        Raises:
            Forbidden: If too large of a page limit is provided.
            BadRequest: If an invalid request is made, e.g., with incorrect fields
                or response format.

        Returns:
            A dictionary representation of the query parameters.

        """
        raise NotImplementedError(
            "This method cannot be used with this class and is a remnant from the "
            "parent class. Use instead the asynchronous method "
            "`ahandle_query_params(params: Union[EntryListingQueryParams, "
            "SingleEntryQueryParams])`."
        )

    async def ahandle_query_params(
        self, params: EntryListingQueryParams | SingleEntryQueryParams
    ) -> dict[str, Any]:
        """Parse and interpret the backend-agnostic query parameter models into a
        dictionary that can be used by the specific backend.

        This is the asynchronous version of the parent class method named
        `handle_query_params()`.

        Note:
            Currently this method returns the pymongo interpretation of the parameters,
            which will need modification for modified for other backends.

        Parameters:
            params: The initialized query parameter model from the server.

        Raises:
            Forbidden: If too large of a page limit is provided.
            BadRequest: If an invalid request is made, e.g., with incorrect fields or
                response format.

        Returns:
            A dictionary representation of the query parameters.

        """
        return super().handle_query_params(params)

    def _run_db_query(
        self, criteria: dict[str, Any], single_entry: bool = False
    ) -> tuple[list[dict[str, Any]], int, bool]:
        raise NotImplementedError(
            "This method cannot be used with this class and is a remnant from the "
            "parent class. Use instead the asynchronous method "
            "`_arun_db_query(criteria: Dict[str, Any], single_entry: bool)`."
        )

    async def _arun_db_query(
        self, criteria: dict[str, Any], single_entry: bool = False
    ) -> tuple[list[dict[str, Any]], int, bool]:
        """Run the query on the backend and collect the results.

        This is the asynchronous version of the parent class method named `count()`.

        Arguments:
            criteria: A dictionary representation of the query parameters.
            single_entry: Whether or not the caller is expecting a single entry
                response.

        Returns:
            The list of entries from the database (without any re-mapping), the total
            number of entries matching the query and a boolean for whether or not there
            is more data available.

        """
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
            data_returned = await self.acount(params=None, **criteria_nolimit)
            more_data_available = len(results) < data_returned

        return results, data_returned, more_data_available

    @staticmethod
    def _check_aliases(aliases: tuple[tuple[str, str]]) -> None:
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

    async def get_one(self, **criteria: Any) -> EntryResource:
        """Get one resource based on criteria

        Warning:
            This is not to be used for creating a REST API response,
            but is rather a utility function to easily retrieve a single resource.

        Parameters:
            **criteria: Already handled/parsed URL query parameters.

        Returns:
            A single resource from the MongoDB (mapped to pydantic models).

        """
        criteria = criteria or {}

        return self.resource_cls(
            **self.resource_mapper.map_back(
                await self.collection.find_one(**self._valid_find_keys(**criteria))
            )
        )

    async def get_multiple(self, **criteria: Any) -> list[EntryResource]:
        """Get a list of resources based on criteria

        Warning:
            This is not to be used for creating a REST API response,
            but is rather a utility function to easily retrieve a list of resources.

        Parameters:
            **criteria: Already handled/parsed URL query parameters.

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
        resource.last_modified = datetime.now(timezone.utc)
        result = await self.collection.insert_one(
            await clean_python_types(resource.model_dump(exclude_unset=True))
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
    def _valid_find_keys(**kwargs: dict[str, Any]) -> dict[str, Any]:
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
