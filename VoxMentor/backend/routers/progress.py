"""
Progress Router
GET  /api/progress/{user_id}    — full progress summary
POST /api/progress/update        — update after practice
"""
from fastapi import APIRouter
from models.progress import ProgressUpdate
from services.learning_engine import (
    calculate_level, compute_streak, award_xp, update_mastery,
    suggest_next_topics, check_badges
)
from db import progress_col, users_col
from datetime import datetime

router = APIRouter(prefix="/api/progress", tags=["progress"])


def _topic_metrics(topic: dict) -> dict:
    attempts = max(0, int(topic.get("attempts", 0)))
    correct = max(0, int(topic.get("correct", 0)))
    mastery = float(topic.get("mastery", 0.0))

    accuracy_pct = (correct / attempts) * 100 if attempts > 0 else 0.0
    confidence = min(1.0, attempts / 8.0)

    base = (mastery * 0.55) + (accuracy_pct * 0.45)
    proficiency = base * (0.35 + (0.65 * confidence))
    proficiency = max(0.0, min(100.0, proficiency))

    return {
        **topic,
        "accuracy_pct": round(accuracy_pct, 1),
        "confidence_pct": round(confidence * 100, 1),
        "proficiency_score": round(proficiency, 1),
        "status": _topic_status(proficiency, attempts),
    }


def _proficiency_band(score: float) -> str:
    if score >= 80:
        return "advanced"
    if score >= 60:
        return "proficient"
    if score >= 40:
        return "developing"
    return "beginner"


def _topic_status(score: float, attempts: int) -> str:
    if attempts < 2:
        return "new"
    if score >= 80 and attempts >= 5:
        return "solid"
    if score >= 55:
        return "improving"
    return "needs_practice"


@router.get("/{user_id}")
async def get_progress(user_id: str):
    doc = await progress_col().find_one({"user_id": user_id})
    user = await users_col().find_one({"user_id": user_id})

    if not doc:
        return {
            "user_id": user_id,
            "topics": [], "total_xp": 0, "streak": 0,
            "level": calculate_level(0),
            "weak_areas": [], "strong_areas": [],
            "suggested_topics": [],
            "badges": [],
        }

    raw_topics = doc.get("topics", [])
    topics = [_topic_metrics(topic) for topic in raw_topics]
    xp = doc.get("total_xp", 0)
    streak = doc.get("streak", 0)

    ranked = sorted(topics, key=lambda t: t.get("proficiency_score", 0.0))
    weak = [t["topic"] for t in ranked if t.get("attempts", 0) >= 2][:3]
    strong = [t["topic"] for t in reversed(ranked) if t.get("attempts", 0) >= 3 and t.get("proficiency_score", 0) >= 65][:3]

    completed_nodes = [
        t["topic"]
        for t in topics
        if t.get("proficiency_score", 0) >= 70 and t.get("attempts", 0) >= 3
    ]
    suggestions = suggest_next_topics(completed_nodes, xp, weak)

    avg_proficiency = round(
        sum(t.get("proficiency_score", 0.0) for t in topics) / len(topics),
        1,
    ) if topics else 0.0
    overall_band = _proficiency_band(avg_proficiency)

    total_attempts = sum(int(t.get("attempts", 0)) for t in topics)
    total_correct = sum(int(t.get("correct", 0)) for t in topics)
    overall_accuracy = round((total_correct / total_attempts) * 100, 1) if total_attempts > 0 else 0.0

    streak_component = min(100.0, (streak / 14.0) * 100.0)
    readiness_score = round(
        (avg_proficiency * 0.6) + (overall_accuracy * 0.3) + (streak_component * 0.1),
        1,
    )

    return {
        "user_id": user_id,
        "topics": topics,
        "total_xp": xp,
        "streak": streak,
        "longest_streak": doc.get("longest_streak", 0),
        "total_sessions": doc.get("total_sessions", 0),
        "total_time_minutes": doc.get("total_time_minutes", 0),
        "avg_proficiency": avg_proficiency,
        "overall_accuracy": overall_accuracy,
        "readiness_score": readiness_score,
        "total_attempts": total_attempts,
        "total_correct": total_correct,
        "overall_band": overall_band,
        "level": calculate_level(xp),
        "weak_areas": weak,
        "strong_areas": strong,
        "suggested_topics": suggestions,
        "badges": user.get("badges", []) if user else [],
        "updated_at": doc.get("updated_at"),
    }


