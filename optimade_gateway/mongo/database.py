from motor.motor_asyncio import AsyncIOMotorClient

from optimade_gateway.common.config import CONFIG


MONGO_CLIENT = AsyncIOMotorClient(CONFIG.mongo_uri)

MONGO_DB = MONGO_CLIENT[CONFIG.mongo_database]
