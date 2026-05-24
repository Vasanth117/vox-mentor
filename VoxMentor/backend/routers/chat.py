"""
Chat Router — AI tutor conversations with streaming support.
POST /api/chat      → non-streaming for simple cases
WS   /ws/chat/{uid} → streaming WebSocket
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import StreamingResponse
from models.session import ChatRequest, ChatRegenerateRequest
from services.ai_engine import explain_topic, debug_code, give_mistake_feedback, smart_chat_stream, chat_complete
from services.mistake_analyzer import analyzer
from services.learning_engine import calculate_level, get_weak_strong_areas
from services.user_memory import update_user_memory
from db import sessions_col, users_col, progress_col
from datetime import datetime
from bson import ObjectId
import json

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Maximum number of previous messages to feed back into the AI (to control token usage)
MAX_HISTORY_MESSAGES = 120
MAX_USER_HISTORY_MESSAGES = 240


async def _get_user_context(user_id: str) -> dict:
    """Fetch full user profile + progress and merge into a single context dict for the AI."""
    user = await users_col().find_one({"user_id": user_id})
    prog = await progress_col().find_one({"user_id": user_id})

    ctx: dict = {
        "level": "beginner",
        "lang": "english",
        "preferred_language": "english",
    }

    if user:
        ctx["name"]             = user.get("name", "")
        ctx["skill_level"]      = user.get("skill_level", "beginner")
        ctx["level"]            = user.get("skill_level", "beginner")
        ctx["preferred_language"] = user.get("preferred_language", "english")
        ctx["lang"]             = user.get("preferred_language", "english")
        ctx["career_goal"]      = user.get("career_goal", "")
        ctx["teaching_style"]   = user.get("teaching_style", "balanced")
        ctx["last_mood"]        = user.get("last_mood", "")
        ctx["xp"]               = user.get("xp", 0)
        ctx["streak"]           = user.get("streak", 0)
        ctx["badges"]           = user.get("badges", [])

    if prog:
        topics = prog.get("topics", [])
        areas = get_weak_strong_areas(topics)
        ctx["weak_areas"]    = areas["weak"]
        ctx["strong_areas"]  = areas["strong"]
        ctx["recent_topics"] = [t["topic"] for t in sorted(
            topics, key=lambda t: t.get("last_practiced", datetime.min), reverse=True
        )][:8]
        ctx["xp"]    = prog.get("total_xp", ctx.get("xp", 0))
        ctx["streak"] = prog.get("streak", ctx.get("streak", 0))
        ctx["level_info"] = calculate_level(ctx["xp"])

    return ctx


async def _load_session_history(session_id: str | None, limit: int = MAX_HISTORY_MESSAGES) -> list[dict]:
    """Load previous messages from a session, returning OpenAI-format dicts."""
    if not session_id:
        return []
    try:
        doc = await sessions_col().find_one({"_id": ObjectId(session_id)})
    except Exception:
        return []
    if not doc:
        return []
    raw = doc.get("messages", [])
    # Take the last `limit` messages, convert to {"role", "content"} dicts
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in raw[-limit:]
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    return history


async def _load_user_history(user_id: str, limit: int = MAX_USER_HISTORY_MESSAGES,
                             exclude_session_id: str | None = None) -> list[dict]:
    """Load recent messages across the user's chat sessions for long-term context."""
    query: dict = {"user_id": user_id}
    if exclude_session_id:
        try:
            query["_id"] = {"$ne": ObjectId(exclude_session_id)}
        except Exception:
            pass

    cursor = sessions_col().find(query).sort("updated_at", -1).limit(30)
    rows = []
    async for doc in cursor:
        for message in doc.get("messages", []):
            role = message.get("role")
            content = message.get("content")
            if role not in ("user", "assistant") or not content:
                continue
            rows.append({
                "role": role,
                "content": content,
                "timestamp": message.get("timestamp", datetime.min),
            })

    rows.sort(key=lambda item: item.get("timestamp") or datetime.min)
    return [{"role": m["role"], "content": m["content"]} for m in rows[-limit:]]


async def _stream_reply_tokens(message: str, mode: str, language: str, ctx: dict,
                               history: list[dict]):
    """Stream response tokens for a message under the selected mode."""
    if mode == "debug":
        parts = message.split("|||", 1)
        code = parts[0].strip()
        error = parts[1].strip() if len(parts) > 1 else ""
        async for token in debug_code(code, error, language, ctx["lang"], history=history, user_context=ctx):
            yield token
        return

    if mode == "analyze":
        mistakes = analyzer.analyze(message, language)
        mistake_list = [m["description"] for m in mistakes]
        async for token in give_mistake_feedback(message, mistake_list, language,
                                                 ctx["lang"], history=history, user_context=ctx):
            yield token
        return

    async for token in smart_chat_stream(
        message,
        language,
        ctx["level"],
        ctx["lang"],
        history=history,
        user_context=ctx,
    ):
        yield token


