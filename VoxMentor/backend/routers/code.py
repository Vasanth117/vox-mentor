"""
Code Execution Router
POST /api/code/run     — execute code and return output
POST /api/code/analyze — static analysis only (no execution)
POST /api/code/ai-explain — AI explains selected code
POST /api/code/ai-help    — AI provides targeted help for code/question
"""
from fastapi import APIRouter
from pydantic import BaseModel
from services.executor import execute_code
from services.mistake_analyzer import analyzer
from services.ai_engine import chat_complete
from services.learning_engine import get_weak_strong_areas
from db import users_col, progress_col
from datetime import datetime
import httpx

router = APIRouter(prefix="/api/code", tags=["code"])


class CodeRunRequest(BaseModel):
    code: str
    language: str = "python"
    user_id: str = ""


class CodeAnalyzeRequest(BaseModel):
    code: str
    language: str = "python"


class PlaygroundExplainRequest(BaseModel):
    user_id: str
    code: str
    language: str = "python"
    stderr: str = ""


class PlaygroundHelpRequest(BaseModel):
    user_id: str
    code: str
    question: str
    language: str = "python"
    stderr: str = ""


async def _build_playground_system_prompt(user_id: str) -> str:
    user = None
    prog = None
    try:
        user = await users_col().find_one({"user_id": user_id})
        prog = await progress_col().find_one({"user_id": user_id})
    except Exception:
        user = None
        prog = None

    level = "beginner"
    preferred_language = "english"
    weak_areas = []
    strong_areas = []

    if user:
        level = user.get("skill_level", "beginner")
        preferred_language = user.get("preferred_language", "english")

    if prog:
        topics = prog.get("topics", [])
        areas = get_weak_strong_areas(topics)
        weak_areas = areas.get("weak", [])
        strong_areas = areas.get("strong", [])

    lang_instruction = ""
    if preferred_language.lower() != "english":
        lang_instruction = f"Respond in {preferred_language}."

    weak_text = ", ".join(weak_areas) if weak_areas else "none"
    strong_text = ", ".join(strong_areas) if strong_areas else "none"

    return (
        "You are VoxMentor, a precise code mentor for the Playground. "
        f"Student level: {level}. {lang_instruction}\n"
        f"Weak areas: {weak_text}. Strong areas: {strong_text}.\n"
        "Keep answers practical, concise, and example-driven."
    )


def _explain_prompt(code: str, language: str, stderr: str = "") -> str:
    if stderr.strip():
        return f"""Explain this {language} code and the runtime/compiler error.

Code:
```{language}
{code}
```

Error:
```
{stderr}
```

Respond with:
1) What this code is trying to do
2) Why the error happened
3) Exact fix with corrected code
4) One short takeaway
"""

    return f"""Explain this {language} code clearly.

Code:
```{language}
{code}
```

Respond with:
1) What the code does
2) Step-by-step logic
3) Time/space complexity (if relevant)
4) Potential improvements
"""


def _help_prompt(code: str, question: str, language: str, stderr: str = "") -> str:
    error_block = ""
    if stderr.strip():
        error_block = f"\nError context:\n```\n{stderr}\n```\n"

    return f"""Help the student with this {language} code question.

Question:
{question}

Code:
```{language}
{code}
```
{error_block}
Provide:
- Direct answer to the question
- Minimal corrected snippet if needed
- Next debug/improvement step
"""


def _local_explain_fallback(code: str, language: str, stderr: str = "") -> str:
    issues = []
    try:
        issues = analyzer.analyze(code, language)
    except Exception:
        issues = []
    lines = [
        f"I couldn't reach the AI provider, so here's a local explanation fallback for your {language} code.",
        "",
        "What your code is doing:",
        "- It executes top-to-bottom and runs the statements/functions defined in your snippet.",
    ]
    if stderr.strip():
        lines += [
            "",
            "Detected error context:",
            f"- {stderr[:300]}",
        ]
    if issues:
        lines += [
            "",
            "Static issues detected:",
        ]
        for item in issues[:5]:
            prefix = f"Line {item.get('line')}: " if item.get("line") else ""
            lines.append(f"- {prefix}{item.get('description', 'Issue found')}")
    lines += [
        "",
        "Try next:",
        "- Re-run the code after fixing one issue at a time.",
        "- Use AI Help for a targeted fix question.",
    ]
    return "\n".join(lines)


