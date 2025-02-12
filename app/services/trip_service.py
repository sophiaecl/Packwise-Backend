from app.core.database import get_collection
from app.services.weather_service import fetch_weather

def create_trip(trip_data: dict):
    """Creates a trip and fetches weather data."""
    weather_data = fetch_weather(trip_data["destination"])
    trip_data["weather_info"] = weather_data

    trip_ref = get_collection("Trips").document()
    trip_ref.set(trip_data)
    return {"message": "Trip created successfully", "trip_id": trip_ref.id}
