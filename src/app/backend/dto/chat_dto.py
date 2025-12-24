from pydantic import BaseModel
from datetime import datetime


##### For 1 chat history
class ChatHistoryRequestDTO(BaseModel):
    chat_id: str
    limit: int
    offset: datetime | None

class ChatHistoryMessageResponseDTO(BaseModel):
    role: str
    content: str
    created_at: datetime

class ChatHistoryResponseDTO(BaseModel):
    messages: list[ChatHistoryMessageResponseDTO]

##### For all chat history base
class ChatHistoryBaseRequestDTO(BaseModel):
    user_id: int
    limit: int
    offset: datetime | None

class ChatHistoryBaseResponseDTO(BaseModel):
    chat_id: str
    title: str
    created_at: datetime

class ChatHistoryBasesResponseDTO(BaseModel):
    chat_history: list[ChatHistoryBaseResponseDTO]