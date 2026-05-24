"""
Refactored Skill Tree Router
- Skill-based modules with strict progression
- Dynamic explanations tailored to user profile
- Module-level doubt chatbot
- Module test gates and final skill test
- Unlock next skill only after passing final test
"""
from datetime import datetime
from typing import Any
import random
import asyncio

from fastapi import APIRouter
from pydantic import BaseModel

from db import skill_tree_col, users_col, progress_col
from services.ai_engine import chat_complete
from services.learning_engine import award_xp, calculate_level, check_badges, compute_streak

router = APIRouter(prefix="/api/skill-tree", tags=["skill-tree"])

MODULE_PASS_XP = 60
FINAL_PASS_XP = 180

SKILL_PATH = [
    {
        "skill_id": "python_fundamentals",
        "title": "Python Fundamentals",
        "description": "Core syntax and flow control.",
        "modules": [
            {"module_id": "variables", "title": "Variables & Data Types", "concept": "variables and primitive data types"},
            {"module_id": "operators", "title": "Operators & Expressions", "concept": "operators and expression evaluation"},
            {"module_id": "conditionals", "title": "Conditionals", "concept": "if elif else branching"},
            {"module_id": "loops", "title": "Loops", "concept": "for and while loops"},
            {"module_id": "functions", "title": "Functions", "concept": "function definitions and return values"},
        ],
    },
    {
        "skill_id": "problem_solving",
        "title": "Problem Solving",
        "description": "Structured thinking and decomposition.",
        "modules": [
            {"module_id": "arrays", "title": "Arrays & Lists", "concept": "list operations and traversal"},
            {"module_id": "strings", "title": "Strings", "concept": "string methods and transformations"},
            {"module_id": "recursion", "title": "Recursion", "concept": "base case and recursive step"},
            {"module_id": "complexity", "title": "Complexity Basics", "concept": "big O intuition"},
        ],
    },
    {
        "skill_id": "data_structures",
        "title": "Data Structures",
        "description": "Practical data structure usage.",
        "modules": [
            {"module_id": "linked_list", "title": "Linked List", "concept": "node-based linear structures"},
            {"module_id": "stack_queue", "title": "Stack & Queue", "concept": "LIFO/FIFO behavior"},
            {"module_id": "trees", "title": "Trees", "concept": "hierarchical traversal"},
            {"module_id": "graphs", "title": "Graphs", "concept": "BFS and DFS traversal"},
        ],
    },
]

SKILL_MAP = {s["skill_id"]: s for s in SKILL_PATH}


class ExplainRequest(BaseModel):
    user_id: str
    skill_id: str
    module_id: str


class ModuleChatRequest(BaseModel):
    user_id: str
    skill_id: str
    module_id: str
    message: str


class TestStartRequest(BaseModel):
    user_id: str
    skill_id: str
    module_id: str


class TestSubmitRequest(BaseModel):
    user_id: str
    skill_id: str
    module_id: str
    selected_index: int


class FinalStartRequest(BaseModel):
    user_id: str
    skill_id: str


class FinalSubmitRequest(BaseModel):
    user_id: str
    skill_id: str
    selected_indices: list[int]


class UnlockCompatRequest(BaseModel):
    user_id: str
    node_id: str


def _default_state(user_id: str) -> dict:
    skills_progress = {}
    for i, skill in enumerate(SKILL_PATH):
        modules = {}
        for j, module in enumerate(skill["modules"]):
            modules[module["module_id"]] = {
                "completed": False,
                "test_passed": False,
                "test_attempts": 0,
                "explanation": "",
                "chat_history": [],
                "test": None,
            }
        skills_progress[skill["skill_id"]] = {
            "unlocked": i == 0,
            "completed": False,
            "current_module_index": 0,
            "final_test": None,
            "final_passed": False,
            "modules": modules,
        }

    return {
        "user_id": user_id,
        "skills_progress": skills_progress,
        "updated_at": datetime.utcnow(),
    }


