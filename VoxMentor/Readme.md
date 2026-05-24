# VoxMentor

VoxMentor is a full-stack AI coding mentor platform that combines guided learning, practice evaluation, code visualization, and voice-enabled tutoring.

This repository contains a complete implementation with:
- FastAPI backend (`backend/`)
- React + Vite frontend (`frontend/`)
- MongoDB persistence
- OpenRouter-powered AI tutoring
- ElevenLabs voice integration (STT + TTS)

---

## 1) Project Overview

VoxMentor provides an end-to-end learning workflow:

1. **Learn concepts** through module-based skill trees
2. **Ask doubts** in context via AI chatbot
3. **Practice daily challenges** personalized by profile/progress
4. **Submit code** and receive AI improvement/hint feedback
5. **Visualize algorithms** step-by-step with custom input
6. **Track progress** with calibrated proficiency metrics, XP, streaks, badges
7. **Use voice** to speak to tutor and hear responses

---

## 2) Implementation Architecture

### Backend (`backend/`)

- **Framework:** FastAPI
- **Database:** MongoDB (Motor async client)
- **Core folders:**
  - `routers/` → API surface by domain
  - `services/` → AI orchestration, learning logic, execution helpers
  - `models/` → Pydantic/data schema layer
  - `scripts/` → utility tasks (example: admin bootstrap)

### Frontend (`frontend/`)

- **Framework:** React + Vite
- **API client:** `src/api.js`
- **Pages:** auth, chat, dashboard, journal, practice, visualizer, progress, skill tree, settings
- **State:** auth context + page-level state

---

## 3) Implemented Modules

### A) Chat Tutor
- Streaming chat responses
- Mode-aware routing (tutor/chat/code)
- Session memory support

### B) Playground + Code Help
- Run code
- AI explain and AI help endpoints
- Error explanation and guidance

### C) Visualizer
- Preset and custom input generation
- Deterministic visualization steps for major categories
- Binary-search target support
- Live code/output panel alongside animation

### D) Practice Engine
- Dynamic challenge generation based on expertise/progress
- Submission analysis with dual feedback mode:
  - Correct solutions → improvement suggestions
  - Incorrect solutions → hint-focused guidance

### E) Skill Tree (Module-based Learning)
- Skill → module progression
- Dynamic module explanation generation
- In-module doubt chatbot
- Module test gating
- Final skill assessment to unlock next skill

### F) Progress & Analytics
- XP, streak, level, badges
- Topic-level tracking (attempts/correct/time/mastery)
- **Calibrated proficiency metrics** (accuracy + confidence + mastery weighting)

### G) Voice
- Speech-to-text (ElevenLabs)
- Text-to-speech (ElevenLabs)

---

## 4) API Surface

Primary route groups:

- `/api/users`
- `/api/chat`
- `/api/code`
- `/api/visualize`
- `/api/progress`
- `/api/skill-tree`
- `/api/practice`
- `/api/journal`
- `/api/voice`

Health and docs:
- `/health`
- `/docs`

---

## 5) Local Setup

### Prerequisites

- Windows 10/11
- Python 3.11+ (3.12 recommended)
- Node.js 18+
- npm
- MongoDB (local or Atlas)
- OpenRouter API key
- ElevenLabs API key (for voice)

### Backend setup

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Frontend setup

```powershell
cd frontend
npm install
```

### Environment

Create/update `backend/.env` with at least:

```dotenv
MONGO_URI=mongodb://localhost:27017/
DB_NAME=voxmentor

OPENROUTER_API_KEY=your_openrouter_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
```

---

## 6) Run Application

From repository root, use two terminals:

Terminal 1:
```powershell
.\start-backend.bat
```

Terminal 2:
```powershell
.\start-frontend.bat
```

Default URLs:
- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

---

## 7) Development Workflow

1. Add/modify backend route in `backend/routers/`
2. Add service logic in `backend/services/`
3. Update frontend API in `frontend/src/api.js`
4. Build/adjust UI page/component
5. Validate:
   - backend compile checks
   - frontend `npm run build`
   - endpoint smoke tests

---

## 8) Troubleshooting

- **`ERR_CONNECTION_REFUSED` (frontend → backend):** ensure backend is running on configured host/port
- **MongoDB down in `/health`:** verify `MONGO_URI`
- **LLM unavailable:** verify `OPENROUTER_API_KEY`
- **Voice auth failures:** verify `ELEVENLABS_API_KEY`
- **Stale backend behavior after code change:** restart backend process

---

## 9) Security Notes

- Keep all secrets in `backend/.env`
- Never commit real API keys or production credentials
- Rotate keys if exposed
