"""
Journal Router — learning reflections
POST /api/journal       — save reflection
GET  /api/journal/{uid} — get all entries
"""
from fastapi import APIRouter
from models.journal import JournalRequest
from services.ai_engine import analyze_reflection
from db import journal_col, users_col
from datetime import datetime

router = APIRouter(prefix="/api/journal", tags=["journal"])


@router.post("/")
async def save_reflection(req: JournalRequest):
    # AI analyzes the reflection
    analysis = await analyze_reflection(req.content)
    mood_assessment = analysis.get("mood_assessment", "neutral")

    entry = {
        "user_id": req.user_id,
        "title": req.title,
        "content": req.content,
        "mood": req.mood,
        "topics_covered": req.topics_covered,
        "key_learnings": analysis.get("key_learnings", []),
        "questions_remaining": analysis.get("questions_remaining", []),
        "encouragement": analysis.get("encouragement", ""),
        "suggested_next_topics": analysis.get("suggested_next_topics", []),
        "mood_assessment": mood_assessment,
        "created_at": datetime.utcnow(),
    }
    result = await journal_col().insert_one(entry)
    entry["_id"] = str(result.inserted_id)

    # Persist the latest mood so the AI tutor can adapt future responses
    await users_col().update_one(
        {"user_id": req.user_id},
        {"$set": {"last_mood": mood_assessment, "last_reflection_at": datetime.utcnow()}},
    )

    return entry


@router.get("/{user_id}")
async def get_journal(user_id: str, limit: int = 20):
    cursor = journal_col().find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    entries = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        entries.append(doc)
    return {"entries": entries, "count": len(entries)}
