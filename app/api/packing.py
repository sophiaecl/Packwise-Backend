from fastapi import APIRouter, HTTPException
from starlette.requests import Request
from google.cloud import bigquery
import os
from dotenv import load_dotenv
import uuid
import json
from app.services.packing_list_generator import generate_packing_list

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TRIP_DATASET_ID = os.getenv("TRIP_DATASET_ID")
TRIP_TABLE_ID = os.getenv("TRIP_TABLE_ID")
PACKING_TABLE_ID = os.getenv("PACKING_TABLE_ID")

router = APIRouter()

client = bigquery.Client()

# generates a packing list based on trip details
@router.post("/generate/{trip_id}")
async def generate_packing_list_route(trip_id: str):
    try:
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
async def get_packing_list(list_id: str):
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