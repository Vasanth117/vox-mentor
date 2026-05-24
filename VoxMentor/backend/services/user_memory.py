import re
from datetime import datetime

from db import users_col, progress_col
from services.learning_engine import update_mastery, get_weak_strong_areas

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "variables": ["variable", "variables"],
    "data_types": ["data type", "datatype", "types"],
    "arrays": ["array", "arrays", "list", "lists"],
    "strings": ["string", "strings"],
    "loops": ["loop", "loops", "for loop", "while loop"],
    "functions": ["function", "functions", "method", "methods"],
    "recursion": ["recursion", "recursive"],
    "sorting": ["sort", "sorting", "bubble sort", "merge sort", "quick sort"],
    "searching": ["search", "searching", "binary search", "linear search"],
    "linked_lists": ["linked list", "linked lists"],
    "stacks": ["stack", "stacks"],
    "queues": ["queue", "queues"],
    "trees": ["tree", "trees", "binary tree"],
    "graphs": ["graph", "graphs", "bfs", "dfs"],
    "dynamic_programming": ["dynamic programming", "dp"],
    "python": ["python"],
    "javascript": ["javascript", "js"],
    "c": ["language c", " c ", "c language"],
    "cpp": ["c++", "cpp"],
}

_POSITIVE_LEARNING = [
    "i understand",
    "i got it",
    "got it",
    "that makes sense",
    "i learned",
    "now i know",
    "i can do it",
    "im confident",
    "i'm confident",
]

