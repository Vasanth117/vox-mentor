"""
Practice Router
POST /api/practice/generate  — AI generates a challenge
GET  /api/practice/daily/{user_id} — today's daily challenge
POST /api/practice/submit    — submit solution
"""
from fastapi import APIRouter
from pydantic import BaseModel
from models.challenge import PracticeRequest, DailyChallenge
from services.ai_engine import generate_practice, chat_complete
from services.executor import execute_code
from services.learning_engine import (
    award_xp, compute_streak, calculate_level, check_badges,
    update_mastery, XP_TABLE, get_weak_strong_areas
)
from db import challenges_col, progress_col, users_col
from datetime import datetime
from config import SUPPORTED_LANGUAGES
import random

router = APIRouter(prefix="/api/practice", tags=["practice"])


class SubmitRequest(BaseModel):
    user_id: str
    challenge_id: str
    code: str
    language: str = "python"


def _difficulty_from_profile(skill_level: str, total_xp: int) -> str:
    level = (skill_level or "beginner").lower()
    if level in {"advanced", "expert", "pro"} or total_xp >= 2500:
        return "advanced"
    if level in {"intermediate", "mid"} or total_xp >= 900:
        return "intermediate"
    return "beginner"


def _topic_pool_for_difficulty(difficulty: str) -> list[str]:
    if difficulty == "advanced":
        return ["recursion", "trees", "dynamic programming", "graphs", "sorting"]
    if difficulty == "intermediate":
        return ["functions", "arrays", "strings", "recursion", "sorting"]
    return ["variables", "loops", "functions", "arrays", "strings", "recursion"]


def _is_vague_challenge(challenge: dict, topic: str, difficulty: str) -> bool:
    if not isinstance(challenge, dict):
        return True
    description = str(challenge.get("description", "")).strip().lower()
    title = str(challenge.get("title", "")).strip()
    tests = challenge.get("test_cases") or []
    starter = str(challenge.get("starter_code", "")).strip()
    if not title or len(description) < 80 or not starter:
        return True
    generic_phrase = f"write a {difficulty}"
    if generic_phrase in description and topic.lower() in description and len(description) < 140:
        return True
    if not isinstance(tests, list) or len(tests) == 0:
        return True
    return False


def _fallback_challenge(topic: str, language: str, difficulty: str) -> dict:
    topic_key = (topic or "general").strip().lower()

    if topic_key == "recursion":
        return {
            "title": "Count Down Recursively",
            "description": (
                "Write a recursive function `count_down(n)` that returns numbers from n to 1 as a single space-separated string. "
                "If n <= 0, return an empty string. Avoid loops in your solution."
            ),
            "starter_code": (
                "def count_down(n):\n"
                "    # TODO: implement using recursion only\n"
                "    pass\n\n"
                "print(count_down(5))\n"
            ),
            "expected_output": "5 4 3 2 1",
            "test_cases": [
                {"input": "5", "expected_output": "5 4 3 2 1"},
                {"input": "1", "expected_output": "1"},
                {"input": "0", "expected_output": ""},
            ],
            "difficulty": difficulty,
            "topic": topic,
            "language": language,
            "xp_reward": 70 if difficulty != "beginner" else 50,
            "hint": "Think about the base case first, then combine current n with result of n-1.",
        }

    if topic_key == "loops":
        return {
            "title": "Sum of Even Numbers",
            "description": (
                "Given an integer n, compute the sum of all even numbers from 1 to n (inclusive) and print only the final sum. "
                "For example, if n is 10 the even numbers are 2, 4, 6, 8, 10 and the output should be 30."
            ),
            "starter_code": "n = 10\n# TODO\nprint(0)\n",
            "expected_output": "30",
            "test_cases": [
                {"input": "10", "expected_output": "30"},
                {"input": "1", "expected_output": "0"},
            ],
            "difficulty": difficulty,
            "topic": topic,
            "language": language,
            "xp_reward": 45,
            "hint": "Iterate from 1 to n and add only numbers where i % 2 == 0.",
        }

    if topic_key == "arrays":
        return {
            "title": "Second Largest Number",
            "description": (
                "Given a list of unique integers, find and print the second largest value without sorting the entire list if possible. "
                "Your program should handle any list length of 2 or more."
            ),
            "starter_code": "arr = [3, 8, 2, 10, 5]\n# TODO\nprint(0)\n",
            "expected_output": "8",
            "test_cases": [
                {"input": "[3,8,2,10,5]", "expected_output": "8"},
                {"input": "[1,2]", "expected_output": "1"},
            ],
            "difficulty": difficulty,
            "topic": topic,
            "language": language,
            "xp_reward": 55,
            "hint": "Track top two values while scanning the list once.",
        }

    return {
        "title": f"{topic.title()} Practice Challenge",
        "description": f"Solve a {difficulty} {language} challenge on {topic}. Print the expected output exactly.",
        "starter_code": "# Write your solution here\n",
        "expected_output": "",
        "test_cases": [{"input": "sample", "expected_output": "sample_output"}],
        "difficulty": difficulty,
        "topic": topic,
        "language": language,
        "xp_reward": 50,
        "hint": "Break the problem into small steps and test each step with a small example.",
    }


