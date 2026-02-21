# database.py
# MongoDB storage for user data

from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from .config import MONGODB_URI, MONGODB_DATABASE, USERS_COLLECTION, MATCHES_COLLECTION


def _get_client():
    """Get MongoDB client"""
    return MongoClient(MONGODB_URI)


def _get_collection():
    """Get users collection"""
    client = _get_client()
    db = client[MONGODB_DATABASE]
    return db[USERS_COLLECTION]


def _get_matches_collection():
    """Get matches collection"""
    client = _get_client()
    db = client[MONGODB_DATABASE]
    return db[MATCHES_COLLECTION]


def _ensure_index():
    """Ensure email index for fast lookups"""
    col = _get_collection()
    col.create_index("email", unique=True)


def save_user(
    email,
    name,
    questionnaire,
    google_id=None,
    profile_picture=None,
    password_hash=None,
    phone_number=None,
):
    """
    Save or update user data based on email.

    Supports both Google OAuth users and email/password users.
    Only fields explicitly passed are written — existing fields
    (e.g. password_hash on a Google user) are never overwritten
    with None.
    """
    col = _get_collection()
    now = datetime.utcnow().isoformat()
    existing = col.find_one({"email": email})

    doc = {
        "email": email,
        "name": name,
        "questionnaire": questionnaire,
        "updated_at": now,
    }

    # Only set optional fields if provided — never overwrite with None
    if google_id:
        doc["google_id"] = google_id
    if profile_picture:
        doc["profile_picture_url"] = profile_picture
    if password_hash:
        doc["password_hash"] = password_hash
    if phone_number:
        doc["phone_number"] = phone_number

    if existing:
        col.update_one({"email": email}, {"$set": doc})
    else:
        doc["created_at"] = now
        col.insert_one(doc)

    return True


def create_email_user(email, name, password_hash, phone_number=None):
    """
    Create a brand new email/password user.
    Returns True on success, raises ValueError if email already exists.
    """
    col = _get_collection()

    if col.find_one({"email": email}):
        raise ValueError(f"An account with {email} already exists.")

    now = datetime.utcnow().isoformat()
    doc = {
        "email": email,
        "name": name,
        "questionnaire": {},
        "password_hash": password_hash,
        "auth_method": "email",
        "created_at": now,
        "updated_at": now,
    }
    if phone_number:
        doc["phone_number"] = phone_number

    col.insert_one(doc)
    return True


def get_password_hash(email) -> str | None:
    """
    Retrieve the stored password hash for an email user.
    Returns None if user doesn't exist or has no password (Google-only user).
    """
    col = _get_collection()
    user = col.find_one({"email": email}, {"password_hash": 1})
    if not user:
        return None
    return user.get("password_hash")


def update_last_login(email, google_id=None, profile_picture=None):
    """Update last login timestamp and optionally sync Google profile fields."""
    col = _get_collection()
    updates = {"last_login_at": datetime.utcnow().isoformat()}
    if google_id:
        updates["google_id"] = google_id
    if profile_picture:
        updates["profile_picture_url"] = profile_picture
    col.update_one({"email": email}, {"$set": updates})


def get_user(email):
    """
    Retrieve user by email.
    Strips password_hash from the returned dict for safety.
    """
    col = _get_collection()
    user = col.find_one({"email": email})
    if user:
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)   # never expose hash outside auth layer
    return user


def get_user_by_google_id(google_id):
    """Retrieve user by Google ID."""
    col = _get_collection()
    user = col.find_one({"google_id": google_id})
    if user:
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
    return user


def user_exists(email):
    """Check if a user exists."""
    return _get_collection().find_one({"email": email}) is not None


def get_all_users():
    """Get all users — strips password hashes."""
    col = _get_collection()
    users = list(col.find({}))
    for u in users:
        u["_id"] = str(u["_id"])
        u.pop("password_hash", None)
    return users


def test_connection():
    """Test MongoDB connection."""
    try:
        client = _get_client()
        client.admin.command("ping")
        return True
    except ConnectionFailure:
        return False


# ─────────────────────────────────────────────
# MATCHES
# ─────────────────────────────────────────────

def save_match_to_db(record: dict) -> bool:
    """
    Persist a match record to MongoDB.
    record must contain match_id as a unique identifier.
    Upserts so re-running analyze on the same room updates rather than duplicates.
    """
    col = _get_matches_collection()
    col.update_one(
        {"match_id": record["match_id"]},
        {"$set": record},
        upsert=True,
    )
    return True


def get_matches_for_user_from_db(user_id: str, include_incompatible: bool = False) -> list:
    """
    Fetch all matches involving a user from MongoDB.
    Queries both user_a_id and user_b_id fields.
    Strips MongoDB _id from results.
    """
    col = _get_matches_collection()
    query = {"$or": [{"user_a_id": user_id}, {"user_b_id": user_id}]}

    if not include_incompatible:
        query["status"] = {"$ne": "incompatible"}

    matches = list(col.find(query, {"_id": 0}).sort("created_at", -1))
    return matches


def get_match_by_id_from_db(match_id: str) -> dict | None:
    """Fetch a single match by match_id."""
    col = _get_matches_collection()
    match = col.find_one({"match_id": match_id}, {"_id": 0})
    return match


def get_match_counts_for_user(user_id: str) -> dict:
    """
    Return a summary count of match statuses for a user.
    Useful for showing badge counts in the UI.
    """
    col = _get_matches_collection()
    pipeline = [
        {"$match": {"$or": [{"user_a_id": user_id}, {"user_b_id": user_id}]}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    results = list(col.aggregate(pipeline))
    counts = {"strong": 0, "conditional": 0, "incompatible": 0}
    for r in results:
        if r["_id"] in counts:
            counts[r["_id"]] = r["count"]
    counts["total"] = sum(counts.values())
    return counts