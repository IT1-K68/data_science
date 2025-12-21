from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = AsyncIOMotorClient(
    MONGO_URI,
    maxPoolSize=10,
    serverSelectionTimeoutMS=5000,
)

mongo_db: AsyncIOMotorDatabase = client["chat_db"]

async def get_mongo_db() -> AsyncIOMotorDatabase:
    return mongo_db

