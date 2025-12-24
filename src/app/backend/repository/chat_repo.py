from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

from ..model.message_model import Message
from ..model.chat_model import Chat

async def create_chat(
        db: AsyncIOMotorDatabase,
        model: Chat,
) -> dict:
    doc: dict = {
        "user_id": model.user_id,
        "title": model.title,
        "created_at": model.created_at,
    }

    result = await db.chats.insert_one(doc)
    doc["id"] = result.inserted_id
    return doc

async def get_chat_history_base(
        db: AsyncIOMotorDatabase,
        user_id: int,
        limit: int = 10,
        offset: datetime = None,
) -> List[dict]:

    query: dict = {
        "user_id": user_id,
    }
    if offset:
        query["created_at"] = {"$lt": offset}

    cursor = (
        db.chats
            .find(query)
            .sort("created_at", -1)
            .limit(limit)
    )

    return await cursor.to_list()
