"""
Learning+ Router
Implements:
- Adaptive Learning Path 2.0
- Goal-Based Roadmaps
- Project-Based Learning (rubric + AI review)
- Mock Interviews (timed + hint penalty)
- Spaced Repetition queue
- Progress Forecasting
"""
from datetime import datetime, timedelta
from typing import Any
from bson import ObjectId
from fastapi import APIRouter
from pydantic import BaseModel, Field

from db import (
    progress_col,
    users_col,
    challenges_col,
    roadmaps_col,
    projects_col,
    interviews_col,
    revision_queue_col,
)
from services.ai_engine import chat_complete
from services.learning_engine import calculate_level

router = APIRouter(prefix="/api/learning-plus", tags=["learning-plus"])


GOAL_TEMPLATES = {
    "crack interviews": [
        ["Arrays & Strings refresh", "Two-pointer and sliding window", "Practice 6 medium problems"],
        ["Hashing + Prefix sums", "Sorting patterns", "Mock interview round 1"],
        ["Trees + Graph traversal", "Dynamic Programming basics", "Timed problem set"],
        ["Systematic revision", "Mock interview round 2", "Behavioral + communication prep"],
    ],
    "web dev": [
        ["HTML/CSS fundamentals", "Responsive layout", "Build landing page"],
        ["JavaScript DOM + events", "Async and fetch", "Mini API client app"],
        ["React state + routing", "Component design", "Build dashboard"],
        ["Backend API integration", "Auth flow basics", "Deploy and polish"],
    ],
    "dsa in 30 days": [
        ["Arrays + Strings", "Recursion basics", "Daily 2 easy problems"],
        ["Linked List + Stack/Queue", "Binary search", "Timed drills"],
        ["Trees + Graphs", "Greedy + two pointers", "Mock round"],
        ["Dynamic Programming intro", "Mixed revision", "Final mock interview"],
    ],
}


class AdaptivePathRequest(BaseModel):
    user_id: str
    skill_id: str = "python_fundamentals"


class RoadmapRequest(BaseModel):
    user_id: str
    goal: str


class ProjectStartRequest(BaseModel):
    user_id: str
    goal: str = "general"
    language: str = "python"


class ProjectReviewRequest(BaseModel):
    user_id: str
    project_id: str
    code: str
    notes: str = ""


class InterviewStartRequest(BaseModel):
    user_id: str
    difficulty: str = "intermediate"
    language: str = "python"
    duration_minutes: int = Field(default=30, ge=15, le=90)


class InterviewHintRequest(BaseModel):
    user_id: str
    interview_id: str
    question_index: int = 0


class InterviewSubmitRequest(BaseModel):
    user_id: str
    interview_id: str
    answers: list[str]


async def _safe_chat(prompt: str, task: str = "tutor", default: str = "") -> str:
    try:
        text = await chat_complete(prompt, task=task)
        if isinstance(text, str) and text.strip():
            return text.strip()
    except Exception:
        pass
    return default


def _estimate_speed_bucket(topic: dict) -> str:
    attempts = max(1, int(topic.get("attempts", 1)))
    minutes = float(topic.get("time_spent_minutes", 0.0))
    avg = minutes / attempts
    if avg <= 3:
        return "fast"
    if avg <= 8:
        return "balanced"
    return "slow"


