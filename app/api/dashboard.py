from fastapi import APIRouter, HTTPException, status
from starlette.requests import Request
from google.cloud import bigquery
import os 
from dotenv import load_dotenv

load_dotenv()

TRIP_DATASET_ID = os.getenv("TRIP_DATASET_ID")
TRIP_TABLE_ID = os.getenv("TRIP_TABLE_ID")

router = APIRouter()

client = bigquery.Client()
dataset_id = TRIP_DATASET_ID
table_id = TRIP_TABLE_ID

# Protected Dashboard Endpoint
@router.get("/")
async def dashboard(request: Request):
    user = request.session.get("user")

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    
    trips = await get_user_trips(user)
    return {"message": f"Welcome to your dashboard, {user}!", "trips": trips} 

async def get_user_trips(username: str):
    query = f"""
        SELECT trip_id, city, country, start_date, end_date, luggage_type, trip_purpose
        FROM `{dataset_id}.{table_id}`
        WHERE username = @username
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("username", "STRING", username)
        ]
    )
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    trips = []
    for row in results:
        trips.append({
            "trip_id": row.trip_id,
            "city": row.city,
            "country": row.country,
            "start_date": row.start_date,
            "end_date": row.end_date,
            "luggage_type": row.luggage_type,
            "trip_purpose": row.trip_purpose
        })
    return trips
