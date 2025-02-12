import requests
from fastapi import APIRouter
from app.config import WEATHERSTACK_API_KEY

router = APIRouter()

@router.get("/")
def get_weather(location: str):
    url = f"http://api.weatherstack.com/current?access_key={WEATHERSTACK_API_KEY}&query={location}"
    response = requests.get(url)
    return response.json()

