"""Configuration of the FastAPI server."""
# pylint: disable=no-self-use,no-self-argument,wrong-import-position
from enum import Enum
import os
from pathlib import Path
import re
from typing import List, Optional, TYPE_CHECKING
from warnings import warn

if not os.getenv("OPTIMADE_CONFIG_FILE"):
    # This needs to be done prior to importing from `optimade`.
    os.environ["OPTIMADE_CONFIG_FILE"] = str(
        Path(__file__).resolve().parent.parent / "config.yml"
    )

from optimade.server.config import ServerConfig as OptimadeServerConfig
from pydantic import Field, SecretStr, root_validator, validator

from optimade_gateway.warnings import OptimadeGatewayWarning

if TYPE_CHECKING:
    from typing import Any, Dict


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
    mongo_atlas_pem_content: Optional[SecretStr] = Field(
        None,
        description="Content of the MongoDB Atlas PEM certificate.",
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

    @root_validator
    def create_pem_file(cls, values: "Dict[str, Any]") -> "Dict[str, Any]":
        """Create PEM file from content, if no PEM file value is set."""
        if values.get("mongo_atlas_pem", None) is None:
            if values.get("mongo_atlas_pem_content", None) is None:
                # Neither is set - just return
                return values
            # Create PEM file and set it
            new_pem = (
                Path(__file__).resolve().parent.parent.parent / "MongoDB_atlas.pem"
            ).resolve()
            new_pem.write_text(
                values.get("mongo_atlas_pem_content", SecretStr("")).get_secret_value(),
                encoding="utf8",
            )
            values["mongo_atlas_pem"] = new_pem
        return values


CONFIG = ServerConfig()
