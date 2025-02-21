from google.cloud import bigquery
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize API and BigQuery clients
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
USER_DATASET_ID = os.getenv("USER_DATASET_ID")
TRIP_DATASET_ID = os.getenv("TRIP_DATASET_ID")
USER_INFO_TABLE_ID = os.getenv("USER_INFO_TABLE_ID")
TRIP_TABLE_ID = os.getenv("TRIP_TABLE_ID")
TRIP_WEATHER_TABLE_ID = os.getenv("TRIP_WEATHER_TABLE_ID")

client = bigquery.Client()
gemini_client = genai.Client(api_key=GEMINI_API_KEY)


# Function to fetch user, trip, and weather info
def fetch_trip_details(trip_id):
    query = f'''
        SELECT * FROM `{TRIP_DATASET_ID}.{TRIP_TABLE_ID}` WHERE trip_id = '{trip_id}'
    '''
    trip_info = client.query(query).to_dataframe().to_dict(orient='records')[0]

    user_query = f'''
        SELECT * FROM `{USER_DATASET_ID}.{USER_INFO_TABLE_ID}` WHERE user_id = '{trip_info['user_id']}'
    '''
    user_info = client.query(user_query).to_dataframe().to_dict(orient='records')[0]

    weather_query = f'''
        SELECT * FROM `{TRIP_DATASET_ID}.{TRIP_WEATHER_TABLE_ID}` WHERE trip_id = '{trip_id}'
    '''
    weather_info = client.query(weather_query).to_dataframe().to_dict(orient='records')[0]

    return user_info, trip_info, weather_info

# Function to generate packing list using Gemini
def generate_packing_list(trip_id):
    user_info, trip_info, weather_info = fetch_trip_details(trip_id)

    prompt = f'''
    I am a {user_info['age']} year old {user_info.get('gender', 'prefer not to say')} going to {trip_info['city']}, {trip_info['country']} from {trip_info['start_date']} to {trip_info['end_date']} for a {trip_info.get('trip_purpose', 'general')} trip.
    The weather forecast shows temperatures between {weather_info['min_temp']}°C and {weather_info['max_temp']}°C with conditions described as {weather_info['description']}.
    I am bringing {trip_info.get('luggage_type', 'standard luggage')}.
    
    Please provide me a detailed packing list in JSON format that is tailored to my specific needs.
    Use this JSON schema:
    {{
      "categories": [
        {{
          "category_name": string,
          "items": [
            {{
              "name": string,
              "quantity": int,
              "essential": boolean,
              "notes": string
            }}
          ]
        }}
      ],
      "total_items": int,
      "recommended_activities": [string],
      "packing_tips": [string]
    }}
    '''

    response = gemini_client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt,
    )

    return response.text
