from motor.motor_asyncio import AsyncIOMotorDatabase

from mapper.message_mapper import message_to_dto
from repository.message_repo import (
    insert_message,
    get_messages_by_chat_id
)
from dto.chat import ChatHistoryResponseDTO

async def send_message(
        db: AsyncIOMotorDatabase,
        chat_id: str,
        user_content: str
) -> dict:
    user_doc = await insert_message(db, chat_id, "user", user_content)

    bot_reply: str = f"Test bot answer"
    bot_doc = await insert_message(db, chat_id, "assistant", bot_reply)

    return {
        "user": message_to_dto(user_doc),
        "assistant": message_to_dto(bot_doc)
    }

async def get_chat_history(db: AsyncIOMotorDatabase, chat_id: str) -> ChatHistoryResponseDTO:
    docs = await get_messages_by_chat_id(db, chat_id)

    return ChatHistoryResponseDTO(
        chat_id=chat_id,
        messages=[message_to_dto(doc) for doc in docs]
    )