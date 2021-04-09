from typing import List

from fastapi import Query
from pydantic import AnyUrl


class SearchQueryParams:
    """URL query parameters for GET /search

    This is an extension of the `EntryListingQueryParams` class in `optimade´, which defines the
    standard entry listing endpoint query parameters.

    The extra query parameters are as follows.

    Attributes:
        databases (List[str]): List of possible database IDs that are already known by the gateway.
            To be known they need to be registered with the gateway (currently not possible).

        optimade_urls (List[AnyUrl]): A list of OPTIMADE base URLs. If a versioned
            base URL is supplied it will be used as is, as long as it represents a supported
            version. If an un-versioned base URL, standard version negotiation will be conducted to
            get the versioned base URL, which will be used as long as it represents a supported
            version.

            **Example**: `http://example.org/optimade/v1/search?optimade_urls="https://example.org/optimade_db/v1","https://optimade.herokuapp.com"`

        endpoint (str): The entry endpoint queried. According to the OPTIMADE specification, this
            is the same as the resource's type.

            **Example**: `structures`

        timeout (int): Timeout time (in seconds) to wait for a query to finish before redirecting
            (*after* starting the query). Note, if the query has not finished after the timeout
            time, a redirection will still be performed, but to a zero-results page, which can be
            refreshed to get the finished query (once it has finished).

    """

    def __init__(
        self,
        *,
        databases: List[str] = Query(
            [],
            description=(
                "List of possible database IDs that are already known by the gateway. To be known "
                "they need to be registered with the gateway (currently not possible)."
            ),
        ),
        optimade_urls: List[AnyUrl] = Query(
            [],
            description=(
                "A list of OPTIMADE base URLs. If a versioned base URL is supplied it will be used"
                " as is, as long as it represents a supported version. If an un-versioned base "
                "URL, standard version negotiation will be conducted to get the versioned base "
                "URL, which will be used as long as it represents a supported version."
            ),
        ),
        endpoint: str = Query(
            "structures",
            description=(
                "The entry endpoint queried. According to the OPTIMADE specification, this is the "
                "same as the resource's type."
            ),
        ),
        timeout: int = Query(
            15,
            description=(
                "Timeout time (in seconds) to wait for a query to finish before redirecting "
                "(*after* starting the query). Note, if the query has not finished after the "
                "timeout time, a redirection will still be performed, but to a zero-results page, "
                "which can be refreshed to get the finished query (once it has finished)."
            ),
        ),
    ) -> None:
        self.databases = databases
        self.optimade_urls = optimade_urls
        self.endpoint = endpoint
        self.timeout = timeout