async def _get_or_create_state(user_id: str) -> dict:
    doc = await skill_tree_col().find_one({"user_id": user_id})
    if not doc or not doc.get("skills_progress"):
        state = _default_state(user_id)
        await skill_tree_col().update_one({"user_id": user_id}, {"$set": state}, upsert=True)
        return state
    return doc


def _module_index(skill: dict, module_id: str) -> int:
    for i, m in enumerate(skill["modules"]):
        if m["module_id"] == module_id:
            return i
    return -1


def _can_access_module(skill_state: dict, skill_def: dict, module_id: str) -> bool:
    idx = _module_index(skill_def, module_id)
    if idx < 0:
        return False
    current = skill_state.get("current_module_index", 0)
    return idx <= current


def _build_module_test_fallback(skill_id: str, module_id: str, concept: str) -> dict:
    return {
        "question": f"Which statement best matches the core idea of {concept}?",
        "options": [
            "Use loops and conditions to evaluate step by step logic.",
            "Ignore inputs and always return constants.",
            "Write code without base cases or validation.",
            "Avoid functions and decomposition entirely.",
        ],
        "answer_index": 0,
        "explanation": f"{concept} requires structured logic and clear flow.",
        "difficulty": "adaptive",
        "kind": "module",
        "skill_id": skill_id,
        "module_id": module_id,
    }


def _build_final_test_fallback(skill_id: str, modules: list[dict]) -> dict:
    questions = []
    for module in modules[:3]:
        questions.append({
            "question": f"Choose the best practice for {module['concept']}.",
            "options": [
                "Use clear structure, valid base/edge handling, and readable steps.",
                "Write random code until output looks right.",
                "Skip testing and rely on guesses.",
                "Remove all conditions to simplify logic.",
            ],
            "answer_index": 0,
            "module_id": module["module_id"],
        })
    return {"questions": questions, "pass_score": max(2, len(questions)), "skill_id": skill_id}


async def _generate_explanation(user: dict, progress: dict, skill: dict, module: dict) -> str:
    level = (user or {}).get("skill_level", "beginner")
    preferred = (user or {}).get("preferred_language", "english")
    xp = (progress or {}).get("total_xp", 0)

    prompt = f"""You are VoxMentor.
Create a concise learning module explanation.

Student level: {level}
Preferred language: {preferred}
Current XP: {xp}
Skill: {skill['title']}
Module: {module['title']}
Concept: {module['concept']}

Return in this exact format:
1) Concept summary (2-3 lines)
2) Why it matters
3) One tiny code example in python
4) 3 quick checkpoints for self-validation
"""
    try:
        text = await chat_complete(prompt, task="tutor")
        if isinstance(text, str) and text.strip():
            return text.strip()
    except Exception:
        pass

    return (
        f"1) {module['title']} teaches {module['concept']} in simple, structured steps.\n"
        f"2) This matters because {skill['title']} depends on this concept for clean solutions.\n"
        f"3) Example:\n```python\n# practice snippet\nprint('Apply {module['module_id']} carefully')\n```\n"
        "4) Checkpoints:\n- I can explain it in one sentence\n- I can solve one small example\n- I can avoid the common pitfall"
    )


async def _generate_module_test(user: dict, skill: dict, module: dict) -> dict:
    level = (user or {}).get("skill_level", "beginner")
    prompt = f"""Generate exactly one multiple-choice test question for this module.
Skill: {skill['title']}
Module: {module['title']}
Concept: {module['concept']}
Student level: {level}

Return valid JSON only:
{{
  "question": "...",
  "options": ["...","...","...","..."],
  "answer_index": 0,
  "explanation": "..."
}}
"""
    try:
        text = await chat_complete(prompt, task="tutor")
        import json
        payload = json.loads(text)
        if isinstance(payload.get("options"), list) and len(payload["options"]) == 4:
            payload["kind"] = "module"
            return payload
    except Exception:
        pass
    return _build_module_test_fallback(skill["skill_id"], module["module_id"], module["concept"])


