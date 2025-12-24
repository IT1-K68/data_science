from fastapi import APIRouter, Depends, Query, Body
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..dto.message_dto import MessageRequestDTO
from ..dto.chat_dto import ChatHistoryRequestDTO, ChatHistoryBaseRequestDTO, ChatHistoryBasesResponseDTO, \
    ChatHistoryResponseDTO
from ..service.message_service import send_message
from ..service.chat_service import get_chat_history, get_all_chat_history_base
from ..core.mongo_db import get_mongo_db

router = APIRouter()

@router.get("/chat_history_base", response_model=ChatHistoryBasesResponseDTO)
async def get_chat_history_base_api(
        user_id: int,
        limit: int = 10,
        offset: datetime | None = None,
        db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    dto = ChatHistoryBaseRequestDTO(
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    return await get_all_chat_history_base(db, dto)

@router.get("/{chat_id}", response_model=ChatHistoryResponseDTO)
async def get_chat_api(
        chat_id: str,
        limit: int = 10,
        offset: datetime | None = None,
        db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    dto = ChatHistoryRequestDTO(
        chat_id=chat_id,
        limit=limit,
        offset=offset
    )
    return await get_chat_history(db, dto)
