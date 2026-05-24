from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Message(BaseModel):
    role: str   # "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatSession(BaseModel):
    user_id: str
    topic: Optional[str] = None
    language: str = "python"
    messages: list[Message] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    user_id: str
    message: str
    language: str = "python"
    session_id: Optional[str] = None
    mode: str = "tutor"   # tutor | practice | debug | reflect | auto


class ChatRegenerateRequest(BaseModel):
    user_id: str
    session_id: str
    language: str = "python"
    mode: str = "auto"
