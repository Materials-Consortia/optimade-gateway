"""Utility functions for the `queries` module."""

from __future__ import annotations

from datetime import datetime, timezone
from os import getenv
from typing import TYPE_CHECKING

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.logger import LOGGER
from optimade_gateway.common.utils import clean_python_types
from optimade_gateway.routers.utils import collection_factory

if TYPE_CHECKING or bool(getenv("MKDOCS_BUILD", "")):  # pragma: no cover
    from typing import Any

    from pydantic import BaseModel
    from pymongo.results import UpdateResult

    from optimade_gateway.models import QueryResource


async def update_query(
    query: QueryResource,
    field: str,
    value: Any,
    operator: str | None = None,
    **mongo_kwargs: Any,
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
        **mongo_kwargs: Further MongoDB update filters.

    """
    operator = operator or "$set"

    if operator and not operator.startswith("$"):
        operator = f"${operator}"

    update_time = datetime.now(timezone.utc)

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
    result: UpdateResult = await collection.collection.update_one(
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
        sub_field: BaseModel | dict[str, Any] = getattr(query.attributes, field_list[0])
        for field_part in field_list[1:-1]:
            if isinstance(sub_field, dict):
                sub_field = sub_field.get(field_part, {})
            else:
                sub_field = getattr(sub_field, field_part)
        if isinstance(sub_field, dict):
            sub_field[field_list[-1]] = value
        else:
            setattr(sub_field, field_list[-1], value)
    else:
        setattr(query.attributes, field, value)