async def _generate_final_test(user: dict, skill: dict) -> dict:
    level = (user or {}).get("skill_level", "beginner")
    module_names = ", ".join([m["title"] for m in skill["modules"]])
    prompt = f"""Generate a final skill assessment with 3 MCQ questions spanning all modules.
Skill: {skill['title']}
Modules: {module_names}
Student level: {level}

Return valid JSON only:
{{
  "questions": [
    {{"question":"...","options":["...","...","...","..."],"answer_index":0}},
    {{"question":"...","options":["...","...","...","..."],"answer_index":1}},
    {{"question":"...","options":["...","...","...","..."],"answer_index":2}}
  ],
  "pass_score": 2
}}
"""
    try:
        text = await chat_complete(prompt, task="tutor")
        import json
        payload = json.loads(text)
        qs = payload.get("questions") or []
        if len(qs) >= 3:
            payload["pass_score"] = int(payload.get("pass_score", 2))
            return payload
    except Exception:
        pass
    return _build_final_test_fallback(skill["skill_id"], skill["modules"])


def _serialize_skill_tree(state: dict) -> dict:
    skills_out = []
    for idx, skill in enumerate(SKILL_PATH):
        s_state = state["skills_progress"][skill["skill_id"]]
        modules_out = []
        for m_idx, module in enumerate(skill["modules"]):
            m_state = s_state["modules"][module["module_id"]]
            status = "locked"
            if m_state.get("test_passed"):
                status = "completed"
            elif m_idx == s_state.get("current_module_index", 0):
                status = "active"
            elif m_idx < s_state.get("current_module_index", 0):
                status = "completed"
            modules_out.append({
                **module,
                "status": status,
                "test_passed": m_state.get("test_passed", False),
                "test_attempts": m_state.get("test_attempts", 0),
            })

        skills_out.append({
            "skill_id": skill["skill_id"],
            "title": skill["title"],
            "description": skill["description"],
            "order": idx,
            "unlocked": s_state.get("unlocked", False),
            "completed": s_state.get("completed", False),
            "current_module_index": s_state.get("current_module_index", 0),
            "modules": modules_out,
            "ready_for_final": all(m["test_passed"] for m in s_state["modules"].values()),
            "final_passed": s_state.get("final_passed", False),
        })

    return {"skills": skills_out}


async def _award_skill_xp(user_id: str, base_xp: int) -> dict:
    now = datetime.utcnow()
    prog = await progress_col().find_one({"user_id": user_id})
    user = await users_col().find_one({"user_id": user_id})

    current_streak = prog.get("streak", 0) if prog else (user.get("streak", 0) if user else 0)
    xp_gain = award_xp(base_xp, current_streak)

    if prog:
        streak_result = compute_streak(prog.get("updated_at"), prog.get("streak", 0))
        new_xp = prog.get("total_xp", 0) + xp_gain
        new_streak = streak_result["streak"]
        total_sessions = prog.get("total_sessions", 0)
        await progress_col().update_one(
            {"user_id": user_id},
            {"$set": {
                "total_xp": new_xp,
                "streak": new_streak,
                "longest_streak": max(prog.get("longest_streak", 0), new_streak),
                "updated_at": now,
            }}
        )
    else:
        new_xp = xp_gain
        new_streak = 1
        total_sessions = 0
        await progress_col().insert_one({
            "user_id": user_id,
            "topics": [],
            "total_xp": new_xp,
            "streak": new_streak,
            "longest_streak": new_streak,
            "total_sessions": 0,
            "total_time_minutes": 0.0,
            "updated_at": now,
        })

    existing_badges = user.get("badges", []) if user else []
    new_badges = check_badges(new_xp, new_streak, total_sessions, existing_badges)
    update_fields = {"xp": new_xp, "streak": new_streak, "last_active": now}
    if new_badges:
        await users_col().update_one(
            {"user_id": user_id},
            {"$set": update_fields, "$push": {"badges": {"$each": new_badges}}},
            upsert=True,
        )
    else:
        await users_col().update_one({"user_id": user_id}, {"$set": update_fields}, upsert=True)

    return {
        "xp_gained": xp_gain,
        "total_xp": new_xp,
        "streak": new_streak,
        "new_badges": new_badges,
        "level": calculate_level(new_xp),
    }


