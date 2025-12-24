import bcrypt
from sqlalchemy.orm import Session
from ..dto.auth import RegisterDTO, LoginDTO, UserResponseDTO
from ..repository.user_repo import (
    is_username_exists,
    get_user_by_username,
    create_user,
)
from ..mapper.user_mapper import user_to_dto


def register(db: Session, dto: RegisterDTO) -> UserResponseDTO:
    if is_username_exists(db, dto.username):
        raise ValueError("Username already exists")

    password_hash: str = bcrypt.hashpw(
        dto.password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    user = create_user(db, dto.username, password_hash)
    return user_to_dto(user)

def login(db: Session, dto: LoginDTO) -> UserResponseDTO:
    user = get_user_by_username(db, dto.username)
    if not user:
        raise ValueError("Invalid credentials")

    if not bcrypt.checkpw(dto.password.encode("utf-8"), user.password_hash.encode("utf-8")):
        raise ValueError("Invalid credentials")

    return user_to_dto(user)










