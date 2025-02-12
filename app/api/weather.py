from fastapi import APIRouter, HTTPException
import requests
import os

router = APIRouter()
WEATHERSTACK_API_KEY = os.getenv("WEATHERSTACK_API_KEY")
WEATHERSTACK_URL = "http://api.weatherstack.com/current"

def fetch_weather(destination: str):
    """Fetches weather data for a given location."""
    params = {"access_key": WEATHERSTACK_API_KEY, "query": destination}
    response = requests.get(WEATHERSTACK_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=500, detail="Failed to fetch weather data")

@router.get("/{destination}")
async def get_weather(destination: str):
    """Retrieves weather data for a specified destination."""
    try:
        weather_data = fetch_weather(destination)
        return {"destination": destination, "weather": weather_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
