from fastapi import APIRouter, Depends, Query
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..dto.message_dto import MessageRequestDTO, NewChatMessageRequestDTO, MessageResponseDTO, NewChatMessageResponseDTO
from ..dto.chat_dto import ChatHistoryRequestDTO
from ..service.message_service import send_message, send_new_chat_message
from ..service.chat_service import get_chat_history
from ..core.mongo_db import get_mongo_db

router = APIRouter()

@router.post("/", response_model=MessageResponseDTO)
async def send_message_api(
        dto: MessageRequestDTO,
        db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    return await send_message(db, dto)

@router.post("/new_chat_message", response_model=NewChatMessageResponseDTO)
async def new_chat_message_api(
        dto: NewChatMessageRequestDTO,
        db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    return await send_new_chat_message(db, dto)




