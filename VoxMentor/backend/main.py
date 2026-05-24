"""
VoxMentor FastAPI Backend — Main Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import httpx

from routers import chat, code, visualize, progress, skill_tree, practice, journal, voice, user, learning_plus
from db import get_client
from config import OPENROUTER_BASE_URL, OPENROUTER_API_KEY, CORS_ORIGINS
from services.provider_router import resolve_provider


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("VoxMentor backend starting...")
    yield
    print("VoxMentor backend shutting down.")


app = FastAPI(
    title="VoxMentor API",
    description="AI-Powered Voice Coding Tutor Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(user.router)
app.include_router(chat.router)
app.include_router(code.router)
app.include_router(visualize.router)
app.include_router(progress.router)
app.include_router(skill_tree.router)
app.include_router(practice.router)
app.include_router(journal.router)
app.include_router(voice.router)
app.include_router(learning_plus.router)


@app.get("/")
async def root():
    return {
        "app": "VoxMentor",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "routes": [
            "/api/users", "/api/chat", "/api/code",
            "/api/visualize", "/api/progress", "/api/skill-tree",
            "/api/practice", "/api/journal", "/api/voice", "/api/learning-plus",
        ],
    }


@app.get("/health")
async def health():
    llm_provider = resolve_provider()

    services = {
        "database": "down",
        "llm": "down",
    }

    # MongoDB health
    try:
        await get_client().admin.command("ping")
        services["database"] = "up"
    except Exception:
        services["database"] = "down"

    # LLM provider health (OpenRouter only)
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(
                f"{OPENROUTER_BASE_URL}/models",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            )
            services["llm"] = "up" if resp.status_code < 500 else "down"
    except Exception:
        services["llm"] = "down"

    overall = "healthy" if services["database"] == "up" and services["llm"] == "up" else "degraded"
    return {"status": overall, "services": services, "llm_provider": llm_provider}