@router.post("/update")
async def update_progress(req: ProgressUpdate):
    doc = await progress_col().find_one({"user_id": req.user_id})
    user = await users_col().find_one({"user_id": req.user_id})

    now = datetime.utcnow()
    xp_gain = award_xp(50 if req.correct else 10, user.get("streak", 0) if user else 0)

    if doc:
        topics = doc.get("topics", [])
        topic_doc = next((t for t in topics if t["topic"] == req.topic), None)

        if topic_doc:
            topic_doc["attempts"] = topic_doc.get("attempts", 0) + 1
            if req.correct:
                topic_doc["correct"] = topic_doc.get("correct", 0) + 1
            topic_doc["mastery"] = update_mastery(
                topic_doc.get("mastery", 0.0), req.correct, topic_doc["attempts"]
            )
            topic_doc["time_spent_minutes"] = topic_doc.get("time_spent_minutes", 0) + req.time_spent_minutes
            topic_doc["last_practiced"] = now
        else:
            topics.append({
                "topic": req.topic,
                "mastery": 35.0 if req.correct else 10.0,
                "attempts": 1,
                "correct": 1 if req.correct else 0,
                "time_spent_minutes": req.time_spent_minutes,
                "last_practiced": now,
            })

        streak_result = compute_streak(doc.get("updated_at"), doc.get("streak", 0))
        new_xp = doc.get("total_xp", 0) + xp_gain
        new_streak = streak_result["streak"]

        await progress_col().update_one(
            {"user_id": req.user_id},
            {"$set": {
                "topics": topics,
                "total_xp": new_xp,
                "streak": new_streak,
                "longest_streak": max(doc.get("longest_streak", 0), new_streak),
                "total_sessions": doc.get("total_sessions", 0) + 1,
                "total_time_minutes": doc.get("total_time_minutes", 0) + req.time_spent_minutes,
                "updated_at": now,
            }}
        )
    else:
        new_xp = xp_gain
        new_streak = 1
        await progress_col().insert_one({
            "user_id": req.user_id,
            "topics": [{
                "topic": req.topic,
                "mastery": 35.0 if req.correct else 10.0,
                "attempts": 1,
                "correct": 1 if req.correct else 0,
                "time_spent_minutes": req.time_spent_minutes,
                "last_practiced": now,
            }],
            "total_xp": new_xp,
            "streak": new_streak,
            "longest_streak": new_streak,
            "total_sessions": 1,
            "total_time_minutes": req.time_spent_minutes,
            "updated_at": now,
        })

    # Badge check
    total_sessions_new = doc.get("total_sessions", 0) + 1 if doc else 1
    new_badges = check_badges(new_xp, new_streak, total_sessions_new, user.get("badges", []) if user else [])
    user_update_fields = {"last_active": now, "xp": new_xp, "streak": new_streak}
    if new_badges:
        await users_col().update_one(
            {"user_id": req.user_id},
            {"$set": user_update_fields, "$push": {"badges": {"$each": new_badges}}},
            upsert=True,
        )
    elif user:
        await users_col().update_one(
            {"user_id": req.user_id},
            {"$set": user_update_fields}
        )

    return {
        "success": True,
        "xp_gained": xp_gain,
        "total_xp": new_xp,
        "streak": new_streak,
        "new_badges": new_badges,
        "level": calculate_level(new_xp),
    }
