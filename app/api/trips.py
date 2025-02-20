from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from starlette.requests import Request
from typing import Literal
from google.cloud import bigquery
from app.services.weather_predictor import WeatherPredictor
import uuid
import os 
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# initialize BigQuery client
client = bigquery.Client()
# get environment variables
TRIP_DATASET_ID = os.getenv("TRIP_DATASET_ID")
TRIP_TABLE_ID = os.getenv("TRIP_TABLE_ID")
TRIP_WEATHER_TABLE_ID = os.getenv("TRIP_WEATHER_TABLE_ID")
WEATHERSTACK_API_KEY = os.getenv("WEATHERSTACK_API_KEY")

# create a Pydantic model for the trip data
class Trip(BaseModel):
    city: str
    country: str
    start_date: str
    end_date: str
    luggage_type: Literal["hand", "carry on", "checked"]
    trip_purpose: Literal["business", "vacation"]

# create a trip
# inserts trip data into the trip information table and the trip weather table
# calls the WeatherPredictor class to predict the weather for the trip
@router.post("/")
async def create_trip(request: Request,trip: Trip):
    # makes sure user is authenticated before creating a trip
    user = request.session.get("user")  
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        # creates trip object from the request data
        trip_data = trip.dict()
        trip_data["user_id"] = user # gets user id from the session
        trip_data["trip_id"] = str(uuid.uuid4())  # generate a unique trip ID

        trip_info_rows = [{
            "user_id": trip_data["user_id"],
            "trip_id": trip_data["trip_id"],
            "start_date": trip_data["start_date"],
            "end_date": trip_data["end_date"],
            "luggage_type": trip_data["luggage_type"],
            "trip_purpose": trip_data["trip_purpose"],
            "city": trip_data["city"],
            "country": trip_data["country"]
        }]

        # call predictor class to predict weather for a trip
        # want to make sure the prediction is successful before inserting data
        predictor = WeatherPredictor(WEATHERSTACK_API_KEY) 

        # making the prediction (dictionary) for the trip with the parameters city, start_date, end_date 
        # try to make prediction, catches any errors when making prediction before trying to insert data
        try:
            prediction = predictor.predict_trip_weather(trip_data["city"], trip_data["start_date"], trip_data["end_date"])
            if not isinstance(prediction, dict):
                raise HTTPException(status_code=500, detail=f"Failed to predict weather: {prediction}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to predict weather: {str(e)}")

        # once prediction is successful, insert the trip data into the trip information table
        info_errors = client.insert_rows_json(f"{TRIP_DATASET_ID}.{TRIP_TABLE_ID}", trip_info_rows)
        if info_errors:
            raise HTTPException(status_code=500, detail=str(info_errors))

        # insert the predicted weather data into the trip weather table (so we don't have to call api every time)
        trip_weather_rows = [{
            "trip_id": trip_data["trip_id"],
            "min_temp": prediction["predicted_min_temp"],
            "max_temp": prediction["predicted_max_temp"],
            "uv": prediction["predicted_uv_index"],
            "description": prediction["predicted_description"],
            "confidence": prediction["confidence_score"] 
        }]

        weather_errors = client.insert_rows_json(f"{TRIP_DATASET_ID}.{TRIP_WEATHER_TABLE_ID}", trip_weather_rows)
        if weather_errors:
            raise HTTPException(status_code=500, detail=str(weather_errors))

        # final message to return if everything is successful
        return {"message": "Trip created successfully", "trip_id": trip_data["trip_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# NEED TO ADD ACCESS TO WEATHER DATA WHEN TRIP IS OPENED
@router.get("/{trip_id}")
async def get_trip(trip_id: str):
    query = f"""
        SELECT trip_id, city, country, start_date, end_date, luggage_type, trip_purpose, user_id
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

# NEED TO DELETE DATA FROM TRIP WEATHER TABLE WHEN TRIP IS DELETED
@router.delete("/delete/{trip_id}")
async def delete_trip(request: Request, trip_id: str):
    user = request.session.get("user") 
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        query = f"""
        DELETE FROM `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}`
        WHERE trip_id = @trip_id AND user_id = @user_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id),
                bigquery.ScalarQueryParameter("user_id", "STRING", user),
            ]
        )
        client.query(query, job_config=job_config).result()
        return {"message": "Trip deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# NEED TO MAKE THE DEFAULT VALUES IN THE DICTIONARY TO THE VALUES ALREADY IN THE DATABASE 
@router.put("/update/{trip_id}")
async def update_trip(request: Request, trip_id: str, trip: Trip):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        trip_data = trip.dict()
        query = f"""
        UPDATE `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}`
        SET city = @city,
            country = @country,
            start_date = @start_date,
            end_date = @end_date,
            luggage_type = @luggage_type,
            trip_purpose = @trip_purpose
        WHERE trip_id = @trip_id AND user_id = @user_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("city", "STRING", trip_data["city"]),
                bigquery.ScalarQueryParameter("country", "STRING", trip_data["country"]),
                bigquery.ScalarQueryParameter("start_date", "STRING", trip_data["start_date"]),
                bigquery.ScalarQueryParameter("end_date", "STRING", trip_data["end_date"]),
                bigquery.ScalarQueryParameter("luggage_type", "STRING", trip_data["luggage_type"]),
                bigquery.ScalarQueryParameter("trip_purpose", "STRING", trip_data["trip_purpose"]),
                bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id),
                bigquery.ScalarQueryParameter("user_id", "STRING", user),
            ]
        )
        client.query(query, job_config=job_config).result()
        return {"message": "Trip updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

