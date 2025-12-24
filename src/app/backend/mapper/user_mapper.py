from ..model.user_model import User
from ..dto.auth_dto import UserResponseDTO

def user_to_dto(user: User) -> UserResponseDTO:
    return UserResponseDTO(
        id=user.id,
        username=user.username,
    )