from datetime import datetime

class Chat:
    def __init__(self, user_id: int, title: str) -> None:
        self.user_id: int = user_id
        self.title: str = title
        self.created_at: datetime = datetime.now()