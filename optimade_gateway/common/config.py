"""Configuration of the FastAPI server."""
# pylint: disable=no-self-use,no-self-argument,wrong-import-position
from enum import Enum
import os
from pathlib import Path
import re
from typing import List, Optional
from warnings import warn

if not os.getenv("OPTIMADE_CONFIG_FILE"):
    # This needs to be done prior to importing from `optimade`.
    os.environ["OPTIMADE_CONFIG_FILE"] = str(
        Path(__file__).resolve().parent.parent / "config.yml"
    )

from optimade.server.config import ServerConfig as OptimadeServerConfig
from pydantic import Field, validator

from optimade_gateway.warnings import OptimadeGatewayWarning


class MarketPlaceHost(Enum):
    """The available MarketPlace host domains."""

    PRODUCTION = "the-marketplace.eu"
    STAGING = "staging.the-marketplace.eu"
    LOCAL = "lvh.me"


class AvailableOAuthScopes(Enum):
    """Available OAuth2 scopes for the MarketPlace."""

    OPENID = "openid"
    PROFILE = "profile"
    EMAIL = "email"
    ADDRESS = "address"
    PHONE = "phone"
    OFFLINE_ACCESS = "offline_access"


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
            "[Materials-Consortia list of OPTIMADE providers]"
            "(https://providers.optimade.org) on server startup."
        ),
    )

    # MarketPlace-specific
    hydra_application_id: str = Field(
        "", description="The MarketPlace hydra client id."
    )
    hydra_scopes: List[AvailableOAuthScopes] = Field(
        [AvailableOAuthScopes.OPENID, AvailableOAuthScopes.EMAIL],
        description="The list of OAuth2 scopes requested by the application.",
    )
    mongo_atlas_pem: Optional[Path] = Field(
        None, description="Path to MongoDB Atlas PEM certificate."
    )
    marketplace_host: MarketPlaceHost = Field(
        MarketPlaceHost.STAGING,
        description=(
            "An enumeration of the available recognized MarketPlace domain host."
        ),
    )

    @validator("mongo_uri")
    def replace_with_env_vars(cls, value: str) -> str:
        """Replace string variables with environment variables, if possible"""
        res = value
        for match in re.finditer(r"\{[^{}]+\}", value):
            string_var = match.group()[1:-1]
            env_var = os.getenv(
                string_var, os.getenv(string_var.upper(), os.getenv(string_var.lower()))
            )
            if env_var is not None:
                res = res.replace(match.group(), env_var)
            else:
                warn(
                    OptimadeGatewayWarning(
                        detail=(
                            "Could not find an environment variable for "
                            f"{match.group()!r} from mongo_uri: {value}"
                        )
                    )
                )
        return res


CONFIG = ServerConfig()
