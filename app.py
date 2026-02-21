# app.py

import streamlit as st
import httpx
import asyncio
import websockets
import json

from shared.questionnaire import LIVING_PREFERENCES, PERSONALITY_QUESTIONS
from shared.database import save_user, get_user, get_all_users, update_last_login, test_connection
from shared.clone import generate_clone_prompt
from shared.ollama_client import check_ollama_running, chat, chat_stream
from shared.config import BACKEND_URL, WS_URL
from auth import get_google_auth_url, exchange_code_for_user, is_google_configured

# Page config
st.set_page_config(page_title="AI Roommate Finder", page_icon="🏠", layout="wide")

# ============== Session State ==============

defaults = {
    "user_data": None,
    "clone_prompt": None,
    "chat_history": [],
    "current_page": "login",
    # Agent chat state
    "user_a": None,
    "user_b": None,
    "room_id": None,
    "agent_conversation": [],
    "analysis_result": None,
    "validation_a": None,
    "validation_b": None,
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ============== API Helpers ==============

def api_get(endpoint: str):
    """GET request to backend"""
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.get(f"{BACKEND_URL}{endpoint}")
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        return None
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def api_post(endpoint: str, data: dict):
    """POST request to backend"""
    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{BACKEND_URL}{endpoint}", json=data)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        return None
    except httpx.HTTPStatusError as e:
        # Show server's error detail (e.g. "Agent X not found")
        detail = ""
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        st.error(f"API Error: {detail}")
        return None
    except Exception as e:
        st.error(f"API Error: {e}")
        return None

def backend_running() -> bool:
    """Check if backend is running"""
    return api_get("/health") is not None

# ============== Page: Login ==============

def render_login():
    st.title("🏠 AI Roommate Finder")
    st.subheader("Find your perfect roommate match")

    query_params = st.query_params
    code = query_params.get("code")
    state = query_params.get("state")

    if code and state:
        user_info = exchange_code_for_user(code, state)
        if user_info:
            email = user_info["email"]
            name = user_info["name"]
            profile_picture = user_info.get("profile_picture_url")
            google_id = user_info.get("google_id")

            existing_user = get_user(email)
            if existing_user:
                update_last_login(email, google_id=google_id, profile_picture=profile_picture)
                st.session_state.user_data = get_user(email)
                st.session_state.current_page = "home"
            else:
                save_user(email=email, name=name, questionnaire={},
                         google_id=google_id, profile_picture=profile_picture)
                st.session_state.user_data = get_user(email)
                st.session_state.current_page = "questionnaire"

            st.query_params.clear()
            st.rerun()
        else:
            st.error("Login failed.")
            st.query_params.clear()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if is_google_configured():
            auth_url, _ = get_google_auth_url()
            if auth_url:
                st.markdown("### Sign in with Google")
                st.link_button("🔐 Continue with Gmail", auth_url, type="primary", use_container_width=True)
        else:
            st.warning("Google OAuth not configured.")

# ============== Page: Questionnaire ==============

def render_questionnaire():
    st.title("📋 Tell us about yourself")
    user = st.session_state.user_data
    st.write(f"Hi **{user['name']}**!")

    with st.form("questionnaire_form"):
        st.header("🏠 Living Preferences")
        living = {}
        for key, q in LIVING_PREFERENCES.items():
            if q["type"] == "text":
                living[key] = st.text_input(q["question"], placeholder=q.get("placeholder", ""))
            elif q["type"] == "number":
                living[key] = st.number_input(q["question"], min_value=q.get("min", 0),
                    max_value=q.get("max", 10000), value=q.get("default", 0))
            elif q["type"] == "select":
                living[key] = st.selectbox(q["question"], q["options"])

        st.divider()
        st.header("😊 Personality")
        personality = {}
        for key, q in PERSONALITY_QUESTIONS.items():
            if q["type"] == "text":
                personality[key] = st.text_input(q["question"], placeholder=q.get("placeholder", ""), key=f"p_{key}")
            elif q["type"] == "select":
                personality[key] = st.selectbox(q["question"], q["options"], key=f"p_{key}")
            elif q["type"] == "slider":
                personality[key] = st.slider(q["question"], q["min"], q["max"], q.get("default", q["min"]), key=f"p_{key}")

        if st.form_submit_button("Save & Continue", type="primary", use_container_width=True):
            questionnaire = {"living": living, "personality": personality}
            save_user(email=user["email"], name=user["name"], questionnaire=questionnaire,
                     google_id=user.get("google_id"), profile_picture=user.get("profile_picture_url"))
            st.session_state.user_data = get_user(user["email"])
            st.session_state.current_page = "home"
            st.rerun()

# ============== Page: Home ==============

def render_home():
    st.title("🏠 AI Roommate Finder")
    user = st.session_state.user_data
    st.markdown(f"Welcome back, **{user['name']}**!")

    # Status checks
    col1, col2, col3 = st.columns(3)
    with col1:
        if backend_running():
            st.success("✅ Backend running")
        else:
            st.error("❌ Backend offline")
            st.code("python backend/server.py", language="bash")
    with col2:
        if check_ollama_running():
            st.success("✅ Ollama running")
        else:
            st.error("❌ Ollama offline")
    with col3:
        if user.get("questionnaire"):
            st.success("✅ Profile complete")
        else:
            st.warning("⚠️ Complete profile")

    st.divider()
    st.subheader("What would you like to do?")

    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💬 Chat with My Clone", use_container_width=True, 
                    disabled=not user.get("questionnaire")):
            st.session_state.current_page = "my_clone"
            st.rerun()
    
    with col2:
        if st.button("👥 Setup Roommate Match", use_container_width=True,
                    disabled=not backend_running()):
            st.session_state.current_page = "setup_match"
            st.rerun()
    
    with col3:
        if st.button("📋 Edit My Profile", use_container_width=True):
            st.session_state.current_page = "questionnaire"
            st.rerun()