async def _complete_reply_text(message: str, mode: str, language: str, ctx: dict,
                               history: list[dict]) -> str:
    """Non-streaming completion fallback used when streaming fails repeatedly."""
    system = (
        "You are VoxMentor, an expert AI programming tutor. "
        f"Student level: {ctx.get('skill_level', 'beginner')}. "
        f"Preferred language: {ctx.get('lang', 'english')}."
    )

    if mode == "debug":
        prompt = (
            f"The user needs debugging help for {language}.\n"
            f"Message:\n{message}\n\n"
            "Provide: what went wrong, root cause, fixed code, and one takeaway."
        )
        return await chat_complete(prompt, system=system, task="code", history=history)

    if mode == "analyze":
        prompt = (
            f"Analyze this {language} code/text and provide concise feedback:\n\n{message}\n\n"
            "Return strengths, issues, and concrete improvements."
        )
        return await chat_complete(prompt, system=system, task="code", history=history)

    return await chat_complete(message, system=system, task="chat", history=history)


@router.post("/")
async def chat(req: ChatRequest):
    ctx = await _get_user_context(req.user_id)
    session_history = await _load_session_history(req.session_id)
    user_history = await _load_user_history(req.user_id, exclude_session_id=req.session_id)
    history = (user_history + session_history)[-MAX_HISTORY_MESSAGES:]

    async def streamer():
        full_response = ""
        try:
            async for token in _stream_reply_tokens(req.message, req.mode, req.language, ctx, history):
                full_response += token
                yield token.encode()
        except Exception:
            # Retry once with minimal history to recover from context/window or transient provider issues.
            try:
                async for token in _stream_reply_tokens(req.message, req.mode, req.language, ctx, []):
                    full_response += token
                    yield token.encode()
            except Exception:
                try:
                    full_response = await _complete_reply_text(req.message, req.mode, req.language, ctx, [])
                    if full_response:
                        yield full_response.encode()
                except Exception:
                    fallback = "Sorry, I hit a temporary AI error while streaming. Please retry."
                    full_response = (full_response + "\n" + fallback).strip() if full_response else fallback
                    yield fallback.encode()

        # Persist session and emit session_id header before streaming
        try:
            new_session_id = None
            msg_user = {"role": "user", "content": req.message, "timestamp": datetime.utcnow()}
            msg_ai   = {"role": "assistant", "content": full_response, "timestamp": datetime.utcnow()}
            if req.session_id:
                await sessions_col().update_one(
                    {"_id": ObjectId(req.session_id)},
                    {"$push": {"messages": {"$each": [msg_user, msg_ai]}},
                     "$set": {"updated_at": datetime.utcnow()}},
                )
            else:
                result = await sessions_col().insert_one({
                    "user_id": req.user_id,
                    "topic": req.message[:80],
                    "language": req.language,
                    "messages": [msg_user, msg_ai],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                })
                new_session_id = str(result.inserted_id)

            if new_session_id:
                yield f"\x00SID:{new_session_id}\x00".encode()
        except Exception:
            return

        try:
            await update_user_memory(req.user_id, req.message)
        except Exception:
            pass

    return StreamingResponse(streamer(), media_type="text/plain")