def _local_help_fallback(code: str, question: str, language: str, stderr: str = "") -> str:
    issues = []
    try:
        issues = analyzer.analyze(code, language)
    except Exception:
        issues = []
    lines = [
        "AI help is temporarily unavailable from provider, so here is a local help fallback.",
        "",
        f"Your question: {question}",
    ]
    if stderr.strip():
        lines.append(f"Error snippet: {stderr[:300]}")
    if issues:
        lines += [
            "",
            "Top issues to fix first:",
        ]
        for item in issues[:3]:
            prefix = f"Line {item.get('line')}: " if item.get("line") else ""
            lines.append(f"- {prefix}{item.get('description', 'Issue found')}")
    lines += [
        "",
        "Hint to complete your code:",
        "- Break the task into small steps, test each step, then combine.",
        "- Add prints/logs for key variables right before the failing line.",
    ]
    return "\n".join(lines)


@router.post("/run")
async def run_code(req: CodeRunRequest):
    result = execute_code(req.code, req.language)
    # Run static analysis in parallel (best-effort)
    mistakes = []
    try:
        mistakes = analyzer.analyze(req.code, req.language)
    except Exception:
        pass
    return {
        **result,
        "language": req.language,
        "static_analysis": mistakes,
    }


@router.post("/analyze")
async def analyze_code(req: CodeAnalyzeRequest):
    mistakes = analyzer.analyze(req.code, req.language)
    return {
        "language": req.language,
        "mistakes": mistakes,
        "count": len(mistakes),
        "has_issues": len(mistakes) > 0,
    }


@router.get("/languages")
async def supported_languages():
    return {
        "languages": [
            {"id": "python",     "label": "Python",     "extension": ".py",  "comment": "#"},
            {"id": "javascript", "label": "JavaScript",  "extension": ".js",  "comment": "//"},
            {"id": "c",          "label": "C",           "extension": ".c",   "comment": "//"},
            {"id": "cpp",        "label": "C++",         "extension": ".cpp", "comment": "//"},
        ]
    }


@router.post("/ai-explain")
async def ai_explain(req: PlaygroundExplainRequest):
    system = await _build_playground_system_prompt(req.user_id)
    prompt = _explain_prompt(req.code, req.language, req.stderr)

    try:
        text = await chat_complete(prompt, system=system, task="code")
    except Exception as exc:
        reason = ""
        if isinstance(exc, httpx.HTTPStatusError):
            reason = f" (provider status: {exc.response.status_code})"
        text = _local_explain_fallback(req.code, req.language, req.stderr) + reason

    return {
        "user_id": req.user_id,
        "language": req.language,
        "explanation": text,
        "generated_at": datetime.utcnow(),
    }


@router.post("/ai-help")
async def ai_help(req: PlaygroundHelpRequest):
    system = await _build_playground_system_prompt(req.user_id)
    prompt = _help_prompt(req.code, req.question, req.language, req.stderr)

    try:
        text = await chat_complete(prompt, system=system, task="tutor")
    except Exception as exc:
        reason = ""
        if isinstance(exc, httpx.HTTPStatusError):
            reason = f" (provider status: {exc.response.status_code})"
        text = _local_help_fallback(req.code, req.question, req.language, req.stderr) + reason

    return {
        "user_id": req.user_id,
        "language": req.language,
        "help": text,
        "generated_at": datetime.utcnow(),
    }
