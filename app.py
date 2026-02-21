# app.py

import streamlit as st
import httpx
import asyncio
import websockets
import json
import threading
import queue

from streamlit_cookies_manager import CookieManager

from shared.questionnaire import get_all_questions, get_section_labels, validate_questionnaire
from shared.database import (
    save_user, get_user, get_all_users,
    update_last_login, test_connection,
)
from shared.clone import generate_clone_prompt
from shared.ollama_client import check_ollama_running, chat, chat_stream
from shared.config import BACKEND_URL, WS_URL, SESSION_COOKIE_NAME
from auth import (
    get_google_auth_url, exchange_code_for_user,
    is_google_configured, register_user, login_with_password,
)
from session_utils import create_session_token, validate_session_token

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(page_title="AI Roommate Finder", page_icon="🏠", layout="wide")

# ─────────────────────────────────────────────
# COOKIE MANAGER  (must run before any session restore)
# ─────────────────────────────────────────────

cookies = CookieManager(prefix="roommate_finder/")
if not cookies.ready():
    with st.spinner("Loading..."):
        st.stop()

# ─────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────

defaults = {
    "user_data": None,
    "clone_prompt": None,
    "chat_history": [],
    "current_page": "login",
    # Agent match state
    "user_a": None,
    "user_b": None,
    "room_id": None,
    "agent_conversation": [],
    "current_phase": None,
    "chat_outcome": None,           # strong | conditional | incompatible
    "analysis_result": None,        # structured dict from server
    "validation_a": None,
    "validation_b": None,
    # Login UI state
    "login_tab": "google",          # google | email
    "email_mode": "login",          # login | register
}

for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ─────────────────────────────────────────────
# SESSION RESTORE FROM COOKIE
# ─────────────────────────────────────────────

if st.session_state.user_data is None:
    token = cookies.get(SESSION_COOKIE_NAME)
    email = validate_session_token(token) if token else None
    if email:
        user = get_user(email)
        if user:
            st.session_state.user_data = user
            st.session_state.current_page = "home"
            st.rerun()

# ─────────────────────────────────────────────
# API HELPERS
# ─────────────────────────────────────────────

