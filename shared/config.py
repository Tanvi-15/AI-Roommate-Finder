# config.py
# Load from environment variables

import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "roommate_finder")
USERS_COLLECTION = "users"

# Google OAuth - YOU NEED TO PROVIDE THESE
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
# Redirect URI - must match what you set in Google Cloud Console
# For local Streamlit: http://localhost:8501/
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501/")

# Ollama
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:latest")

# Backend 
BACKEND_HOST = os.getenv("BACKEND_HOST", "localhost")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"   # REST API URL
WS_URL = f"ws://{BACKEND_HOST}:{BACKEND_PORT}"          # WebSocket URL


# Debug / Logging - set DEBUG=true to see LLM input/output in terminal
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
