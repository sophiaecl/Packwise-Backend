from fastapi import APIRouter, HTTPException, Depends
from google.cloud import bigquery
import os
from dotenv import load_dotenv
import uuid
import json
from app.services.packing_list_generator import generate_packing_list
from app.api.auth import get_current_user

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TRIP_DATASET_ID = os.getenv("TRIP_DATASET_ID")
TRIP_TABLE_ID = os.getenv("TRIP_TABLE_ID")
PACKING_TABLE_ID = os.getenv("PACKING_TABLE_ID")

router = APIRouter()

client = bigquery.Client()

# generates a packing list based on trip details
@router.post("/generate/{trip_id}")
async def generate_packing_list_route(trip_id: str, current_user: str = Depends(get_current_user)):
    try:
        # Verify trip belongs to user
        trip_query = f"""
            SELECT trip_id FROM `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}`
            WHERE trip_id = @trip_id AND user_id = @user_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id),
                bigquery.ScalarQueryParameter("user_id", "STRING", current_user),
            ]
        )
        trip_results = client.query(trip_query, job_config=job_config).result()
        
        if trip_results.total_rows == 0:
            raise HTTPException(status_code=404, detail="Trip not found or access denied")

        packing_list = str(generate_packing_list(trip_id))[7:-3]
        packing_list_id = str(uuid.uuid4())
        
        # Save to BigQuery
        table_id = f"{TRIP_DATASET_ID}.{PACKING_TABLE_ID}"
        row = {
            "list_id": packing_list_id,
            "trip_id": trip_id,
            "packing_list": packing_list
        }
        errors = client.insert_rows_json(table_id, [row])
        if errors:
            raise HTTPException(status_code=500, detail=f"Error saving to BigQuery: {errors}")
        
        return {"packing_list_id": packing_list_id, "packing_list": packing_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{packing_list_id}")
async def get_packing_list(list_id: str, current_user: str = Depends(get_current_user)):
    """Fetches the packing list for a trip."""
    # First get the trip_id associated with this packing list
    trip_query = f"""
        SELECT t.trip_id, t.user_id 
        FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}` p
        JOIN `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}` t ON p.trip_id = t.trip_id
        WHERE p.list_id = @list_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("list_id", "STRING", list_id),
        ]
    )
    trip_results = client.query(trip_query, job_config=job_config).result()
    
    if trip_results.total_rows == 0:
        raise HTTPException(status_code=404, detail="Packing list not found")
    
    trip_data = [row for row in trip_results][0]
    
    # Verify the trip belongs to the current user
    if trip_data["user_id"] != current_user:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get the packing list
    query = f'''
        SELECT packing_list FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}` WHERE list_id = '{list_id}'
    '''
    results = client.query(query).to_dataframe()
    if results.empty:
        raise HTTPException(status_code=404, detail="list not found")
    
    row = results.iloc[0].to_dict()
    packing_list_str = row.get("packing_list", "[]")

    try:
        packing_list = json.loads(packing_list_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Packing list contains invalid JSON format.")
    
    return {"packing_list": packing_list}