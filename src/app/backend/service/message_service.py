from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

from ..model.chat_model import Chat
from ..model.message_model import Message
from ..mapper.message_mapper import message_to_dto
from ..repository.chat_repo import create_chat
from ..repository.message_repo import (
    insert_message,
    get_messages_by_chat_id
)
from ..dto.message_dto import MessageRequestDTO, MessageResponseDTO, NewChatMessageRequestDTO, NewChatMessageResponseDTO

async def send_message(
        db: AsyncIOMotorDatabase,
        dto: MessageRequestDTO,
) -> MessageResponseDTO:

    user_doc = await insert_message(db, Message(dto.chat_id, "user", dto.content))
    bot_reply: str = f"Test bot answer"
    bot_doc = await insert_message(db, Message(dto.chat_id, "assistant", bot_reply))

    return MessageResponseDTO(content=bot_reply)

async def send_new_chat_message(
        db: AsyncIOMotorDatabase,
        dto: NewChatMessageRequestDTO
):
    # Create new chat
    model: Chat = Chat(
        user_id=dto.user_id,
        title=build_title(dto.content, 10),
    )
    new_chat = await create_chat(db, model)

    # Get bot reply and insert all to MongoDB
    user_doc = await insert_message(db, Message(new_chat["id"], "user", dto.content))
    bot_reply: str = f"Test bot answer"
    bot_doc = await insert_message(db, Message(new_chat["id"], "assistant", bot_reply))

    return NewChatMessageResponseDTO(
        chat_id=str(new_chat["id"]),
        title=new_chat["title"],
        content=bot_reply
    )



def build_title(content: str, max_word: int) -> str:

    words = content.strip().split()
    title = ""
    if len(words) < max_word:
        title = content.strip()
    else:
        title = " ".join(words[:max_word])

    title[0].upper() + title[1:]

    return title
