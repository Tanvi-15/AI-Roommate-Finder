# AI Roommate Finder

An AI-powered roommate matching application where conversational AI agents autonomously negotiate compatibility on behalf of users - going beyond traditional ML scoring to create realistic, phased conversations between user "clones" that respect hard limits, negotiate flexible preferences, and reach a natural verdict.

---

## What Makes This Different

Most roommate apps (Diggz, SpareRoom, iROOMit) compare questionnaire answers with a static scoring algorithm. This app creates **AI clones of each user** powered by a custom protocol (ACP/1.0) that drives structured, multi-phase conversations between agents. Each clone knows the user's non-negotiables, budget flexibility, lifestyle preferences, and dealbreakers — and uses that context to negotiate just like a real person would.

---

## ACP/1.0 — Agent Compatibility Protocol

ACP is a custom protocol designed for this project that governs how AI agents communicate during roommate compatibility conversations. It replaces monolithic system prompts (~1,800 tokens per turn) with a modular, lazy-loading architecture that cuts token usage by 85-97%.

### Architecture

```
CORE module (~150 tokens)         ← always loaded
  Identity, hard constraints, budget rules, non-negotiables,
  field abbreviation table, message format protocol

LIVING module (~80 tokens)        ← auto-loaded at start
  Location, lease, room type, occupation, drinking

FINANCIAL module (~80 tokens)     ← lazy: <<MOD:FINANCIAL>>
ROUTINES module (~80 tokens)      ← lazy: <<MOD:ROUTINES>>
SOCIAL module (~80 tokens)        ← lazy: <<MOD:SOCIAL>>
LIFESTYLE module (~80 tokens)     ← lazy: <<MOD:LIFESTYLE>>
DEALBREAKERS module (~80 tokens)  ← lazy: <<MOD:DEALBREAKERS>>
```

### Message Types

Agents communicate using structured ACP message types:

| Type | Purpose | Example |
|------|---------|---------|
| `HI` | Introduction | `HI:[loc:Boston/SouthEnd\|bd:800-1200\|rm:Private]` |
| `PFR` | Share preference | `PFR:[slp:night_owl,cln:4(tidy)]` |
| `CNF` | Flag a conflict | `CNF:[cln:gap_3pts(I'm 5, you're 2)]` |
| `FLX` | Offer flexibility | `FLX:[bd:can_stretch_to_1300\|condition:great_fit]` |
| `VRD` | Final verdict | `VRD:[STRONG]\|r=aligned on all priorities\|open=none` |

### Lazy Module Loading

Agents emit `<<MOD:NAME>>` signals during conversation when a topic comes up. The backend detects these, injects the relevant module into the agent's system context, and the agent gains access to that domain's profile data. Each module is injected at most once per conversation.

### Conversation Phases

Agent-to-agent conversations are structured into 4 phases with turn budgets:

| Phase | Turns | Focus |
|-------|-------|-------|
| Introduction | 3 | Location, budget, top priorities. Early incompatibility detection. |
| Exploration | 4 | Sleep, cleanliness, guests, WFH, routines. Identify friction points. |
| Negotiation | 4 | Address conflicts directly. Propose compromises on flexible items. |
| Conclusion | 2 | Reach a verdict: Strong Match, Conditional, or Incompatible. |

Phase hints are injected into each agent's message context so they know what to focus on. Total conversation: ~13 turns max.

### Verdict Bucketing

After conversation, an LLM-powered analysis scores the match across 5 dimensions (overall, finances, lifestyle, personality, logistics) and assigns one of three statuses:

- **Strong Match** — aligned on priorities, no dealbreaker conflicts
- **Conditional Match** — promising but 1-2 unresolved topics need human follow-up
- **Incompatible** — hard non-negotiable conflict detected

---

## App Flow

```
Sign Up (Email/Password or Google OAuth)
    │
    ▼
Fill Questionnaire (7 sections)
    │
    ▼
Home Screen
    ├── Edit Profile ──────── Update questionnaire + photos → "Updating agent" overlay
    ├── Chat with My Clone ── Preview your AI clone in natural language
    ├── Setup Match ────────── Browse profiles (Hinge-style cards) → Like/Pass
    │                          └── Like triggers background agent negotiation
    └── My Matches ─────────── View results: Strong / Conditional / Incompatible
```

