import requests
from fastapi import APIRouter
from app.config import CANOPY_API_KEY

router = APIRouter()

@router.get("/")
def get_packing_recommendations(query: str):
    url = f"https://api.canopy.com/items?search={query}&api_key={CANOPY_API_KEY}"
    response = requests.get(url)
    return response.json()

