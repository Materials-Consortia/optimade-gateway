"""Initialize the MongoDB database."""
from os import getenv
from typing import TYPE_CHECKING

from motor.motor_asyncio import AsyncIOMotorClient

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.logger import LOGGER

if TYPE_CHECKING or bool(getenv("MKDOCS_BUILD", "")):  # pragma: no cover
    # pylint: disable=unused-import
    from pymongo.database import Database
    from pymongo.mongo_client import MongoClient


client_extras = {
    "tls": True,
    "tlsCertificateKeyFile": str(CONFIG.mongo_atlas_pem),
}

if any(
    _ in CONFIG.mongo_uri
    for _ in (
        getenv("HOST_IP", "THIS SHOULDN'T BE IN"),
        "localhost",
        "127.0.0.1",
    )
):
    # Assume we are running locally
    client_extras = {}


MONGO_CLIENT: "MongoClient" = AsyncIOMotorClient(
    CONFIG.mongo_uri,
    appname="optimade-gateway",
    readConcernLevel="majority",
    readPreference="primary",
    w="majority",
    **client_extras,
)
"""The MongoDB motor client."""

MONGO_DB: "Database" = MONGO_CLIENT[CONFIG.mongo_database]
"""The MongoDB motor database.
This is a representation of the database used for the gateway service."""

LOGGER.info("Using: Real MongoDB (motor) at %s", CONFIG.mongo_uri)
LOGGER.info("Database: %s", CONFIG.mongo_database)
