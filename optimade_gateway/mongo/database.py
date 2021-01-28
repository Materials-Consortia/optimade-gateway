import os

from motor.motor_asyncio import AsyncIOMotorClient


MONGO_URI = f"mongodb://{os.getenv('HOST_IP', 'localhost')}:27017"

MONGO_CLIENT = AsyncIOMotorClient(MONGO_URI)

MONGO_DB = MONGO_CLIENT["optimade_gateway"]
