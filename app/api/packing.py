from fastapi import APIRouter, HTTPException
from app.core.database import get_collection

router = APIRouter()

@router.post("/{trip_id}/generate")
async def generate_packing_list(trip_id: str):
    """Generates a packing list based on trip details."""
    trip_ref = get_collection("Trips").document(trip_id).get()
    if not trip_ref.exists:
        raise HTTPException(status_code=404, detail="Trip not found")

    trip_data = trip_ref.to_dict()
    packing_list = [
        "T-Shirts", "Jeans", "Toothbrush", "Socks",
        "Passport", "Phone Charger", "Sunglasses"
    ]

    # Store packing list in Firestore
    trip_ref.reference.update({"packing_list": packing_list})
    return {"message": "Packing list generated", "packing_list": packing_list}

@router.get("/{trip_id}")
async def get_packing_list(trip_id: str):
    """Fetches the packing list for a trip."""
    trip_ref = get_collection("Trips").document(trip_id).get()
    if not trip_ref.exists:
        raise HTTPException(status_code=404, detail="Trip not found")

    return {"packing_list": trip_ref.to_dict().get("packing_list", [])}
