from typing import Any

from pymongo.results import UpdateResult

from optimade_gateway.common.logger import LOGGER
from optimade_gateway.models import QueryResource


async def update_query(query: QueryResource, field: str, value: Any) -> None:
    """Update a query's `field` attribute with `value`.

    !!! note
        This can *only* update a field for a query's `attributes`, i.e., this function cannot
        update `id`, `type` or any other top-level resource field.

    Parameters:
        query: The query to be updated.
        field: The `attributes` field (key) to be set.
        value: The (possibly) new value for `field`.

    """
    from datetime import datetime

    from optimade_gateway.common.utils import clean_python_types
    from optimade_gateway.routers.queries import QUERIES_COLLECTION

    update_time = datetime.utcnow()

    # MongoDB
    result: UpdateResult = await QUERIES_COLLECTION.collection.update_one(
        filter={"id": {"$eq": query.id}},
        update={
            "$set": {
                "last_modified": update_time,
                field: await clean_python_types(value),
            }
        },
    )
    if result.matched_count != 1:
        LOGGER.error(
            "matched_count should have been exactly 1, it was: %s. Returned update_one result: %s",
            result.matched_count,
            result.raw_result,
        )

    # Pydantic model instance
    query.attributes.last_modified = update_time
    setattr(query.attributes, field, value)