@router.post("/adaptive-path")
async def adaptive_path(req: AdaptivePathRequest):
    prog = await progress_col().find_one({"user_id": req.user_id})
    topics = (prog or {}).get("topics", [])

    if not topics:
        ordered = [
            {"topic": "variables", "priority": 1, "recommended_difficulty": "beginner", "reason": "Foundational start"},
            {"topic": "operators", "priority": 2, "recommended_difficulty": "beginner", "reason": "Core expression fluency"},
            {"topic": "conditionals", "priority": 3, "recommended_difficulty": "beginner", "reason": "Control flow basics"},
            {"topic": "loops", "priority": 4, "recommended_difficulty": "beginner", "reason": "Iteration practice"},
        ]
        return {"user_id": req.user_id, "skill_id": req.skill_id, "path": ordered, "strategy": "bootstrapped"}

    ranked = []
    for topic in topics:
        attempts = int(topic.get("attempts", 0))
        correct = int(topic.get("correct", 0))
        mastery = float(topic.get("mastery", 0.0))
        accuracy = (correct / attempts) * 100 if attempts > 0 else 0.0
        speed_bucket = _estimate_speed_bucket(topic)

        mistake_pressure = max(0.0, 100.0 - accuracy)
        confidence_penalty = 20.0 if attempts < 3 else 0.0
        speed_penalty = 15.0 if speed_bucket == "slow" else 0.0
        priority_score = (mistake_pressure * 0.5) + ((100 - mastery) * 0.35) + confidence_penalty + speed_penalty

        if priority_score >= 65:
            diff = "beginner"
        elif priority_score >= 40:
            diff = "intermediate"
        else:
            diff = "advanced"

        ranked.append({
            "topic": topic.get("topic", "general"),
            "priority_score": round(priority_score, 1),
            "recommended_difficulty": diff,
            "speed_bucket": speed_bucket,
            "attempts": attempts,
            "accuracy_pct": round(accuracy, 1),
            "mastery": round(mastery, 1),
        })

    ranked.sort(key=lambda x: x["priority_score"], reverse=True)
    path = []
    for idx, item in enumerate(ranked[:8]):
        reason = "High mistakes" if item["accuracy_pct"] < 60 else "Needs reinforcement"
        if item["speed_bucket"] == "slow":
            reason += " + slow solving speed"
        path.append({
            "topic": item["topic"],
            "priority": idx + 1,
            "recommended_difficulty": item["recommended_difficulty"],
            "reason": reason,
            "metrics": {
                "accuracy_pct": item["accuracy_pct"],
                "attempts": item["attempts"],
                "speed_bucket": item["speed_bucket"],
                "mastery": item["mastery"],
            },
        })

    return {
        "user_id": req.user_id,
        "skill_id": req.skill_id,
        "strategy": "mistakes_speed_mastery",
        "path": path,
        "updated_at": datetime.utcnow(),
    }


