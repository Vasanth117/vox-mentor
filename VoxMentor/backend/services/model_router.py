"""
Smart Model Router — two-tier intent detection:
  1. Fast heuristics  → handles obvious cases instantly (free)
  2. LLM classifier   → used only for ambiguous/short/mixed messages
"""

import re
import httpx
from typing import Literal

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_SITE_URL,
    OPENROUTER_APP_NAME,
    MODEL_CHAT,
    MODEL_CHAT_MAX_TOKENS,
    MODEL_CHAT_TEMPERATURE,
    MODEL_CHAT_TOP_P,
    MODEL_ROUTER,
    MODEL_CODE,
    MODEL_CODE_MAX_TOKENS,
    MODEL_CODE_TEMPERATURE,
    MODEL_CODE_TOP_P,
    MODEL_TUTOR,
    MODEL_TUTOR_MAX_TOKENS,
    MODEL_TUTOR_TEMPERATURE,
    MODEL_TUTOR_TOP_P,
)

TaskKind = Literal["code", "tutor", "chat"]

# ── Heuristic word lists ──────────────────────────────────────────────────────

_GREETINGS = {
    "hi", "hello", "hey", "hiya", "howdy", "sup", "yo", "greetings",
    "good morning", "good afternoon", "good evening", "good night",
    "how are you", "how's it going", "what's up", "whats up",
    "nice to meet you", "who are you", "what can you do",
    "thanks", "thank you", "ok", "okay", "cool", "great", "awesome",
    "bye", "goodbye", "see you", "later", "cya",
}

_CODE_STRONG = {
    "debug", "error", "traceback", "exception", "syntax error", "runtime error",
    "compile", "fix this", "fix my code", "fix the bug", "bug in",
    "write a function", "write code", "write a program", "write a script",
    "generate code", "code for", "implement", "algorithm for",
    "what does this code", "review my code", "optimize this",
    "leetcode", "hackerrank", "time complexity", "space complexity",
    "segfault", "segmentation fault", "import error", "nameerror", "typeerror",
    "indexerror", "keyerror", "attributeerror", "valueerror",
}

_TUTOR_STRONG = {
    "explain", "what is", "what are", "what does", "how does", "how do",
    "teach me", "help me understand", "i don't understand", "i dont understand",
    "can you explain", "tell me about", "describe", "define",
    "why does", "why do", "why is", "difference between", "compare",
    "concept of", "meaning of", "example of", "give me an example",
    "step by step", "step-by-step", "when to use", "when should i",
    "best practice", "how to learn",
}

_CODE_KEYWORDS = {
    "function", "variable", "array", "list", "dictionary", "dict", "loop",
    "recursion", "class", "object", "method", "module", "library", "api",
    "database", "query", "async", "await", "callback", "promise",
    "pointer", "memory", "heap", "stack", "queue", "graph", "tree",
    "sort", "search", "binary", "linked list", "hash", "map", "set",
    "python", "javascript", "java", "c++", "rust", "typescript", "golang",
    "html", "css", "react", "node", "django", "flask", "fastapi",
    "git", "docker", "kubernetes", "sql", "mongodb", "redis",
}


def _normalize(text: str) -> str:
    return text.strip().lower()


def _contains_code_block(text: str) -> bool:
    """Detect actual code: backtick fences, indented blocks, or common syntax."""
    if "```" in text:
        return True
    # Lines starting with 4+ spaces / tabs (code indent)
    lines = text.splitlines()
    indented = sum(1 for l in lines if l.startswith("    ") or l.startswith("\t"))
    if indented >= 2:
        return True
    # Common code syntax patterns
    code_patterns = [
        r"\bdef\s+\w+\s*\(",          # Python function
        r"\bfunction\s+\w+\s*\(",      # JS function
        r"\bfor\s*\(.*;\s*.*;\s*.*\)", # C-style for loop
        r"\bif\s*\(.*\)\s*\{",        # C-style if
        r"\bclass\s+\w+[\s:{]",        # class definition
        r"print\s*\(|console\.log\(",  # print statements
        r"#include\s*<|import\s+\w+",  # imports
        r"\bint\s+\w+\s*=\s*\d+",     # typed variable
        r"->|=>|::",                    # arrows / scope resolution
    ]
    return any(re.search(p, text) for p in code_patterns)


