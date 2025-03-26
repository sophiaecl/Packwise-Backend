from fastapi import APIRouter, HTTPException, Depends
from google.cloud import bigquery
import os
from dotenv import load_dotenv
import uuid
import json
from app.services.packing_list_generator import generate_packing_list
from app.api.auth import get_current_user
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Union

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TRIP_DATASET_ID = os.getenv("TRIP_DATASET_ID")
TRIP_TABLE_ID = os.getenv("TRIP_TABLE_ID")
PACKING_TABLE_ID = os.getenv("PACKING_TABLE_ID")

class PackingListUpdate(BaseModel):
    packing_list: Dict[str, Any]

router = APIRouter()

client = bigquery.Client(project="capstone-sophiallamas")

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

@router.get("/lists/{trip_id}")
async def get_packing_lists(trip_id: str, current_user: str = Depends(get_current_user)):
    """Fetches all packing lists for a trip."""
    query = f'''
        SELECT list_id FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}` WHERE trip_id = '{trip_id}'
    '''
    results = client.query(query).to_dataframe()
    if results.empty:
        raise HTTPException(status_code=404, detail="No packing lists found for this trip")
    
    return {"packing_lists": results.to_dict(orient="records")}

@router.get("/progress/{packing_list_id}")
async def get_packing_progress(packing_list_id: str, current_user: str = Depends(get_current_user)):
    try: 
        # First get the trip_id associated with this packing list
        trip_query = f"""
            SELECT t.trip_id, t.user_id 
            FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}` p
            JOIN `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}` t ON p.trip_id = t.trip_id
            WHERE p.list_id = @list_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("list_id", "STRING", packing_list_id),
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
            SELECT packing_list FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}` WHERE list_id = '{packing_list_id}'
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
        
        # Calculate the progress
        total_items = packing_list.get("total_items")
        packed_items = 0
        for category in packing_list["categories"]:
            for item in category["items"]:
                if item.get("packed") == True:
                    packed_items += 1
        
        progress = {
            "total_items": total_items,
            "packed_items": packed_items,
            "progress": round(packed_items / total_items * 100, 2)
        }
        
        return progress
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/progress/{trip_id}")
async def get_trip_packing_progress(trip_id: str, current_user: str = Depends(get_current_user)):
    """Fetches the combined packing progress for all packing lists in a trip."""
    try:
        # First verify the trip belongs to the user
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
        trip_result = trip_job.result()
        
        if trip_result.total_rows == 0:
            raise HTTPException(status_code=404, detail="Trip not found or access denied")
        
        print(f"Trip verified for user {current_user}")
        
        # Get all packing lists for this trip
        lists_query = f"""
            SELECT list_id, packing_list
            FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}`
            WHERE trip_id = @trip_id
        """
        lists_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("trip_id", "STRING", trip_id)
            ]
        )
        lists_job = client.query(lists_query, lists_config)
        lists_results = lists_job.result()
        
        # Convert to list to check if empty and to iterate multiple times
        lists_data = list(lists_results)
        
        print(f"Found {len(lists_data)} packing lists for trip {trip_id}")
        
        # If no packing lists for this trip, return 0% progress
        if len(lists_data) == 0:
            return {
                "trip_id": trip_id,
                "total_items": 0,
                "packed_items": 0,
                "progress": 0,
                "lists_count": 0
            }
        
        # Aggregate data from all packing lists
        total_items = 0
        packed_items = 0
        valid_lists = 0
        parsed_lists = []
        
        for row in lists_data:
            list_id = row.list_id
            packing_list_str = row.packing_list
            
            if not packing_list_str:
                print(f"Skipping empty packing list {list_id}")
                continue
                
            try:
                print(f"Parsing packing list {list_id}")
                packing_list = json.loads(packing_list_str)
                parsed_lists.append({"list_id": list_id, "data": packing_list})
                
                # Skip invalid packing lists
                if not isinstance(packing_list, dict):
                    print(f"Packing list {list_id} is not a dictionary")
                    continue
                    
                if "categories" not in packing_list:
                    print(f"Packing list {list_id} has no categories")
                    continue
                
                if not isinstance(packing_list["categories"], list):
                    print(f"Categories in packing list {list_id} is not a list")
                    continue
                
                # Count items from all categories
                list_items = 0
                list_packed = 0
                
                for category_idx, category in enumerate(packing_list.get("categories", [])):
                    if not isinstance(category, dict):
                        print(f"Category {category_idx} in list {list_id} is not a dictionary")
                        continue
                        
                    if "items" not in category:
                        print(f"Category {category_idx} in list {list_id} has no items")
                        continue
                        
                    if not isinstance(category["items"], list):
                        print(f"Items in category {category_idx} of list {list_id} is not a list")
                        continue
                    
                    for item_idx, item in enumerate(category.get("items", [])):
                        if not isinstance(item, dict):
                            print(f"Item {item_idx} in category {category_idx} of list {list_id} is not a dictionary")
                            continue
                            
                        list_items += 1
                        if item.get("packed") == True:
                            list_packed += 1
                
                print(f"List {list_id}: {list_items} items, {list_packed} packed")
                
                # Only count this list if it has items
                if list_items > 0:
                    total_items += list_items
                    packed_items += list_packed
                    valid_lists += 1
                
            except json.JSONDecodeError as e:
                print(f"Invalid JSON in packing list {list_id}: {str(e)}")
                continue
            except Exception as e:
                print(f"Error processing packing list {list_id}: {str(e)}")
                continue
        
        print(f"Total: {total_items} items, {packed_items} packed, {valid_lists} valid lists")
        
        # Calculate overall progress
        progress = 0
        if total_items > 0:
            progress = round((packed_items / total_items) * 100, 2)
        
        result = {
            "trip_id": trip_id,
            "total_items": total_items,
            "packed_items": packed_items,
            "progress": progress,
            "lists_count": valid_lists
        }
        
        print(f"Final result: {result}")
        return result
        
    except Exception as e:
        print(f"Error calculating trip packing progress: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error calculating progress: {str(e)}")

@router.get("/progress/all")
async def get_all_packing_progress(current_user: str = Depends(get_current_user)):
    """Fetches the average progress for all packing lists across all trips for the user."""
    try:
        # Query all packing lists for the user
        query = f"""
            SELECT p.packing_list 
            FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}` p
            JOIN `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}` t ON p.trip_id = t.trip_id
            WHERE t.user_id = @user_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", current_user),
            ]
        )
        results = client.query(query, job_config=job_config).result()

        # If no results, return 0% progress
        if results.total_rows == 0:
            return {"average_progress": 0}

        # Calculate progress for each packing list
        total_progress = 0
        list_count = 0

        for row in results:
            packing_list_str = row.packing_list
            if not packing_list_str:
                continue
                
            try:
                packing_list = json.loads(packing_list_str)
                
                # Skip invalid packing lists
                if not isinstance(packing_list, dict) or "categories" not in packing_list:
                    continue
                
                # Get total items - either from the property or count manually
                if "total_items" in packing_list and isinstance(packing_list["total_items"], (int, float)) and packing_list["total_items"] > 0:
                    total_items = packing_list["total_items"]
                else:
                    # Count total items manually
                    total_items = sum(
                        len(category.get("items", []))
                        for category in packing_list.get("categories", [])
                        if isinstance(category, dict)
                    )
                
                # Skip if no items
                if total_items == 0:
                    continue
                
                # Count packed items
                packed_items = 0
                for category in packing_list.get("categories", []):
                    if not isinstance(category, dict) or "items" not in category:
                        continue
                    
                    for item in category.get("items", []):
                        if isinstance(item, dict) and item.get("packed") == True:
                            packed_items += 1
                
                # Calculate progress for this list
                list_progress = (packed_items / total_items) * 100
                total_progress += list_progress
                list_count += 1
                
            except json.JSONDecodeError:
                # Skip invalid JSON
                continue
            except Exception as e:
                # Log error but continue processing
                print(f"Error processing packing list: {str(e)}")
                continue

        # If no valid lists processed, return 0%
        if list_count == 0:
            return {"average_progress": 0}

        # Calculate average progress
        average_progress = round(total_progress / list_count, 2)
        return {"average_progress": average_progress}
        
    except Exception as e:
        # Log the error but return a default instead of raising an exception
        print(f"Error calculating overall packing progress: {str(e)}")
        return {"average_progress": 0}

