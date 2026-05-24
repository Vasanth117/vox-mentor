from pydantic import BaseModel, Field
from datetime import datetime

class TopicProgress(BaseModel):
    topic: str
    mastery: float = 0.0          # 0-100
    attempts: int = 0
    correct: int = 0
    time_spent_minutes: float = 0.0
    last_practiced: datetime = Field(default_factory=datetime.utcnow)

class UserProgress(BaseModel):
    user_id: str
    topics: list[TopicProgress] = []
    total_xp: int = 0
    streak: int = 0
    longest_streak: int = 0
    total_sessions: int = 0
    total_time_minutes: float = 0.0
    weak_areas: list[str] = []
    strong_areas: list[str] = []
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ProgressUpdate(BaseModel):
    user_id: str
    topic: str
    correct: bool
    time_spent_minutes: float = 0.0
