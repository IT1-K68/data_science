from pydantic import BaseModel

class RegisterDTO(BaseModel):
    username: str
    password: str

class LoginDTO(BaseModel):
    username: str
    password: str


class UserResponseDTO(BaseModel):
    id: int
    username: str