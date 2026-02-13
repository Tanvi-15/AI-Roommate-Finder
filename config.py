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

# Debug / Logging - set DEBUG=true to see LLM input/output in terminal
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
