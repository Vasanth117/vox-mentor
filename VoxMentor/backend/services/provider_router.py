"""Provider router for OpenRouter."""

import asyncio
import json
from typing import AsyncGenerator

import httpx

from config import (
    OPENROUTER_API_KEY,
    OPENROUTER_APP_NAME,
    OPENROUTER_BASE_URL,
    OPENROUTER_SITE_URL,
    MODEL_CODE,
    MODEL_TUTOR,
    MODEL_CHAT,
    MODEL_ROUTER,
)
from services.model_router import get_model_config

SAFE_FALLBACK_MODEL = "nvidia/nemotron-nano-9b-v2:free"

# Ordered list of all configured models to cycle through on failure
_ALL_MODELS = [MODEL_CHAT, MODEL_TUTOR, MODEL_CODE, MODEL_ROUTER, SAFE_FALLBACK_MODEL]


def _fallback_chain(primary: str) -> list[str]:
    """Return fallback models to try after `primary` fails, deduplicated."""
    seen = {primary}
    chain = []
    for m in _ALL_MODELS:
        if m and m not in seen:
            seen.add(m)
            chain.append(m)
    return chain


def _is_model_rejection(resp: httpx.Response) -> bool:
    if resp.status_code not in (400, 404):
        return False
    try:
        body = resp.json()
        message = (
            body.get("error", {}).get("message")
            if isinstance(body, dict)
            else ""
        )
    except Exception:
        message = resp.text or ""
    text = (message or "").lower()
    return (
        "valid model" in text
        or "not a valid model" in text
        or "unknown model" in text
        or "model not found" in text
    )


def _is_rate_limit(resp: httpx.Response) -> bool:
    return resp.status_code == 429


def _is_retriable_http(resp: httpx.Response) -> bool:
    """True if the response warrants trying a different model."""
    return _is_model_rejection(resp) or _is_rate_limit(resp)


def resolve_provider() -> str:
    """Current provider in this deployment."""
    return "openrouter"


def _ensure_openrouter_key() -> None:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")


def _openrouter_headers() -> dict:
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": OPENROUTER_SITE_URL,
        "X-OpenRouter-Title": OPENROUTER_APP_NAME,
        "Content-Type": "application/json",
    }


def _build_messages(prompt: str, system: str, history: list[dict] | None = None) -> list[dict]:
    """Build an OpenAI-format messages array from prompt + optional history."""
    msgs = [{"role": "system", "content": system or "You are VoxMentor AI."}]
    if history:
        for h in history:
            role = h.get("role", "user")
            content = h.get("content", "")
            if role in ("user", "assistant") and content:
                msgs.append({"role": role, "content": content})
    msgs.append({"role": "user", "content": prompt})
    return msgs


async def _openrouter_complete(prompt: str, system: str, task: str | None,
                                history: list[dict] | None = None) -> str:
    _ensure_openrouter_key()
    cfg = await get_model_config(task, prompt)
    primary_model = cfg["model"]
    payload = {
        "model": primary_model,
        "messages": _build_messages(prompt, system, history),
        "temperature": cfg["temperature"],
        "top_p": cfg["top_p"],
        "max_tokens": cfg["max_tokens"],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=_openrouter_headers(),
            json=payload,
        )
        if _is_retriable_http(resp):
            for fallback_model in _fallback_chain(primary_model):
                await asyncio.sleep(0.5)
                payload["model"] = fallback_model
                resp = await client.post(
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers=_openrouter_headers(),
                    json=payload,
                )
                if not _is_retriable_http(resp):
                    break
    resp.raise_for_status()
    data = resp.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")


async def _iter_sse_tokens(resp: httpx.Response) -> AsyncGenerator[str, None]:
    """Parse an SSE streaming response, raising RuntimeError on provider error payloads."""
    async for line in resp.aiter_lines():
        if not line or not line.startswith("data:"):
            continue
        data_str = line[5:].strip()
        if data_str == "[DONE]":
            break
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            continue
        # OpenRouter wraps provider errors as {"error": {"message": "..."}} in the stream
        if isinstance(data, dict) and "error" in data and "choices" not in data:
            err = data["error"]
            err_msg = err.get("message", "Provider returned error") if isinstance(err, dict) else str(err)
            err_code = err.get("code", 0) if isinstance(err, dict) else 0
            raise RuntimeError(f"[{err_code}] OpenRouter stream error: {err_msg}")
        choices = data.get("choices") or []
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        token = delta.get("content", "")
        if token:
            yield token


async def _openrouter_stream(prompt: str, system: str, task: str | None,
                             history: list[dict] | None = None) -> AsyncGenerator[str, None]:
    _ensure_openrouter_key()
    cfg = await get_model_config(task, prompt)
    primary_model = cfg["model"]
    models_to_try = [primary_model] + _fallback_chain(primary_model)

    base_payload = {
        "messages": _build_messages(prompt, system, history),
        "temperature": cfg["temperature"],
        "top_p": cfg["top_p"],
        "max_tokens": cfg["max_tokens"],
        "stream": True,
    }

    last_error: Exception | None = None
    for model in models_to_try:
        payload = {**base_payload, "model": model}
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST",
                    f"{OPENROUTER_BASE_URL}/chat/completions",
                    headers=_openrouter_headers(),
                    json=payload,
                ) as resp:
                    if _is_retriable_http(resp):
                        last_error = RuntimeError(
                            f"Model {model} returned {resp.status_code}, trying next"
                        )
                        await asyncio.sleep(0.5)
                        continue
                    resp.raise_for_status()
                    async for token in _iter_sse_tokens(resp):
                        yield token
                    return  # stream finished successfully
        except RuntimeError as exc:
            last_error = exc
            await asyncio.sleep(0.5)
            continue

    raise last_error or RuntimeError("All models failed")


async def provider_chat_complete(prompt: str, system: str = "", task: str | None = None,
                                  history: list[dict] | None = None) -> str:
    """Call OpenRouter provider.
    Pass `history` as a list of {"role": "user"|"assistant", "content": "..."} dicts
    to maintain conversation context.
    """
    return await _openrouter_complete(prompt, system, task, history)


async def provider_chat_stream(prompt: str, system: str = "", task: str | None = None,
                                history: list[dict] | None = None) -> AsyncGenerator[str, None]:
    """Stream from OpenRouter provider.
    Pass `history` as a list of {"role": "user"|"assistant", "content": "..."} dicts
    to maintain conversation context.
    """
    async for token in _openrouter_stream(prompt, system, task, history):
        yield token
