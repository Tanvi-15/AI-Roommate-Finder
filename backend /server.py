# backend/server.py
"""
FastAPI backend with WebSocket support for real-time agent chat.

Run with: python backend/server.py
"""

import sys
import os
import asyncio
import uuid
import re
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ollama

from shared.config import BACKEND_PORT, OLLAMA_MODEL, DEBUG, FRONTEND_URL, SESSION_COOKIE_NAME
from shared.database import save_user, get_user, update_last_login
from auth import (
    register_user,
    login_with_password,
    get_google_auth_url,
    exchange_code_for_user,
    is_google_configured,
)
from session_utils import create_session_token, validate_session_token
from shared.clone import generate_clone_prompt, get_clone_intro
from shared.database import (
    save_match_to_db,
    get_matches_for_user_from_db,
    get_match_by_id_from_db,
    get_match_counts_for_user,
)

# ============== FastAPI App ==============

app = FastAPI(title="AI Roommate Finder - Backend")

# CORS: with credentials, origins must be explicit (not "*")
_cors_origins = [FRONTEND_URL, "http://localhost:8501", "http://127.0.0.1:8080", "http://127.0.0.1:8501"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== In-Memory Storage ==============

agents: Dict[str, "Agent"] = {}
chat_rooms: Dict[str, "ChatRoom"] = {}
connections: Dict[str, List[WebSocket]] = {}   # room_id -> [websockets]
# matches are now persisted in MongoDB — no in-memory list needed

# ============== Conversation Phases ==============
#
# Each phase has a turn budget and a context hint injected into the
# agent's next message so it knows how to behave.
#
# Phases are tracked on ChatRoom, not on Agent, because both agents
# need to be in the same phase at the same time.

PHASES = [
    {
        "name": "introduction",
        "label": "Phase 1 — Introduction",
        "turns": 3,         # total turns in this phase (both agents combined)
        "hint": (
            "[PHASE: INTRODUCTION] "
            "Focus on: who you are, location, budget range, and 1–2 top priorities. "
            "If location is clearly incompatible, say so and end politely now."
        ),
    },
    {
        "name": "exploration",
        "label": "Phase 2 — Lifestyle Exploration",
        "turns": 4,
        "hint": (
            "[PHASE: EXPLORATION] "
            "Go deeper on: sleep schedule, cleanliness, guests, WFH, daily routines. "
            "Share your own preferences and ask theirs. Note where you align and where friction exists."
        ),
    },
    {
        "name": "negotiation",
        "label": "Phase 3 — Negotiation",
        "turns": 4,
        "hint": (
            "[PHASE: NEGOTIATION] "
            "Address any friction points directly. Propose specific compromises on flexible items. "
            "If a non-negotiable conflict surfaces, acknowledge it honestly. "
            "Be concrete — 'I could do X if you're okay with Y.'"
        ),
    },
    {
        "name": "conclusion",
        "label": "Phase 4 — Conclusion",
        "turns": 2,
        "hint": (
            "[PHASE: CONCLUSION] "
            "Wrap up the conversation now. You MUST reach one of three verdicts: "
            "STRONG MATCH, CONDITIONAL MATCH (name the 1–2 unresolved topics), "
            "or INCOMPATIBLE (name the specific reason). "
            "Do not trail off. End naturally and conclusively."
        ),
    },
]

TOTAL_PHASE_TURNS = sum(p["turns"] for p in PHASES)  # = 13 turns max


# ============== Match Outcome Detection ==============

def detect_outcome(conversation: List[dict]) -> dict:
    """
    Parse the final messages of the conversation to detect verdict.
    Returns a dict with: status, reason, unresolved_topics
    """
    # Look at the last 3 messages for verdict signals
    tail = " ".join(m["message"].lower() for m in conversation[-3:])

    # Incompatible signals
    incompatible_signals = [
        "difficult fit", "tough fit", "don't think we'd be a good fit",
        "doesn't seem like we're compatible", "not a great match",
        "dealbreaker", "won't work", "false hope", "hope you find someone"
    ]
    # Conditional signals
    conditional_signals = [
        "couple of things", "a few things", "weigh in on", "follow up",
        "worth exploring", "potential here", "discuss directly",
        "conditional", "unresolved"
    ]
    # Strong match signals
    strong_signals = [
        "great fit", "really promising", "flag this as a match",
        "strong match", "sounds perfect", "really well", "love this",
        "so aligned", "think we'd work well"
    ]

    if any(s in tail for s in incompatible_signals):
        # Try to extract the reason — look for "think [X] makes this"
        reason = _extract_reason(tail, "incompatible")
        return {"status": "incompatible", "reason": reason, "unresolved_topics": []}

    if any(s in tail for s in conditional_signals):
        topics = _extract_unresolved_topics(tail)
        return {"status": "conditional", "reason": None, "unresolved_topics": topics}

    if any(s in tail for s in strong_signals):
        return {"status": "strong", "reason": None, "unresolved_topics": []}

    # Fallback — couldn't detect clearly, treat as conditional
    return {"status": "conditional", "reason": "Outcome unclear from conversation", "unresolved_topics": []}


def _extract_reason(text: str, outcome_type: str) -> str:
    """Try to pull the specific reason from the agent's conclusion message."""
    # Look for patterns like "I think X makes this a tough fit"
    patterns = [
        r"think (.{10,80}) makes this",
        r"because (.{10,80})\.",
        r"due to (.{10,80})\.",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip().capitalize()
    return "Incompatible preferences (see conversation for details)"


def _extract_unresolved_topics(text: str) -> List[str]:
    """Try to extract the 1–2 unresolved topics mentioned in a conditional ending."""
    # Look for "specifically X and Y" or "specifically X"
    match = re.search(r"specifically (.{5,120}?)[\.\,\!]", text)
    if match:
        raw = match.group(1)
        # Split on "and" to get individual topics
        topics = [t.strip() for t in re.split(r"\band\b", raw) if t.strip()]
        return topics[:2]  # max 2
    return ["See conversation for details"]


# ============== Pydantic Models ==============

class AgentCreate(BaseModel):
    user_id: str
    name: str
    questionnaire: dict

class RoomCreate(BaseModel):
    user_a_id: str
    user_b_id: str

class MatchFilter(BaseModel):
    user_id: str
    include_incompatible: bool = False


class AuthRegister(BaseModel):
    email: str
    password: str
    name: str
    phone_number: str | None = None


class AuthLogin(BaseModel):
    email: str
    password: str


class AuthGoogleCallback(BaseModel):
    code: str
    state: str


class CloneChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class CloneChatRequest(BaseModel):
    message: str
    history: List[CloneChatMessage] = []


# ============== Agent Class ==============

class Agent:
    """AI Clone of a user"""

    def __init__(self, user_id: str, name: str, questionnaire: dict):
        self.user_id = user_id
        self.name = name
        self.questionnaire = questionnaire
        self.system_prompt = generate_clone_prompt(name, questionnaire)
        self.history: List[dict] = []

    async def get_response(self, message: str) -> str:
        """Get response from Ollama"""
        self.history.append({"role": "user", "content": message})
        messages = [{"role": "system", "content": self.system_prompt}] + self.history

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: ollama.chat(model=OLLAMA_MODEL, messages=messages)
        )
        content = response["message"]["content"]
        self.history.append({"role": "assistant", "content": content})
        return content

    def clear_history(self):
        self.history = []


# ============== ChatRoom Class ==============

class ChatRoom:
    """Manages a phased conversation between two agents"""

    def __init__(self, room_id: str, agent_a: Agent, agent_b: Agent):
        self.room_id = room_id
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.conversation: List[dict] = []
        self.is_running = False
        self.current_phase_index = 0
        self.match_result: Optional[dict] = None  # set after conversation ends

    def _current_phase(self) -> dict:
        idx = min(self.current_phase_index, len(PHASES) - 1)
        return PHASES[idx]

    def _advance_phase(self):
        if self.current_phase_index < len(PHASES) - 1:
            self.current_phase_index += 1

    def _build_phase_message(self, base_message: str) -> str:
        """Prepend the current phase hint to the message so the agent knows the context."""
        hint = self._current_phase()["hint"]
        return f"{hint}\n\n{base_message}"

    async def run_conversation(self, delay: float = 2.0):
        """
        Run a phased agent-to-agent conversation.
        Phase boundaries are determined by turn counts defined in PHASES.
        """
        self.is_running = True
        self.conversation = []
        self.current_phase_index = 0
        self.agent_a.clear_history()
        self.agent_b.clear_history()

        # Track turns within the current phase
        phase_turn_count = 0
        global_turn = 0
        turn = "a"  # agent_a always starts

        # Starter message — goes to agent_a to kick off Phase 1
        current_msg = (
            "Hey! We've both been matched as potential roommates. "
            "Tell me a bit about yourself and what you're looking for?"
        )

        # Broadcast phase start
        await broadcast(self.room_id, {
            "type": "phase_start",
            "phase": self._current_phase()["name"],
            "label": self._current_phase()["label"],
        })

        while self.is_running:
            global_turn += 1
            phase = self._current_phase()

            # Inject phase hint into the message the agent receives
            msg_with_hint = self._build_phase_message(current_msg)

            # Get response from the correct agent
            if turn == "a":
                response = await self.agent_a.get_response(msg_with_hint)
                speaker = self.agent_a.name
                speaker_id = "a"
                # Cross-feed: what A said becomes B's next "user" message
                self.agent_b.history.append({"role": "user", "content": response})
            else:
                response = await self.agent_b.get_response(msg_with_hint)
                speaker = self.agent_b.name
                speaker_id = "b"
                self.agent_a.history.append({"role": "user", "content": response})

            msg = {
                "speaker": speaker,
                "speaker_id": speaker_id,
                "message": response,
                "turn": global_turn,
                "phase": phase["name"],
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.conversation.append(msg)

            await broadcast(self.room_id, {"type": "agent_message", "data": msg})

            current_msg = response
            turn = "b" if turn == "a" else "a"
            phase_turn_count += 1

            # Advance phase if we've used up this phase's turn budget
            if phase_turn_count >= phase["turns"]:
                phase_turn_count = 0
                self._advance_phase()

                # Broadcast phase transition so the UI can show it
                if self.current_phase_index < len(PHASES):
                    await broadcast(self.room_id, {
                        "type": "phase_start",
                        "phase": self._current_phase()["name"],
                        "label": self._current_phase()["label"],
                    })

            # End conversation after conclusion phase completes
            if (self._current_phase()["name"] == "conclusion"
                    and phase_turn_count >= PHASES[-1]["turns"]):
                break

            # Safety valve — never exceed total turns
            if global_turn >= TOTAL_PHASE_TURNS + 2:
                break

            await asyncio.sleep(delay)

        self.is_running = False

        # Detect outcome and save match
        outcome = detect_outcome(self.conversation)
        self.match_result = outcome

        await broadcast(self.room_id, {
            "type": "chat_complete",
            "conversation": self.conversation,
            "outcome": outcome,
        })

    async def analyze(self) -> dict:
        """
        Structured compatibility analysis.
        Returns a dict with sub-scores, highlights, concerns,
        dealbreaker flag, negotiated middle ground, and recommendation tier.
        """
        conv_text = "\n".join(
            [f"{m['speaker']}: {m['message']}" for m in self.conversation]
        )

        system_prompt = """You are an expert roommate compatibility analyst.
Analyze the two profiles and their conversation. You MUST respond in the following
exact JSON format — no extra text, no markdown, just valid JSON:

{
  "scores": {
    "overall": 0,
    "finances": 0,
    "lifestyle": 0,
    "personality": 0,
    "logistics": 0
  },
  "highlights": ["string", "string", "string"],
  "concerns": ["string", "string", "string"],
  "dealbreaker_detected": false,
  "dealbreaker_detail": "",
  "middle_ground": ["string", "string"],
  "recommendation": "strong|conditional|incompatible",
  "recommendation_summary": "string (2-3 sentences)"
}

Scores are 0–100. Be specific — reference actual details from the profiles and conversation.
dealbreaker_detected is true only if a hard non-negotiable conflict was found.
middle_ground lists concrete compromises that could make a conditional match work.
recommendation must be exactly one of: strong, conditional, incompatible."""

        request = f"""
## {self.agent_a.name}'s Profile:
{self.agent_a.questionnaire}

## {self.agent_b.name}'s Profile:
{self.agent_b.questionnaire}

## Their Conversation:
{conv_text}
"""
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: ollama.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request},
                ],
            )
        )
        raw = response["message"]["content"]

        # Parse JSON — fall back to raw string if the model doesn't comply
        import json
        try:
            # Strip any accidental markdown fences
            cleaned = re.sub(r"```json|```", "", raw).strip()
            return {"structured": True, "data": json.loads(cleaned)}
        except Exception:
            return {"structured": False, "data": raw}

    def stop(self):
        self.is_running = False


