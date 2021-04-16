from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.database import Database
from pymongo.mongo_client import MongoClient

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.logger import LOGGER


MONGO_CLIENT: MongoClient = AsyncIOMotorClient(
    CONFIG.mongo_uri,
    appname="optimade-gateway",
    readConcernLevel="majority",
    readPreference="primary",
    w="majority",
)

MONGO_DB: Database = MONGO_CLIENT[CONFIG.mongo_database]

LOGGER.info("Using: Real MongoDB (motor) at %s", CONFIG.mongo_uri)
LOGGER.info("Database: %s", CONFIG.mongo_database)