@router.post("/regenerate")
async def regenerate(req: ChatRegenerateRequest):
    ctx = await _get_user_context(req.user_id)

    try:
        sid = ObjectId(req.session_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    session_doc = await sessions_col().find_one({"_id": sid, "user_id": req.user_id})
    if not session_doc:
        raise HTTPException(status_code=404, detail="Session not found")

    raw_messages = session_doc.get("messages", [])
    if not raw_messages:
        raise HTTPException(status_code=400, detail="Session has no messages to regenerate")

    last_user_idx = None
    for idx in range(len(raw_messages) - 1, -1, -1):
        msg = raw_messages[idx]
        if msg.get("role") == "user" and msg.get("content"):
            last_user_idx = idx
            break

    if last_user_idx is None:
        raise HTTPException(status_code=400, detail="No user message found for regeneration")

    target_message = raw_messages[last_user_idx].get("content", "")
    session_history_before_target = [
        {"role": m.get("role"), "content": m.get("content")}
        for m in raw_messages[:last_user_idx]
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    user_history = await _load_user_history(req.user_id, exclude_session_id=req.session_id)
    history = (user_history + session_history_before_target)[-MAX_HISTORY_MESSAGES:]

    async def streamer():
        full_response = ""
        try:
            async for token in _stream_reply_tokens(target_message, req.mode, req.language, ctx, history):
                full_response += token
                yield token.encode()
        except Exception:
            try:
                async for token in _stream_reply_tokens(target_message, req.mode, req.language, ctx, []):
                    full_response += token
                    yield token.encode()
            except Exception:
                try:
                    full_response = await _complete_reply_text(target_message, req.mode, req.language, ctx, [])
                    if full_response:
                        yield full_response.encode()
                except Exception:
                    fallback = "Sorry, I hit a temporary AI error while regenerating. Please retry."
                    full_response = (full_response + "\n" + fallback).strip() if full_response else fallback
                    yield fallback.encode()

        trimmed_messages = raw_messages[:last_user_idx + 1]
        trimmed_messages.append({
            "role": "assistant",
            "content": full_response,
            "timestamp": datetime.utcnow(),
        })
        await sessions_col().update_one(
            {"_id": sid},
            {
                "$set": {
                    "messages": trimmed_messages,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

    return StreamingResponse(streamer(), media_type="text/plain")


@router.get("/sessions/{user_id}")
async def get_sessions(user_id: str, limit: int = 10):
    cursor = sessions_col().find(
        {"user_id": user_id},
        {"messages": 0}   # exclude messages for list view
    ).sort("updated_at", -1).limit(limit)
    sessions = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        sessions.append(doc)
    return {"sessions": sessions}


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    doc = await sessions_col().find_one({"_id": ObjectId(session_id)})
    if not doc:
        return {"error": "Session not found"}
    doc["_id"] = str(doc["_id"])
    return doc


# ── WebSocket streaming endpoint ──────────────────────────────────────────────

@router.websocket("/ws/{user_id}")
async def websocket_chat(websocket: WebSocket, user_id: str):
    await websocket.accept()
    ctx = await _get_user_context(user_id)

    # In-session memory — grows as the conversation continues
    ws_history: list[dict] = []

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            message   = payload.get("message", "")
            language  = payload.get("language", "python")
            mode      = payload.get("mode", "tutor")
            session_id = payload.get("session_id")

            # Load DB history once per message if a session ID is supplied,
            # but prefer the live in-memory history for subsequent turns
            if session_id and not ws_history:
                ws_history = await _load_session_history(session_id)
                ws_history = (await _load_user_history(user_id, exclude_session_id=session_id) + ws_history)[-MAX_HISTORY_MESSAGES:]

            full_response = ""
            if mode == "debug":
                parts = message.split("|||", 1)
                code  = parts[0].strip()
                error = parts[1].strip() if len(parts) > 1 else ""
                async for token in debug_code(code, error, language, ctx["lang"],
                                               history=ws_history, user_context=ctx):
                    full_response += token
                    await websocket.send_text(json.dumps({"type": "token", "data": token}))
            else:
                async for token in smart_chat_stream(message, language, ctx["level"], ctx["lang"],
                                                     history=ws_history, user_context=ctx):
                    full_response += token
                    await websocket.send_text(json.dumps({"type": "token", "data": token}))

            # Add this exchange to the in-session history
            ws_history.append({"role": "user",      "content": message})
            ws_history.append({"role": "assistant",  "content": full_response})
            # Keep history trimmed
            if len(ws_history) > MAX_HISTORY_MESSAGES:
                ws_history = ws_history[-MAX_HISTORY_MESSAGES:]

            # Persist to DB
            if session_id:
                now = datetime.utcnow()
                await sessions_col().update_one(
                    {"_id": ObjectId(session_id)},
                    {"$push": {"messages": {"$each": [
                        {"role": "user",      "content": message,       "timestamp": now},
                        {"role": "assistant", "content": full_response, "timestamp": now},
                    ]}},
                     "$set": {"updated_at": now}},
                )
            else:
                await sessions_col().insert_one({
                    "user_id": user_id,
                    "topic": message[:80],
                    "language": language,
                    "messages": [
                        {"role": "user",      "content": message,       "timestamp": datetime.utcnow()},
                        {"role": "assistant", "content": full_response, "timestamp": datetime.utcnow()},
                    ],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                })

            await websocket.send_text(json.dumps({"type": "done", "full": full_response}))

            try:
                await update_user_memory(user_id, message)
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
