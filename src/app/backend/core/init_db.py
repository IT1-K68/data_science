from model.user import Base
from core.postgres_db import engine

def init_db():
    Base.metadata.create_all(engine)
