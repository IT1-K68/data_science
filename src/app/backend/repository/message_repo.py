from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List

async def insert_message(
        db: AsyncIOMotorDatabase,
        chat_id: int,
        role: str,
        content: str,
):
    doc: dict = {
        "chat_id": chat_id,
        "role": role,
        "content": content,
        "created_at": datetime.now(),
    }
    result = await db.messages.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_messages_by_chat_id(
        db: AsyncIOMotorDatabase,
        chat_id: str,
        limit: int = 100
) -> List[dict]:
    cursor = (
        db.messages
            .find({"chat_id": chat_id})
            .sort("created_at", 1)
            .limit(limit)
    )

    return await cursor.to_list(length=limit)



