"""
Learning Engine — handles XP calculation, streaks, skill tree unlocking,
learning style analysis, and personalized suggestions.
"""
from datetime import datetime, timedelta
from typing import Optional
from models.skill_tree import SKILL_TREE_NODES


# ── XP & Levels ──────────────────────────────────────────────────────────────

XP_TABLE = {
    "correct_answer": 50,
    "session_complete": 20,
    "daily_challenge": 100,
    "streak_bonus_factor": 1.5,   # multiplier for streak > 7
}

LEVEL_THRESHOLDS = [0, 100, 250, 500, 1000, 1750, 2750, 4000, 5500, 7500, 10000]
LEVEL_NAMES = ["Novice", "Apprentice", "Learner", "Coder", "Developer",
               "Engineer", "Architect", "Expert", "Master", "Grandmaster", "Legend"]


def calculate_level(xp: int) -> dict:
    level = 0
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            level = i
    next_threshold = LEVEL_THRESHOLDS[level + 1] if level + 1 < len(LEVEL_THRESHOLDS) else LEVEL_THRESHOLDS[-1]
    current_threshold = LEVEL_THRESHOLDS[level]
    progress = ((xp - current_threshold) / (next_threshold - current_threshold)) * 100 if next_threshold != current_threshold else 100
    return {
        "level": level,
        "level_name": LEVEL_NAMES[level],
        "xp": xp,
        "next_threshold": next_threshold,
        "progress_pct": round(progress, 1),
    }


def award_xp(base_xp: int, streak: int) -> int:
    multiplier = XP_TABLE["streak_bonus_factor"] if streak >= 7 else 1.0
    return int(base_xp * multiplier)


# ── Streak Management ─────────────────────────────────────────────────────────

def compute_streak(last_active: Optional[datetime], current_streak: int) -> dict:
    now = datetime.utcnow().date()
    if last_active is None:
        return {"streak": 1, "maintained": True, "broken": False}

    last_date = last_active.date()
    delta = (now - last_date).days

    if delta == 0:
        return {"streak": current_streak, "maintained": True, "broken": False}
    elif delta == 1:
        return {"streak": current_streak + 1, "maintained": True, "broken": False}
    else:
        return {"streak": 1, "maintained": False, "broken": True}


# ── Skill Tree Logic ──────────────────────────────────────────────────────────

_NODE_MAP = {n["node_id"]: n for n in SKILL_TREE_NODES}


def get_available_nodes(unlocked: list[str], completed: list[str], total_xp: int) -> list[str]:
    """Return node_ids that can be unlocked by the student right now."""
    available = []
    for node in SKILL_TREE_NODES:
        nid = node["node_id"]
        if nid in unlocked or nid in completed:
            continue
        prereqs_met = all(p in unlocked or p in completed for p in node["prerequisites"])
        xp_met = total_xp >= node["xp_required"]
        if prereqs_met and xp_met:
            available.append(nid)
    return available


def evaluate_unlock(node_id: str, unlocked: list[str], completed: list[str], total_xp: int) -> dict:
    node = _NODE_MAP.get(node_id)
    if not node:
        return {"can_unlock": False, "reason": "Node not found"}
    if node_id in unlocked or node_id in completed:
        return {"can_unlock": False, "reason": "Already unlocked"}

    missing_prereqs = [p for p in node["prerequisites"] if p not in unlocked and p not in completed]
    if missing_prereqs:
        return {
            "can_unlock": False,
            "reason": f"Complete {', '.join(missing_prereqs)} first",
            "missing_prerequisites": missing_prereqs,
        }
    if total_xp < node["xp_required"]:
        return {
            "can_unlock": False,
            "reason": f"Need {node['xp_required']} XP (you have {total_xp})",
            "xp_needed": node["xp_required"] - total_xp,
        }
    return {"can_unlock": True, "node": node}


# ── Learning Style Analyzer ───────────────────────────────────────────────────

