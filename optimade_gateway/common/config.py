"""Configuration of the FastAPI server"""
# pylint: disable=no-self-argument
import os
import re
import warnings

from optimade.server.config import ServerConfig as OptimadeServerConfig
from pydantic import Field, validator


class ServerConfig(OptimadeServerConfig):
    """This class stores server config parameters in a way that
    can be easily extended for new config file types.

    """

    databases_collection: str = Field(
        "databases",
        description="Mongo collection name for `/databases` endpoint resources.",
    )
    gateways_collection: str = Field(
        "gateways",
        description="Mongo collection name for `/gateways` endpoint resources.",
    )
    queries_collection: str = Field(
        "queries",
        description="Mongo collection name for `/queries` endpoint resources.",
    )
    load_optimade_providers_databases: bool = Field(
        True,
        description=(
            "Whether or not to load all valid OPTIMADE providers' databases from the "
            "[Materials-Consortia list of OPTIMADE providers](https://providers.optimade.org) on "
            "server startup."
        ),
    )

    @validator("mongo_uri")
    def replace_with_env_vars(cls, v):
        """Replace string variables with environment variables, if possible"""
        res: str = v
        for match in re.finditer(r"\{[^{}]+\}", v):
            string_var = match.group()[1:-1]
            env_var = os.getenv(
                string_var, os.getenv(string_var.upper(), os.getenv(string_var.lower()))
            )
            if env_var is not None:
                res = res.replace(match.group(), env_var)
            else:
                warnings.warn(
                    f"Could not find an environment variable for {match.group()!r} from mongo_uri: {v}"
                )
        return res


CONFIG = ServerConfig()
