from pydantic import BaseModel
from datetime import datetime

##### For new chat message
class NewChatMessageRequestDTO(BaseModel):
    user_id: int
    content: str

class NewChatMessageResponseDTO(BaseModel):
    chat_id: str
    title: str
    content: str

##### For normal chat message
class MessageRequestDTO(BaseModel):
    chat_id: str
    content: str

class MessageResponseDTO(BaseModel):
    content: str