# ============== WebSocket Helpers ==============

async def broadcast(room_id: str, message: dict):
    if room_id in connections:
        dead = []
        for ws in connections[room_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            connections[room_id].remove(ws)


# ============== Match Storage Helpers ==============

def save_match(room: "ChatRoom", analysis: dict) -> dict:
    """
    Build match record and persist to MongoDB.
    Called after analyze() completes.
    """
    outcome = room.match_result or detect_outcome(room.conversation)
    record = {
        "match_id": room.room_id,
        "user_a_id": room.agent_a.user_id,
        "user_a_name": room.agent_a.name,
        "user_b_id": room.agent_b.user_id,
        "user_b_name": room.agent_b.name,
        "status": outcome["status"],                         # strong | conditional | incompatible
        "reason": outcome.get("reason"),                     # for incompatible
        "unresolved_topics": outcome.get("unresolved_topics", []),  # for conditional
        "analysis": analysis,
        "conversation": room.conversation,
        "created_at": datetime.utcnow().isoformat(),
    }
    save_match_to_db(record)
    return record


def get_matches_for_user(user_id: str, include_incompatible: bool = False) -> list:
    """Fetch matches for a user from MongoDB."""
    return get_matches_for_user_from_db(user_id, include_incompatible)


# ============== Auth Endpoints ==============

def _set_session_cookie(response: JSONResponse, email: str) -> None:
    """Set the session cookie on the response."""
    token = create_session_token(email)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=14 * 24 * 3600,  # 14 days
    )


