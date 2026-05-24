from pydantic import BaseModel, Field
from datetime import datetime

class MistakePattern(BaseModel):
    pattern_type: str   # e.g. "missing_return", "infinite_loop_risk", "bare_except"
    description: str
    example: str
    frequency: int = 1
    last_seen: datetime = Field(default_factory=datetime.utcnow)

class UserMistakes(BaseModel):
    user_id: str
    language: str = "python"
    patterns: list[MistakePattern] = []
    total_mistakes: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)
