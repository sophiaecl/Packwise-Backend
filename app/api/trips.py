from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Literal
from google.cloud import bigquery
from app.services.weather_predictor import WeatherPredictor
from app.api.auth import get_current_user
import uuid
import os 
import json
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# initialize BigQuery client
client = bigquery.Client(project="capstone-sophiallamas")
# get environment variables
TRIP_DATASET_ID = os.getenv("TRIP_DATASET_ID")
TRIP_TABLE_ID = os.getenv("TRIP_TABLE_ID")
TRIP_WEATHER_TABLE_ID = os.getenv("TRIP_WEATHER_TABLE_ID")
WEATHERSTACK_API_KEY = os.getenv("WEATHERSTACK_API_KEY")
HISTORICAL_WEATHER_TABLE = os.getenv("HISTORICAL_WEATHER_TABLE")
PACKING_TABLE_ID = os.getenv("PACKING_TABLE_ID")

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
async def create_trip(trip: Trip, current_user: str = Depends(get_current_user)):
    try:
        # creates trip object from the request data
        trip_data = trip.dict()
        trip_data["user_id"] = current_user  # gets user id from JWT token
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
        
        historical_data_rows = [{
            "trip_id": trip_data["trip_id"], 
            "historical_stats": json.dumps(prediction["historical_data"], indent=2)  # contains the array of historical records
        }]

        historical_errors = client.insert_rows_json(f"{TRIP_DATASET_ID}.{HISTORICAL_WEATHER_TABLE}", historical_data_rows)
        if historical_errors:
            raise HTTPException(status_code=500, detail=str(historical_errors))

        # final message to return if everything is successful
        return {"message": "Trip created successfully", "trip_id": trip_data["trip_id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{trip_id}")
async def get_trip(trip_id: str, current_user: str = Depends(get_current_user)):
    query = f"""
        SELECT trip_id, city, country, start_date, end_date, luggage_type, trip_purpose, user_id
        FROM `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}`
        WHERE trip_id = @trip_id AND user_id = @user_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id),
            bigquery.ScalarQueryParameter("user_id", "STRING", current_user)
        ]
    )
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    if results.total_rows == 0:
        raise HTTPException(status_code=404, detail="Trip not found")

    trip_data = [row for row in results][0]

    return trip_data

@router.get("/weather/{trip_id}")
async def get_trip_weather(trip_id: str, current_user: str = Depends(get_current_user)):
    # First verify that the trip belongs to the user
    trip_query = f"""
        SELECT 1
        FROM `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}`
        WHERE trip_id = @trip_id AND user_id = @user_id
    """
    trip_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id),
            bigquery.ScalarQueryParameter("user_id", "STRING", current_user)
        ]
    )
    trip_job = client.query(trip_query, trip_config)
    if trip_job.result().total_rows == 0:
        raise HTTPException(status_code=404, detail="Trip not found")

    # If trip belongs to user, get weather data
    query = f"""
        SELECT *
        FROM `{TRIP_DATASET_ID}.{TRIP_WEATHER_TABLE_ID}`
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
        raise HTTPException(status_code=404, detail="Trip weather not found")

    trip_weather_data = [row for row in results][0]
    return trip_weather_data

@router.get("/weather/historical/{trip_id}")
async def get_historical_weather(trip_id: str, current_user: str = Depends(get_current_user)):
    # verify that the trip belongs to the user
    trip_query = f"""
        SELECT 1
        FROM `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}`
        WHERE trip_id = @trip_id AND user_id = @user_id
    """
    trip_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id),
            bigquery.ScalarQueryParameter("user_id", "STRING", current_user)
        ]
    )
    trip_job = client.query(trip_query, trip_config)
    if trip_job.result().total_rows == 0:
        raise HTTPException(status_code=404, detail="Trip not found")

    # get historical weather data
    query = f"""
        SELECT *
        FROM `{TRIP_DATASET_ID}.{HISTORICAL_WEATHER_TABLE}`
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
        raise HTTPException(status_code=404, detail="Historical weather data not found")

    data = [row for row in results][0]
    historical_data = json.loads(data.historical_stats)

    return {"trip_id": data.trip_id, "historical_data": historical_data}

@router.delete("/delete/{trip_id}")
async def delete_trip(trip_id: str, current_user: str = Depends(get_current_user)):
    try:
        # First verify that the trip belongs to the user
        trip_query = f"""
            SELECT 1
            FROM `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}`
            WHERE trip_id = @trip_id AND user_id = @user_id
        """
        trip_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id),
                bigquery.ScalarQueryParameter("user_id", "STRING", current_user)
            ]
        )
        trip_job = client.query(trip_query, trip_config)
        if trip_job.result().total_rows == 0:
            raise HTTPException(status_code=404, detail="Trip not found or you don't have permission to delete it")
        
        # 1. Delete packing lists associated with the trip
        packing_query = f"""
            DELETE FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}`
            WHERE trip_id = @trip_id
        """
        packing_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id),
            ]
        )
        client.query(packing_query, packing_config).result()
        
        # 2. Delete weather data associated with the trip
        weather_query = f"""
            DELETE FROM `{TRIP_DATASET_ID}.{TRIP_WEATHER_TABLE_ID}`
            WHERE trip_id = @trip_id
        """
        weather_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id),
            ]
        )
        client.query(weather_query, weather_config).result()
        
        # 3. Finally delete the trip itself
        trip_delete_query = f"""
            DELETE FROM `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}`
            WHERE trip_id = @trip_id AND user_id = @user_id
        """
        trip_delete_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id),
                bigquery.ScalarQueryParameter("user_id", "STRING", current_user),
            ]
        )
        client.query(trip_delete_query, trip_delete_config).result()
        
        return {"message": "Trip and all associated data deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/update/{trip_id}")
async def update_trip(trip_id: str, trip: Trip, current_user: str = Depends(get_current_user)):
    try:
        trip_data = trip.dict()
        
        # First verify that the trip belongs to the user
        trip_query = f"""
            SELECT 1
            FROM `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}`
            WHERE trip_id = @trip_id AND user_id = @user_id
        """
        trip_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id),
                bigquery.ScalarQueryParameter("user_id", "STRING", current_user)
            ]
        )
        trip_job = client.query(trip_query, trip_config)
        if trip_job.result().total_rows == 0:
            raise HTTPException(status_code=404, detail="Trip not found")

        # Update trip information
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
                bigquery.ScalarQueryParameter("user_id", "STRING", current_user),
            ]
        )
        client.query(query, job_config=job_config).result()

        # Get new weather predictions
        predictor = WeatherPredictor(WEATHERSTACK_API_KEY)
        try:
            prediction = predictor.predict_trip_weather(trip_data["city"], trip_data["start_date"], trip_data["end_date"])
            if not isinstance(prediction, dict):
                raise HTTPException(status_code=500, detail=f"Failed to predict weather: {prediction}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to predict weather: {str(e)}")

        # Update weather data
        weather_query = f"""
        UPDATE `{TRIP_DATASET_ID}.{TRIP_WEATHER_TABLE_ID}`
        SET min_temp = @min_temp,
            max_temp = @max_temp,
            uv = @uv,
            description = @description,
            confidence = @confidence
        WHERE trip_id = @trip_id
        """
        weather_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("min_temp", "FLOAT64", prediction["predicted_min_temp"]),
                bigquery.ScalarQueryParameter("max_temp", "FLOAT64", prediction["predicted_max_temp"]),
                bigquery.ScalarQueryParameter("uv", "FLOAT64", prediction["predicted_uv_index"]),
                bigquery.ScalarQueryParameter("description", "STRING", prediction["predicted_description"]),
                bigquery.ScalarQueryParameter("confidence", "FLOAT64", prediction["confidence_score"]),
                bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id)
            ]
        )
        client.query(weather_query, weather_config).result()

        return {"message": "Trip and weather data updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