_NEGATIVE_LEARNING = [
    "i don't understand",
    "i dont understand",
    "i am confused",
    "i'm confused",
    "confused",
    "i am stuck",
    "i'm stuck",
    "struggling",
    "this is hard",
    "not clear",
]


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _extract_name(text: str) -> str | None:
    patterns = [
        r"\bmy name is\s+([a-z][a-z\s'\-]{1,40})",
        r"\bcall me\s+([a-z][a-z\s'\-]{1,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = match.group(1).strip(" .,!?")
        if len(candidate.split()) <= 4:
            return " ".join(w.capitalize() for w in candidate.split())
    return None


def _extract_skill_level(text: str) -> str | None:
    t = _normalize(text)
    if "beginner" in t:
        return "beginner"
    if "intermediate" in t:
        return "intermediate"
    if "advanced" in t or "expert" in t:
        return "advanced"
    return None


def _extract_career_goal(text: str) -> str | None:
    patterns = [
        r"\bmy goal is to\s+(.+)$",
        r"\bi want to become\s+(.+)$",
        r"\bi want to be\s+(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            goal = match.group(1).strip(" .,!?")
            if 3 <= len(goal) <= 120:
                return goal
    return None


def _extract_preferred_language(text: str) -> str | None:
    t = _normalize(text)
    for lang in ("english", "hindi", "tamil", "telugu", "kannada", "malayalam"):
        if f"respond in {lang}" in t or f"speak in {lang}" in t or f"{lang} please" in t:
            return lang
    return None


def _extract_teaching_style(text: str) -> str | None:
    t = _normalize(text)
    if any(phrase in t for phrase in ["step by step", "explain slowly", "more detailed"]):
        return "guided"
    if any(phrase in t for phrase in ["be concise", "short answer", "brief answer"]):
        return "independent"
    return None


def _infer_mood(text: str) -> str | None:
    t = _normalize(text)
    if any(x in t for x in ["frustrated", "stressed", "overwhelmed", "struggling"]):
        return "struggling"
    if any(x in t for x in ["confused", "not clear", "don't understand", "dont understand"]):
        return "confused"
    if any(x in t for x in ["confident", "got it", "understand now", "makes sense"]):
        return "confident"
    return None


def _extract_topics(text: str) -> list[str]:
    t = f" {_normalize(text)} "
    topics: list[str] = []
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(f" {kw} " in t for kw in keywords):
            topics.append(topic)
    return topics


def _infer_learning_signal(text: str) -> str:
    t = _normalize(text)
    if any(phrase in t for phrase in _POSITIVE_LEARNING):
        return "positive"
    if any(phrase in t for phrase in _NEGATIVE_LEARNING):
        return "negative"
    return "neutral"


async def update_user_memory(user_id: str, user_message: str) -> None:
    """Persist long-term conversational memory from chat into user/profile/progress docs."""
    now = datetime.utcnow()
    text = user_message or ""

    set_fields: dict = {"last_active": now}
    add_set_fields: dict = {}

    name = _extract_name(text)
    if name:
        set_fields["name"] = name
        add_set_fields.setdefault("memory_facts", []).append(f"name:{name}")

    skill_level = _extract_skill_level(text)
    if skill_level:
        set_fields["skill_level"] = skill_level
        add_set_fields.setdefault("memory_facts", []).append(f"skill_level:{skill_level}")

    goal = _extract_career_goal(text)
    if goal:
        set_fields["career_goal"] = goal
        add_set_fields.setdefault("memory_facts", []).append(f"career_goal:{goal}")

    pref_lang = _extract_preferred_language(text)
    if pref_lang:
        set_fields["preferred_language"] = pref_lang
        add_set_fields.setdefault("memory_facts", []).append(f"preferred_language:{pref_lang}")

    style = _extract_teaching_style(text)
    if style:
        set_fields["teaching_style"] = style

    mood = _infer_mood(text)
    if mood:
        set_fields["last_mood"] = mood

    update_doc: dict = {"$set": set_fields}
    if add_set_fields:
        update_doc["$addToSet"] = {k: {"$each": v} for k, v in add_set_fields.items()}
    await users_col().update_one({"user_id": user_id}, update_doc, upsert=True)

    topics = _extract_topics(text)
    signal = _infer_learning_signal(text)
    if not topics and signal == "neutral":
        return

    prog = await progress_col().find_one({"user_id": user_id})
    if prog:
        topic_docs = prog.get("topics", [])
        for topic in topics:
            topic_doc = next((t for t in topic_docs if t.get("topic") == topic), None)
            if topic_doc is None:
                base_mastery = 55.0 if signal == "positive" else 35.0 if signal == "negative" else 45.0
                topic_docs.append({
                    "topic": topic,
                    "mastery": base_mastery,
                    "attempts": 1,
                    "correct": 1 if signal == "positive" else 0,
                    "time_spent_minutes": 0.0,
                    "last_practiced": now,
                })
                continue

            attempts = topic_doc.get("attempts", 0) + 1
            topic_doc["attempts"] = attempts
            if signal == "positive":
                topic_doc["correct"] = topic_doc.get("correct", 0) + 1
                topic_doc["mastery"] = update_mastery(topic_doc.get("mastery", 0.0), True, attempts)
            elif signal == "negative":
                topic_doc["mastery"] = update_mastery(topic_doc.get("mastery", 0.0), False, attempts)
            topic_doc["last_practiced"] = now

        areas = get_weak_strong_areas(topic_docs)
        await progress_col().update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "topics": topic_docs,
                    "weak_areas": areas["weak"],
                    "strong_areas": areas["strong"],
                    "updated_at": now,
                }
            },
            upsert=True,
        )
    else:
        topic_docs = []
        for topic in topics:
            topic_docs.append({
                "topic": topic,
                "mastery": 55.0 if signal == "positive" else 35.0 if signal == "negative" else 45.0,
                "attempts": 1,
                "correct": 1 if signal == "positive" else 0,
                "time_spent_minutes": 0.0,
                "last_practiced": now,
            })

        areas = get_weak_strong_areas(topic_docs)
        await progress_col().insert_one({
            "user_id": user_id,
            "topics": topic_docs,
            "total_xp": 0,
            "streak": 0,
            "longest_streak": 0,
            "total_sessions": 0,
            "total_time_minutes": 0.0,
            "weak_areas": areas["weak"],
            "strong_areas": areas["strong"],
            "updated_at": now,
        })
