"""Process performed OPTIMADE queries"""
from typing import Any, Dict, List, Tuple, Union

from optimade.models import (
    EntryResource,
    EntryResponseMany,
    EntryResponseOne,
    ErrorResponse,
    Meta,
    OptimadeError,
)

from optimade_gateway.common.utils import get_resource_attribute
from optimade_gateway.models import GatewayResource, QueryResource
from optimade_gateway.queries.utils import update_query
from optimade_gateway.warnings import OptimadeGatewayWarning


async def process_db_response(
    response: Union[ErrorResponse, EntryResponseMany, EntryResponseOne],
    database_id: str,
    query: QueryResource,
    gateway: GatewayResource,
    use_query_resource: bool = True,
) -> Tuple[
    Union[
        List[EntryResource], List[Dict[str, Any]], EntryResource, Dict[str, Any], None
    ],
    List[OptimadeError],
    Dict[str, Union[bool, int]],
]:
    """Process an OPTIMADE database response.

    The passed `query` will be updated with the top-level `meta` information: `data_available`,
    `data_returned`, and `more_data_available`.

    Since, only either `data` or `errors` should ever be present, one or the other will be either
    an empty list or `None`.
    `meta` will only be a non-empty dictionary when not using a
    [`QueryResource`][optimade_gateway.models.queries.QueryResource], i.e., if `use_query_resource`
    is `False`.

    Parameters:
        response: The OPTIMADE database response to be processed.
        database_id: The database's `id` under which the returned resources or errors will be
            delivered.
        query: A resource representing the performed query.
        gateway: A resource representing the gateway that was queried.
        use_query_resource: Whether or not to update the passed
            [`QueryResource`][optimade_gateway.models.queries.QueryResource].

    Returns:
        A tuple of the response's `data`, `errors`, and `meta`.

    """
    results = []
    errors = []
    meta = {}

    if isinstance(response, ErrorResponse):
        for error in response.errors:
            if isinstance(error.id, str) and error.id.startswith("OPTIMADE_GATEWAY"):
                import warnings

                warnings.warn(error.detail, OptimadeGatewayWarning)
            else:
                # The model `ErrorResponse` does not allow the objects in the top-level `errors`
                # list to be parsed as dictionaries - they must be a pydantic model.
                meta_error = {}
                if error.meta:
                    meta_error = error.meta.dict()
                meta_error.update(
                    {
                        "optimade_gateway": {
                            "gateway": gateway,
                            "source_database_id": database_id,
                        }
                    }
                )
                error.meta = Meta(**meta_error)
                errors.append(error)
        data_returned = 0
        more_data_available = False
    else:
        results = response.data

        if isinstance(results, list):
            data_returned = response.meta.data_returned or len(results)
        else:
            data_returned = response.meta.data_returned or (0 if not results else 1)

        more_data_available = response.meta.more_data_available or False

    data_available = response.meta.data_available or 0

    if use_query_resource:
        extra_updates = {
            "$inc": {
                "response.meta.data_available": data_available,
                "response.meta.data_returned": data_returned,
            }
        }
        if not get_resource_attribute(
            query,
            "attributes.response.meta.more_data_available",
            False,
            disambiguate=False,  # Extremely minor speed-up
        ):
            # Keep it True, if set to True once.
            extra_updates.update(
                {"$set": {"response.meta.more_data_available": more_data_available}}
            )

        # This ensures an empty list under `response.data.{database_id}` is returned if the case is
        # simply that there is no results to return.
        # It also ensures that only `response.errors.{database_id}` is created if there are any
        # errors.
        await update_query(
            query,
            f"response.errors.{database_id}"
            if errors
            else f"response.data.{database_id}",
            errors or results,
            **extra_updates,
        )
    else:
        meta = {
            "data_returned": data_returned,
            "data_available": data_available,
            "more_data_available": more_data_available,
        }

    return results, errors, meta
