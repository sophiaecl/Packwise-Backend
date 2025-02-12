from fastapi import APIRouter, Depends
from app.core.database import db
from app.api.auth import verify_token

router = APIRouter()

@router.post("/")
def create_trip(trip_data: dict, user=Depends(verify_token)):
    trip_ref = db.collection("users").document(user["uid"]).collection("trips").add(trip_data)
    return {"message": "Trip created successfully", "trip_id": trip_ref[1].id}

@router.get("/")
def get_trips(user=Depends(verify_token)):
    trips = db.collection("users").document(user["uid"]).collection("trips").stream()
    return [trip.to_dict() for trip in trips]

