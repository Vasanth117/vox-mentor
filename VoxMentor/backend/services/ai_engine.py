"""
AI Engine orchestrates task prompts and delegates model/provider selection
through provider_router + model_router.
"""

import json
from typing import AsyncGenerator

from services.provider_router import provider_chat_complete, provider_chat_stream

MAX_LLM_JSON_CHARS = 120_000


def _strip_markdown_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if not lines:
        return stripped

    # Drop opening fence (``` or ```json) and closing fence if present.
    body_lines = lines[1:]
    if body_lines and body_lines[-1].strip() == "```":
        body_lines = body_lines[:-1]
    return "\n".join(body_lines).strip()


def _parse_first_json_object(raw_text: str) -> dict:
    """Safely parse the first JSON object from LLM output with bounds checks."""
    if not isinstance(raw_text, str):
        raise ValueError("LLM output must be text")

    cleaned = _strip_markdown_code_fence(raw_text)
    if len(cleaned) > MAX_LLM_JSON_CHARS:
        raise ValueError("LLM JSON output is too large")

    decoder = json.JSONDecoder()
    for index, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("No valid JSON object found in LLM response")

# ─── Prompt Templates ────────────────────────────────────────────────────────

def _tutor_prompt(topic: str, language: str, student_level: str, preferred_lang: str) -> str:
    lang_instruction = f"Respond in {preferred_lang}." if preferred_lang.lower() != "english" else ""
    return f"""You are VoxMentor, an expert programming tutor specializing in {language}.
The student is a {student_level} learner. {lang_instruction}

Explain the topic: "{topic}"

Structure your response EXACTLY as follows (use these exact section headers):

## 📌 Concept Overview
[Brief 2-3 sentence overview of what this concept is]

## 💡 Why It Matters
[Why this concept is important and where it is used in real projects]

## 🔢 Step-by-Step Explanation
[Break it down into numbered steps, very clearly]

## 💻 Code Example
```{language}
[Working code example that demonstrates the concept]
```

## ⚠️ Common Mistakes
[List 2-3 common mistakes beginners make with this topic]

## 🎯 Mini Challenge
[One small practice problem the student can try right now]

Keep explanations clear, friendly, and encouraging. Avoid jargon unless explained."""


def _build_system_prompt(user_context: dict | None) -> str:
    """Build a rich system prompt embedding all known user data for personalised tutoring."""
    base = "You are VoxMentor, an expert AI programming tutor. Your job is to teach, guide, and motivate the student."
    if not user_context:
        return base

    parts = [base, "", "## Student Profile"]

    name = user_context.get("name")
    if name:
        parts.append(f"- Name: {name}")

    level = user_context.get("skill_level", "beginner")
    parts.append(f"- Skill level: {level}")

    lang = user_context.get("preferred_language", "english")
    if lang.lower() != "english":
        parts.append(f"- Preferred response language: {lang} — always respond in {lang}")

    goal = user_context.get("career_goal")
    if goal:
        parts.append(f"- Career goal: {goal}")

    style = user_context.get("teaching_style", "balanced")
    style_descs = {
        "guided":      "needs step-by-step explanations, extra examples, and reassurance",
        "independent": "prefers concise explanations; go straight to the point",
        "balanced":    "balanced approach; adapt based on topic difficulty",
    }
    parts.append(f"- Teaching style: {style} ({style_descs.get(style, style)})")

    mood = user_context.get("last_mood")
    if mood and mood != "positive":
        mood_guidance = {
            "struggling": "The student is currently struggling — be extra patient, break things down further, and offer encouragement.",
            "confused":   "The student seems confused — ask clarifying questions and simplify your language.",
            "confident":  "The student feels confident — you can be a bit more challenging and thorough.",
        }
        parts.append(f"- Recent mood: {mood}. {mood_guidance.get(mood, '')}")

    # Progress / learning state
    xp = user_context.get("xp", 0)
    streak = user_context.get("streak", 0)
    parts.append(f"- XP earned: {xp}  |  Day streak: {streak}")

    level_info = user_context.get("level_info")
    if not isinstance(level_info, dict):
        fallback_level = user_context.get("level")
        level_info = fallback_level if isinstance(fallback_level, dict) else None
    if isinstance(level_info, dict) and level_info:
        parts.append(f"- Level: {level_info.get('level', 0)} ({level_info.get('level_name', 'Novice')})")

    weak = user_context.get("weak_areas", [])
    if weak:
        parts.append(f"- Weak areas (needs extra help): {', '.join(weak)}")

    strong = user_context.get("strong_areas", [])
    if strong:
        parts.append(f"- Strong areas: {', '.join(strong)}")

    recent_topics = user_context.get("recent_topics", [])
    if recent_topics:
        parts.append(f"- Recently studied: {', '.join(recent_topics[:5])}")

    parts += [
        "",
        "## Instructions",
        "- Tailor all explanations to this student's level, goals, and weak areas.",
        "- You DO know this student's profile from the Student Profile section above.",
        "- If the student asks about their own profile (name, level, goal, language, streak, XP, weak/strong areas), answer directly using those fields.",
        "- Do not claim you don't know their name/profile when the information is present above.",
        "- Reference their weak areas when relevant to reinforce learning.",
        "- If they are struggling or confused, be especially patient and use analogies.",
        "- Build on their strong areas to bridge understanding.",
        "- If the conversation continues below, remember the previous messages and build upon them — do NOT restart the explanation.",
    ]
    return "\n".join(parts)