@router.get("/{user_id}")
async def get_skill_tree(user_id: str):
    state = await _get_or_create_state(user_id)
    payload = _serialize_skill_tree(state)
    payload["user_id"] = user_id
    return payload


@router.post("/module/explain")
async def module_explain(req: ExplainRequest):
    state = await _get_or_create_state(req.user_id)
    skill = SKILL_MAP.get(req.skill_id)
    if not skill:
        return {"success": False, "error": "Skill not found"}

    s_state = state["skills_progress"].get(req.skill_id)
    if not s_state or not s_state.get("unlocked"):
        return {"success": False, "error": "Skill is locked"}

    if not _can_access_module(s_state, skill, req.module_id):
        return {"success": False, "error": "Complete previous module test first"}

    module = next((m for m in skill["modules"] if m["module_id"] == req.module_id), None)
    if not module:
        return {"success": False, "error": "Module not found"}

    m_state = s_state["modules"][req.module_id]
    if not m_state.get("explanation"):
        user = await users_col().find_one({"user_id": req.user_id})
        progress = await progress_col().find_one({"user_id": req.user_id})
        explanation = await _generate_explanation(user or {}, progress or {}, skill, module)
        m_state["explanation"] = explanation
        state["updated_at"] = datetime.utcnow()
        await skill_tree_col().update_one(
            {"user_id": req.user_id},
            {"$set": {"skills_progress": state["skills_progress"], "updated_at": state["updated_at"]}},
            upsert=True,
        )

    return {
        "success": True,
        "skill_id": req.skill_id,
        "module_id": req.module_id,
        "explanation": m_state.get("explanation", ""),
    }


@router.post("/module/chat")
async def module_chat(req: ModuleChatRequest):
    state = await _get_or_create_state(req.user_id)
    skill = SKILL_MAP.get(req.skill_id)
    if not skill:
        return {"success": False, "error": "Skill not found"}

    s_state = state["skills_progress"].get(req.skill_id)
    if not s_state or not s_state.get("unlocked"):
        return {"success": False, "error": "Skill is locked"}

    if not _can_access_module(s_state, skill, req.module_id):
        return {"success": False, "error": "Complete previous module test first"}

    module = next((m for m in skill["modules"] if m["module_id"] == req.module_id), None)
    if not module:
        return {"success": False, "error": "Module not found"}

    m_state = s_state["modules"][req.module_id]
    history = m_state.get("chat_history", [])
    history_context = history[-4:]

    system = f"""You are VoxMentor module doubt assistant.
Skill: {skill['title']}
Module: {module['title']} ({module['concept']})

Rules:
- Give complete answers, not one-liners.
- Format using markdown with short headings and bullet points.
- If user asks list/all types, include full list.
- Include one tiny Python example in fenced code block when relevant.
- End with 1 short self-check question.
"""
    prompt = f"Student doubt: {req.message}\nRespond with a complete but compact answer in markdown."

    try:
        response = await asyncio.wait_for(
            chat_complete(prompt, system=system, task="tutor", history=history_context),
            timeout=45,
        )
        if not isinstance(response, str) or not response.strip():
            raise ValueError("Empty primary tutor response")
    except Exception:
        try:
            response = await asyncio.wait_for(
                chat_complete(prompt, system=system, task="chat", history=history_context),
                timeout=35,
            )
            if not isinstance(response, str) or not response.strip():
                raise ValueError("Empty secondary chat response")
        except Exception:
            lowered = (req.message or "").lower()
            if "operator" in lowered and "python" in lowered:
                response = (
                    "### Python Operators\n"
                    "- **Arithmetic:** `+`, `-`, `*`, `/`, `//`, `%`, `**`\n"
                    "- **Comparison:** `==`, `!=`, `>`, `<`, `>=`, `<=`\n"
                    "- **Logical:** `and`, `or`, `not`\n"
                    "- **Assignment:** `=`, `+=`, `-=`, `*=`, `/=`, `//=`, `%=`, `**=`\n"
                    "- **Bitwise:** `&`, `|`, `^`, `~`, `<<`, `>>`\n"
                    "- **Membership:** `in`, `not in`\n"
                    "- **Identity:** `is`, `is not`\n\n"
                    "```python\n"
                    "x = 5\n"
                    "y = 3\n"
                    "print(x + y * 2)  # 11\n"
                    "print(x > y and y != 0)  # True\n"
                    "```\n\n"
                    "Self-check: Why does `y * 2` happen before `x + ...` in the first line?"
                )
            else:
                response = (
                    "### Quick fallback\n"
                    "- Break the doubt into input, operation, and expected output.\n"
                    "- Apply one concept at a time, then combine steps.\n"
                    "- Validate with one tiny example before scaling.\n\n"
                    "```python\n"
                    "x = 5\n"
                    "y = 3\n"
                    "print(x + y * 2)  # 11\n"
                    "```\n\n"
                    "Self-check: Can you explain each operation in order?"
                )

    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": response})
    m_state["chat_history"] = history[-20:]
    state["updated_at"] = datetime.utcnow()

    await skill_tree_col().update_one(
        {"user_id": req.user_id},
        {"$set": {"skills_progress": state["skills_progress"], "updated_at": state["updated_at"]}},
        upsert=True,
    )

    return {"success": True, "reply": response, "history": m_state["chat_history"]}


