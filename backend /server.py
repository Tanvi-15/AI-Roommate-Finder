# backend/server.py
"""
FastAPI backend with WebSocket support for real-time agent chat.

Run with: python backend/server.py
"""

import sys
import os
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ollama

from shared.config import BACKEND_PORT, OLLAMA_MODEL, DEBUG
from shared.clone import generate_clone_prompt

# ============== FastAPI App ==============

app = FastAPI(title="AI Roommate Finder - Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============== In-Memory Storage ==============

agents: Dict[str, "Agent"] = {}
chat_rooms: Dict[str, "ChatRoom"] = {}
connections: Dict[str, List[WebSocket]] = {}  # room_id -> [websockets]

# ============== Models ==============

class AgentCreate(BaseModel):
    user_id: str
    name: str
    questionnaire: dict

class RoomCreate(BaseModel):
    user_a_id: str
    user_b_id: str

# Pydantic automatically:
# 1. Validates incoming JSON
# 2. Converts to Python object
# 3. Returns 422 error if validation fails

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
        
        # Run in executor to not block
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
    """Manages conversation between two agents"""
    
    def __init__(self, room_id: str, agent_a: Agent, agent_b: Agent):
        self.room_id = room_id
        self.agent_a = agent_a
        self.agent_b = agent_b
        self.conversation: List[dict] = []
        self.is_running = False
    
    async def run_conversation(self, num_exchanges: int = 8, delay: float = 2.0):
        """Run agent-to-agent conversation"""
        self.is_running = True
        self.conversation = []
        self.agent_a.clear_history()
        self.agent_b.clear_history()
        
        # Starter message
        starter = "Hey! We might be potential roommates. Tell me about yourself and what you're looking for?"
        current_msg = starter
        turn = "a"
        
        for i in range(num_exchanges):
            if not self.is_running:
                break
            
            if turn == "a":
                response = await self.agent_a.get_response(current_msg)
                speaker = self.agent_a.name
                speaker_id = "a"
                # Feed response to agent B's history
                self.agent_b.history.append({"role": "user", "content": response})
            else:
                response = await self.agent_b.get_response(current_msg)
                speaker = self.agent_b.name
                speaker_id = "b"
                # Feed response to agent A's history
                self.agent_a.history.append({"role": "user", "content": response})
            
            msg = {
                "speaker": speaker,
                "speaker_id": speaker_id,
                "message": response,
                "turn": i + 1,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.conversation.append(msg)
            
            # Broadcast to connected clients
            await broadcast(self.room_id, {"type": "agent_message", "data": msg})
            
            current_msg = response
            turn = "b" if turn == "a" else "a"
            
            await asyncio.sleep(delay)
        
        self.is_running = False
        await broadcast(self.room_id, {"type": "chat_complete", "conversation": self.conversation})
    
    async def analyze(self) -> str:
        """Analyze compatibility"""
        conv_text = "\n".join([f"{m['speaker']}: {m['message']}" for m in self.conversation])
        
        prompt = """You are a roommate compatibility analyst. Based on the conversation and profiles, provide:

1. **Compatibility Score**: X/100
2. **Top 3 Highlights**: Things they agree on
3. **Top 3 Concerns**: Potential friction points
4. **Recommendation**: Would they make good roommates?

Be specific and reference actual details."""

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
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": request}
                ]
            )
        )
        return response["message"]["content"]
    
    def stop(self):
        self.is_running = False

# ============== WebSocket Helpers ==============

async def broadcast(room_id: str, message: dict):
    """Send message to all clients in a room"""
    if room_id in connections:
        dead = []
        for ws in connections[room_id]:
            try:
                await ws.send_json(message)
            except:
                dead.append(ws)
        for ws in dead:
            connections[room_id].remove(ws)

# ============== REST Endpoints ==============

@app.get("/")
async def root():
    return {"status": "running", "agents": len(agents), "rooms": len(chat_rooms)}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/agents")
