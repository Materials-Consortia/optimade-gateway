"""Configuration of the FastAPI server."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Annotated
from warnings import warn

from optimade.server.config import ServerConfig as OptimadeServerConfig
from pydantic import Field, SecretStr, field_validator, model_validator

from optimade_gateway.warnings import OptimadeGatewayWarning


class ServerConfig(OptimadeServerConfig):
    """This class stores server config parameters in a way that
    can be easily extended for new config file types.

    """

    databases_collection: Annotated[
        str,
        Field(
            description="Mongo collection name for `/databases` endpoint resources.",
        ),
    ] = "databases"

    gateways_collection: Annotated[
        str,
        Field(
            description="Mongo collection name for `/gateways` endpoint resources.",
        ),
    ] = "gateways"

    queries_collection: Annotated[
        str,
        Field(
            description="Mongo collection name for `/queries` endpoint resources.",
        ),
    ] = "queries"

    load_optimade_providers_databases: Annotated[
        bool,
        Field(
            description=(
                "Whether or not to load all valid OPTIMADE providers' databases from "
                "the [Materials-Consortia list of OPTIMADE providers]"
                "(https://providers.optimade.org) on server startup."
            ),
        ),
    ] = True

    mongo_certfile: Annotated[
        Path,
        Field(
            description="Path to the MongoDB certificate file.",
        ),
    ] = Path("/certs/mongodb.pem")

    mongo_atlas_pem_content: Annotated[
        SecretStr | None,
        Field(
            description="PEM content for MongoDB Atlas certificate.",
        ),
    ] = None

    @field_validator("mongo_uri", mode="after")
    @classmethod
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

    @model_validator(mode="after")
    def write_pem_content_to_file(self) -> ServerConfig:
        """Write the MongoDB Atlas PEM content to a file"""
        if self.mongo_atlas_pem_content:
            self.mongo_certfile.write_text(
                self.mongo_atlas_pem_content.get_secret_value()
            )

        return self


CONFIG = ServerConfig()