def _get_current_user(request: Request):
    """Return current user from session or raise 401."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    email = validate_session_token(token) if token else None
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = get_user(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.post("/auth/register")
async def auth_register(data: AuthRegister):
    result = register_user(
        email=data.email,
        password=data.password,
        name=data.name,
        phone_number=data.phone_number,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    user = result["user"]
    resp = JSONResponse(content={"user": user})
    _set_session_cookie(resp, user["email"])
    return resp


@app.post("/auth/login")
async def auth_login(data: AuthLogin):
    result = login_with_password(data.email, data.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    user = result["user"]
    resp = JSONResponse(content={"user": user})
    _set_session_cookie(resp, user["email"])
    return resp


@app.get("/auth/google/url")
async def auth_google_url():
    if not is_google_configured():
        return {"url": None}
    url, _ = get_google_auth_url()
    return {"url": url}


@app.post("/auth/google/callback")
async def auth_google_callback(data: AuthGoogleCallback):
    user_info = exchange_code_for_user(data.code, data.state)
    if not user_info:
        raise HTTPException(status_code=401, detail="Google login failed")
    email = user_info["email"]
    existing = get_user(email)
    if existing:
        update_last_login(
            email,
            google_id=user_info.get("google_id"),
            profile_picture=user_info.get("profile_picture_url"),
        )
        user = get_user(email)
    else:
        save_user(
            email=email,
            name=user_info["name"],
            questionnaire={},
            google_id=user_info.get("google_id"),
            profile_picture=user_info.get("profile_picture_url"),
        )
        user = get_user(email)
    resp = JSONResponse(content={"user": user})
    _set_session_cookie(resp, email)
    return resp


@app.get("/auth/me")
async def auth_me(request: Request):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    email = validate_session_token(token) if token else None
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = get_user(email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {"user": user}


@app.post("/auth/logout")
async def auth_logout():
    resp = JSONResponse(content={"ok": True})
    resp.delete_cookie(SESSION_COOKIE_NAME)
    return resp


# ============== REST Endpoints ==============

@app.get("/")
async def root():
    return {"status": "running", "agents": len(agents), "rooms": len(chat_rooms)}

@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/clone/intro")
async def clone_intro(request: Request):
    """Get the clone's greeting message for the current user. Requires auth."""
    user = _get_current_user(request)
    if not user.get("questionnaire") or not isinstance(user["questionnaire"], dict):
        raise HTTPException(
            status_code=400,
            detail="Complete your profile (questionnaire) first.",
        )
    intro = get_clone_intro(user.get("name", "User"))
    return {"intro": intro}


