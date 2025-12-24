from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List
from bson import ObjectId

from ..model.message_model import Message


async def insert_message(
        db: AsyncIOMotorDatabase,
        model: Message
) -> dict:
    doc: dict = {
        "chat_id": ObjectId(model.chat_id),
        "role": model.role,
        "content": model.content,
        "created_at": model.created_at,
    }
    result = await db.messages.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_messages_by_chat_id(
        db: AsyncIOMotorDatabase,
        chat_id: str,
        limit: int = 10,
        offset: datetime = None,
) -> List[dict]:

    query: dict = {"chat_id": ObjectId(chat_id)}
    if offset:
        query["created_at"] = {"$lt": offset}

    cursor = (
        db.messages
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
    )

    return await cursor.to_list()



