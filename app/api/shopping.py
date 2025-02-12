from fastapi import APIRouter, HTTPException
import requests
import os

router = APIRouter()
CANOPY_API_KEY = os.getenv("CANOPY_API_KEY")

@router.get("/{trip_id}/recommendations")
async def get_shopping_recommendations(trip_id: str):
    """Fetches product recommendations for a trip."""
    canopy_url = f"https://api.canopy.com/products?trip_id={trip_id}&api_key={CANOPY_API_KEY}"
    response = requests.get(canopy_url)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to fetch recommendations")

    return {"recommendations": response.json()}
