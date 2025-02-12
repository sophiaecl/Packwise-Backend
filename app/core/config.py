import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Firestore Credentials
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")

# API Keys
WEATHERSTACK_API_KEY = os.getenv("WEATHERSTACK_API_KEY")
CANOPY_API_KEY = os.getenv("CANOPY_API_KEY")

# Debug Mode
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

