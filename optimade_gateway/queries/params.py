"""URL query parameters."""

from typing import Annotated

from fastapi import Query
from pydantic import AnyUrl


class SearchQueryParams:
    """URL query parameters for `GET /search`

    This is an extension of the
    [`EntryListingQueryParams`](https://www.optimade.org/optimade-python-tools/api_reference/server/query_params/#optimade.server.query_params.EntryListingQueryParams)
    class in `optimade`, which defines the standard entry listing endpoint query
    parameters.

    The extra query parameters are as follows.

    Attributes:
        database_ids (set[str]): List of possible database IDs that are already known by
            the gateway. To be known they need to be registered with the gateway
            (currently not possible).

        optimade_urls (set[AnyUrl]): A list of OPTIMADE base URLs. If a versioned base
            URL is supplied it will be used as is, as long as it represents a supported
            version. If an un-versioned base URL, standard version negotiation will be
            conducted to get the versioned base URL, which will be used as long as it
            represents a supported version.

            **Example**: `http://example.org/optimade/v1/search?optimade_urls="https://example.org/optimade_db/v1","https://optimade.herokuapp.com"`

        endpoint (str): The entry endpoint queried. According to the OPTIMADE
            specification, this is the same as the resource's type.

            **Example**: `structures`

        timeout (int): Timeout time (in seconds) to wait for a query to finish before
            redirecting (*after* starting the query). Note, if the query has not
            finished after the timeout time, a redirection will still be performed, but
            to a zero-results page, which can be refreshed to get the finished query
            (once it has finished).

        as_optimade (bool): Return the response as a standard OPTIMADE entry listing
            endpoint response. Otherwise, the response will be based on the
            [`QueriesResponseSingle`][optimade_gateway.models.responses.QueriesResponseSingle]
            model.

    """

    def __init__(
        self,
        *,
        database_ids: Annotated[
            set[str],
            Query(
                description=(
                    "Unique list of possible database IDs that are already known by "
                    "the gateway. To be known they need to be registered with the "
                    "gateway (currently not possible)."
                ),
            ),
        ] = set(),
        optimade_urls: Annotated[
            set[AnyUrl],
            Query(
                description=(
                    "A unique list of OPTIMADE base URLs. If a versioned base URL is "
                    "supplied it will be used as is, as long as it represents a "
                    "supported version. If an un-versioned base URL, standard version "
                    "negotiation will be conducted to get the versioned base URL, "
                    "which will be used as long as it represents a supported version."
                ),
            ),
        ] = set(),
        endpoint: Annotated[
            str,
            Query(
                description=(
                    "The entry endpoint queried. According to the OPTIMADE "
                    "specification, this is the same as the resource's type."
                ),
            ),
        ] = "structures",
        timeout: Annotated[
            int,
            Query(
                description=(
                    "Timeout time (in seconds) to wait for a query to finish before "
                    "redirecting (*after* starting the query). Note, if the query has "
                    "not finished after the timeout time, a redirection will still be "
                    "performed, but to a zero-results page, which can be refreshed to "
                    "get the finished query (once it has finished)."
                ),
            ),
        ] = 15,
        as_optimade: Annotated[
            bool,
            Query(
                description=(
                    "Return the response as a standard OPTIMADE entry listing endpoint "
                    "response. Otherwise, the response will be based on the "
                    "[`QueriesResponseSingle`][optimade_gateway.models.responses.QueriesResponseSingle]"
                    " model."
                ),
            ),
        ] = False,
    ) -> None:
        self.database_ids = database_ids
        self.optimade_urls = optimade_urls
        self.endpoint = endpoint
        self.timeout = timeout
        self.as_optimade = as_optimade
