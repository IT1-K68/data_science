from fastapi import FastAPI
from api import auth, chat
from dotenv import load_dotenv
from core.init_db import init_db

load_dotenv()

init_db()

app = FastAPI()

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])