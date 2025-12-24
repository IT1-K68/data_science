from ..dto.chat_dto import ChatHistoryBaseResponseDTO


def chat_base_to_dto(doc: dict) -> ChatHistoryBaseResponseDTO:
    return ChatHistoryBaseResponseDTO(
        chat_id=str(doc["_id"]),
        title=doc["title"],
        created_at=doc["created_at"],
    )