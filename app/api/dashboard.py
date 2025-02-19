from fastapi import APIRouter, HTTPException, status
from starlette.requests import Request
from google.cloud import bigquery
import os 
from dotenv import load_dotenv

load_dotenv()

TRIP_DATASET_ID = os.getenv("TRIP_DATASET_ID")
TRIP_TABLE_ID = os.getenv("TRIP_TABLE_ID")
USER_DATASET_ID = os.getenv("USER_DATASET_ID")
USER_INFO_TABLE_ID = os.getenv("USER_INFO_TABLE_ID")

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
    
    name = await get_name(user)
    trips = await get_user_trips(user)
    return {"message": f"Welcome to your dashboard, {name}!", "trips": trips} 

async def get_name(user_id: str):
    query = f"""
        SELECT name
        FROM `{USER_DATASET_ID}.{USER_INFO_TABLE_ID}`
        WHERE user_id = @user_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
        ]
    )
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    if results.total_rows == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_data = [row for row in results][0]
    return user_data["name"]

async def get_user_trips(user_id: str):
    query = f"""
        SELECT trip_id, city, country, start_date, end_date, luggage_type, trip_purpose
        FROM `{dataset_id}.{table_id}`
        WHERE user_id = @user_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
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
