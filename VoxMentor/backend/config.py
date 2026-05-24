import os
from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str, default: list[str]) -> list[str]:
	if not value:
		return default
	return [item.strip() for item in value.split(",") if item.strip()]

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "voxmentor")

API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = _split_csv(
	os.getenv("CORS_ORIGINS", ""),
	[
		"http://localhost:5173",
		"http://127.0.0.1:5173",
		"http://localhost:3000",
		"http://127.0.0.1:3000",
		f"http://localhost:{API_PORT}",
		f"http://127.0.0.1:{API_PORT}",
	],
)

AI_PROVIDER = "openrouter"

OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "http://localhost")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "VoxMentor")

MODEL_CODE = os.getenv("MODEL_CODE", "qwen/qwen3-coder-480b-a35b-instruct")
MODEL_TUTOR = os.getenv("MODEL_TUTOR", "meta-llama/llama-3.3-70b-instruct")
MODEL_CHAT = os.getenv("MODEL_CHAT", "qwen/qwen3-next-80b-a3b-instruct")
MODEL_ROUTER = os.getenv("MODEL_ROUTER", "meta-llama/llama-3.3-70b-instruct")

MODEL_CODE_TEMPERATURE = float(os.getenv("MODEL_CODE_TEMPERATURE", "0.2"))
MODEL_CODE_TOP_P = float(os.getenv("MODEL_CODE_TOP_P", "0.9"))
MODEL_CODE_MAX_TOKENS = int(os.getenv("MODEL_CODE_MAX_TOKENS", "1200"))

MODEL_TUTOR_TEMPERATURE = float(os.getenv("MODEL_TUTOR_TEMPERATURE", "0.6"))
MODEL_TUTOR_TOP_P = float(os.getenv("MODEL_TUTOR_TOP_P", "0.9"))
MODEL_TUTOR_MAX_TOKENS = int(os.getenv("MODEL_TUTOR_MAX_TOKENS", "1500"))

MODEL_CHAT_TEMPERATURE = float(os.getenv("MODEL_CHAT_TEMPERATURE", "0.5"))
MODEL_CHAT_TOP_P = float(os.getenv("MODEL_CHAT_TOP_P", "0.9"))
MODEL_CHAT_MAX_TOKENS = int(os.getenv("MODEL_CHAT_MAX_TOKENS", "1000"))

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_BASE_URL = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io")
ELEVENLABS_TTS_VOICE_ID = os.getenv("ELEVENLABS_TTS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_TTS_MODEL_ID = os.getenv("ELEVENLABS_TTS_MODEL_ID", "eleven_multilingual_v2")
ELEVENLABS_STT_MODEL_ID = os.getenv("ELEVENLABS_STT_MODEL_ID", "scribe_v1")

SECRET_KEY = os.getenv("SECRET_KEY", "voxmentor-secret-key-change-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7   # 7 days

SUPPORTED_LANGUAGES = ["python", "javascript", "c", "cpp"]
CODE_TIMEOUT = 5   # seconds
