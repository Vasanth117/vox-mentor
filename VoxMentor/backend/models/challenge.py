from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Challenge(BaseModel):
    title: str
    description: str
    starter_code: str
    expected_output: Optional[str] = None
    test_cases: list[dict] = []     # [{input, expected_output}]
    difficulty: str = "beginner"    # beginner / intermediate / advanced
    topic: str = "general"
    language: str = "python"
    xp_reward: int = 50

class DailyChallenge(BaseModel):
    user_id: str
    date: str                       # YYYY-MM-DD
    challenge: Challenge
    completed: bool = False
    submitted_code: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PracticeRequest(BaseModel):
    user_id: str
    topic: str
    language: str = "python"
    difficulty: str = "beginner"