# ============== Page: My Clone ==============

def render_my_clone():
    st.title("💬 Chat with Your Clone")
    
    if st.button("← Back to Home"):
        st.session_state.current_page = "home"
        st.rerun()

    user = st.session_state.user_data

    if not check_ollama_running():
        st.error("Ollama not running!")
        return

    if not st.session_state.clone_prompt:
        st.session_state.clone_prompt = generate_clone_prompt(user["name"], user["questionnaire"])

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Clear"):
            st.session_state.chat_history = []
            st.rerun()

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Say something..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full = ""
            for chunk in chat_stream(st.session_state.clone_prompt, st.session_state.chat_history):
                full += chunk
                placeholder.write(full + "▌")
            placeholder.write(full)

        st.session_state.chat_history.append({"role": "assistant", "content": full})

# ============== Page: Setup Match ==============

def render_setup_match():
    st.title("👥 Setup Roommate Match")

    if st.button("← Back to Home"):
        st.session_state.current_page = "home"
        st.rerun()

    # Get users with completed profiles
    all_users = get_all_users()
    users_with_profiles = [u for u in all_users if u.get("questionnaire")]

    if len(users_with_profiles) < 2:
        st.warning(f"Need at least 2 users with profiles. Currently: {len(users_with_profiles)}")
        return

    user_map = {u["email"]: f"{u['name']} ({u['email']})" for u in users_with_profiles}

    col1, col2 = st.columns(2)

    # User A
    with col1:
        st.subheader("🅰️ User A")
        email_a = st.selectbox("Select User A", list(user_map.keys()), 
                               format_func=lambda x: user_map[x], key="sel_a")
        
        if email_a:
            user_a = next(u for u in users_with_profiles if u["email"] == email_a)
            st.session_state.user_a = user_a
            
            if st.button("✅ Validate Clone A"):
                with st.spinner("Validating..."):
                    api_post("/agents", {
                        "user_id": user_a["email"],
                        "name": user_a["name"],
                        "questionnaire": user_a["questionnaire"]
                    })
                    result = api_post(f"/agents/{user_a['email']}/validate", {})
                    st.session_state.validation_a = result
            
            if st.session_state.validation_a:
                v = st.session_state.validation_a
                if v.get("validated"):
                    st.success("✅ Validated!")
                else:
                    st.error("❌ Failed")
                for r in v.get("results", []):
                    with st.expander(r["question"][:40] + "..."):
                        st.write(r.get("response") or r.get("error"))

    # User B
    with col2:
        st.subheader("🅱️ User B")
        remaining = {k: v for k, v in user_map.items() if k != email_a}
        
        if remaining:
            email_b = st.selectbox("Select User B", list(remaining.keys()),
                                   format_func=lambda x: remaining[x], key="sel_b")
            
            if email_b:
                user_b = next(u for u in users_with_profiles if u["email"] == email_b)
                st.session_state.user_b = user_b
                
                if st.button("✅ Validate Clone B"):
                    with st.spinner("Validating..."):
                        api_post("/agents", {
                            "user_id": user_b["email"],
                            "name": user_b["name"],
                            "questionnaire": user_b["questionnaire"]
                        })
                        result = api_post(f"/agents/{user_b['email']}/validate", {})
                        st.session_state.validation_b = result
                
                if st.session_state.validation_b:
                    v = st.session_state.validation_b
                    if v.get("validated"):
                        st.success("✅ Validated!")
                    else:
                        st.error("❌ Failed")
                    for r in v.get("results", []):
                        with st.expander(r["question"][:40] + "..."):
                            st.write(r.get("response") or r.get("error"))

    # Start chat button
    st.divider()
    both_valid = (st.session_state.validation_a and st.session_state.validation_a.get("validated") and
                  st.session_state.validation_b and st.session_state.validation_b.get("validated"))

    if st.session_state.user_a and st.session_state.user_b:
        if st.button("🚀 Start Agent Chat", type="primary", use_container_width=True):
            # Create room
            result = api_post("/rooms", {
                "user_a_id": st.session_state.user_a["email"],
                "user_b_id": st.session_state.user_b["email"]
            })
            if result:
                st.session_state.room_id = result["room_id"]
                st.session_state.agent_conversation = []
                st.session_state.analysis_result = None
                st.session_state.current_page = "agent_chat"
                st.rerun()
            else:
                st.error("Failed to create room. Is backend running?")

