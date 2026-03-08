# 🏠 AI Roommate Finder

An AI-powered roommate matching application where conversational AI agents autonomously chat with each other to assess compatibility — going beyond traditional ML scoring to create realistic, negotiation-aware conversations between user "clones".

---

## 🚀 What Makes This Different

Most roommate apps (Diggz, SpareRoom, iROOMit) compare questionnaire answers mathematically. This app creates **AI clones of each user** that actually talk to each other, negotiate flexible preferences, respect hard limits, and reach a natural verdict — just like a real roommate conversation would.

---

## Architecture

```
AI-Roommate-Finder/
├── app.py                  # Streamlit frontend (multi-page UI)
├── auth.py                 # Google OAuth + Email/Password authentication
├── session_utils.py        # JWT session tokens for cookie persistence
├── backend/
│   └── server.py           # FastAPI backend + WebSocket + Auth API
├── frontend/               # React UI (Vite + shadcn/ui) — alternative to Streamlit
├── shared/
│   ├── config.py           # Environment variables & constants
│   ├── database.py         # MongoDB — users + matches collections
│   ├── questionnaire.py    # All question definitions (7 sections)
│   ├── clone.py            # AI clone prompt generator
│   └── ollama_client.py    # Ollama LLM wrapper
└── data/
    └── users.json          # (legacy, replaced by MongoDB)
```

### Tech Stack
- **Frontend**: Streamlit
- **Backend**: FastAPI + WebSockets (uvicorn)
- **Database**: MongoDB Atlas
- **LLM**: Ollama (local) — default model: `gemma3:latest`
- **Auth**: Google OAuth 2.0 + Email/Password (bcrypt)
- **Sessions**: JWT tokens in cookies

---

## Setup

### 1. Clone & install dependencies

```bash
git clone <repo-url>
cd AI-Roommate-Finder
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the project root:

```env
# MongoDB Atlas
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/
MONGODB_DATABASE=roommate_finder

# Google OAuth (optional — app works without it)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8501/

# Ollama
OLLAMA_MODEL=gemma3:latest

# Backend
BACKEND_HOST=localhost
BACKEND_PORT=8000

# Session
JWT_SECRET=your-random-secret-here

# Debug — set true to see full LLM prompts in terminal
DEBUG=false
```

### 3. Start Ollama

```bash
ollama serve
ollama pull gemma3  # if not already pulled
```

### 4. Run the app

**Option A — React frontend (recommended)**

```bash
# Terminal 1 — FastAPI backend
python "backend /server.py"

# Terminal 2 — React frontend
cd frontend && npm install && npm run dev
```

Open `http://localhost:8080` in your browser.

**Option B — Streamlit frontend**

```bash
# Terminal 1 — FastAPI backend
python "backend /server.py"

# Terminal 2 — Streamlit frontend
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

**Google OAuth:** Set `GOOGLE_REDIRECT_URI` to match your frontend:
- React: `http://localhost:8080/auth/callback`
- Streamlit: `http://localhost:8501/`


