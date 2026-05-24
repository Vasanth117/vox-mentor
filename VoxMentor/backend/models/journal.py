from pydantic import BaseModel, Field
from datetime import datetime

class JournalEntry(BaseModel):
    user_id: str
    title: str
    content: str
    mood: str = "neutral"       # great / good / neutral / stuck / frustrated
    topics_covered: list[str] = []
    key_learnings: list[str] = []
    questions_remaining: list[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class JournalRequest(BaseModel):
    user_id: str
    title: str
    content: str
    mood: str = "neutral"
    topics_covered: list[str] = []
