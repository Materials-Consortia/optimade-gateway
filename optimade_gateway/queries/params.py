"""URL query parameters."""
# pylint: disable=line-too-long,too-few-public-methods
from typing import Set

from fastapi import Query
from pydantic import AnyUrl


class SearchQueryParams:
    """URL query parameters for `GET /search`

    This is an extension of the
    [`EntryListingQueryParams`](https://www.optimade.org/optimade-python-tools/api_reference/server/query_params/#optimade.server.query_params.EntryListingQueryParams)
    class in `optimade´, which defines the standard entry listing endpoint query
    parameters.

    The extra query parameters are as follows.

    Attributes:
        database_ids (Set[str]): List of possible database IDs that are already known by
            the gateway. To be known they need to be registered with the gateway
            (currently not possible).

        optimade_urls (Set[AnyUrl]): A list of OPTIMADE base URLs. If a versioned base
            URL is supplied it will be used as is, as long as it represents a supported
            version. If an un-versioned base URL, standard version negotiation will be
            conducted to get the versioned base URL, which will be used as long as it
            represents a supported version.

            **Example**: `http://example.org/optimade/v1/search?optimade_urls="https://example.org/optimade_db/v1","https://optimade.herokuapp.com"`

        endpoint (str): The entry endpoint queried. According to the OPTIMADE
            specification, this is the same as the resource's type.

            **Example**: `structures`

        timeout (int): Timeout time (in seconds) to wait for a query to finish before
            redirecting (*after* starting the query). Note, if the query has not finished
            after the timeout time, a redirection will still be performed, but to a
            zero-results page, which can be refreshed to get the finished query (once it
            has finished).

        as_optimade (bool): Return the response as a standard OPTIMADE entry listing
            endpoint response. Otherwise, the response will be based on the
            [`QueriesResponseSingle`][optimade_gateway.models.responses.QueriesResponseSingle]
            model.

    """

    def __init__(
        self,
        *,
        database_ids: Set[str] = Query(
            set(),
            description=(
                "Unique list of possible database IDs that are already known by the "
                "gateway. To be known they need to be registered with the gateway "
                "(currently not possible)."
            ),
        ),
        optimade_urls: Set[AnyUrl] = Query(
            set(),
            description=(
                "A unique list of OPTIMADE base URLs. If a versioned base URL is "
                "supplied it will be used as is, as long as it represents a supported "
                "version. If an un-versioned base URL, standard version negotiation will"
                " be conducted to get the versioned base URL, which will be used as long"
                " as it represents a supported version."
            ),
        ),
        endpoint: str = Query(
            "structures",
            description=(
                "The entry endpoint queried. According to the OPTIMADE specification, "
                "this is the same as the resource's type."
            ),
        ),
        timeout: int = Query(
            15,
            description=(
                "Timeout time (in seconds) to wait for a query to finish before "
                "redirecting (*after* starting the query). Note, if the query has not "
                "finished after the timeout time, a redirection will still be performed,"
                " but to a zero-results page, which can be refreshed to get the finished"
                " query (once it has finished)."
            ),
        ),
        as_optimade: bool = Query(
            False,
            description=(
                "Return the response as a standard OPTIMADE entry listing endpoint "
                "response. Otherwise, the response will be based on the "
                "[`QueriesResponseSingle`][optimade_gateway.models.responses.QueriesResponseSingle]"
                " model."
            ),
        ),
    ) -> None:
        self.database_ids = database_ids
        self.optimade_urls = optimade_urls
        self.endpoint = endpoint
        self.timeout = timeout
        self.as_optimade = as_optimade
