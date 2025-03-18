from fastapi import APIRouter, HTTPException, Depends
from google.cloud import bigquery
import json
from collections import Counter
import os
from dotenv import load_dotenv
from app.api.auth import get_current_user
from typing import List, Dict, Any

load_dotenv()

TRIP_DATASET_ID = os.getenv("TRIP_DATASET_ID")
TRIP_TABLE_ID = os.getenv("TRIP_TABLE_ID")
TRIP_WEATHER_TABLE_ID = os.getenv("TRIP_WEATHER_TABLE_ID")
PACKING_TABLE_ID = os.getenv("PACKING_TABLE_ID")

router = APIRouter()

client = bigquery.Client(project="capstone-sophiallamas")

def get_packing_list_trip_info(list_id: str, user_id: str):
    """Get trip information associated with a specific packing list."""
    query = f"""
        SELECT p.packing_list, t.trip_id, t.trip_purpose, t.country, t.city,
               w.min_temp, w.max_temp, w.description
        FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}` p
        JOIN `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}` t ON p.trip_id = t.trip_id
        JOIN `{TRIP_DATASET_ID}.{TRIP_WEATHER_TABLE_ID}` w ON t.trip_id = w.trip_id
        WHERE p.list_id = @list_id AND t.user_id = @user_id
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("list_id", "STRING", list_id),
            bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
        ]
    )
    
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()
    
    if results.total_rows == 0:
        raise HTTPException(status_code=404, detail="Packing list or associated trip not found")
    
    return next(results)

def find_similar_trips(trip_info, similarity_threshold: float = 0.6) -> List[str]:
    """
    Find similar trips based on destination, weather conditions, and trip purpose.
    
    Parameters:
    - trip_info: The trip information associated with the packing list
    - similarity_threshold: Minimum similarity score (0-1) to consider trips as similar
    
    Returns:
    - List of similar trip IDs
    """
    # Find trips with similar characteristics
    similar_trips_query = f"""
        WITH trip_details AS (
            SELECT t.trip_id,
                   CASE 
                       WHEN t.trip_purpose = @trip_purpose THEN 0.2 ELSE 0 
                   END +
                   CASE 
                       WHEN t.country = @country THEN 0.1 ELSE 0 
                   END +
                   CASE 
                       WHEN t.city = @city THEN 0.1 ELSE 0 
                   END +
                   CASE 
                       WHEN ABS(w.min_temp - @min_temp) < 5 THEN 0.2 ELSE 0 
                   END +
                   CASE 
                       WHEN ABS(w.max_temp - @max_temp) < 5 THEN 0.2 ELSE 0 
                   END +
                   CASE 
                       WHEN w.description LIKE @description_pattern THEN 0.2 ELSE 0 
                   END AS similarity_score
            FROM `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}` t
            JOIN `{TRIP_DATASET_ID}.{TRIP_WEATHER_TABLE_ID}` w ON t.trip_id = w.trip_id
            WHERE t.trip_id != @trip_id  -- Exclude the current trip
        )
        SELECT trip_id 
        FROM trip_details
        WHERE similarity_score >= @similarity_threshold
        ORDER BY similarity_score DESC
        LIMIT 50
    """
    
    # Create pattern for partial matching of weather description
    description_words = trip_info.description.split()
    description_pattern = '%' + '%'.join(description_words) + '%' if description_words else '%'
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("trip_id", "STRING", trip_info.trip_id),
            bigquery.ScalarQueryParameter("trip_purpose", "STRING", trip_info.trip_purpose),
            bigquery.ScalarQueryParameter("country", "STRING", trip_info.country),
            bigquery.ScalarQueryParameter("city", "STRING", trip_info.city),
            bigquery.ScalarQueryParameter("min_temp", "FLOAT64", trip_info.min_temp),
            bigquery.ScalarQueryParameter("max_temp", "FLOAT64", trip_info.max_temp),
            bigquery.ScalarQueryParameter("description_pattern", "STRING", description_pattern),
            bigquery.ScalarQueryParameter("similarity_threshold", "FLOAT64", similarity_threshold)
        ]
    )
    
    query_job = client.query(similar_trips_query, job_config=job_config)
    results = query_job.result()
    
    similar_trip_ids = [row.trip_id for row in results]
    return similar_trip_ids

def extract_items_from_packing_list(packing_list_str: str) -> set:
    """Extract a set of item names from a packing list string."""
    items = set()
    
    try:
        packing_list = json.loads(packing_list_str)
        if not packing_list or "categories" not in packing_list:
            return items
        
        for category in packing_list.get("categories", []):
            for item in category.get("items", []):
                # Normalize item names (lowercase, strip spaces)
                item_name = item.get("name", "").lower().strip()
                if item_name:
                    items.add(item_name)
        
    except json.JSONDecodeError:
        # Return empty set for invalid JSON
        pass
    
    return items

def get_all_packing_lists_for_similar_trips(similar_trip_ids: List[str]) -> Dict[str, set]:
    """
    Get all packing lists for the given trip IDs.
    
    Returns a dictionary mapping trip_id to a set of items.
    """
    if not similar_trip_ids:
        return {}
    
    # Format the trip IDs for the SQL IN clause
    trip_ids_str = "', '".join(similar_trip_ids)
    
    query = f"""
        SELECT trip_id, packing_list
        FROM `{TRIP_DATASET_ID}.{PACKING_TABLE_ID}`
        WHERE trip_id IN ('{trip_ids_str}')
    """
    
    query_job = client.query(query)
    results = query_job.result()
    
    trip_items = {}
    for row in results:
        # Extract items from this packing list
        items = extract_items_from_packing_list(row.packing_list)
        
        # Add to our trip_items dictionary
        if row.trip_id in trip_items:
            # If we've seen this trip before, combine the items
            trip_items[row.trip_id].update(items)
        else:
            trip_items[row.trip_id] = items
    
    return trip_items

def generate_item_statistics(user_items: set, similar_trip_items: Dict[str, set]) -> List[Dict[str, Any]]:
    """
    Generate statistics on items packed by users with similar trips.
    
    Parameters:
    - user_items: Set of items the user already has in their packing list
    - similar_trip_items: Dictionary mapping trip_id to a set of items
    
    Returns:
    - List of items with usage statistics for visualization
    """
    if not similar_trip_items:
        return []
    
    # Count how many trips have each item
    item_trip_counts = Counter()
    all_items = set()
    
    for trip_id, items in similar_trip_items.items():
        all_items.update(items)
        for item in items:
            item_trip_counts[item] += 1
    
    total_trips = len(similar_trip_items)
    
    # Generate recommendations (items not in user's list)
    recommendations = []
    for item in all_items:
        if item not in user_items:
            count = item_trip_counts[item]
            percentage = (count / total_trips) * 100
            
            if count > 1:  # Only recommend if at least 2 trips have this item
                recommendations.append({
                    "item_name": item,
                    "percentage": round(percentage, 1),
                    "trip_count": count,
                    "total_trips": total_trips
                })
    
    # Sort by percentage (highest first)
    recommendations.sort(key=lambda x: x["percentage"], reverse=True)
    
    return recommendations[:30]  # Limit to top 30 recommendations

def categorize_recommendations(recommendations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Categorize recommendations for easier visualization.
    """
    # Define categories and their keywords
    categories = {
        "Clothing": ["shirt", "pants", "dress", "socks", "underwear", "jacket", "sweater", "sweatshirt", 
                    "coat", "jeans", "shorts", "hat", "cap", "gloves", "scarf", "t-shirt", "hoodie", 
                    "swimsuit", "swimwear", "bikini", "trunks"],
        "Toiletries": ["toothbrush", "toothpaste", "shampoo", "conditioner", "soap", "deodorant", 
                      "razor", "sunscreen", "lotion", "moisturizer", "makeup", "perfume", "cologne"],
        "Electronics": ["charger", "adapter", "camera", "phone", "laptop", "tablet", "headphones", 
                       "earbuds", "power bank", "battery", "kindle", "e-reader", "drone"],
        "Travel Essentials": ["passport", "id", "wallet", "money", "cash", "card", "tickets", 
                             "boarding", "reservation", "itinerary", "maps", "guide", "translator"],
        "Accessories": ["sunglasses", "watch", "jewelry", "belt", "umbrella", "backpack", "bag", 
                       "purse", "suitcase", "luggage", "daypack", "tote"],
        "Health & Safety": ["medicine", "pills", "first aid", "bandage", "prescription", "vitamin", 
                           "medication", "painkillers", "sanitizer", "mask", "insect repellent", "sunblock"],
        "Footwear": ["shoes", "sneakers", "sandals", "flip flops", "boots", "hiking", "slippers", "flats", "heels"]
    }
    
    # Initialize result with empty lists
    categorized = {category: [] for category in categories.keys()}
    categorized["Other"] = []  # For items that don't match any category
    
    # Categorize each recommendation
    for rec in recommendations:
        item_name = rec["item_name"].lower()
        categorized_flag = False
        
        for category, keywords in categories.items():
            if any(keyword in item_name for keyword in keywords):
                categorized[category].append(rec)
                categorized_flag = True
                break
        
        if not categorized_flag:
            categorized["Other"].append(rec)
    
    # Remove empty categories
    return {category: items for category, items in categorized.items() if items}

