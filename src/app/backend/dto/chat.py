from pydantic import BaseModel
from datetime import datetime

class SendMessageDTO(BaseModel):
    chat_id: str
    content: str

class MessageResponseDTO(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

class ChatHistoryResponseDTO(BaseModel):
    chat_id: str
    messages: list[MessageResponseDTO]

