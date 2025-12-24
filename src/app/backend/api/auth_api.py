from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..dto.auth_dto import RegisterDTO, LoginDTO, UserResponseDTO
from ..service.auth_service import register, login
from ..core.postgres_db import get_pg_db

router = APIRouter()

@router.post("/register", response_model=UserResponseDTO)
def register_api(
        dto: RegisterDTO,
        db: Session = Depends(get_pg_db),
):
    try:
        return register(db, dto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=UserResponseDTO)
def login_api(
    dto: LoginDTO,
    db: Session = Depends(get_pg_db)
):
    try:
        return login(db, dto)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))