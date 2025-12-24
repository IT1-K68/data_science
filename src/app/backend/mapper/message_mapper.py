from ..dto.chat_dto import ChatHistoryMessageResponseDTO


def message_to_dto(doc: dict) -> ChatHistoryMessageResponseDTO:
    return ChatHistoryMessageResponseDTO(
        role=doc["role"],
        content=doc["content"],
        created_at=doc["created_at"],
    )