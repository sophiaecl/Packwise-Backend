import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Config:
    FIREBASE_API_KEY = os.getenv('FIREBASE_API_KEY')
    WEATHERSTACK_API_KEY = os.getenv('WEATHERSTACK_API_KEY')
    CANOPY_API_KEY = os.getenv('CANOPY_API_KEY')
    DATABASE_URL = os.getenv('DATABASE_URL')

config = Config()
