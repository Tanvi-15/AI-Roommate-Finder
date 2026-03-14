# config.py
# Load from environment variables

import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "roommate_finder")
USERS_COLLECTION = "users"
MATCHES_COLLECTION = "matches"
INTERACTIONS_COLLECTION = "interactions"

# Google OAuth - YOU NEED TO PROVIDE THESE
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
# Redirect URI - must match what you set in Google Cloud Console
# For Streamlit: http://localhost:8501/
# For React frontend: http://localhost:8080/auth/callback
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/auth/callback")

# Frontend URL for CORS - React: http://localhost:8080 | Streamlit: http://localhost:8501
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")

# LLM (Groq)
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Backend 
BACKEND_HOST = os.getenv("BACKEND_HOST", "localhost")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"   # REST API URL
WS_URL = f"ws://{BACKEND_HOST}:{BACKEND_PORT}"          # WebSocket URL


# Debug / Logging - set DEBUG=true to see LLM input/output in terminal
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Session persistence (JWT in cookie) - set a long random secret in production
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-use-secrets-token-urlsafe-32")
SESSION_COOKIE_NAME = "roommate_session"
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "14"))
