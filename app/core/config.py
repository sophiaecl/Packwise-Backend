import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Config:
    WEATHERSTACK_API_KEY = os.getenv('WEATHERSTACK_API_KEY')
    CANOPY_API_KEY = os.getenv('CANOPY_API_KEY')
    SECRET_KEY = "a1b2c3d4e5f67890abcdef1234567890abcdefabcdefabcdefabcdefabcdef1234"
    USER_DATASET_ID = "capstone-sophiallamas.Users"
    TRIP_DATASET_ID = "capstone-sophiallamas.Trips"
    USERNAME_TABLE_ID = "user_login"
    USER_INFO_TABLE_ID = "user_info"
    TRIP_TABLE_ID = "trips"

config = Config()
