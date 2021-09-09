"""Utility functions for the `queries` module."""
# pylint: disable=import-outside-toplevel
from datetime import datetime
from os import getenv
from typing import TYPE_CHECKING

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.logger import LOGGER
from optimade_gateway.common.utils import clean_python_types
from optimade_gateway.routers.utils import collection_factory

if TYPE_CHECKING or bool(getenv("MKDOCS_BUILD", "")):
    # pylint: disable=unused-import,ungrouped-imports
    from typing import Any, Optional

    from pymongo.results import UpdateResult

    from optimade_gateway.models import QueryResource


async def update_query(  # pylint: disable=too-many-branches
    query: "QueryResource",
    field: str,
    value: "Any",
    operator: "Optional[str]" = None,
    **mongo_kwargs,
) -> None:
    """Update a query's `field` attribute with `value`.

    If `field` is a dot-separated value, then only the last field part may be a
    non-pre-existing field. Otherwise a `KeyError` or `AttributeError` will be raised.

    !!! note
        This can *only* update a field for a query's `attributes`, i.e., this function
        cannot update `id`, `type` or any other top-level resource field.

    !!! important
        `mongo_kwargs` will not be considered for updating the pydantic model instance.

    Parameters:
        query: The query to be updated.
        field: The `attributes` field (key) to be set.
            This can be a dot-separated key value to signify embedded fields.

            **Example**: `response.meta`.
        value: The (possibly) new value for `field`.
        operator: A MongoDB operator to be used for updating `field` with `value`.
        mongo_kwargs (dict): Further MongoDB update filters.

    """
    operator = operator or "$set"

    if operator and not operator.startswith("$"):
        operator = f"${operator}"

    update_time = datetime.utcnow()

    update_kwargs = {"$set": {"last_modified": update_time}}

    if mongo_kwargs:
        update_kwargs.update(mongo_kwargs)

    if operator and operator == "$set":
        update_kwargs["$set"].update({field: value})
    elif operator:
        if operator in update_kwargs:
            update_kwargs[operator].update({field: value})
        else:
            update_kwargs.update({operator: {field: value}})

    # MongoDB
    collection = await collection_factory(CONFIG.queries_collection)
    result: "UpdateResult" = await collection.collection.update_one(
        filter={"id": {"$eq": query.id}},
        update=await clean_python_types(update_kwargs),
    )
    if result.matched_count != 1:
        LOGGER.error(
            (
                "matched_count should have been exactly 1, it was: %s. "
                "Returned update_one result: %s"
            ),
            result.matched_count,
            result.raw_result,
        )

    # Pydantic model instance
    query.attributes.last_modified = update_time
    if "." in field:
        field_list = field.split(".")
        field = getattr(query.attributes, field_list[0])
        for field_part in field_list[1:-1]:
            if isinstance(field, dict):
                field = field.get(field_part)
            else:
                field = getattr(field, field_part)
        if isinstance(field, dict):
            field[field_list[-1]] = value
        else:
            setattr(field, field_list[-1], value)
    else:
        setattr(query.attributes, field, value)