@router.get("/{list_id}", response_model=dict)
async def get_packing_recommendations_for_list(
    list_id: str, 
    similarity_threshold: float = 0.7,
    current_user: str = Depends(get_current_user)
):
    """
    Get packing recommendations based on similar trips for a specific packing list.
    
    Parameters:
    - list_id: The ID of the packing list
    - similarity_threshold: Minimum similarity score (0-1) to consider trips as similar
    
    Returns:
    - Recommendations statistics for items not in the user's packing list
    """
    try:
        # Get trip information for this packing list
        trip_info = get_packing_list_trip_info(list_id, current_user)
        
        # Get user's current packing list items
        user_items = extract_items_from_packing_list(trip_info.packing_list)
        
        # Find similar trips
        similar_trip_ids = find_similar_trips(trip_info, similarity_threshold)
        
        if not similar_trip_ids:
            return {
                "success": False,
                "message": "No similar trips found. Try adjusting the similarity threshold.",
                "recommendations": {}
            }
        
        # Get all packing lists for similar trips
        similar_trip_items = get_all_packing_lists_for_similar_trips(similar_trip_ids)
        
        if not similar_trip_items:
            return {
                "success": False,
                "message": "No packing lists found for similar trips.",
                "recommendations": {}
            }
        
        # Generate item statistics and recommendations
        recommendations = generate_item_statistics(user_items, similar_trip_items)
        
        if not recommendations:
            return {
                "success": True,
                "message": "No new recommendations found. Your packing list is comprehensive!",
                "similar_trips_count": len(similar_trip_ids),
                "recommendations": {}
            }
        
        # Categorize recommendations
        categorized_recommendations = categorize_recommendations(recommendations)
        
        return {
            "success": True,
            "message": f"Found {len(similar_trip_ids)} similar trips with recommendations for your packing list.",
            "similar_trips_count": len(similar_trip_ids),
            "recommendations": categorized_recommendations
        }
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error generating recommendations: {str(e)}")
        # Return a user-friendly error
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating recommendations: {str(e)}")