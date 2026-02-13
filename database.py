# database.py
# MongoDB storage for user data

from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from config import MONGODB_URI, MONGODB_DATABASE, USERS_COLLECTION


def _get_client():
    """Get MongoDB client (singleton-like, creates new each time for simplicity)"""
    return MongoClient(MONGODB_URI)


def _get_collection():
    """Get users collection"""
    client = _get_client()
    db = client[MONGODB_DATABASE]
    return db[USERS_COLLECTION]


def _ensure_index():
    """Ensure email index for fast lookups"""
    col = _get_collection()
    col.create_index("email", unique=True)


def save_user(email, name, questionnaire, google_id=None, profile_picture=None):
    """Save or update user data based on email"""
    col = _get_collection()
    now = datetime.utcnow().isoformat()

    existing = col.find_one({"email": email})

    doc = {
        "email": email,
        "name": name,
        "questionnaire": questionnaire,
        "updated_at": now,
    }
    if google_id:
        doc["google_id"] = google_id
    if profile_picture:
        doc["profile_picture_url"] = profile_picture

    if existing:
        col.update_one(
            {"email": email},
            {"$set": doc}
        )
    else:
        doc["created_at"] = now
        col.insert_one(doc)

    return True


def update_last_login(email, google_id=None, profile_picture=None):
    """Update last login timestamp and optionally sync Google profile"""
    col = _get_collection()
    updates = {"last_login_at": datetime.utcnow().isoformat()}
    if google_id:
        updates["google_id"] = google_id
    if profile_picture:
        updates["profile_picture_url"] = profile_picture
    col.update_one(
        {"email": email},
        {"$set": updates}
    )


def get_user(email):
    """Retrieve user by email"""
    col = _get_collection()
    user = col.find_one({"email": email})
    if user:
        user["_id"] = str(user["_id"])  # Convert ObjectId for JSON/session
    return user


def get_user_by_google_id(google_id):
    """Retrieve user by Google ID"""
    col = _get_collection()
    user = col.find_one({"google_id": google_id})
    if user:
        user["_id"] = str(user["_id"])
    return user


def user_exists(email):
    """Check if user exists"""
    return get_user(email) is not None


def get_all_users():
    """Get all users (for admin/debug)"""
    col = _get_collection()
    users = list(col.find({}))
    for u in users:
        u["_id"] = str(u["_id"])
    return users


def test_connection():
    """Test MongoDB connection"""
    try:
        client = _get_client()
        client.admin.command("ping")
        return True
    except ConnectionFailure:
        return False