# ============== Page: Agent Chat ==============

def render_agent_chat():
    st.title("🤖 Agent-to-Agent Chat")

    if st.button("← Back to Setup"):
        st.session_state.current_page = "setup_match"
        st.rerun()

    user_a = st.session_state.user_a
    user_b = st.session_state.user_b
    room_id = st.session_state.room_id

    if not user_a or not user_b:
        st.error("Please select users first!")
        return

    st.markdown(f"**{user_a['name']}'s Clone** 🗣️ ↔️ 🗣️ **{user_b['name']}'s Clone**")
    st.caption(f"Room: {room_id}")
    st.divider()

    # Display conversation
    for msg in st.session_state.agent_conversation:
        avatar = "🅰️" if msg.get("speaker_id") == "a" else "🅱️"
        with st.chat_message("assistant", avatar=avatar):
            st.markdown(f"**{msg['speaker']}**: {msg['message']}")

    # Controls
    col1, col2, col3 = st.columns(3)

    with col1:
        start_disabled = bool(st.session_state.agent_conversation)
        if st.button("▶️ Start Chat", type="primary", use_container_width=True, disabled=start_disabled):
            run_websocket_chat(room_id)

    with col2:
        analyze_disabled = not st.session_state.agent_conversation
        if st.button("📊 Analyze", use_container_width=True, disabled=analyze_disabled):
            with st.spinner("Analyzing..."):
                # Use REST endpoint for simplicity
                conv_text = "\n".join([f"{m['speaker']}: {m['message']}" for m in st.session_state.agent_conversation])
                
                analysis_prompt = "You are a roommate compatibility analyst."
                analysis_request = f"""
## {user_a['name']}'s Profile:
{user_a['questionnaire']}

## {user_b['name']}'s Profile:
{user_b['questionnaire']}

## Their Conversation:
{conv_text}

Provide:
1. Compatibility Score (0-100)
2. Top 3 Highlights
3. Top 3 Concerns
4. Recommendation
"""
                result = chat(analysis_prompt, [{"role": "user", "content": analysis_request}], stream=False)
                st.session_state.analysis_result = result
                st.rerun()

    with col3:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.agent_conversation = []
            st.session_state.analysis_result = None
            st.session_state.room_id = None
            st.rerun()

    # Show analysis
    if st.session_state.analysis_result:
        st.divider()
        st.header("📊 Compatibility Analysis")
        st.markdown(st.session_state.analysis_result)

def run_websocket_chat(room_id: str):
    """Connect to WebSocket and run agent chat"""
    
    async def connect_and_chat():
        uri = f"{WS_URL}/ws/{room_id}"
        
        try:
            async with websockets.connect(uri) as ws:
                # Send start command
                await ws.send(json.dumps({"action": "start", "num_exchanges": 8}))
                
                # Listen for messages
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    
                    if data["type"] == "agent_message":
                        st.session_state.agent_conversation.append(data["data"])
                    
                    elif data["type"] == "chat_complete":
                        break
                    
                    elif data["type"] == "error":
                        st.error(data.get("message"))
                        break
        
        except Exception as e:
            st.error(f"WebSocket error: {e}")
    
    with st.spinner("🤖 Clones are chatting..."):
        asyncio.run(connect_and_chat())
    
    st.rerun()

# ============== Sidebar ==============

def render_sidebar():
    with st.sidebar:
        st.title("🏠 Roommate Finder")

        if not test_connection():
            st.error("❌ MongoDB")
        else:
            st.success("✅ MongoDB")

        if st.session_state.user_data:
            user = st.session_state.user_data
            if user.get("profile_picture_url"):
                st.image(user["profile_picture_url"], width=60)
            st.write(f"**{user.get('name')}**")
            st.caption(user.get("email"))

            if st.button("Logout", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

            st.divider()

            # Match status
            if st.session_state.user_a:
                st.info(f"🅰️ {st.session_state.user_a['name']}")
            if st.session_state.user_b:
                st.info(f"🅱️ {st.session_state.user_b['name']}")

# ============== Main ==============

def main():
    render_sidebar()

    page = st.session_state.current_page

    if page == "login":
        render_login()
    elif page == "questionnaire":
        render_questionnaire()
    elif page == "home":
        render_home()
    elif page == "my_clone":
        render_my_clone()
    elif page == "setup_match":
        render_setup_match()
    elif page == "agent_chat":
        render_agent_chat()

if __name__ == "__main__":
    main()