from ..model.user import User
from ..dto.auth import UserResponseDTO

def user_to_dto(user: User) -> UserResponseDTO:
    return UserResponseDTO(
        id=user.id,
        username=user.username,
    )