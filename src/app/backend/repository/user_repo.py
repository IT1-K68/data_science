from sqlalchemy.orm import Session
from ..model.user_model import User

def is_username_exists(db: Session, username: str) -> bool:
    return db.query(User.id).filter(User.username == username).first() is not None

def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, password_hash: str) -> User:
    user: User = User(username=username, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