def _practice_prompt(topic: str, language: str, difficulty: str, preferred_lang: str) -> str:
    lang_instruction = f"Respond in {preferred_lang}." if preferred_lang.lower() != "english" else ""
    return f"""You are VoxMentor, a coding tutor. {lang_instruction}
Generate a {difficulty} level coding challenge about "{topic}" in {language}.

Respond with ONLY valid JSON in this exact format:
{{
  "title": "Challenge title",
  "description": "Clear problem description with constraints",
  "starter_code": "# starter code here\\n",
  "expected_output": "Expected output for the sample input",
  "test_cases": [
    {{"input": "sample input", "expected_output": "expected output"}},
    {{"input": "edge input",   "expected_output": "edge output"}}
  ],
  "difficulty": "{difficulty}",
  "topic": "{topic}",
  "language": "{language}",
  "xp_reward": 50,
  "hint": "A helpful hint if the student is stuck"
}}"""


def _debug_prompt(code: str, error: str, language: str, preferred_lang: str) -> str:
    lang_instruction = f"Respond in {preferred_lang}." if preferred_lang.lower() != "english" else ""
    return f"""You are VoxMentor, a helpful debugging assistant. {lang_instruction}
The student has written {language} code that produces an error.

Code:
```{language}
{code}
```

Error:
```
{error}
```

Provide a helpful debug analysis:
## 🐛 What Went Wrong
[Explain the error in simple terms]

## 🔍 Root Cause
[Explain WHY this error happens]

## ✅ Fixed Code
```{language}
[The corrected code with comments explaining changes]
```

## 📚 What to Remember
[Key lesson to avoid this error in the future]"""


def _visualization_prompt(algorithm: str, language: str) -> str:
    return f"""You are VoxMentor. Generate step-by-step visualization data for: "{algorithm}"

Respond with ONLY valid JSON in this format (no extra text):
{{
  "algorithm": "{algorithm}",
  "type": "sorting|graph|tree|linked_list|recursion|array",
  "description": "Brief description of how this algorithm works",
  "initial_state": {{}},
  "steps": [
    {{
      "step_number": 1,
      "action": "Description of what happens",
      "state": {{}},
      "highlight_indices": [],
      "comparison": {{"left": null, "right": null}},
      "swap": false
    }}
  ],
  "time_complexity": "O(?)",
  "space_complexity": "O(?)"
}}

For sorting: state has "array" field with the array at that step.
For trees: state has "nodes" and "edges" fields.
For graphs: state has "visited", "current", "queue/stack" fields.
For recursion: state has "call_stack" field as an array of frames.
Generate realistic steps for a small example (5-8 elements max).
Ensure valid JSON only, no markdown."""


