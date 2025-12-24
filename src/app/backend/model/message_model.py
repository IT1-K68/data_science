from datetime import datetime

class Message:
    def __init__(self, chat_id: str, role: str, content: str):
        self.chat_id: str = chat_id
        self.role: str = role
        self.content: str = content
        self.created_at: datetime = datetime.now()