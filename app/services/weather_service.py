import requests
import os

WEATHERSTACK_URL = "http://api.weatherstack.com/current"
WEATHER_API_KEY = os.getenv("WEATHERSTACK_API_KEY")

def fetch_weather(destination: str):
    """Fetches weather data for a given location."""
    params = {"access_key": WEATHER_API_KEY, "query": destination}
    response = requests.get(WEATHERSTACK_URL, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": "Failed to fetch weather data"}