@router.post("/module/test/start")
async def start_module_test(req: TestStartRequest):
    state = await _get_or_create_state(req.user_id)
    skill = SKILL_MAP.get(req.skill_id)
    if not skill:
        return {"success": False, "error": "Skill not found"}

    s_state = state["skills_progress"].get(req.skill_id)
    if not s_state or not s_state.get("unlocked"):
        return {"success": False, "error": "Skill is locked"}

    if not _can_access_module(s_state, skill, req.module_id):
        return {"success": False, "error": "Complete previous module test first"}

    module = next((m for m in skill["modules"] if m["module_id"] == req.module_id), None)
    if not module:
        return {"success": False, "error": "Module not found"}

    user = await users_col().find_one({"user_id": req.user_id})
    test = await _generate_module_test(user or {}, skill, module)

    m_state = s_state["modules"][req.module_id]
    m_state["test"] = test
    m_state["test_attempts"] = m_state.get("test_attempts", 0) + 1

    state["updated_at"] = datetime.utcnow()
    await skill_tree_col().update_one(
        {"user_id": req.user_id},
        {"$set": {"skills_progress": state["skills_progress"], "updated_at": state["updated_at"]}},
        upsert=True,
    )

    return {
        "success": True,
        "skill_id": req.skill_id,
        "module_id": req.module_id,
        "question": test.get("question", ""),
        "options": test.get("options", []),
        "attempt": m_state["test_attempts"],
    }


@router.post("/module/test/submit")
async def submit_module_test(req: TestSubmitRequest):
    state = await _get_or_create_state(req.user_id)
    skill = SKILL_MAP.get(req.skill_id)
    if not skill:
        return {"success": False, "error": "Skill not found"}

    s_state = state["skills_progress"].get(req.skill_id)
    if not s_state:
        return {"success": False, "error": "Skill state missing"}

    m_state = s_state["modules"].get(req.module_id)
    if not m_state or not m_state.get("test"):
        return {"success": False, "error": "Start module test first"}

    test = m_state["test"]
    correct_index = int(test.get("answer_index", 0))
    passed = req.selected_index == correct_index

    reward = None
    if passed:
        m_state["test_passed"] = True
        module_idx = _module_index(skill, req.module_id)
        if module_idx >= 0 and module_idx == s_state.get("current_module_index", 0):
            s_state["current_module_index"] = min(module_idx + 1, len(skill["modules"]))
        reward = await _award_skill_xp(req.user_id, MODULE_PASS_XP)

    state["updated_at"] = datetime.utcnow()
    await skill_tree_col().update_one(
        {"user_id": req.user_id},
        {"$set": {"skills_progress": state["skills_progress"], "updated_at": state["updated_at"]}},
        upsert=True,
    )

    return {
        "success": True,
        "passed": passed,
        "correct_index": correct_index,
        "explanation": test.get("explanation", ""),
        "ready_for_next_module": passed,
        "reward": reward,
    }


