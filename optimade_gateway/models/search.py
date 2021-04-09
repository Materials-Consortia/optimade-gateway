from typing import List, Union
import warnings

from pydantic import AnyUrl, BaseModel, Field, validator
from pydantic.networks import url_regex

from optimade_gateway.models.queries import OptimadeQueryParameters


class Search(BaseModel):
    """A general coordinated OPTIMADE search"""

    query_parameters: OptimadeQueryParameters = Field(
        {},
        description="OPTIMADE query parameters for entry listing endpoints used for this query.",
    )
    optimade_urls: List[AnyUrl] = Field(
        ...,
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

    @validator("optimade_urls", pre=True)
    def wrap_value_in_list(cls, value: Union[str, List[AnyUrl]]) -> List[AnyUrl]:
        """Wrap a supplied `optimade_urls` value in a list."""
        if isinstance(value, str):
            parts = url_regex().match(value).groupdict()
            host, tld, host_type, _ = AnyUrl.validate_host(parts)
            for key in ("ipv4", "ipv6", "domain"):
                parts.pop(key)
            value = AnyUrl(url=value, host=host, tld=tld, host_type=host_type, **parts)
            return [value]
        elif isinstance(value, list):
            return value
        else:
            raise TypeError(
                "value of `optimade_urls` should be either a list of URLs or a single URL, but was"
                f" instead of type {type(value)} with value: {value}"
            )

    @validator("optimade_urls")
    def unique_urls(cls, value: List[AnyUrl]) -> List[AnyUrl]:
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

        # Assert length of optimade_urls is > 0
        assert new_value, "At least a single URL must be supplied."

        return new_value
