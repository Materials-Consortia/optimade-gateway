import importlib
import re
from typing import Dict, List, Tuple, Union
import urllib.parse

from optimade.models.responses import EntryResponseMany, EntryResponseOne
from optimade.server.exceptions import BadRequest

from optimade_gateway.models.queries import OptimadeQueryParameters


async def prepare_query(
    database_ids: List[str],
    endpoint_model: Tuple[str, str],
    filter_query: Union[str, None],
) -> Tuple[Dict[str, Union[str, None]], Union[EntryResponseMany, EntryResponseOne]]:
    """Prepare a query by returning necessary variables."""
    return (
        await update_query_filter(database_ids, filter_query),
        await get_response_model(endpoint_model),
    )


async def update_query_filter(
    database_ids: List[str], filter_query: Union[str, None]
) -> Dict[str, Union[str, None]]:
    """Update the query parameter `filter` value to be database-specific

    This is needed due to the served change of `id` values.
    If someone searches for a gateway-changed `id`, it needs to be reverted to be
    database-specific.

    Parameters:
        database_ids: List of the databases to create updated filter values for.
            These values are part of the gateway-changed `id` values and are essential.
        filter_query: The submitted `filter` query parameter value. Can be `None` if not supplied.

    Returns:
        A mapping for database IDs to database-specific `filter` query parameter values.

    """
    updated_filter = {}.fromkeys(database_ids, filter_query)

    if not filter_query:
        return updated_filter

    for id_match in re.finditer(
        r'"(?P<id_value_l>[^\s]*)"[\s]*(<|>|<=|>=|=|!=|CONTAINS|STARTS WITH|ENDS WITH|STARTS|ENDS)'
        r'[\s]*id|[^_]+id[\s]*(<|>|<=|>=|=|!=|CONTAINS|STARTS WITH|ENDS WITH|STARTS|ENDS)[\s]*"'
        r'(?P<id_value_r>[^\s]*)"',
        f"={filter_query}" if filter_query else "",
    ):
        matched_id = id_match.group("id_value_l") or id_match.group("id_value_r")
        for database_id in database_ids:
            if matched_id.startswith(f"{database_id}/"):
                # Database found
                updated_filter[database_id] = updated_filter[database_id].replace(
                    f"{database_id}/", "", 1
                )
                break
            # TODO: Remove `id="value"` sections here for queries to databases that doesn't match the id value!
        else:
            raise BadRequest(
                detail=(
                    f"Structures entry <id={matched_id}> not found. To get a specific structures "
                    "entry one needs to prepend the ID with a database ID belonging to the gateway,"
                    f" e.g., '{database_ids[0]}/<local_database_ID>'. Available"
                    f"databases for this gateway: {database_ids}"
                )
            )
    return updated_filter


async def get_query_params(
    query_parameters: OptimadeQueryParameters,
    database_id: str,
    filter_mapping: Dict[str, Union[str, None]],
) -> str:
    """Construct the parsed URL query parameters"""
    query_params = {
        param: value for param, value in query_parameters.dict().items() if value
    }
    if filter_mapping[database_id]:
        query_params.update({"filter": filter_mapping[database_id]})
    return urllib.parse.urlencode(query_params)


async def get_response_model(
    endpoint_model: Tuple[str, str]
) -> Union[EntryResponseMany, EntryResponseOne]:
    """Import and return response model based on `endpoint_model`.

    Parameters:
        endpoint_model: The
            [`endpoint_model`][optimade_gateway.models.queries.QueryResourceAttributes.endpoint_model]
            from the
            [`QueryResource` attributes][optimade_gateway.models.queries.QueryResourceAttributes].

    Returns:
        The imported response model class, e.g., `StructureResponseMany`.

    """
    module, name = endpoint_model
    return getattr(importlib.import_module(module), name)
