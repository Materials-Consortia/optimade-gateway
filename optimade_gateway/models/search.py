from typing import List, Union
import warnings

from pydantic import AnyUrl, BaseModel, Field, validator

from optimade_gateway.models.queries import OptimadeQueryParameters


class Search(BaseModel):
    """A general coordinated OPTIMADE search"""

    query_parameters: OptimadeQueryParameters = Field(
        ...,
        description="OPTIMADE query parameters for entry listing endpoints used for this query.",
    )
    optimade_urls: Union[AnyUrl, List[AnyUrl]] = Field(
        ...,
        description=(
            "A single or a list of OPTIMADE base URLs. If a versioned base URL is supplied it will"
            " be used as is, as long as it represents a supported version. If an un-versioned base"
            " URL, standard version negotiation will be conducted to get the versioned base URL, "
            "which will be used as long as it represents a supported version."
        ),
    )
    endpoint: str = Field(
        "structures",
        description=(
            "The entry endpoint queried. According to the OPTIMADE specification, this is the same"
            " as the resource's type."
        ),
    )

    @validator("optimade_urls")
    def unique_urls(
        cls, value: Union[AnyUrl, List[AnyUrl]]
    ) -> Union[AnyUrl, List[AnyUrl]]:
        """Remove non-unique entries"""
        if isinstance(value, AnyUrl):
            return value

        unique_urls = set(value)
        if len(value) == len(unique_urls):
            return value

        new_value = list(unique_urls)
        warnings.warn(
            f"Removed duplicate URLs. Original number of databases: {len(value)}. New number of "
            f"databases: {len(new_value)} Repeated URLs (number of repeats): "
            "{}".format(
                [
                    f"{url} ({value.count(url)})"
                    for url in [_ for _ in unique_urls if value.count(_) > 1]
                ]
            )
        )
        return new_value