@app.post("/clone/chat")
async def clone_chat(request: Request, data: CloneChatRequest):
    """Chat with the current user's AI clone. Requires auth and a completed questionnaire."""
    user = _get_current_user(request)
    if not user.get("questionnaire") or not isinstance(user["questionnaire"], dict):
        raise HTTPException(
            status_code=400,
            detail="Complete your profile (questionnaire) first so your clone can represent you.",
        )
    agent = Agent(
        user_id=user["email"],
        name=user.get("name", "User"),
        questionnaire=user["questionnaire"],
    )
    # Restore conversation history so the clone has context
    agent.history = [{"role": m.role, "content": m.content} for m in data.history]
    reply = await agent.get_response(data.message)
    return {"reply": reply}


@app.post("/agents")
async def create_agent(data: AgentCreate):
    agent = Agent(data.user_id, data.name, data.questionnaire)
    agents[data.user_id] = agent
    return {"status": "created", "user_id": data.user_id, "name": data.name}

@app.get("/agents")
async def list_agents():
    return [{"user_id": a.user_id, "name": a.name} for a in agents.values()]

@app.post("/agents/{user_id}/validate")
async def validate_agent(user_id: str):
    if user_id not in agents:
        raise HTTPException(404, "Agent not found")

    agent = agents[user_id]
    test_questions = [
        "What's your budget and where are you looking?",
        "Are you a morning person or night owl?",
        "How do you feel about guests and overnight visitors?",
    ]

    results = []
    for q in test_questions:
        try:
            messages = [
                {"role": "system", "content": agent.system_prompt},
                {"role": "user", "content": q},
            ]
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(
                None,
                lambda: ollama.chat(model=OLLAMA_MODEL, messages=messages)
            )
            results.append({"question": q, "response": resp["message"]["content"], "status": "success"})
        except Exception as e:
            results.append({"question": q, "error": str(e), "status": "failed"})

    return {
        "user_id": user_id,
        "name": agent.name,
        "validated": all(r["status"] == "success" for r in results),
        "results": results,
    }

