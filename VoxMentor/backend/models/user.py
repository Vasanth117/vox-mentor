from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    preferred_language: str = "english"
    career_goal: Optional[str] = None
    skill_level: str = "beginner"   # beginner / intermediate / advanced

class UserLogin(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    user_id: str
    name: str
    email: str
    preferred_language: str
    career_goal: Optional[str]
    skill_level: str
    xp: int = 0
    streak: int = 0
    last_active: Optional[datetime] = None
    badges: list[str] = []
    teaching_style: str = "balanced"   # guided / independent / balanced
    created_at: datetime = Field(default_factory=datetime.utcnow)
