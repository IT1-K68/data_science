from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId

from ..mapper.chat_mapper import chat_base_to_dto
from ..model.message_model import Message
from ..mapper.message_mapper import message_to_dto
from ..repository.chat_repo import get_chat_history_base
from ..repository.message_repo import (
    insert_message,
    get_messages_by_chat_id
)
from ..dto.message_dto import MessageRequestDTO, MessageResponseDTO
from ..dto.chat_dto import ChatHistoryResponseDTO, ChatHistoryRequestDTO, ChatHistoryBaseRequestDTO, \
    ChatHistoryBasesResponseDTO

##### Get chat history for a chat_id
async def get_chat_history(db: AsyncIOMotorDatabase, dto: ChatHistoryRequestDTO) -> ChatHistoryResponseDTO:
    print("call get_chat_history")
    docs = await get_messages_by_chat_id(db, dto.chat_id, dto.limit, dto.offset)
    print(docs)

    return ChatHistoryResponseDTO(
        messages=[message_to_dto(doc) for doc in docs[::-1]]
    )

##### Get all chat history base (chat_id, title) for an user_id
async def get_all_chat_history_base(db: AsyncIOMotorDatabase, dto: ChatHistoryBaseRequestDTO):
    print("call get_all_chat_history_base")
    docs = await get_chat_history_base(db, dto.user_id, dto.limit, dto.offset)

    return ChatHistoryBasesResponseDTO(
        chat_history=[chat_base_to_dto(doc) for doc in docs[::-1]]
    )