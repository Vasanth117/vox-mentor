"""
Voice Router — Speech-to-Text and Text-to-Speech
POST /api/voice/stt — audio file → transcript
POST /api/voice/tts — text → audio (mp3)
"""
import io
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse, Response
import httpx

from config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_BASE_URL,
    ELEVENLABS_TTS_VOICE_ID,
    ELEVENLABS_TTS_MODEL_ID,
    ELEVENLABS_STT_MODEL_ID,
)

router = APIRouter(prefix="/api/voice", tags=["voice"])

AUDIO_MPEG = "audio/mpeg"

ALLOWED_AUDIO_EXTENSIONS = {".webm", ".wav", ".mp3", ".m4a", ".ogg", ".mp4"}
ALLOWED_AUDIO_CONTENT_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    AUDIO_MPEG,
    "audio/mp4",
    "audio/ogg",
    "video/webm",
}
CONTENT_TYPE_DEFAULT_EXTENSIONS = {
    "audio/webm": ".webm",
    "video/webm": ".webm",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/ogg": ".ogg",
}
MAX_AUDIO_BYTES = 15 * 1024 * 1024


def _elevenlabs_api_base() -> str:
    """Return normalized ElevenLabs API base without duplicate '/v1'."""
    base = (ELEVENLABS_BASE_URL or "https://api.elevenlabs.io").strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return f"{base}/v1"


def _elevenlabs_url(path: str) -> str:
    return f"{_elevenlabs_api_base()}/{path.lstrip('/')}"


def _normalize_content_type(value: str) -> str:
    """Return the media type without optional parameters (e.g. codecs)."""
    return (value or "").split(";", 1)[0].strip().lower()


def _missing_key_response():
    return JSONResponse(
        status_code=500,
        content={
            "error": "ELEVENLABS_API_KEY is not configured in backend/.env",
        },
    )


def _extract_elevenlabs_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
        detail = payload.get("detail")
        if isinstance(detail, dict):
            message = detail.get("message") or detail.get("status")
            if isinstance(message, str) and message.strip():
                return message.strip()
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
    except Exception:
        pass

    text = (response.text or "").strip()
    if text:
        return text[:600]
    return f"ElevenLabs HTTP {response.status_code}"


@router.get("/status")
async def voice_status():
    """Returns whether ElevenLabs STT service is currently reachable."""
    if not ELEVENLABS_API_KEY:
        return {
            "status": "not_configured",
            "available": False,
            "reason": "ELEVENLABS_API_KEY is missing in backend/.env",
        }

    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            # Probe STT auth with a tiny placeholder file. A 4xx validation error
            # like 400/415/422 means credentials are accepted and endpoint is reachable.
            probe_files = {
                "file": ("probe.webm", io.BytesIO(b"0"), "audio/webm"),
            }
            probe_form = {
                "model_id": ELEVENLABS_STT_MODEL_ID,
            }
            resp = await client.post(
                _elevenlabs_url("speech-to-text"),
                headers=headers,
                data=probe_form,
                files=probe_files,
            )

        if resp.status_code < 400 or resp.status_code in {400, 415, 422}:
            return {
                "status": "ready",
                "available": True,
                "reason": "Voice STT provider reachable",
            }

        reason = _extract_elevenlabs_error(resp)
        if resp.status_code in {401, 403}:
            status = "blocked"
        elif resp.status_code >= 500:
            status = "provider_down"
        else:
            status = "error"

        return {
            "status": status,
            "available": False,
            "reason": reason,
            "upstream_status": resp.status_code,
        }
    except Exception as exc:
        return {
            "status": "network_error",
            "available": False,
            "reason": str(exc),
        }

# ── STT (Speech to Text) ─────────────────────────────────────────────────────
@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    model_id: str | None = Form(None),
):
    """Receives an audio file and returns transcribed text using ElevenLabs STT."""
    if not ELEVENLABS_API_KEY:
        return _missing_key_response()

    selected_model_id = (model_id or ELEVENLABS_STT_MODEL_ID or "scribe_v1").strip()

    raw_content_type = audio.content_type or "application/octet-stream"
    content_type = _normalize_content_type(raw_content_type)
    if content_type not in ALLOWED_AUDIO_CONTENT_TYPES:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Unsupported content type '{raw_content_type}' for audio upload"
            },
        )

    safe_filename = Path(audio.filename or "").name
    ext = Path(safe_filename).suffix.lower()
    if not ext:
        ext = CONTENT_TYPE_DEFAULT_EXTENSIONS.get(content_type, "")
    if not ext or ext not in ALLOWED_AUDIO_EXTENSIONS:
        return JSONResponse(
            status_code=400,
            content={
                "error": (
                    f"Unsupported audio file extension '{ext or '(none)'}'. "
                    f"Allowed: {sorted(ALLOWED_AUDIO_EXTENSIONS)}"
                )
            },
        )

    data = await audio.read()
    if not data:
        return JSONResponse(status_code=400, content={"error": "Audio file is empty"})
    if len(data) > MAX_AUDIO_BYTES:
        return JSONResponse(
            status_code=413,
            content={
                "error": f"Audio file is too large. Max size is {MAX_AUDIO_BYTES // (1024 * 1024)} MB"
            },
        )

    if not safe_filename:
        safe_filename = f"recording{ext}"

    try:
        files = {
            "file": (safe_filename, io.BytesIO(data), content_type),
        }
        form_data = {
            "model_id": selected_model_id,
        }
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
        }
        stt_url = _elevenlabs_url("speech-to-text")
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                stt_url,
                headers=headers,
                data=form_data,
                files=files,
            )

        if resp.status_code >= 400:
            reason = _extract_elevenlabs_error(resp)
            return JSONResponse(
                status_code=resp.status_code,
                content={
                    "transcript": "",
                    "error": f"ElevenLabs STT error: {reason}",
                },
            )

        payload = resp.json()
        transcript = (payload.get("text") or "").strip()
        language = payload.get("language_code", "en")
        return {"transcript": transcript, "language": language}
    except Exception as e:
        return {
            "transcript": "",
            "error": str(e),
        }


# ── TTS (Text to Speech) ─────────────────────────────────────────────────────
@router.post("/tts")
async def text_to_speech(text: str = Form(...)):
    """Converts text to speech using ElevenLabs TTS and returns mp3 audio."""
    if not ELEVENLABS_API_KEY:
        return _missing_key_response()

    if not text.strip():
        return JSONResponse(status_code=400, content={"error": "Text is empty"})

    try:
        payload = {
            "text": text,
            "model_id": ELEVENLABS_TTS_MODEL_ID,
        }
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": AUDIO_MPEG,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                _elevenlabs_url(f"text-to-speech/{ELEVENLABS_TTS_VOICE_ID}"),
                headers=headers,
                json=payload,
            )

        if resp.status_code >= 400:
            return JSONResponse(
                status_code=resp.status_code,
                content={"error": f"ElevenLabs TTS error: {resp.text}"},
            )

        return Response(content=resp.content, media_type=AUDIO_MPEG)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
