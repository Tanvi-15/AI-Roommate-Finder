# auth.py
# Authentication — Google OAuth + Email/Password

import re
import time
import secrets

import bcrypt
from authlib.integrations.requests_client import OAuth2Session

from shared.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)
from shared.database import (
    create_email_user,
    get_password_hash,
    get_user,
    update_last_login,
    user_exists,
)

# ─────────────────────────────────────────────
# EMAIL VALIDATION
# ─────────────────────────────────────────────

# RFC-5322 inspired but practical — catches obvious invalids
_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
)


def is_valid_email(email: str) -> bool:
    """Returns True if email looks valid (format check only, no OTP)."""
    if not email or not isinstance(email, str):
        return False
    return bool(_EMAIL_REGEX.match(email.strip()))


def is_valid_phone(phone: str) -> bool:
    """
    Returns True if phone looks valid.
    Accepts formats: +1234567890, 123-456-7890, (123) 456-7890, 10+ digits.
    Phone is optional so this is only called when a value is provided.
    """
    if not phone:
        return True  # optional field — empty is fine
    digits = re.sub(r"\D", "", phone)
    return 7 <= len(digits) <= 15


# ─────────────────────────────────────────────
# PASSWORD HELPERS
# ─────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ─────────────────────────────────────────────
# EMAIL / PASSWORD AUTH
# ─────────────────────────────────────────────

def register_user(
    email: str,
    password: str,
    name: str,
    phone_number: str = None,
) -> dict:
    """
    Register a new email/password user.

    Returns:
        {"success": True, "user": {...}}
        {"success": False, "error": "human-readable message"}
    """
    # Validate email
    email = email.strip().lower()
    if not is_valid_email(email):
        return {"success": False, "error": "Please enter a valid email address."}

    # Validate password — at least 8 chars
    if not password or len(password) < 8:
        return {"success": False, "error": "Password must be at least 8 characters."}

    # Validate name
    name = name.strip()
    if not name:
        return {"success": False, "error": "Please enter your name."}

    # Validate phone if provided
    if phone_number and not is_valid_phone(phone_number):
        return {"success": False, "error": "Please enter a valid phone number."}

    # Check email not already taken
    if user_exists(email):
        return {"success": False, "error": "An account with this email already exists. Try logging in."}

    # Hash and store
    try:
        pw_hash = hash_password(password)
        create_email_user(
            email=email,
            name=name,
            password_hash=pw_hash,
            phone_number=phone_number or None,
        )
        user = get_user(email)
        return {"success": True, "user": user}
    except Exception as e:
        return {"success": False, "error": f"Registration failed: {str(e)}"}


def login_with_password(email: str, password: str) -> dict:
    """
    Authenticate an email/password user.

    Returns:
        {"success": True, "user": {...}}
        {"success": False, "error": "human-readable message"}
    """
    email = email.strip().lower()

    if not is_valid_email(email):
        return {"success": False, "error": "Please enter a valid email address."}

    if not password:
        return {"success": False, "error": "Please enter your password."}

    # Fetch hash — intentionally vague error to not reveal if email exists
    stored_hash = get_password_hash(email)
    if not stored_hash:
        return {"success": False, "error": "Invalid email or password."}

    if not verify_password(password, stored_hash):
        return {"success": False, "error": "Invalid email or password."}

    # Update last login
    update_last_login(email)
    user = get_user(email)
    return {"success": True, "user": user}


# ─────────────────────────────────────────────
# GOOGLE OAUTH  (unchanged from original)
# ─────────────────────────────────────────────

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
SCOPES = "openid email profile"

_oauth_states = {}


def _generate_state():
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = time.time()
    return state


def _validate_state(state):
    if not state or state not in _oauth_states:
        return False
    created = _oauth_states[state]
    del _oauth_states[state]
    return time.time() - created < 600


def _cleanup_expired_states():
    now = time.time()
    expired = [s for s, t in _oauth_states.items() if now - t > 600]
    for s in expired:
        del _oauth_states[s]


def get_google_auth_url():
    """Generate Google OAuth authorization URL."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return None, None
    _cleanup_expired_states()
    state = _generate_state()
    client = OAuth2Session(
        GOOGLE_CLIENT_ID,
        GOOGLE_CLIENT_SECRET,
        scope=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    uri, _ = client.create_authorization_url(GOOGLE_AUTH_URL, state=state)
    return uri, state


def exchange_code_for_user(code, state, request_url=None):
    """
    Exchange authorization code for token and fetch user info.
    Returns user dict or None on failure.
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return None
    if not _validate_state(state):
        return None
    if not code:
        return None

    client = OAuth2Session(
        GOOGLE_CLIENT_ID,
        GOOGLE_CLIENT_SECRET,
        scope=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    redirect_url = request_url or f"{GOOGLE_REDIRECT_URI.rstrip('/')}/?code={code}&state={state}"

    try:
        client.fetch_token(GOOGLE_TOKEN_URL, authorization_response=redirect_url)
    except Exception:
        return None

    try:
        resp = client.get(GOOGLE_USERINFO_URL)
        resp.raise_for_status()
        info = resp.json()
    except Exception:
        return None

    return {
        "email": info.get("email"),
        "name": info.get("name", info.get("email", "User")),
        "profile_picture_url": info.get("picture"),
        "google_id": info.get("id"),
    }


def is_google_configured():
    """Check if Google OAuth is configured."""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)