def _heuristic_route(prompt: str) -> TaskKind | None:
    """
    Returns a TaskKind if heuristics are confident, or None if ambiguous.
    """
    norm = _normalize(prompt)
    word_count = len(norm.split())

    # 1. Greetings / small talk — always chat
    if norm in _GREETINGS:
        return "chat"
    # Short message with greeting-like content (≤4 words, no code keywords)
    if word_count <= 4 and not any(kw in norm for kw in _CODE_KEYWORDS):
        # Check against greeetings more loosely
        for greet in _GREETINGS:
            if norm.startswith(greet) or norm == greet:
                return "chat"

    # 2. Actual code block in message → always code task
    if _contains_code_block(prompt):
        return "code"

    # 3. Strong code signals
    if any(kw in norm for kw in _CODE_STRONG):
        return "code"

    # 4. Strong tutor signals
    if any(kw in norm for kw in _TUTOR_STRONG):
        return "tutor"

    # 5. Ambiguous — return None to trigger AI classifier
    return None


# ── LLM-based classifier ──────────────────────────────────────────────────────

_CLASSIFIER_SYSTEM = """\
You are an intent classifier for an AI coding tutor app called VoxMentor.
Given a user message, respond with EXACTLY one word — no explanation, no punctuation:
  code   → user wants code written, debugged, reviewed, or executed
  tutor  → user wants a concept explained, taught, or clarified
  chat   → general conversation, greeting, small talk, off-topic
Only output one of: code, tutor, chat"""

_CLASSIFIER_MODEL = MODEL_ROUTER  # cheap model for intent assignment


async def _ai_classify(prompt: str) -> TaskKind:
    """Use a lightweight LLM to classify intent. Falls back to 'chat' on error."""
    if not OPENROUTER_API_KEY:
        return _keyword_fallback(prompt)

    payload = {
        "model": _CLASSIFIER_MODEL,
        "messages": [
            {"role": "system", "content": _CLASSIFIER_SYSTEM},
            {"role": "user", "content": prompt[:800]},  # cap input length
        ],
        "temperature": 0.0,
        "max_tokens": 5,
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": OPENROUTER_SITE_URL,
        "X-Title": OPENROUTER_APP_NAME,
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
        resp.raise_for_status()
        result = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
        if result in {"code", "tutor", "chat"}:
            return result  # type: ignore[return-value]
    except Exception:
        pass
    return _keyword_fallback(prompt)


def _keyword_fallback(prompt: str) -> TaskKind:
    """Minimal fallback when AI classifier can't be reached."""
    norm = _normalize(prompt)
    if any(kw in norm for kw in _CODE_KEYWORDS):
        return "code"
    if any(kw in norm for kw in _TUTOR_STRONG):
        return "tutor"
    return "chat"


# ── Public API ────────────────────────────────────────────────────────────────

def route_task_sync(task: str | None, prompt: str = "") -> TaskKind:
    """
    Synchronous route — for backwards compatibility.
    Uses heuristics only. Falls back to keyword check when ambiguous.
    """
    if task in {"code", "tutor", "chat"}:
        return task  # type: ignore[return-value]
    result = _heuristic_route(prompt)
    if result:
        return result
    return _keyword_fallback(prompt)


async def route_task_smart(task: str | None, prompt: str = "") -> TaskKind:
    """
    Smart async route — heuristics first, then LLM classifier if ambiguous.
    This is the preferred function to call.
    """
    # Explicit override from caller (e.g. mode="debug" in chat router)
    if task in {"code", "tutor", "chat"}:
        return task  # type: ignore[return-value]

    # Try fast heuristics first
    result = _heuristic_route(prompt)
    if result is not None:
        return result

    # Ambiguous → use LLM classifier
    return await _ai_classify(prompt)


def get_model_config_sync(task: str | None, prompt: str = "") -> dict:
    """Synchronous model config (uses heuristics only, no AI classifier)."""
    resolved = route_task_sync(task, prompt)
    return _config_for(resolved)


async def get_model_config(task: str | None, prompt: str = "") -> dict:
    """Async model config — uses smart AI-assisted routing."""
    resolved = await route_task_smart(task, prompt)
    return _config_for(resolved)


def _config_for(resolved: TaskKind) -> dict:
    if resolved == "code":
        return {
            "task": "code",
            "model": MODEL_CODE,
            "temperature": MODEL_CODE_TEMPERATURE,
            "top_p": MODEL_CODE_TOP_P,
            "max_tokens": MODEL_CODE_MAX_TOKENS,
        }
    if resolved == "tutor":
        return {
            "task": "tutor",
            "model": MODEL_TUTOR,
            "temperature": MODEL_TUTOR_TEMPERATURE,
            "top_p": MODEL_TUTOR_TOP_P,
            "max_tokens": MODEL_TUTOR_MAX_TOKENS,
        }
    return {
        "task": "chat",
        "model": MODEL_CHAT,
        "temperature": MODEL_CHAT_TEMPERATURE,
        "top_p": MODEL_CHAT_TOP_P,
        "max_tokens": MODEL_CHAT_MAX_TOKENS,
    }
