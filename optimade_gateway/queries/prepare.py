"""Prepare OPTIMADE queries."""
from os import getenv
import re
from typing import TYPE_CHECKING
import urllib.parse
from warnings import warn

from optimade_gateway.warnings import OptimadeGatewayWarning

if TYPE_CHECKING or bool(getenv("MKDOCS_BUILD", "")):  # pragma: no cover
    # pylint: disable=unused-import,ungrouped-imports
    from typing import List, Mapping, Union

    from optimade_gateway.models.queries import OptimadeQueryParameters


async def prepare_query_filter(
    database_ids: "List[str]", filter_query: "Union[str, None]"
) -> "Mapping[str, Union[str, None]]":
    """Update the query parameter `filter` value to be database-specific

    This is needed due to the served change of `id` values.
    If someone searches for a gateway-changed `id`, it needs to be reverted to be
    database-specific.

    Parameters:
        database_ids: List of the databases to create updated filter values for.
            These values are part of the gateway-changed `id` values and are essential.
        filter_query: The submitted `filter` query parameter value. Can be `None` if not
            supplied.

    Returns:
        A mapping for database IDs to database-specific `filter` query parameter values.

    """
    updated_filter = {}.fromkeys(database_ids, filter_query)

    if not filter_query:
        return updated_filter

    for id_match in re.finditer(
        r'"(?P<id_value_l>[^\s]*)"[\s]*'
        r"(<|>|<=|>=|=|!=|CONTAINS|STARTS WITH|ENDS WITH|STARTS|ENDS)"
        r"[\s]*id|[^_]+id[\s]*"
        r'(<|>|<=|>=|=|!=|CONTAINS|STARTS WITH|ENDS WITH|STARTS|ENDS)[\s]*"'
        r'(?P<id_value_r>[^\s]*)"',
        f"={filter_query}" if filter_query else "",
    ):
        matched_id = id_match.group("id_value_l") or id_match.group("id_value_r")
        for database_id in database_ids:
            if matched_id.startswith(f"{database_id}/"):
                # Database found
                updated_filter[database_id] = updated_filter[database_id].replace(  # type: ignore[union-attr]  # pylint: disable=line-too-long
                    f"{database_id}/", "", 1
                )
                break
        else:
            warn(
                OptimadeGatewayWarning(
                    title="Non-Unique Entry ID",
                    detail=(
                        f"The passed entry ID <id={matched_id}> may be ambiguous! To get"
                        " a specific structures entry, one can prepend the ID with a "
                        "database ID belonging to the gateway, followed by a forward "
                        f"slash, e.g., '{database_ids[0]}/<local_database_ID>'. "
                        f"Available databases for this gateway: {database_ids}"
                    ),
                )
            )
    return updated_filter  # type: ignore[return-value]


async def get_query_params(
    query_parameters: "OptimadeQueryParameters",
    database_id: str,
    filter_mapping: "Mapping[str, Union[str, None]]",
) -> str:
    """Construct the parsed URL query parameters"""
    query_params = {
        param: value for param, value in query_parameters.dict().items() if value
    }
    if filter_mapping[database_id]:
        query_params.update({"filter": filter_mapping[database_id]})
    return urllib.parse.urlencode(query_params)