def api_get(endpoint: str, params: dict = None):
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.get(f"{BACKEND_URL}{endpoint}", params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        return None
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def api_post(endpoint: str, data: dict):
    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{BACKEND_URL}{endpoint}", json=data)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        return None
    except httpx.HTTPStatusError as e:
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
    return api_get("/health") is not None


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

STATUS_BADGE = {
    "strong":       "🟢 Strong Match",
    "conditional":  "🟡 Conditional Match",
    "incompatible": "🔴 Incompatible",
}

STATUS_COLOR = {
    "strong":       "green",
    "conditional":  "orange",
    "incompatible": "red",
}

PHASE_LABELS = {
    "introduction": "📋 Phase 1 — Introduction",
    "exploration":  "🔍 Phase 2 — Exploration",
    "negotiation":  "🤝 Phase 3 — Negotiation",
    "conclusion":   "🏁 Phase 4 — Conclusion",
}


def _login_user(email: str, user: dict):
    """Set session state and cookie after successful login."""
    st.session_state.user_data = user
    cookies[SESSION_COOKIE_NAME] = create_session_token(email)
    cookies.save()


# ─────────────────────────────────────────────
# PAGE: LOGIN
# ─────────────────────────────────────────────

def render_login():
    st.title("🏠 AI Roommate Finder")
    st.subheader("Find your perfect roommate match")

    # ── Handle Google OAuth callback ──
    query_params = st.query_params
    code = query_params.get("code")
    state = query_params.get("state")

    if code and state:
        user_info = exchange_code_for_user(code, state)
        if user_info:
            email = user_info["email"]
            existing = get_user(email)
            if existing:
                update_last_login(
                    email,
                    google_id=user_info.get("google_id"),
                    profile_picture=user_info.get("profile_picture_url"),
                )
                _login_user(email, get_user(email))
                st.session_state.current_page = "home"
            else:
                save_user(
                    email=email,
                    name=user_info["name"],
                    questionnaire={},
                    google_id=user_info.get("google_id"),
                    profile_picture=user_info.get("profile_picture_url"),
                )
                _login_user(email, get_user(email))
                st.session_state.current_page = "questionnaire"
            st.query_params.clear()
            st.rerun()
        else:
            st.error("Google login failed. Please try again.")
            st.query_params.clear()

    # ── Auth form ──
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_google, tab_email = st.tabs(["🔐 Google", "📧 Email / Password"])

        # Google tab
        with tab_google:
            st.write("")
            if is_google_configured():
                auth_url, _ = get_google_auth_url()
                if auth_url:
                    st.link_button(
                        "Continue with Google",
                        auth_url,
                        type="primary",
                        use_container_width=True,
                    )
            else:
                st.warning("Google OAuth is not configured.")

        # Email / Password tab
        with tab_email:
            st.write("")
            mode = st.radio(
                "Mode",
                ["Login", "Create account"],
                horizontal=True,
                label_visibility="collapsed",
            )

            if mode == "Login":
                with st.form("email_login_form"):
                    email_input = st.text_input("Email")
                    password_input = st.text_input("Password", type="password")
                    submitted = st.form_submit_button(
                        "Log in", type="primary", use_container_width=True
                    )
                    if submitted:
                        result = login_with_password(email_input, password_input)
                        if result["success"]:
                            user = result["user"]
                            _login_user(user["email"], user)
                            if user.get("questionnaire"):
                                st.session_state.current_page = "home"
                            else:
                                st.session_state.current_page = "questionnaire"
                            st.rerun()
                        else:
                            st.error(result["error"])

            else:  # Create account
                with st.form("email_register_form"):
                    name_input = st.text_input("Full name")
                    email_input = st.text_input("Email")
                    password_input = st.text_input(
                        "Password", type="password",
                        help="At least 8 characters"
                    )
                    phone_input = st.text_input(
                        "Phone number (optional)",
                        placeholder="+1 234 567 8900"
                    )
                    submitted = st.form_submit_button(
                        "Create account", type="primary", use_container_width=True
                    )
                    if submitted:
                        result = register_user(
                            email=email_input,
                            password=password_input,
                            name=name_input,
                            phone_number=phone_input or None,
                        )
                        if result["success"]:
                            user = result["user"]
                            _login_user(user["email"], user)
                            st.session_state.current_page = "questionnaire"
                            st.rerun()
                        else:
                            st.error(result["error"])


# ─────────────────────────────────────────────
# PAGE: QUESTIONNAIRE
# ─────────────────────────────────────────────

def render_questionnaire():
    st.title("📋 Tell us about yourself")
    user = st.session_state.user_data
    existing_q = user.get("questionnaire", {})
    st.write(f"Hi **{user['name']}**! Fill this out so your AI clone knows how to represent you.")
    st.caption("Fields marked with \\* are required to create your clone.")

    all_questions = get_all_questions()
    section_labels = get_section_labels()

    with st.form("questionnaire_form"):
        collected = {}

        for section_key, questions in all_questions.items():
            st.header(section_labels[section_key])
            section_data = {}
            existing_section = existing_q.get(section_key, {})

            for q_key, q in questions.items():
                existing_val = existing_section.get(q_key)
                widget_key = f"{section_key}_{q_key}"
                is_required = q.get("required", False)

                # Add * to label for required fields
                label = q["question"] + (" \\*" if is_required else "")
                help_txt = q.get("help")

                if q["type"] == "text":
                    section_data[q_key] = st.text_input(
                        label,
                        value=existing_val or "",
                        placeholder=q.get("placeholder", ""),
                        key=widget_key,
                        help=help_txt,
                    )

                elif q["type"] == "number":
                    section_data[q_key] = st.number_input(
                        label,
                        min_value=q.get("min", 0),
                        max_value=q.get("max", 10000),
                        value=existing_val or q.get("default", 0),
                        key=widget_key,
                        help=help_txt,
                    )

                elif q["type"] == "select":
                    options = q["options"]
                    default_idx = options.index(existing_val) if existing_val in options else 0
                    section_data[q_key] = st.selectbox(
                        label,
                        options,
                        index=default_idx,
                        key=widget_key,
                        help=help_txt,
                    )

                elif q["type"] == "slider":
                    slider_labels = q.get("labels")
                    label_str = f" ({slider_labels[0]} → {slider_labels[1]})" if slider_labels else ""
                    section_data[q_key] = st.slider(
                        label + label_str,
                        q["min"],
                        q["max"],
                        existing_val or q.get("default", q["min"]),
                        key=widget_key,
                        help=help_txt,
                    )

                elif q["type"] == "multiselect":
                    max_sel = q.get("max_select")
                    ms_help = help_txt or (f"Choose up to {max_sel}" if max_sel else None)
                    selected = st.multiselect(
                        label,
                        q["options"],
                        default=existing_val or [],
                        key=widget_key,
                        help=ms_help,
                    )
                    if max_sel and len(selected) > max_sel:
                        st.warning(f"Please select at most {max_sel} options.")
                        selected = selected[:max_sel]
                    section_data[q_key] = selected

            collected[section_key] = section_data
            st.divider()

        submitted = st.form_submit_button(
            "💾 Save & Continue", type="primary", use_container_width=True
        )

        if submitted:
            errors = validate_questionnaire(collected)
            if errors:
                for err in errors:
                    st.error(f"⚠️ {err}")
            else:
                save_user(
                    email=user["email"],
                    name=user["name"],
                    questionnaire=collected,
                    google_id=user.get("google_id"),
                    profile_picture=user.get("profile_picture_url"),
                )
                st.session_state.user_data = get_user(user["email"])
                st.session_state.clone_prompt = None  # force regeneration
                st.session_state.current_page = "home"
                st.success("Profile saved!")
                st.rerun()


# ─────────────────────────────────────────────
# PAGE: HOME
# ─────────────────────────────────────────────

def render_home():
    st.title("🏠 AI Roommate Finder")
    user = st.session_state.user_data
    st.markdown(f"Welcome back, **{user['name']}**!")

    # Status row
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
            st.warning("⚠️ Complete your profile first")

    st.divider()
    st.subheader("What would you like to do?")

    # Match counts badge
    counts = api_get("/matches/counts", params={"user_id": user["email"]}) or {}
    total_matches = counts.get("total", 0)
    match_label = f"🤝 My Matches"
    if total_matches:
        match_label += f" ({total_matches})"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button(
            "💬 Chat with My Clone",
            use_container_width=True,
            disabled=not user.get("questionnaire"),
        ):
            st.session_state.current_page = "my_clone"
            st.rerun()

    with col2:
        if st.button(
            "👥 Setup Roommate Match",
            use_container_width=True,
            disabled=not backend_running(),
        ):
            st.session_state.current_page = "setup_match"
            st.rerun()

    with col3:
        if st.button(match_label, use_container_width=True):
            st.session_state.current_page = "matches"
            st.rerun()

    with col4:
        if st.button("📋 Edit My Profile", use_container_width=True):
            st.session_state.current_page = "questionnaire"
            st.rerun()


# ─────────────────────────────────────────────
# PAGE: MY CLONE (chat preview)
# ─────────────────────────────────────────────

def render_my_clone():
    st.title("💬 Chat with Your Clone")

    if st.button("← Back to Home"):
        st.session_state.current_page = "home"
        st.rerun()

    user = st.session_state.user_data

    if not check_ollama_running():
        st.error("Ollama is not running. Start it with: `ollama serve`")
        return

    if not user.get("questionnaire"):
        st.warning("Complete your profile first so your clone knows how to represent you.")
        if st.button("Complete Profile"):
            st.session_state.current_page = "questionnaire"
            st.rerun()
        return

    if not st.session_state.clone_prompt:
        st.session_state.clone_prompt = generate_clone_prompt(
            user["name"], user["questionnaire"]
        )

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Clear chat"):
            st.session_state.chat_history = []
            st.rerun()

    st.caption("This is your AI clone. Talk to it to verify it represents you correctly before matching.")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if prompt := st.chat_input("Ask your clone something..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full = ""
            for chunk in chat_stream(
                st.session_state.clone_prompt, st.session_state.chat_history
            ):
                full += chunk
                placeholder.write(full + "▌")
            placeholder.write(full)

        st.session_state.chat_history.append({"role": "assistant", "content": full})


# ─────────────────────────────────────────────
# PAGE: SETUP MATCH
# ─────────────────────────────────────────────

def render_setup_match():
    st.title("👥 Setup Roommate Match")

    if st.button("← Back to Home"):
        st.session_state.current_page = "home"
        st.rerun()

    all_users = get_all_users()
    users_with_profiles = [
        u for u in all_users
        if u.get("questionnaire") and u["questionnaire"]
    ]

    if len(users_with_profiles) < 2:
        st.warning(
            f"Need at least 2 users with completed profiles. "
            f"Currently have: {len(users_with_profiles)}"
        )
        return

    user_map = {
        u["email"]: f"{u['name']} ({u['email']})"
        for u in users_with_profiles
    }

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🅰️ User A")
        email_a = st.selectbox(
            "Select User A",
            list(user_map.keys()),
            format_func=lambda x: user_map[x],
            key="sel_a",
        )
        if email_a:
            user_a = next(u for u in users_with_profiles if u["email"] == email_a)
            st.session_state.user_a = user_a

            if st.button("✅ Validate Clone A"):
                with st.spinner("Validating..."):
                    api_post("/agents", {
                        "user_id": user_a["email"],
                        "name": user_a["name"],
                        "questionnaire": user_a["questionnaire"],
                    })
                    result = api_post(f"/agents/{user_a['email']}/validate", {})
                    st.session_state.validation_a = result

            if st.session_state.validation_a:
                v = st.session_state.validation_a
                if v.get("validated"):
                    st.success("✅ Clone A validated")
                else:
                    st.error("❌ Validation failed")
                for r in v.get("results", []):
                    with st.expander(r["question"][:50] + "..."):
                        st.write(r.get("response") or r.get("error"))

    with col2:
        st.subheader("🅱️ User B")
        remaining = {k: v for k, v in user_map.items() if k != email_a}
        if remaining:
            email_b = st.selectbox(
                "Select User B",
                list(remaining.keys()),
                format_func=lambda x: remaining[x],
                key="sel_b",
            )
            if email_b:
                user_b = next(u for u in users_with_profiles if u["email"] == email_b)
                st.session_state.user_b = user_b

                if st.button("✅ Validate Clone B"):
                    with st.spinner("Validating..."):
                        api_post("/agents", {
                            "user_id": user_b["email"],
                            "name": user_b["name"],
                            "questionnaire": user_b["questionnaire"],
                        })
                        result = api_post(f"/agents/{user_b['email']}/validate", {})
                        st.session_state.validation_b = result

                if st.session_state.validation_b:
                    v = st.session_state.validation_b
                    if v.get("validated"):
                        st.success("✅ Clone B validated")
                    else:
                        st.error("❌ Validation failed")
                    for r in v.get("results", []):
                        with st.expander(r["question"][:50] + "..."):
                            st.write(r.get("response") or r.get("error"))

    st.divider()

    if st.session_state.user_a and st.session_state.user_b:
        if st.button("🚀 Start Agent Chat", type="primary", use_container_width=True):
            result = api_post("/rooms", {
                "user_a_id": st.session_state.user_a["email"],
                "user_b_id": st.session_state.user_b["email"],
            })
            if result:
                st.session_state.room_id = result["room_id"]
                st.session_state.agent_conversation = []
                st.session_state.current_phase = None
                st.session_state.chat_outcome = None
                st.session_state.analysis_result = None
                st.session_state.current_page = "agent_chat"
                st.rerun()
            else:
                st.error("Failed to create room — is the backend running?")


# ─────────────────────────────────────────────
# PAGE: AGENT CHAT
# ─────────────────────────────────────────────

def render_agent_chat():
    st.title("🤖 Agent-to-Agent Chat")

    if st.button("← Back to Setup"):
        st.session_state.current_page = "setup_match"
        st.rerun()

    user_a = st.session_state.user_a
    user_b = st.session_state.user_b
    room_id = st.session_state.room_id

    if not user_a or not user_b:
        st.error("No users selected. Go back to Setup.")
        return

    st.markdown(
        f"**{user_a['name']}'s Clone** 🗣️ ↔️ 🗣️ **{user_b['name']}'s Clone**"
    )
    st.caption(f"Room: {room_id}")
    st.divider()

    # ── Render existing conversation with phase dividers ──
    last_phase = None
    for msg in st.session_state.agent_conversation:
        phase = msg.get("phase")
        if phase and phase != last_phase:
            st.markdown(
                f"<div style='text-align:center; color:gray; font-size:0.85em; "
                f"padding:4px 0'>— {PHASE_LABELS.get(phase, phase)} —</div>",
                unsafe_allow_html=True,
            )
            last_phase = phase

        avatar = "🅰️" if msg.get("speaker_id") == "a" else "🅱️"
        with st.chat_message("assistant", avatar=avatar):
            st.markdown(f"**{msg['speaker']}**: {msg['message']}")

    # ── Outcome badge ──
    if st.session_state.chat_outcome:
        outcome = st.session_state.chat_outcome
        status = outcome.get("status", "")
        color = STATUS_COLOR.get(status, "gray")
        badge = STATUS_BADGE.get(status, status)
        st.markdown(
            f"<div style='text-align:center; margin:12px 0'>"
            f"<span style='background:{color}; color:white; padding:6px 16px; "
            f"border-radius:20px; font-weight:bold'>{badge}</span></div>",
            unsafe_allow_html=True,
        )
        if status == "conditional" and outcome.get("unresolved_topics"):
            st.info(
                "⚠️ Unresolved topics: "
                + ", ".join(outcome["unresolved_topics"])
            )
        if status == "incompatible" and outcome.get("reason"):
            st.error(f"Reason: {outcome['reason']}")

    # ── Controls ──
    col1, col2, col3 = st.columns(3)

    with col1:
        start_disabled = bool(st.session_state.agent_conversation)
        if st.button(
            "▶️ Start Chat",
            type="primary",
            use_container_width=True,
            disabled=start_disabled,
        ):
            run_websocket_chat(room_id)

    with col2:
        analyze_disabled = not st.session_state.agent_conversation
        if st.button(
            "📊 Analyze",
            use_container_width=True,
            disabled=analyze_disabled,
        ):
            _run_analysis(room_id)

    with col3:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.agent_conversation = []
            st.session_state.current_phase = None
            st.session_state.chat_outcome = None
            st.session_state.analysis_result = None
            st.session_state.room_id = None
            st.rerun()

    # ── Analysis display ──
    if st.session_state.analysis_result:
        st.divider()
        _render_analysis(st.session_state.analysis_result)


def run_websocket_chat(room_id: str):
    """
    Connect to WebSocket and stream agent messages live into the UI.
    Uses a background thread + queue so Streamlit can rerun on each message.
    """
    msg_queue = queue.Queue()

    def ws_thread():
        async def _run():
            uri = f"{WS_URL}/ws/{room_id}"
            try:
                async with websockets.connect(uri) as ws:
                    await ws.send(json.dumps({"action": "start"}))
                    while True:
                        raw = await ws.recv()
                        data = json.loads(raw)
                        msg_queue.put(data)
                        if data["type"] in ("chat_complete", "error", "stopped"):
                            break
            except Exception as e:
                msg_queue.put({"type": "error", "message": str(e)})

        asyncio.run(_run())

    thread = threading.Thread(target=ws_thread, daemon=True)
    thread.start()

    # Stream messages into the UI as they arrive
    status_placeholder = st.empty()
    phase_placeholder = st.empty()

    while thread.is_alive() or not msg_queue.empty():
        try:
            data = msg_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        if data["type"] == "phase_start":
            phase_name = data.get("phase", "")
            phase_label = PHASE_LABELS.get(phase_name, data.get("label", ""))
            phase_placeholder.markdown(
                f"<div style='text-align:center; color:gray; font-size:0.85em; "
                f"padding:4px 0'>— {phase_label} —</div>",
                unsafe_allow_html=True,
            )
            st.session_state.current_phase = phase_name

        elif data["type"] == "agent_message":
            msg = data["data"]
            st.session_state.agent_conversation.append(msg)
            avatar = "🅰️" if msg.get("speaker_id") == "a" else "🅱️"
            with st.chat_message("assistant", avatar=avatar):
                st.markdown(f"**{msg['speaker']}**: {msg['message']}")
            status_placeholder.caption(
                f"Turn {msg['turn']} · {PHASE_LABELS.get(msg.get('phase',''), '')}"
            )

        elif data["type"] == "chat_complete":
            st.session_state.chat_outcome = data.get("outcome")
            status_placeholder.empty()
            phase_placeholder.empty()
            break

        elif data["type"] == "error":
            st.error(f"WebSocket error: {data.get('message')}")
            break

    thread.join(timeout=5)
    st.rerun()


def _run_analysis(room_id: str):
    """Trigger analysis via WebSocket and store result."""
    async def _analyze():
        uri = f"{WS_URL}/ws/{room_id}"
        try:
            async with websockets.connect(uri) as ws:
                await ws.send(json.dumps({"action": "analyze"}))
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if data["type"] == "analysis":
                        return data
                    if data["type"] == "error":
                        return None
        except Exception as e:
            st.error(f"Analysis error: {e}")
            return None

    with st.spinner("🔍 Analyzing compatibility..."):
        result = asyncio.run(_analyze())

    if result:
        st.session_state.analysis_result = result
        st.rerun()


def _render_analysis(result: dict):
    """Render structured analysis or fall back to raw text."""
    st.header("📊 Compatibility Analysis")

    if not result.get("structured"):
        # Fallback — model returned raw text instead of JSON
        st.markdown(result.get("data", "No analysis available."))
        return

    data = result["data"]

    # ── Overall score + recommendation badge ──
    overall = data.get("scores", {}).get("overall", 0)
    rec = data.get("recommendation", "")
    badge = STATUS_BADGE.get(rec, rec)
    color = STATUS_COLOR.get(rec, "gray")

    col_score, col_rec = st.columns([1, 2])
    with col_score:
        st.metric("Overall Score", f"{overall}/100")
    with col_rec:
        st.markdown(
            f"<div style='padding-top:8px'>"
            f"<span style='background:{color}; color:white; padding:6px 16px; "
            f"border-radius:20px; font-weight:bold'>{badge}</span></div>",
            unsafe_allow_html=True,
        )

    # ── Sub-scores ──
    scores = data.get("scores", {})
    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    s_col1.metric("💰 Finances",   f"{scores.get('finances', '—')}/100")
    s_col2.metric("🌅 Lifestyle",  f"{scores.get('lifestyle', '—')}/100")
    s_col3.metric("🤝 Personality", f"{scores.get('personality', '—')}/100")
    s_col4.metric("📍 Logistics",  f"{scores.get('logistics', '—')}/100")

    st.divider()

    # ── Dealbreaker flag ──
    if data.get("dealbreaker_detected"):
        st.error(
            f"🚨 Dealbreaker detected: {data.get('dealbreaker_detail', 'See concerns below.')}"
        )

    # ── Highlights & Concerns ──
    col_h, col_c = st.columns(2)
    with col_h:
        st.subheader("✅ Highlights")
        for h in data.get("highlights", []):
            st.success(h)
    with col_c:
        st.subheader("⚠️ Concerns")
        for c in data.get("concerns", []):
            st.warning(c)

    # ── Middle ground ──
    middle = data.get("middle_ground", [])
    if middle:
        st.subheader("🤝 Possible Middle Ground")
        for m in middle:
            st.info(m)

    # ── Summary ──
    summary = data.get("recommendation_summary", "")
    if summary:
        st.divider()
        st.markdown(f"**Summary:** {summary}")


# ─────────────────────────────────────────────
# PAGE: MATCHES
# ─────────────────────────────────────────────

def render_matches():
    st.title("🤝 My Matches")

    if st.button("← Back to Home"):
        st.session_state.current_page = "home"
        st.rerun()

    user = st.session_state.user_data
    user_id = user["email"]

    # Fetch counts first (cheap)
    counts = api_get("/matches/counts", params={"user_id": user_id}) or {}
    strong_count       = counts.get("strong", 0)
    conditional_count  = counts.get("conditional", 0)
    incompatible_count = counts.get("incompatible", 0)
    total              = counts.get("total", 0)

    # Fetch strong + conditional matches
    matches = api_get("/matches", params={"user_id": user_id}) or []

    # ── Empty state handling ──
    if not matches:
        if incompatible_count > 0:
            # Case 2 — all results are incompatible
            st.info(
                f"No strong or conditional matches yet — but you have "
                f"**{incompatible_count}** incompatible result(s). "
                f"Toggle below to see them."
            )
        elif total == 0:
            # Case 1 — truly no matches at all
            st.markdown("### You haven't matched with anyone yet!")
            st.write(
                "Run an agent conversation in **Setup Match** to generate your first results."
            )
            if st.button("👥 Go to Setup Match", type="primary"):
                st.session_state.current_page = "setup_match"
                st.rerun()
            st.caption(
                "Note: Match history is tied to the backend session. "
                "If the server was restarted, previous matches may not appear here."
            )
            return
        else:
            st.info("No strong or conditional matches to show.")
    else:
        # ── Match cards ──
        st.caption(
            f"Showing {len(matches)} match(es) — "
            f"🟢 {strong_count} strong · 🟡 {conditional_count} conditional"
        )

        for match in matches:
            _render_match_card(match, user_id)

    # ── Incompatible toggle ──
    st.divider()
    if incompatible_count > 0:
        show_incompatible = st.toggle(
            f"Show incompatible matches ({incompatible_count})",
            value=False,
        )
        if show_incompatible:
            all_matches = api_get(
                "/matches",
                params={"user_id": user_id, "include_incompatible": True}
            ) or []
            incompatible = [m for m in all_matches if m["status"] == "incompatible"]

            if incompatible:
                st.subheader("🔴 Incompatible Matches")
                st.caption(
                    "These matches didn't work out — but you can still view "
                    "who they were and why the agents concluded incompatibility."
                )
                for match in incompatible:
                    _render_match_card(match, user_id, show_reason=True)
    else:
        st.caption("No incompatible matches on record.")


def _render_match_card(match: dict, current_user_id: str, show_reason: bool = False):
    """Render a single match card with contact button."""
    status = match.get("status", "")
    color = STATUS_COLOR.get(status, "gray")
    badge = STATUS_BADGE.get(status, status)

    # Determine the other person
    if match.get("user_a_id") == current_user_id:
        other_name  = match.get("user_b_name", "Unknown")
        other_email = match.get("user_b_id", "")
    else:
        other_name  = match.get("user_a_name", "Unknown")
        other_email = match.get("user_a_id", "")

    with st.container(border=True):
        col_info, col_badge, col_btn = st.columns([3, 2, 1])

        with col_info:
            st.markdown(f"### {other_name}")
            st.caption(f"Matched on {match.get('created_at', '')[:10]}")

            # Sub-scores summary if structured analysis exists
            analysis = match.get("analysis", {})
            if analysis.get("structured"):
                scores = analysis["data"].get("scores", {})
                if scores:
                    st.caption(
                        f"Overall: **{scores.get('overall','—')}/100** · "
                        f"Finances: {scores.get('finances','—')} · "
                        f"Lifestyle: {scores.get('lifestyle','—')} · "
                        f"Personality: {scores.get('personality','—')}"
                    )

            # Unresolved topics for conditional
            if status == "conditional" and match.get("unresolved_topics"):
                st.caption(
                    "⚠️ Needs discussion: "
                    + ", ".join(match["unresolved_topics"])
                )

            # Reason for incompatible
            if show_reason and match.get("reason"):
                st.caption(f"❌ Reason: {match['reason']}")

        with col_badge:
            st.markdown(
                f"<div style='padding-top:12px'>"
                f"<span style='background:{color}; color:white; padding:5px 12px; "
                f"border-radius:16px; font-size:0.85em; font-weight:bold'>"
                f"{badge}</span></div>",
                unsafe_allow_html=True,
            )

        with col_btn:
            if status != "incompatible":
                # Contact button — shows email in an expander
                with st.expander("📬 Contact"):
                    st.write(f"**{other_name}**")
                    st.code(other_email, language=None)
                    st.caption("Send them an email to follow up on your match.")


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.title("🏠 Roommate Finder")

        # DB status
        if not test_connection():
            st.error("❌ MongoDB offline")
        else:
            st.success("✅ MongoDB")

        if st.session_state.user_data:
            user = st.session_state.user_data
            if user.get("profile_picture_url"):
                st.image(user["profile_picture_url"], width=60)
            st.write(f"**{user.get('name')}**")
            st.caption(user.get("email"))

            st.divider()

            # Nav buttons
            nav_items = [
                ("🏠 Home",            "home"),
                ("💬 My Clone",        "my_clone"),
                ("👥 Setup Match",     "setup_match"),
                ("🤝 My Matches",      "matches"),
                ("📋 Edit Profile",    "questionnaire"),
            ]
            for label, page in nav_items:
                if st.button(label, use_container_width=True, key=f"nav_{page}"):
                    st.session_state.current_page = page
                    st.rerun()

            st.divider()

            if st.button("🚪 Logout", use_container_width=True):
                token = cookies.get(SESSION_COOKIE_NAME)
                if token:
                    del cookies[SESSION_COOKIE_NAME]
                    cookies.save()
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

            # Active match context
            if st.session_state.get("user_a") or st.session_state.get("user_b"):
                st.divider()
                st.caption("Active match:")
                if st.session_state.user_a:
                    st.info(f"🅰️ {st.session_state.user_a['name']}")
                if st.session_state.user_b:
                    st.info(f"🅱️ {st.session_state.user_b['name']}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

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
    elif page == "matches":
        render_matches()


if __name__ == "__main__":
    main()