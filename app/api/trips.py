from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from starlette.requests import Request
from typing import Literal
from google.cloud import bigquery
import uuid
import os 
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Initialize BigQuery client
client = bigquery.Client()
TRIP_DATASET_ID = os.getenv("TRIP_DATASET_ID")
TRIP_TABLE_ID = os.getenv("TRIP_TABLE_ID")

class Trip(BaseModel):
    city: str
    country: str
    start_date: str
    end_date: str
    luggage_type: Literal["hand", "carry on", "checked"]
    trip_purpose: Literal["business", "vacation"]

@router.post("/")
async def create_trip(request: Request,trip: Trip):
    user = request.session.get("user")  
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        trip_data = trip.dict()
        trip_data["username"] = user
        trip_data["trip_id"] = str(uuid.uuid4())  # Generate a unique trip ID

        rows_to_insert = [{
            "username": trip_data["username"],
            "trip_id": trip_data["trip_id"],
            "start_date": trip_data["start_date"],
            "end_date": trip_data["end_date"],
            "luggage_type": trip_data["luggage_type"],
            "trip_purpose": trip_data["trip_purpose"],
            "city": trip_data["city"],
            "country": trip_data["country"]
        }]
        errors = client.insert_rows_json(f"{TRIP_DATASET_ID}.{TRIP_TABLE_ID}", rows_to_insert)
        if errors:
            raise HTTPException(status_code=500, detail=str(errors))

        return {"message": "Trip created successfully", "trip_id": trip_data["trip_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{trip_id}")
async def get_trip(trip_id: str):
    query = f"""
        SELECT trip_id, city, country, start_date, end_date, luggage_type, trip_purpose, username
        FROM `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}`
        WHERE trip_id = @trip_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id)
        ]
    )
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    if results.total_rows == 0:
        raise HTTPException(status_code=404, detail="Trip not found")

    trip_data = [row for row in results][0]
    # weather_data = fetch_weather(trip_data["city"])
    # trip_data["weather_info"] = weather_data

    return trip_data

@router.delete("/delete/{trip_id}")
async def delete_trip(request: Request, trip_id: str):
    user = request.session.get("user") 
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        query = f"""
        DELETE FROM `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}`
        WHERE trip_id = @trip_id AND username = @username
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id),
                bigquery.ScalarQueryParameter("username", "STRING", user),
            ]
        )
        client.query(query, job_config=job_config).result()
        return {"message": "Trip deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