@router.post("/skill/final/start")
async def start_final_test(req: FinalStartRequest):
    state = await _get_or_create_state(req.user_id)
    skill = SKILL_MAP.get(req.skill_id)
    if not skill:
        return {"success": False, "error": "Skill not found"}

    s_state = state["skills_progress"].get(req.skill_id)
    if not s_state or not s_state.get("unlocked"):
        return {"success": False, "error": "Skill is locked"}

    if not all(mod_state.get("test_passed") for mod_state in s_state["modules"].values()):
        return {"success": False, "error": "Complete all module tests first"}

    user = await users_col().find_one({"user_id": req.user_id})
    final_test = await _generate_final_test(user or {}, skill)

    s_state["final_test"] = final_test
    state["updated_at"] = datetime.utcnow()
    await skill_tree_col().update_one(
        {"user_id": req.user_id},
        {"$set": {"skills_progress": state["skills_progress"], "updated_at": state["updated_at"]}},
        upsert=True,
    )

    questions = [{"question": q.get("question"), "options": q.get("options", [])} for q in final_test.get("questions", [])]
    return {"success": True, "questions": questions, "pass_score": final_test.get("pass_score", 2)}


@router.post("/skill/final/submit")
async def submit_final_test(req: FinalSubmitRequest):
    state = await _get_or_create_state(req.user_id)
    skill = SKILL_MAP.get(req.skill_id)
    if not skill:
        return {"success": False, "error": "Skill not found"}

    s_state = state["skills_progress"].get(req.skill_id)
    if not s_state or not s_state.get("final_test"):
        return {"success": False, "error": "Start final test first"}

    final_test = s_state["final_test"]
    questions = final_test.get("questions", [])
    selected = req.selected_indices or []

    score = 0
    for i, q in enumerate(questions):
        try:
            if i < len(selected) and int(selected[i]) == int(q.get("answer_index", -1)):
                score += 1
        except Exception:
            continue

    pass_score = int(final_test.get("pass_score", max(2, len(questions) // 2)))
    passed = score >= pass_score

    reward = None
    unlocked_next = None
    if passed:
        s_state["final_passed"] = True
        s_state["completed"] = True
        reward = await _award_skill_xp(req.user_id, FINAL_PASS_XP)

        current_idx = next((i for i, s in enumerate(SKILL_PATH) if s["skill_id"] == req.skill_id), -1)
        if current_idx >= 0 and current_idx + 1 < len(SKILL_PATH):
            next_skill_id = SKILL_PATH[current_idx + 1]["skill_id"]
            next_state = state["skills_progress"].get(next_skill_id)
            if next_state and not next_state.get("unlocked"):
                next_state["unlocked"] = True
                unlocked_next = next_skill_id

    state["updated_at"] = datetime.utcnow()
    await skill_tree_col().update_one(
        {"user_id": req.user_id},
        {"$set": {"skills_progress": state["skills_progress"], "updated_at": state["updated_at"]}},
        upsert=True,
    )

    return {
        "success": True,
        "passed": passed,
        "score": score,
        "pass_score": pass_score,
        "unlocked_next_skill": unlocked_next,
        "reward": reward,
    }


# Compatibility endpoints retained (legacy UI safety)
@router.post("/unlock")
async def unlock_node(_req: UnlockCompatRequest):
    return {"success": False, "error": "Legacy node unlock removed. Use module workflow endpoints."}


@router.post("/complete")
async def complete_node(_req: UnlockCompatRequest):
    return {"success": False, "error": "Legacy node completion removed. Use module/final test endpoints."}