@router.delete("/{packing_list_id}")
async def delete_packing_list(packing_list_id: str, current_user: str = Depends(get_current_user)):
    try:
        # verify the packing list belongs to the current user
        trip_query = f"""
            SELECT t.trip_id, t.user_id 
            FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}` p
            JOIN `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}` t ON p.trip_id = t.trip_id
            WHERE p.list_id = @list_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("list_id", "STRING", packing_list_id),
                bigquery.ScalarQueryParameter("user_id", "STRING", current_user),
            ]
        )
        list_results = client.query(trip_query, job_config=job_config).result()
        if list_results.total_rows == 0:
            raise HTTPException(status_code=404, detail="Packing list not found")
        
        # delete the packing list
        list_query = f"""
            DELETE FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}` 
            WHERE list_id = '{packing_list_id}'
        """
        list_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("list_id", "STRING", packing_list_id),
            ]
        )
        client.query(list_query, list_config).result()

        return {"message": "Packing list deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.put("/{packing_list_id}")
async def update_packing_list(packing_list_id: str, update_data: PackingListUpdate, current_user: str = Depends(get_current_user)):
    try:
        # First verify the packing list belongs to the current user
        trip_query = f"""
            SELECT t.trip_id, t.user_id 
            FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}` p
            JOIN `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}` t ON p.trip_id = t.trip_id
            WHERE p.list_id = @list_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("list_id", "STRING", packing_list_id),
            ]
        )
        trip_results = client.query(trip_query, job_config=job_config).result()
        
        if trip_results.total_rows == 0:
            raise HTTPException(status_code=404, detail="Packing list not found")
        
        trip_data = [row for row in trip_results][0]
        
        # Verify the trip belongs to the current user
        if trip_data["user_id"] != current_user:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Serialize the packing list to a JSON string
        packing_list_json = json.dumps(update_data.packing_list)
        
        # Update the packing list in the database
        update_query = f"""
            UPDATE `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}`
            SET packing_list = @packing_list
            WHERE list_id = @list_id
        """
        update_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("packing_list", "STRING", packing_list_json),
                bigquery.ScalarQueryParameter("list_id", "STRING", packing_list_id),
            ]
        )
        client.query(update_query, update_config).result()
        
        return {
            "message": "Packing list updated successfully",
            "list_id": packing_list_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update packing list: {str(e)}")