@app.post("/rooms")
async def create_room(data: RoomCreate):
    if data.user_a_id not in agents:
        raise HTTPException(404, f"Agent for {data.user_a_id} not found. Re-validate Clone A first.")
    if data.user_b_id not in agents:
        raise HTTPException(404, f"Agent for {data.user_b_id} not found. Re-validate Clone B first.")

    room_id = str(uuid.uuid4())[:8]
    room = ChatRoom(room_id, agents[data.user_a_id], agents[data.user_b_id])
    chat_rooms[room_id] = room

    return {
        "room_id": room_id,
        "agent_a": agents[data.user_a_id].name,
        "agent_b": agents[data.user_b_id].name,
        "total_turns": TOTAL_PHASE_TURNS,
        "phases": [{"name": p["name"], "label": p["label"], "turns": p["turns"]} for p in PHASES],
    }

@app.get("/rooms/{room_id}")
async def get_room(room_id: str):
    if room_id not in chat_rooms:
        raise HTTPException(404, "Room not found")
    room = chat_rooms[room_id]
    return {
        "room_id": room_id,
        "agent_a": room.agent_a.name,
        "agent_b": room.agent_b.name,
        "is_running": room.is_running,
        "messages": len(room.conversation),
        "current_phase": room._current_phase()["name"],
        "match_result": room.match_result,
    }