def _reflection_prompt(content: str, preferred_lang: str) -> str:
    lang_instruction = f"Respond in {preferred_lang}." if preferred_lang.lower() != "english" else ""
    return f"""You are VoxMentor, a supportive learning coach. {lang_instruction}
The student has shared their learning reflection:

"{content}"

Extract and respond with ONLY valid JSON:
{{
  "key_learnings": ["learning 1", "learning 2"],
  "questions_remaining": ["question 1"],
  "encouragement": "A short, genuine, personalized encouraging message",
  "suggested_next_topics": ["topic 1", "topic 2"],
  "mood_assessment": "positive|struggling|confused|confident"
}}"""


def _mistake_analysis_prompt(code: str, mistakes: list, language: str, preferred_lang: str) -> str:
    lang_instruction = f"Respond in {preferred_lang}." if preferred_lang.lower() != "english" else ""
    pattern_text = "\n".join(f"- {m}" for m in mistakes) if mistakes else "None detected statically"
    return f"""You are VoxMentor. {lang_instruction}
Analyze the student's {language} code for learning insights.

Code:
```{language}
{code}
```

Static patterns detected: {pattern_text}

## 🔎 Code Analysis
[What the student attempted to do]

## 🎯 Improvement Suggestions
[Specific, actionable improvements with examples]

## 💪 What You Did Well
[Genuine positive feedback on good practices]"""


# ─── Low-level chat wrappers ────────────────────────────────────────────────

async def chat_stream(prompt: str, system: str = "", task: str | None = None,
                       history: list[dict] | None = None) -> AsyncGenerator[str, None]:
    async for token in provider_chat_stream(prompt, system=system, task=task, history=history):
        yield token


async def chat_complete(prompt: str, system: str = "", task: str | None = None,
                         history: list[dict] | None = None) -> str:
    return await provider_chat_complete(prompt, system=system, task=task, history=history)


# ─── High-level AI actions ───────────────────────────────────────────────────

async def explain_topic(topic: str, language: str, student_level: str = "beginner",
                         preferred_lang: str = "english",
                         history: list[dict] | None = None,
                         user_context: dict | None = None) -> AsyncGenerator[str, None]:
    system = _build_system_prompt(user_context)
    prompt = _tutor_prompt(topic, language, student_level, preferred_lang)
    async for token in chat_stream(prompt, system=system, task="tutor", history=history):
        yield token


def _casual_chat_prompt(message: str, preferred_lang: str) -> str:
    lang_instruction = f"Respond in {preferred_lang}." if preferred_lang.lower() != "english" else ""
    return (
        f"You are VoxMentor, a friendly AI coding tutor. {lang_instruction} "
        f"The user is chatting casually. Reply naturally and warmly — no markdown headers, "
        f"no bullet sections, no structured format. Keep it short and human.\n\n"
        f"User: {message}"
    )


async def casual_chat_stream(message: str,
                              preferred_lang: str = "english") -> AsyncGenerator[str, None]:
    """Friendly conversational reply — no structured tutor format."""
    prompt = _casual_chat_prompt(message, preferred_lang)
    async for token in chat_stream(prompt, task="chat"):
        yield token


async def smart_chat_stream(message: str, language: str,
                              student_level: str = "beginner",
                              preferred_lang: str = "english",
                              history: list[dict] | None = None,
                              user_context: dict | None = None) -> AsyncGenerator[str, None]:
    """
    Auto-detects message intent, then streams from the right response style:
      chat  -> casual_chat_stream   (conversational, no structure)
      tutor -> explain_topic        (structured educational response)
      code  -> code-model stream    (code-focused response)
    """
    from services.model_router import route_task_smart
    intent = await route_task_smart(None, message)

    if intent == "chat":
        async for token in chat_stream(
            _casual_chat_prompt(message, preferred_lang),
            system=_build_system_prompt(user_context),
            task="chat",
            history=history,
        ):
            yield token
    elif intent == "code":
        async for token in chat_stream(
            _tutor_prompt(message, language, student_level, preferred_lang),
            system=_build_system_prompt(user_context),
            task="code",
            history=history,
        ):
            yield token
    else:  # "tutor"
        async for token in explain_topic(
            message,
            language,
            student_level,
            preferred_lang,
            history=history,
            user_context=user_context,
        ):
            yield token


