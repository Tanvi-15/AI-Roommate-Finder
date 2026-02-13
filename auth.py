# auth.py
# Google OAuth authentication for Streamlit

import time
from authlib.integrations.requests_client import OAuth2Session

from config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
SCOPES = "openid email profile"

# In-memory store for OAuth state (valid for 10 min)
# In production, use Redis or DB for multi-instance
_oauth_states = {}


def _generate_state():
    """Generate and store OAuth state for CSRF protection"""
    import secrets
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = time.time()
    return state


def _validate_state(state):
    """Validate OAuth state and clean up"""
    if not state or state not in _oauth_states:
        return False
    created = _oauth_states[state]
    del _oauth_states[state]
    return time.time() - created < 600  # 10 min expiry


def _cleanup_expired_states():
    """Remove expired states"""
    now = time.time()
    expired = [s for s, t in _oauth_states.items() if now - t > 600]
    for s in expired:
        del _oauth_states[s]


def get_google_auth_url():
    """Generate Google OAuth authorization URL"""
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
    uri, _ = client.create_authorization_url(
        GOOGLE_AUTH_URL,
        state=state,
    )
    return uri, state


def exchange_code_for_user(code, state, request_url=None):
    """
    Exchange authorization code for token and fetch user info.
    Returns user dict with email, name, picture, google_id or None on failure.
    request_url: full callback URL (e.g. from Streamlit's current URL) - optional
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

    # Build redirect URL for fetch_token (must match what Google sent)
    redirect_url = request_url or f"{GOOGLE_REDIRECT_URI.rstrip('/')}/?code={code}&state={state}"

    try:
        token = client.fetch_token(
            GOOGLE_TOKEN_URL,
            authorization_response=redirect_url,
        )
    except Exception:
        return None

    # Fetch user info
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
    """Check if Google OAuth is configured"""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
