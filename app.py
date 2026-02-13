import streamlit as st
from questionnaire import LIVING_PREFERENCES, PERSONALITY_QUESTIONS
from database import save_user, get_user, user_exists, update_last_login, test_connection
from clone import generate_clone_prompt
from ollama_client import check_ollama_running, chat, chat_stream
from auth import get_google_auth_url, exchange_code_for_user, is_google_configured

# Page config
st.set_page_config(
    page_title="AI Roommate Finder",
    page_icon="🏠",
    layout="wide"
)

# Initialize session state
if "user_data" not in st.session_state:
    st.session_state.user_data = None
if "clone_prompt" not in st.session_state:
    st.session_state.clone_prompt = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"


def render_login():
    """Login page with Google OAuth"""
    st.title("🏠 AI Roommate Finder")
    st.subheader("Find your perfect roommate match")

    # Check if we're returning from Google OAuth callback
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
                # Update last login and sync Google profile
                update_last_login(email, google_id=google_id, profile_picture=profile_picture)
                st.session_state.user_data = get_user(email)
                st.session_state.current_page = "chat"
                st.success(f"Welcome back, {existing_user['name']}!")
            else:
                # New user - save to DB (without questionnaire yet)
                save_user(
                    email=email,
                    name=name,
                    questionnaire={},
                    google_id=google_id,
                    profile_picture=profile_picture,
                )
                st.session_state.user_data = get_user(email)
                st.session_state.current_page = "questionnaire"
                st.success(f"Welcome, {name}!")

            # Clear URL params for clean state
            st.query_params.clear()
            st.rerun()
        else:
            st.error("Login failed. Please try again.")
            st.query_params.clear()
            st.rerun()

    # Show login UI
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if is_google_configured():
            auth_url, _ = get_google_auth_url()
            if auth_url:
                st.markdown("### Sign in with Google")
                st.link_button(
                    "🔐 Continue with Gmail",
                    auth_url,
                    type="primary",
                    use_container_width=True,
                )
                st.caption("We'll use your Gmail to save your profile and preferences.")
            else:
                st.error("Google OAuth misconfigured. Check your .env credentials.")
        else:
            st.warning(
                "Google OAuth is not configured. Add GOOGLE_CLIENT_ID and "
                "GOOGLE_CLIENT_SECRET to your .env file."
            )
            st.info("See .env.example for the required variables.")


def render_questionnaire():
    """Questionnaire page"""
    st.title("📋 Tell us about yourself")
    user = st.session_state.user_data
    st.write(f"Hi **{user['name']}**! Let's find your ideal roommate.")

    with st.form("questionnaire_form"):
        st.header("🏠 Living Preferences")
        living_answers = {}

        for key, q in LIVING_PREFERENCES.items():
            if q["type"] == "text":
                living_answers[key] = st.text_input(q["question"], placeholder=q.get("placeholder", ""))
            elif q["type"] == "number":
                living_answers[key] = st.number_input(
                    q["question"],
                    min_value=q.get("min", 0),
                    max_value=q.get("max", 10000),
                    value=q.get("default", 0)
                )
            elif q["type"] == "select":
                living_answers[key] = st.selectbox(q["question"], q["options"])

        st.divider()
        st.header("😊 Personality & Lifestyle")
        personality_answers = {}

        for key, q in PERSONALITY_QUESTIONS.items():
            if q["type"] == "text":
                personality_answers[key] = st.text_input(
                    q["question"],
                    placeholder=q.get("placeholder", ""),
                    key=f"personality_{key}"
                )
            elif q["type"] == "select":
                personality_answers[key] = st.selectbox(q["question"], q["options"], key=f"personality_{key}")
            elif q["type"] == "slider":
                labels = q.get("labels", [str(q["min"]), str(q["max"])])
                col1, col2, col3 = st.columns([1, 3, 1])
                with col1:
                    st.caption(labels[0])
                with col2:
                    personality_answers[key] = st.slider(
                        q["question"],
                        min_value=q["min"],
                        max_value=q["max"],
                        value=q.get("default", q["min"]),
                        key=f"personality_{key}"
                    )
                with col3:
                    st.caption(labels[1] if len(labels) > 1 else str(q["max"]))

        submitted = st.form_submit_button("Save & Continue", type="primary", use_container_width=True)

        if submitted:
            questionnaire = {
                "living": living_answers,
                "personality": personality_answers
            }

            save_user(
                email=user["email"],
                name=user["name"],
                questionnaire=questionnaire,
                google_id=user.get("google_id"),
                profile_picture=user.get("profile_picture_url"),
            )

            st.session_state.user_data = get_user(user["email"])
            st.session_state.current_page = "chat"
            st.success("Profile saved! Let's meet your clone.")
            st.rerun()


