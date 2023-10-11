"""Process performed OPTIMADE queries."""
from os import getenv
from typing import TYPE_CHECKING
from warnings import warn

from optimade.models import ErrorResponse, Meta

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.logger import LOGGER
from optimade_gateway.common.utils import get_resource_attribute
from optimade_gateway.queries.utils import update_query
from optimade_gateway.warnings import OptimadeGatewayWarning

if TYPE_CHECKING or bool(getenv("MKDOCS_BUILD", "")):  # pragma: no cover
    from typing import Any, Dict, List, Union

    from optimade.models import EntryResource, EntryResponseMany, EntryResponseOne

    from optimade_gateway.models import GatewayResource, QueryResource


async def process_db_response(
    response: "Union[ErrorResponse, EntryResponseMany, EntryResponseOne]",
    database_id: str,
    query: "QueryResource",
    gateway: "GatewayResource",
) -> "Union[List[EntryResource], List[Dict[str, Any]], EntryResource, Dict[str, Any], None]":  # noqa: E501
    """Process an OPTIMADE database response.

    The passed `query` will be updated with the top-level `meta` information:
    `data_available`, `data_returned`, and `more_data_available`.

    Since, only either `data` or `errors` should ever be present, one or the other will
    be either an empty list or `None`.

    Parameters:
        response: The OPTIMADE database response to be processed.
        database_id: The database's `id` under which the returned resources or errors
            will be delivered.
        query: A resource representing the performed query.
        gateway: A resource representing the gateway that was queried.

    Returns:
        The response's `data`.

    """
    results = []
    errors = []

    LOGGER.debug("Starting to process database_id: %s", database_id)

    if isinstance(response, ErrorResponse):
        for error in response.errors:
            if isinstance(error.id, str) and error.id.startswith("OPTIMADE_GATEWAY"):
                warn(error.detail, OptimadeGatewayWarning)
            else:
                # The model `ErrorResponse` does not allow the objects in the top-level
                # `errors` list to be parsed as dictionaries - they must be a pydantic
                # model.
                meta_error = {}
                if error.meta:
                    meta_error = error.meta.dict()
                meta_error.update(
                    {
                        f"_{CONFIG.provider.prefix}_source_gateway": {
                            "id": gateway.id,
                            "type": gateway.type,
                            "links": {"self": gateway.links.self},
                        },
                        f"_{CONFIG.provider.prefix}_source_database": {
                            "id": database_id,
                            "type": "links",
                            "links": {
                                "self": (
                                    str(gateway.links.self).split(
                                        "gateways", maxsplit=1
                                    )[0]
                                    + f"databases/{database_id}"
                                )
                            },
                        },
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

    # This ensures an empty list under `response.data.{database_id}` is returned if the
    # case is simply that there are no results to return.
    if errors:
        extra_updates.update({"$addToSet": {"response.errors": {"$each": errors}}})
    await update_query(
        query,
        f"response.data.{database_id}",
        results,
        operator=None,
        **extra_updates,
    )

    return results
