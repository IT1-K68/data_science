from ..dto.chat import MessageResponseDTO

def message_to_dto(doc: dict) -> MessageResponseDTO:
    return MessageResponseDTO(
        id=str(doc["_id"]),
        role=doc["role"],
        content=doc["content"],
        created_at=doc["created_at"],
    )