async def generate_practice(topic: str, language: str, difficulty: str = "beginner",
                              preferred_lang: str = "english") -> dict:
    prompt = _practice_prompt(topic, language, difficulty, preferred_lang)
    raw = ""
    try:
        raw = await chat_complete(prompt, task="code")
    except Exception:
        return {
            "title": f"{topic.title()} Practice",
            "description": f"Write a {difficulty} {language} solution for the topic: {topic}.",
            "starter_code": "# Write your solution here\n",
            "expected_output": "",
            "difficulty": difficulty,
            "topic": topic,
            "language": language,
            "xp_reward": 50,
            "hint": "Break the problem into small steps, then test with a simple input.",
            "test_cases": [],
        }

    if raw is None:
        raw = ""
    if not isinstance(raw, str):
        raw = str(raw)

    try:
        parsed = _parse_first_json_object(raw)
        if not isinstance(parsed.get("test_cases", []), list):
            parsed["test_cases"] = []
        return parsed
    except Exception:
        return {
            "title": f"{topic} Challenge",
            "description": (raw[:300] if raw else f"Solve a {difficulty} {language} challenge on {topic}."),
            "starter_code": "# Write your solution here\n",
            "difficulty": difficulty,
            "topic": topic,
            "language": language,
            "xp_reward": 50,
            "test_cases": [],
        }


async def debug_code(code: str, error: str, language: str,
                      preferred_lang: str = "english",
                      history: list[dict] | None = None,
                      user_context: dict | None = None) -> AsyncGenerator[str, None]:
    system = _build_system_prompt(user_context)
    prompt = _debug_prompt(code, error, language, preferred_lang)
    async for token in chat_stream(prompt, system=system, task="code", history=history):
        yield token


async def generate_visualization(algorithm: str, language: str = "python") -> dict:
    prompt = _visualization_prompt(algorithm, language)
    try:
        raw = await chat_complete(prompt, task="code")
    except Exception:
        raw = ""

    try:
        parsed = _parse_first_json_object(raw)
        if not parsed.get("steps"):
            return _visualization_fallback(algorithm)
        return parsed
    except Exception:
        lower_name = (algorithm or "").strip().lower()
        fallback_type = "unknown"
        if any(k in lower_name for k in ["sort", "bubble", "merge", "quick", "heap"]):
            fallback_type = "sorting"
        elif any(k in lower_name for k in ["graph", "bfs", "dfs"]):
            fallback_type = "graph"
        elif any(k in lower_name for k in ["list", "linked"]):
            fallback_type = "linked_list"
        elif any(k in lower_name for k in ["tree"]):
            fallback_type = "tree"
        elif any(k in lower_name for k in ["recursion", "fibonacci", "factorial"]):
            fallback_type = "recursion"
        elif any(k in lower_name for k in ["search", "array"]):
            fallback_type = "array"

        return {
            "algorithm": algorithm,
            "type": fallback_type,
            "description": f"Visualization for {algorithm}",
            "steps": [{"step_number": 1, "action": "AI visualization unavailable offline", "state": {"array": [5, 3, 8, 1, 9, 2]}, "highlight_indices": [], "swap": False}],
            "time_complexity": "O(?)",
            "space_complexity": "O(?)",
        }


async def analyze_reflection(content: str, preferred_lang: str = "english") -> dict:
    prompt = _reflection_prompt(content, preferred_lang)
    raw = await chat_complete(prompt, task="tutor")
    try:
        parsed = _parse_first_json_object(raw)
        if not isinstance(parsed.get("key_learnings", []), list):
            parsed["key_learnings"] = []
        if not isinstance(parsed.get("questions_remaining", []), list):
            parsed["questions_remaining"] = []
        if not isinstance(parsed.get("suggested_next_topics", []), list):
            parsed["suggested_next_topics"] = []
        return parsed
    except Exception:
        return {
            "key_learnings": [],
            "questions_remaining": [],
            "encouragement": "Great work reflecting on your learning! Keep it up!",
            "suggested_next_topics": [],
            "mood_assessment": "positive",
        }


async def give_mistake_feedback(code: str, mistakes: list, language: str,
                                 preferred_lang: str = "english",
                                 history: list[dict] | None = None,
                                 user_context: dict | None = None) -> AsyncGenerator[str, None]:
    system = _build_system_prompt(user_context)
    prompt = _mistake_analysis_prompt(code, mistakes, language, preferred_lang)
    async for token in chat_stream(prompt, system=system, task="code", history=history):
        yield token

