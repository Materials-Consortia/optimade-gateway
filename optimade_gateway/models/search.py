from typing import Set

from pydantic import AnyUrl, BaseModel, Field, root_validator

from optimade_gateway.models.queries import OptimadeQueryParameters


class Search(BaseModel):
    """A general coordinated OPTIMADE search

    Either `database_ids` or `optimade_urls` MUST be specified.
    """

    query_parameters: OptimadeQueryParameters = Field(
        {},
        description="OPTIMADE query parameters for entry listing endpoints used for this query.",
    )
    database_ids: Set[str] = Field(
        set(),
        description=(
            "A list of registered database IDs. Go to /databases to get all registered databases."
        ),
    )
    optimade_urls: Set[AnyUrl] = Field(
        set(),
        description=(
            "A list of OPTIMADE base URLs. If a versioned base URL is supplied it will be used as "
            "is, as long as it represents a supported version. If an un-versioned base URL, "
            "standard version negotiation will be conducted to get the versioned base URL, which "
            "will be used as long as it represents a supported version. Note: A single URL can be "
            "supplied as well, and it will automatically be wrapped in a list in the server logic."
        ),
    )
    endpoint: str = Field(
        "structures",
        description=(
            "The entry endpoint queried. According to the OPTIMADE specification, this is the same"
            " as the resource's type."
        ),
    )

    @root_validator
    def either_ids_or_urls(cls, values: dict) -> dict:
        """Either `database_ids` or `optimade_urls` must be defined"""
        if not any(values.get(field) for field in ("database_ids", "optimade_urls")):
            raise ValueError(
                "Either 'database_ids' or 'optimade_urls' MUST be specified."
            )
        return values