def analyze_learning_style(sessions_count: int, avg_time_per_problem: float,
                            hint_usage_rate: float, retry_rate: float) -> dict:
    """
    Classify student into one of three teaching styles based on behavior metrics.
    guided: asks for hints often, retries a lot → needs step-by-step
    independent: fast, low hints → prefers concise explanations
    balanced: middle ground
    """
    style = "balanced"
    if hint_usage_rate > 0.6 or retry_rate > 0.7:
        style = "guided"
    elif hint_usage_rate < 0.2 and retry_rate < 0.3 and avg_time_per_problem < 5:
        style = "independent"

    descriptions = {
        "guided": "You learn best with step-by-step explanations and examples. The tutor will go into more detail for you.",
        "independent": "You learn quickly and prefer concise explanations. The tutor will keep things brief and challenge-focused.",
        "balanced": "You have a balanced learning approach. The tutor will adapt based on each topic.",
    }

    return {"style": style, "description": descriptions[style]}


# ── Badge System ──────────────────────────────────────────────────────────────

BADGES = {
    "first_session": {"name": "First Steps 👶", "description": "Completed your first session"},
    "streak_3":      {"name": "3-Day Flame 🔥",  "description": "3-day learning streak"},
    "streak_7":      {"name": "Week Warrior ⚔️",  "description": "7-day learning streak"},
    "streak_30":     {"name": "Monthly Master 🏆","description": "30-day learning streak"},
    "xp_500":        {"name": "XP Hunter 💎",     "description": "Earned 500 XP"},
    "xp_1000":       {"name": "XP Champion 🥇",   "description": "Earned 1000 XP"},
    "debugger":      {"name": "Bug Slayer 🐛",     "description": "Successfully debugged 5 programs"},
    "speed_coder":   {"name": "Speed Coder ⚡",    "description": "Solved a challenge in under 2 minutes"},
}


def check_badges(xp: int, streak: int, sessions: int, existing_badges: list[str]) -> list[str]:
    """Return list of newly earned badge IDs."""
    new_badges = []
    checks = {
        "first_session": sessions >= 1,
        "streak_3":      streak >= 3,
        "streak_7":      streak >= 7,
        "streak_30":     streak >= 30,
        "xp_500":        xp >= 500,
        "xp_1000":       xp >= 1000,
    }
    for badge_id, condition in checks.items():
        if condition and badge_id not in existing_badges:
            new_badges.append(badge_id)
    return new_badges


def get_badge_display_names(badge_ids: list[str]) -> list[str]:
    """Convert badge IDs to human-readable display names."""
    return [BADGES[b]["name"] for b in badge_ids if b in BADGES]


# ── Topic Mastery ─────────────────────────────────────────────────────────────

def update_mastery(current_mastery: float, correct: bool, attempts: int) -> float:
    """Simple Elo-like mastery update."""
    k = max(5, 20 - attempts)   # learning rate decreases with experience
    if correct:
        delta = k * (1 - current_mastery / 100)
    else:
        delta = -k * (current_mastery / 100)
    return max(0.0, min(100.0, current_mastery + delta))


def get_weak_strong_areas(topics: list[dict]) -> dict:
    graded = [(t["topic"], t["mastery"]) for t in topics if t["attempts"] > 0]
    graded.sort(key=lambda x: x[1])
    weak = [t for t, m in graded if m < 50][:3]
    strong = [t for t, m in graded if m >= 80][:3]
    return {"weak": weak, "strong": strong}


def suggest_next_topics(completed: list[str], current_xp: int, weak_areas: list[str]) -> list[str]:
    """Prioritize weak areas, then available skill tree nodes."""
    suggestions = list(weak_areas)
    available = get_available_nodes(completed, [], current_xp)
    for nid in available:
        node = _NODE_MAP.get(nid, {})
        if node.get("title") and node["title"] not in suggestions:
            suggestions.append(node["title"])
        if len(suggestions) >= 5:
            break
    return suggestions[:5]