def render_chat():
    """Chat with clone page"""
    user = st.session_state.user_data

    if not user or "questionnaire" not in user:
        st.error("Please complete the questionnaire first")
        st.session_state.current_page = "questionnaire"
        st.rerun()
        return

    if not user.get("questionnaire"):
        st.session_state.current_page = "questionnaire"
        st.rerun()
        return

    # Check Ollama
    if not check_ollama_running():
        st.error("⚠️ Ollama is not running or gemma3 model not found!")
        st.code("ollama pull gemma3\nollama serve", language="bash")
        st.stop()

    # Generate clone prompt if not exists
    if not st.session_state.clone_prompt:
        st.session_state.clone_prompt = generate_clone_prompt(user["name"], user["questionnaire"])

    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title(f"💬 Chat with {user['name']}'s Clone")
    with col2:
        if st.button("🔄 New Chat"):
            st.session_state.chat_history = []
            st.rerun()
        if st.button("📋 Edit Profile"):
            st.session_state.current_page = "questionnaire"
            st.rerun()

    st.caption("Talk to your AI clone to see how it represents you!")

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat input
    if prompt := st.chat_input("Say something to your clone..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            for chunk in chat_stream(st.session_state.clone_prompt, st.session_state.chat_history):
                full_response += chunk
                response_placeholder.write(full_response + "▌")

            response_placeholder.write(full_response)

        st.session_state.chat_history.append({"role": "assistant", "content": full_response})


def render_sidebar():
    """Sidebar with user info and navigation"""
    with st.sidebar:
        st.title("🏠 Roommate Finder")

        # MongoDB connection status
        if not test_connection():
            st.error("MongoDB not connected")

        if st.session_state.user_data:
            user = st.session_state.user_data
            if user.get("profile_picture_url"):
                st.image(user["profile_picture_url"], width=60)
            st.write(f"**Logged in as:** {user.get('name', 'Unknown')}")
            st.write(f"**Email:** {user.get('email', 'Unknown')}")

            if st.button("Logout"):
                st.session_state.user_data = None
                st.session_state.clone_prompt = None
                st.session_state.chat_history = []
                st.session_state.current_page = "login"
                st.rerun()

            st.divider()

            if user.get("questionnaire"):
                with st.expander("Your Profile Summary"):
                    q = user["questionnaire"]
                    living = q.get("living", {})
                    personality = q.get("personality", {})

                    st.write("**Location:**", living.get("location", "N/A"))
                    st.write("**Budget:**", f"${living.get('budget_min', '?')} - ${living.get('budget_max', '?')}")
                    st.write("**Room:**", living.get("room_type", "N/A"))
                    st.write("**Sleep:**", personality.get("sleep_schedule", "N/A"))
                    st.write("**Cleanliness:**", f"{personality.get('cleanliness', '?')}/5")


def main():
    render_sidebar()

    if st.session_state.current_page == "login":
        render_login()
    elif st.session_state.current_page == "questionnaire":
        render_questionnaire()
    elif st.session_state.current_page == "chat":
        render_chat()


if __name__ == "__main__":
    main()