async def _build_ai_feedback(challenge: dict, code: str, run_result: dict, success: bool, language: str) -> str:
    title = challenge.get("title", "Practice Challenge")
    description = challenge.get("description", "")
    expected = challenge.get("expected_output", "")
    stdout = run_result.get("stdout", "")
    stderr = run_result.get("stderr", "")

    if success:
        prompt = f"""You are a concise coding reviewer.
The student's solution is correct. Provide improvement suggestions only.

Challenge: {title}
Description: {description}
Language: {language}
Expected output: {expected}

Code:
```{language}
{code}
```

Program output:
```
{stdout}
```

Return:
1) Two short strengths
2) Two concrete improvements (readability/performance/edge-cases)
3) One tiny refactor suggestion (no full rewrite)
"""
    else:
        prompt = f"""You are a coding tutor.
The student's solution is not correct yet. Give hints only, do NOT give complete solution code.

Challenge: {title}
Description: {description}
Language: {language}
Expected output: {expected}

Student code:
```{language}
{code}
```

stdout:
```
{stdout}
```

stderr:
```
{stderr}
```

Return:
- One diagnosis sentence
- 2 or 3 hints in bullet points
- One next step to try
"""

    try:
        text = await chat_complete(prompt, task="tutor")
        if text and text.strip():
            return text.strip()
    except Exception:
        pass

    if success:
        return "Great job! Your solution works. Next, improve naming clarity, reduce repeated logic, and test one extra edge case."
    return "You're close. Focus on matching the expected output exactly, test one small input first, and trace variable values before the failing step."


@router.post("/generate")
async def generate_challenge(req: PracticeRequest):
    challenge = await generate_practice(req.topic, req.language, req.difficulty)
    # Persist
    doc = {
        "user_id": req.user_id,
        "challenge": challenge,
        "created_at": datetime.utcnow(),
        "completed": False,
    }
    result = await challenges_col().insert_one(doc)
    challenge["_id"] = str(result.inserted_id)
    return challenge


@router.get("/daily/{user_id}")
async def get_daily(user_id: str, language: str = "python"):
    if not language or language == "undefined" or language not in SUPPORTED_LANGUAGES:
        language = "python"

    today = datetime.utcnow().strftime("%Y-%m-%d")
    doc = await challenges_col().find_one({"user_id": user_id, "date": today})

    user = await users_col().find_one({"user_id": user_id})
    prog = await progress_col().find_one({"user_id": user_id})

    skill_level = (user or {}).get("skill_level", "beginner")
    preferred_language = (user or {}).get("preferred_language", "english")
    total_xp = (prog or {}).get("total_xp", (user or {}).get("xp", 0))
    difficulty = _difficulty_from_profile(skill_level, total_xp)

    weak_areas = []
    if prog and isinstance(prog.get("topics"), list):
        weak_areas = get_weak_strong_areas(prog.get("topics", [])).get("weak", [])

    pool = _topic_pool_for_difficulty(difficulty)
    candidate_topics = weak_areas + [t for t in pool if t not in weak_areas]
    topic = random.choice(candidate_topics[:5] or pool)

    if doc:
        existing = doc.get("challenge", {})
        existing_topic = existing.get("topic", topic)
        existing_diff = existing.get("difficulty", difficulty)
        if _is_vague_challenge(existing, existing_topic, existing_diff):
            refreshed = await generate_practice(existing_topic, language, existing_diff, preferred_language)
            if _is_vague_challenge(refreshed, existing_topic, existing_diff):
                refreshed = _fallback_challenge(existing_topic, language, existing_diff)
            await challenges_col().update_one({"_id": doc["_id"]}, {"$set": {"challenge": refreshed}})
            doc["challenge"] = refreshed
        doc["_id"] = str(doc["_id"])
        return doc

    challenge = await generate_practice(topic, language, difficulty, preferred_language)
    if _is_vague_challenge(challenge, topic, difficulty):
        challenge = _fallback_challenge(topic, language, difficulty)

    new_doc = {
        "user_id": user_id,
        "date": today,
        "challenge": challenge,
        "completed": False,
        "created_at": datetime.utcnow(),
    }
    result = await challenges_col().insert_one(new_doc)
    new_doc["_id"] = str(result.inserted_id)
    return new_doc


