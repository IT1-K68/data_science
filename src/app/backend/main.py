from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from .api import auth_api, message_api, chat_api
from dotenv import load_dotenv
from .core.init_db import init_db

load_dotenv()

init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_api.router, prefix="/auth", tags=["auth"])
app.include_router(message_api.router, prefix="/message", tags=["message"])
app.include_router(chat_api.router, prefix="/chat", tags=["chat"])