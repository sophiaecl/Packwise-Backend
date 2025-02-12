from fastapi import APIRouter, HTTPException
from app.core.database import get_collection
from app.services.weather_service import fetch_weather

router = APIRouter()

@router.post("/")
def create_trip(trip_data: dict):
    try:
        weather_data = fetch_weather(trip_data["destination"])
        trip_data["weather_info"] = weather_data
        trip_ref = get_collection("Trips").document()
        trip_ref.set(trip_data)
        return {"message": "Trip created successfully", "trip_id": trip_ref.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{trip_id}")
async def get_trip(trip_id: str):
    trip_ref = get_collection("Trips").document(trip_id).get()
    if trip_ref.exists:
        return trip_ref.to_dict()
    raise HTTPException(status_code=404, detail="Trip not found")

