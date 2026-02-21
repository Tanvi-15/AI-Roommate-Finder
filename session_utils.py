# session_utils.py
# JWT-based session tokens for cookie persistence

import jwt
from datetime import datetime, timedelta

from shared.config import JWT_SECRET, SESSION_DAYS


def create_session_token(email: str) -> str:
    """Create a JWT session token for the given email."""
    payload = {
        "email": email,
        "exp": datetime.utcnow() + timedelta(days=SESSION_DAYS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def validate_session_token(token: str) -> str | None:
    """
    Validate JWT and return email if valid, else None.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload.get("email")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