@app.get("/matches")
async def list_matches(user_id: str, include_incompatible: bool = False):
    """Get all matches for a user. Pass include_incompatible=true to see rejected ones."""
    return get_matches_for_user_from_db(user_id, include_incompatible)

@app.get("/matches/counts")
async def match_counts(user_id: str):
    """Get match status counts for a user — useful for badge numbers in UI."""
    return get_match_counts_for_user(user_id)

@app.get("/matches/{match_id}")
async def get_match(match_id: str):
    """Get a specific match by ID."""
    match = get_match_by_id_from_db(match_id)
    if not match:
        raise HTTPException(404, "Match not found")
    return match


# ============== WebSocket Endpoint ==============

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()

    if room_id not in connections:
        connections[room_id] = []
    connections[room_id].append(websocket)

    print(f"[WS] Client connected to room {room_id}")

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "start":
                if room_id not in chat_rooms:
                    await websocket.send_json({"type": "error", "message": "Room not found"})
                    continue

                room = chat_rooms[room_id]

                await websocket.send_json({
                    "type": "started",
                    "agent_a": room.agent_a.name,
                    "agent_b": room.agent_b.name,
                    "total_turns": TOTAL_PHASE_TURNS,
                    "phases": [{"name": p["name"], "label": p["label"], "turns": p["turns"]} for p in PHASES],
                })

                asyncio.create_task(room.run_conversation())

            elif action == "stop":
                if room_id in chat_rooms:
                    chat_rooms[room_id].stop()
                    await broadcast(room_id, {"type": "stopped"})

            elif action == "analyze":
                if room_id not in chat_rooms:
                    continue
                room = chat_rooms[room_id]

                await broadcast(room_id, {"type": "analyzing"})
                analysis = await room.analyze()

                # Save to matches dataset
                match_record = save_match(room, analysis)

                await broadcast(room_id, {
                    "type": "analysis",
                    "result": analysis,
                    "match_id": match_record["match_id"],
                    "status": match_record["status"],
                    "reason": match_record.get("reason"),
                    "unresolved_topics": match_record.get("unresolved_topics", []),
                })

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected from room {room_id}")
        if room_id in connections and websocket in connections[room_id]:
            connections[room_id].remove(websocket)


# ============== Run Server ==============

def start_server():
    import uvicorn
    print(f"\n🚀 Starting backend server on http://localhost:{BACKEND_PORT}")
    print(f"   WebSocket: ws://localhost:{BACKEND_PORT}/ws/{{room_id}}")
    print(f"   Phases: {' → '.join(p['label'] for p in PHASES)}\n")
    uvicorn.run(app, host="0.0.0.0", port=BACKEND_PORT)

if __name__ == "__main__":
    start_server()