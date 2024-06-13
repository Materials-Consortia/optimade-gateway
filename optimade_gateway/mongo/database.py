"""Initialize the MongoDB database."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.logger import LOGGER

MONGO_CLIENT = AsyncIOMotorClient(
    CONFIG.mongo_uri,
    appname="optimade-gateway",
    readConcernLevel="majority",
    readPreference="primary",
    w="majority",
)
"""The MongoDB motor client."""

MONGO_DB = MONGO_CLIENT[CONFIG.mongo_database]
"""The MongoDB motor database.
This is a representation of the database used for the gateway service."""

LOGGER.info("Using: Real MongoDB (motor) at %s", CONFIG.mongo_uri)
LOGGER.info("Database: %s", CONFIG.mongo_database)
