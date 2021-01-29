from motor.motor_asyncio import AsyncIOMotorClient

from optimade_gateway.common.config import CONFIG
from optimade_gateway.common.logger import LOGGER


MONGO_CLIENT = AsyncIOMotorClient(CONFIG.mongo_uri)

MONGO_DB = MONGO_CLIENT[CONFIG.mongo_database]

LOGGER.info("Using: Real MongoDB (motor) at %s", CONFIG.mongo_uri)
LOGGER.info("Database: %s", CONFIG.mongo_database)
