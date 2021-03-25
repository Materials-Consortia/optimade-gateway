from optimade_gateway.common.logger import LOGGER
from optimade_gateway.models import QueryResource, QueryState


async def update_query_state(query: QueryResource, state: QueryState) -> None:
    """Update a query's state in the MongoDB.

    Parameters:
        query: The query to be updated.
        state: The (possibly) new state to be set.

    """
    from datetime import datetime

    from optimade_gateway.routers.queries import QUERIES_COLLECTION

    update_time = datetime.utcnow()

    # MongoDB
    result = await QUERIES_COLLECTION.collection.update_one(
        filter={"id": {"$eq": query.id}},
        update={"$set": {"last_modified": update_time, "state": state.value}},
    )
    if result.matched_count != 1:
        LOGGER.error(
            "matched_count should have been exactly 1, it was: %s. Returned update_one result: %s",
            result.matched_count,
            result,
        )

    # Pydantic model instance
    query.attributes.last_modified = update_time
    query.attributes.state = state