@router.post("/submit")
async def submit_solution(req: SubmitRequest):
    from bson import ObjectId
    doc = await challenges_col().find_one({"_id": ObjectId(req.challenge_id)})
    if not doc:
        return {"success": False, "error": "Challenge not found"}

    # Run the code
    run_result = execute_code(req.code, req.language)

    # Basic pass check: if test cases exist, validate output
    challenge = doc.get("challenge", {})
    test_results = []
    passed = run_result["success"]

    if challenge.get("expected_output") and run_result["stdout"]:
        expected = challenge["expected_output"].strip()
        actual = run_result["stdout"].strip()
        passed = expected == actual
        test_results.append({
            "input": "sample",
            "expected": expected,
            "actual": actual,
            "passed": passed,
        })

    ai_feedback = await _build_ai_feedback(challenge, req.code, run_result, passed, req.language)

    if passed:
        await challenges_col().update_one(
            {"_id": ObjectId(req.challenge_id)},
            {"$set": {"completed": True, "submitted_code": req.code}}
        )

        # ── Award XP ──────────────────────────────────────────────────────────
        now = datetime.utcnow()
        is_daily = bool(doc.get("date"))  # daily challenges have a date field
        base_xp = XP_TABLE["daily_challenge"] if is_daily else challenge.get("xp_reward", 50)
        topic = challenge.get("topic", "general")

        # Pull current progress & user docs
        prog = await progress_col().find_one({"user_id": req.user_id})
        user = await users_col().find_one({"user_id": req.user_id})

        current_streak = prog.get("streak", 0) if prog else (user.get("streak", 0) if user else 0)
        xp_gain = award_xp(base_xp, current_streak)

        if prog:
            topics = prog.get("topics", [])
            topic_doc = next((t for t in topics if t["topic"] == topic), None)
            if topic_doc:
                topic_doc["attempts"] = topic_doc.get("attempts", 0) + 1
                topic_doc["correct"] = topic_doc.get("correct", 0) + 1
                topic_doc["mastery"] = update_mastery(topic_doc.get("mastery", 0.0), True, topic_doc["attempts"])
                topic_doc["last_practiced"] = now
            else:
                topics.append({
                    "topic": topic, "mastery": 60.0, "attempts": 1,
                    "correct": 1, "time_spent_minutes": 0.0, "last_practiced": now,
                })

            streak_result = compute_streak(prog.get("updated_at"), prog.get("streak", 0))
            new_xp = prog.get("total_xp", 0) + xp_gain
            new_streak = streak_result["streak"]
            new_sessions = prog.get("total_sessions", 0) + 1

            await progress_col().update_one(
                {"user_id": req.user_id},
                {"$set": {
                    "topics": topics,
                    "total_xp": new_xp,
                    "streak": new_streak,
                    "longest_streak": max(prog.get("longest_streak", 0), new_streak),
                    "total_sessions": new_sessions,
                    "updated_at": now,
                }}
            )
        else:
            new_xp = xp_gain
            new_streak = 1
            new_sessions = 1
            await progress_col().insert_one({
                "user_id": req.user_id,
                "topics": [{"topic": topic, "mastery": 60.0, "attempts": 1, "correct": 1,
                             "time_spent_minutes": 0.0, "last_practiced": now}],
                "total_xp": new_xp, "streak": new_streak, "longest_streak": new_streak,
                "total_sessions": new_sessions, "total_time_minutes": 0.0, "updated_at": now,
            })

        # Check & award new badges
        existing_badges = user.get("badges", []) if user else []
        new_badges = check_badges(new_xp, new_streak, new_sessions, existing_badges)

        update_fields = {"xp": new_xp, "streak": new_streak, "last_active": now}
        if new_badges:
            await users_col().update_one(
                {"user_id": req.user_id},
                {"$set": update_fields, "$push": {"badges": {"$each": new_badges}}}
            )
        else:
            await users_col().update_one({"user_id": req.user_id}, {"$set": update_fields})

        return {
            "success": True,
            "run_result": run_result,
            "test_results": test_results,
            "ai_feedback": ai_feedback,
            "feedback_mode": "improvements",
            "xp_reward": xp_gain,
            "total_xp": new_xp,
            "streak": new_streak,
            "new_badges": new_badges,
            "level": calculate_level(new_xp),
            "is_daily": is_daily,
        }

    return {
        "success": False,
        "run_result": run_result,
        "test_results": test_results,
        "ai_feedback": ai_feedback,
        "feedback_mode": "hint_only",
        "xp_reward": 0,
    }
