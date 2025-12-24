from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..dto.chat import SendMessageDTO
from ..service.chat_service import send_message, get_messages_by_chat_id, get_chat_history
from ..core.mongo_db import get_mongo_db

router = APIRouter()

@router.post("/message")
async def send_message_api(
        dto: SendMessageDTO,
        db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    return await send_message(db, dto.chat_id, dto.content)

@router.get("/{chat_id}")
async def get_chat_api(
        chat_id: str,
        db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    return await get_chat_history(db, chat_id)