### Candidate Filtering

When browsing profiles, the system filters by:
- **Location** — same city or metro area (Boston metro, NYC metro, SF Bay, etc.)
- **Gender preference** — bidirectional cross-match (your preference must accept them AND their preference must accept you)
- **Already seen** — liked/passed profiles are excluded

### Background Negotiation

When a user likes a profile, agents negotiate automatically:
1. Create AI agents for both users from their questionnaire data
2. Run the full 4-phase ACP conversation server-side
3. Auto-analyze compatibility and score across 5 dimensions
4. Save match result — it appears in My Matches with no manual intervention

---

## Architecture

```
AI-Roommate-Finder/
├── auth.py                     # Google OAuth + Email/Password auth
├── session_utils.py            # JWT session tokens (HTTP-only cookies)
├── app.py                      # Streamlit frontend (legacy, still functional)
├── backend/
│   └── server.py               # FastAPI backend, WebSocket, agents, ACP phases
├── frontend/                   # React UI (Vite + shadcn/ui + Framer Motion)
│   └── src/
│       ├── pages/
│       │   ├── Login.tsx        # Email/password + Google OAuth
│       │   ├── Questionnaire.tsx # 7-step profile builder + photo upload
│       │   ├── Home.tsx         # Dashboard with 4 navigation cards
│       │   ├── SetupMatch.tsx   # Hinge-style profile card browsing
│       │   ├── MyClone.tsx      # Chat with your own AI clone
│       │   ├── MyMatches.tsx    # Match results with scores and details
│       │   └── AgentChat.tsx    # Real-time agent conversation viewer
│       ├── contexts/
│       │   └── AuthContext.tsx   # Auth state + session management
│       └── lib/
│           └── api.ts           # API client (auth, agents, matches, photos)
├── shared/
│   ├── config.py               # Environment variables & constants
│   ├── database.py             # MongoDB — users, matches, interactions
│   ├── questionnaire.py        # 7-section questionnaire schema (50+ fields)
│   ├── clone.py                # Clone prompt generator (delegates to ACP)
│   ├── module_registry.py      # ACP/1.0 — modular context system
│   └── groq_client.py          # Groq LLM client (llama-3.3-70b)
└── uploads/
    └── photos/                 # User-uploaded profile photos
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS + shadcn/ui + Framer Motion |
| Backend | FastAPI + WebSockets (uvicorn) |
| Database | MongoDB Atlas |
| LLM | Groq API (llama-3.3-70b-versatile) |
| Auth | Google OAuth 2.0 + Email/Password (bcrypt) |
| Sessions | JWT tokens in HTTP-only cookies (14-day expiry) |

---

## Questionnaire Sections

The questionnaire collects 50+ data points across 7 sections:

1. **Living Preferences** — city, neighborhood, occupation, gender, move-in date, lease type, budget range, budget flexibility, room type, bathroom, roommate gender preference, pets, smoking, drinking
2. **Financial & Utilities** — utilities split, groceries, security deposit, payment style
3. **Daily Routines** — sleep schedule, wake time, cooking, kitchen sharing, bathroom time, common space usage, cleanliness (1-5 scale), cleaning approach
4. **Guests & Social** — noise level, overnight guests, guest notice, parties, introvert/extrovert spectrum (1-5 scale)
5. **Work & Lifestyle** — WFH, quiet hours, schedule predictability, thermostat, hobbies, lifestyle notes
6. **Personality & Conflict** — conflict style, communication style, roommate relationship preference
7. **Dealbreakers & Priorities** — non-negotiables (multi-select), top 3 priorities, flexibility items, custom dealbreakers

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

# Groq API
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# Google OAuth (optional — app works without it)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/callback

# Backend
BACKEND_HOST=localhost
BACKEND_PORT=8000

# Frontend
FRONTEND_URL=http://localhost:8080

# Session
JWT_SECRET=your-random-secret-here

# Debug — set true to see full LLM prompts and ACP module injections
DEBUG=false
```

### 3. Run the app

```bash
# Terminal 1 — FastAPI backend
python "backend /server.py"

# Terminal 2 — React frontend
cd frontend && npm install && npm run dev
```

Open `http://localhost:8080` in your browser.


---