@router.post("/roadmap")
async def build_goal_roadmap(req: RoadmapRequest):
    goal_key = (req.goal or "").strip().lower()
    template = GOAL_TEMPLATES.get(goal_key, GOAL_TEMPLATES["crack interviews"])

    weekly = []
    for idx, milestones in enumerate(template, start=1):
        weekly.append({"week": idx, "milestones": milestones, "status": "pending"})

    payload = {
        "user_id": req.user_id,
        "goal": req.goal,
        "weeks": weekly,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    await roadmaps_col().update_one(
        {"user_id": req.user_id, "goal": req.goal},
        {"$set": payload},
        upsert=True,
    )

    return {"success": True, **payload}


@router.get("/roadmap/{user_id}")
async def get_roadmaps(user_id: str):
    cursor = roadmaps_col().find({"user_id": user_id}).sort("updated_at", -1)
    data = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        data.append(doc)
    return {"roadmaps": data, "count": len(data)}


@router.post("/projects/start")
async def start_project(req: ProjectStartRequest):
    base_spec = {
        "title": f"Mini Project: {req.goal.title()}",
        "brief": f"Build a practical {req.language} mini project aligned with goal '{req.goal}'.",
        "rubric": [
            {"criterion": "Correctness", "weight": 40},
            {"criterion": "Code quality", "weight": 25},
            {"criterion": "Edge-case handling", "weight": 20},
            {"criterion": "Readability", "weight": 15},
        ],
        "deliverables": ["Working code", "Short README", "Sample input/output"],
    }

    prompt = f"""Create a concise mini project spec for:
Goal: {req.goal}
Language: {req.language}
Return markdown with sections: Title, Problem, Requirements, Bonus.
"""
    ai_spec = await _safe_chat(prompt, task="tutor", default="")
    project_doc = {
        "user_id": req.user_id,
        "goal": req.goal,
        "language": req.language,
        "spec": ai_spec or base_spec,
        "rubric": base_spec["rubric"],
        "status": "in_progress",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await projects_col().insert_one(project_doc)
    project_doc["_id"] = str(result.inserted_id)
    return project_doc


@router.post("/projects/review")
async def review_project(req: ProjectReviewRequest):
    project = await projects_col().find_one({"_id": ObjectId(req.project_id), "user_id": req.user_id})
    if not project:
        return {"success": False, "error": "Project not found"}

    prompt = f"""You are a strict but supportive code reviewer.
Rubric weights: Correctness 40, Code quality 25, Edge-case handling 20, Readability 15.
Assess the submission and return valid JSON:
{{
  "scores": {{"correctness":0-40,"code_quality":0-25,"edge_cases":0-20,"readability":0-15}},
  "total": 0-100,
  "strengths": ["..."],
  "improvements": ["..."],
  "next_step": "..."
}}

Notes: {req.notes}
Code:
```{project.get('language','python')}
{req.code}
```
"""

    review_text = await _safe_chat(prompt, task="code", default="")
    try:
        import json
        parsed = json.loads(review_text)
    except Exception:
        parsed = {
            "scores": {"correctness": 25, "code_quality": 16, "edge_cases": 10, "readability": 10},
            "total": 61,
            "strengths": ["Functional structure"],
            "improvements": ["Add edge-case tests", "Refactor repeated logic"],
            "next_step": "Add tests for invalid inputs and simplify helper functions.",
        }

    await projects_col().update_one(
        {"_id": ObjectId(req.project_id)},
        {
            "$set": {
                "review": parsed,
                "last_submission": req.code,
                "status": "reviewed",
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return {"success": True, "project_id": req.project_id, "review": parsed}


@router.post("/interview/start")
async def start_interview(req: InterviewStartRequest):
    prompt = f"""Generate 3 coding interview questions for {req.language} at {req.difficulty} level.
Return valid JSON only:
{{"questions":[{{"title":"...","prompt":"...","expected_focus":"..."}}]}}
"""
    text = await _safe_chat(prompt, task="tutor", default="")
    try:
        import json
        payload = json.loads(text)
        questions = payload.get("questions", [])[:3]
    except Exception:
        questions = [
            {"title": "Array Pair Sum", "prompt": "Find two numbers summing to target.", "expected_focus": "hash map"},
            {"title": "Valid Parentheses", "prompt": "Check if brackets are balanced.", "expected_focus": "stack"},
            {"title": "Merge Intervals", "prompt": "Merge overlapping intervals.", "expected_focus": "sorting + scan"},
        ]

    doc = {
        "user_id": req.user_id,
        "difficulty": req.difficulty,
        "language": req.language,
        "duration_minutes": req.duration_minutes,
        "questions": questions,
        "hints_used": 0,
        "hint_penalty": 0,
        "started_at": datetime.utcnow(),
        "ends_at": datetime.utcnow() + timedelta(minutes=req.duration_minutes),
        "status": "active",
    }
    result = await interviews_col().insert_one(doc)
    return {
        "success": True,
        "interview_id": str(result.inserted_id),
        "questions": questions,
        "duration_minutes": req.duration_minutes,
    }


@router.post("/interview/hint")
async def interview_hint(req: InterviewHintRequest):
    interview = await interviews_col().find_one({"_id": ObjectId(req.interview_id), "user_id": req.user_id})
    if not interview:
        return {"success": False, "error": "Interview not found"}

    questions = interview.get("questions", [])
    if req.question_index < 0 or req.question_index >= len(questions):
        return {"success": False, "error": "Invalid question index"}

    question = questions[req.question_index]
    hint_prompt = f"Give one concise interview hint (not solution) for: {question.get('prompt', '')}"
    hint = await _safe_chat(hint_prompt, task="tutor", default="Break into smaller steps and test a tiny case first.")

    hints_used = int(interview.get("hints_used", 0)) + 1
    penalty = min(30, hints_used * 5)

    await interviews_col().update_one(
        {"_id": ObjectId(req.interview_id)},
        {"$set": {"hints_used": hints_used, "hint_penalty": penalty}},
    )

    return {"success": True, "hint": hint, "hints_used": hints_used, "hint_penalty": penalty}


@router.post("/interview/submit")
async def interview_submit(req: InterviewSubmitRequest):
    interview = await interviews_col().find_one({"_id": ObjectId(req.interview_id), "user_id": req.user_id})
    if not interview:
        return {"success": False, "error": "Interview not found"}

    questions = interview.get("questions", [])
    answers = req.answers or []
    answered = sum(1 for a in answers if isinstance(a, str) and a.strip())
    completion_score = min(100, int((answered / max(1, len(questions))) * 100))
    hint_penalty = int(interview.get("hint_penalty", 0))
    final_score = max(0, completion_score - hint_penalty)

    feedback_prompt = f"""Give concise post-interview feedback.
Questions: {questions}
Answers count: {answered}/{len(questions)}
Hint penalty: {hint_penalty}
Final score: {final_score}
Return 3 strengths and 3 improvements in markdown bullets.
"""
    feedback = await _safe_chat(feedback_prompt, task="tutor", default="- Strength: Attempted all major parts\n- Improve: Add edge-case handling and complexity explanation")

    await interviews_col().update_one(
        {"_id": ObjectId(req.interview_id)},
        {
            "$set": {
                "answers": answers,
                "completion_score": completion_score,
                "final_score": final_score,
                "feedback": feedback,
                "status": "completed",
                "submitted_at": datetime.utcnow(),
            }
        },
    )

    return {
        "success": True,
        "completion_score": completion_score,
        "hint_penalty": hint_penalty,
        "final_score": final_score,
        "feedback": feedback,
    }


@router.get("/spaced-revision/{user_id}")
async def spaced_revision(user_id: str):
    prog = await progress_col().find_one({"user_id": user_id})
    topics = (prog or {}).get("topics", [])
    now = datetime.utcnow()

    queue = []
    for topic in topics:
        tname = topic.get("topic", "general")
        mastery = float(topic.get("mastery", 0.0))
        attempts = int(topic.get("attempts", 0))
        correct = int(topic.get("correct", 0))
        acc = (correct / attempts) * 100 if attempts > 0 else 0.0
        last = topic.get("last_practiced")
        days_since = 999
        if isinstance(last, datetime):
            days_since = (now.date() - last.date()).days

        priority = (100 - mastery) * 0.45 + (100 - acc) * 0.35 + min(30, max(0, days_since) * 2)
        if mastery < 70 or days_since >= 4:
            queue.append({
                "topic": tname,
                "priority": round(priority, 1),
                "days_since": days_since,
                "mastery": round(mastery, 1),
                "accuracy_pct": round(acc, 1),
            })

    queue.sort(key=lambda x: x["priority"], reverse=True)
    queue = queue[:10]

    await revision_queue_col().update_one(
        {"user_id": user_id},
        {"$set": {"queue": queue, "updated_at": now}},
        upsert=True,
    )

    return {"user_id": user_id, "queue": queue, "count": len(queue), "generated_at": now}


@router.get("/forecast/{user_id}")
async def forecast_progress(user_id: str):
    prog = await progress_col().find_one({"user_id": user_id})
    if not prog:
        return {
            "user_id": user_id,
            "message": "Not enough data. Complete a few practice sessions first.",
            "days_to_next_level": None,
            "nudge": "Start with 1-2 short sessions daily to establish momentum.",
        }

    xp = int(prog.get("total_xp", 0))
    sessions = max(1, int(prog.get("total_sessions", 1)))
    streak = int(prog.get("streak", 0))
    level = calculate_level(xp)

    next_threshold = int(level.get("next_threshold", xp))
    xp_to_next = max(0, next_threshold - xp)
    avg_xp_per_session = max(10.0, xp / sessions)
    sessions_needed = xp_to_next / avg_xp_per_session if xp_to_next > 0 else 0.0
    days_to_next = int(round(max(0.0, sessions_needed / 1.0)))

    nudge = "Keep consistency: one focused session daily beats long irregular sessions."
    if streak < 3:
        nudge = "Build a 3-day streak first; consistency will accelerate level growth."
    elif days_to_next <= 3:
        nudge = "You are close to the next level—do one revision + one challenge each day."

    return {
        "user_id": user_id,
        "current_xp": xp,
        "current_level": level,
        "xp_to_next_level": xp_to_next,
        "avg_xp_per_session": round(avg_xp_per_session, 1),
        "estimated_sessions_needed": round(sessions_needed, 1),
        "days_to_next_level": days_to_next,
        "consistency_streak": streak,
        "nudge": nudge,
    }