async def create_agent(data: AgentCreate):
    """Register an agent"""
    agent = Agent(data.user_id, data.name, data.questionnaire)
    agents[data.user_id] = agent
    return {"status": "created", "user_id": data.user_id, "name": data.name}

@app.get("/agents")
async def list_agents():
    """List all agents"""
    return [{"user_id": a.user_id, "name": a.name} for a in agents.values()]

@app.post("/agents/{user_id}/validate")
async def validate_agent(user_id: str):
    """Validate agent with test questions"""
    if user_id not in agents:
        raise HTTPException(404, "Agent not found")
    
    agent = agents[user_id]
    test_questions = [
        "What's your budget for rent?",
        "Are you a morning person or night owl?",
        "How do you feel about guests?"
    ]
    
    results = []
    for q in test_questions:
        try:
            # Don't save to history for validation
            messages = [
                {"role": "system", "content": agent.system_prompt},
                {"role": "user", "content": q}
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
        "results": results
    }

@app.post("/rooms")
async def create_room(data: RoomCreate):
    """Create a chat room. Expects user_a_id and user_b_id to be emails.
    Agents must exist - create them via POST /agents first, or validate both clones in the UI."""
    if data.user_a_id not in agents:
        raise HTTPException(
            404,
            f"Agent for {data.user_a_id} not found. Restart cleared agents? Re-validate Clone A first."
        )
    if data.user_b_id not in agents:
        raise HTTPException(
            404,
            f"Agent for {data.user_b_id} not found. Restart cleared agents? Re-validate Clone B first."
        )
    
    room_id = str(uuid.uuid4())[:8]
    room = ChatRoom(room_id, agents[data.user_a_id], agents[data.user_b_id])
    chat_rooms[room_id] = room
    
    return {
        "room_id": room_id,
        "agent_a": agents[data.user_a_id].name,
        "agent_b": agents[data.user_b_id].name
    }

@app.get("/rooms/{room_id}")
async def get_room(room_id: str):
    """Get room status"""
    if room_id not in chat_rooms:
        raise HTTPException(404, "Room not found")
    room = chat_rooms[room_id]
    return {
        "room_id": room_id,
        "agent_a": room.agent_a.name,
        "agent_b": room.agent_b.name,
        "is_running": room.is_running,
        "messages": len(room.conversation)
    }

# ============== WebSocket Endpoint ==============

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket for real-time updates"""
    await websocket.accept()
    
    # Add to connections
    if room_id not in connections:
        connections[room_id] = []
    connections[room_id].append(websocket)
    
    print(f"[WS] Client connected to room {room_id}")
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "start":
                # Start agent conversation
                if room_id not in chat_rooms:
                    await websocket.send_json({"type": "error", "message": "Room not found"})
                    continue
                
                room = chat_rooms[room_id]
                num = data.get("num_exchanges", 8)
                
                await websocket.send_json({
                    "type": "started",
                    "agent_a": room.agent_a.name,
                    "agent_b": room.agent_b.name
                })
                
                # Run in background
                asyncio.create_task(room.run_conversation(num_exchanges=num))
            
            elif action == "stop":
                if room_id in chat_rooms:
                    chat_rooms[room_id].stop()
                    await broadcast(room_id, {"type": "stopped"})
            
            elif action == "analyze":
                if room_id not in chat_rooms:
                    continue
                
                await broadcast(room_id, {"type": "analyzing"})
                analysis = await chat_rooms[room_id].analyze()
                await broadcast(room_id, {"type": "analysis", "result": analysis})
    
    except WebSocketDisconnect:
        print(f"[WS] Client disconnected from room {room_id}")
        if room_id in connections and websocket in connections[room_id]:
            connections[room_id].remove(websocket)

# ============== Run Server ==============

def start_server():
    import uvicorn
    print(f"\n🚀 Starting backend server on http://localhost:{BACKEND_PORT}")
    print(f"   WebSocket available at ws://localhost:{BACKEND_PORT}/ws/{{room_id}}\n")
    uvicorn.run(app, host="0.0.0.0", port=BACKEND_PORT)

if __name__ == "__main__":
    start_server()