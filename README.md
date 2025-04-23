# PackWise Backend API

PackWise Backend API is a FastAPI service that powers the intelligent packing list generator for travelers. The service integrates with weather APIs, uses AI for packing suggestions, and provides comprehensive trip and packing management.

## Features

- **User Authentication**: Secure JWT-based authentication
- **Trip Management**: Create, retrieve, update, and delete trip data
- **Weather Prediction**: Intelligent weather forecasting using historical data
- **AI-Powered Packing Lists**: Generate custom packing lists using Google's Gemini API
- **Packing Recommendations**: Collaborative filtering for item recommendations based on similar trips
- **Progress Tracking**: Track packing completion for individual trips

## Technology Stack

- **FastAPI**: High-performance Python web framework
- **Google BigQuery**: Data storage and querying
- **Google Gemini API**: AI text generation for packing lists
- **WeatherStack API**: Historical weather data
- **JWT**: Authentication and authorization
- **Pydantic**: Data validation

## Project Structure

```
app/
├── api/                   # API routes
│   ├── __init__.py       
│   ├── auth.py            # Authentication endpoints
│   ├── dashboard.py       # Dashboard endpoints
│   ├── packing.py         # Packing list endpoints
│   ├── packing_recommender.py # Recommendation engine
│   └── trips.py           # Trip management endpoints
├── core/                  # Core functionality
│   ├── __init__.py
│   ├── config.py          # Application configuration
│   └── database.py        # Database connection
├── services/              # External services integration
│   ├── __init__.py
│   ├── packing_list_generator.py # Gemini integration
│   └── weather_predictor.py      # Weather API integration
└── main.py                # Application entry point
```

## Setup and Installation

### Prerequisites

- Python 3.9+
- Google Cloud account with BigQuery enabled
- WeatherStack API key
- Google Gemini API key

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/packwise-backend.git
   cd packwise-backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables by creating a `.env` file:
   ```
   SECRET_KEY=your_secret_key_for_jwt
   WEATHERSTACK_API_KEY=your_weatherstack_api_key
   GEMINI_API_KEY=your_gemini_api_key
   USER_DATASET_ID=your_bigquery_user_dataset
   TRIP_DATASET_ID=your_bigquery_trip_dataset
   USERNAME_TABLE_ID=your_bigquery_username_table
   USER_INFO_TABLE_ID=your_bigquery_user_info_table
   TRIP_TABLE_ID=your_bigquery_trip_table
   TRIP_WEATHER_TABLE_ID=your_bigquery_trip_weather_table
   HISTORICAL_WEATHER_TABLE=your_bigquery_historical_weather_table
   PACKING_TABLE_ID=your_bigquery_pakcinglist_table
   ```
   The database schema is featured further down.

5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Documentation

When the application is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Main Endpoints

#### Authentication
- `POST /auth/register`: Create a new user account
- `POST /auth/token`: Get JWT access token
- `POST /auth/logout`: Logout user
- `GET /auth/profile`: Get user profile
- `PUT /auth/profile`: Update user profile

#### Dashboard
- `GET /dashboard`: Get dashboard data with user trips

#### Trips
- `POST /trips/`: Create a new trip
- `GET /trips/{trip_id}`: Get trip details
- `PUT /trips/update/{trip_id}`: Update a trip
- `DELETE /trips/delete/{trip_id}`: Delete a trip
- `GET /trips/weather/{trip_id}`: Get weather forecast
- `GET /trips/weather/historical/{trip_id}`: Get historical weather data

#### Packing Lists
- `POST /packing/generate/{trip_id}`: Generate a packing list
- `GET /packing/{packing_list_id}`: Get a specific packing list
- `GET /packing/lists/{trip_id}`: Get all packing lists for a trip
- `PUT /packing/{packing_list_id}`: Update a packing list
- `DELETE /packing/{packing_list_id}`: Delete a packing list
- `GET /packing/progress/{trip_id}`: Get packing progress for a trip
- `GET /packing/progress/all`: Get overall packing progress

#### Recommendations
- `GET /packing_recommendations/{packing_list_id}`: Get recommendations based on similar trips

## Database Schema

### Users Tables
- **users**: User authentication data
  - id (STRING): User ID
  - username (STRING): Username
  - password (STRING): Hashed password

- **users_info**: User profile information
  - user_id (STRING): User ID
  - name (STRING): Full name
  - age (INTEGER): User age
  - gender (STRING): User gender

### Trips Tables
- **user_trips**: Trip information
  - trip_id (STRING): Trip ID
  - user_id (STRING): User ID
  - city (STRING): Destination city
  - country (STRING): Destination country
  - start_date (STRING): Trip start date
  - end_date (STRING): Trip end date
  - luggage_type (STRING): Type of luggage
  - trip_purpose (STRING): Purpose of trip

- **trip_weather**: Weather predictions
  - trip_id (STRING): Trip ID
  - min_temp (FLOAT): Minimum temperature
  - max_temp (FLOAT): Maximum temperature
  - uv (FLOAT): UV index
  - description (STRING): Weather description
  - confidence (FLOAT): Prediction confidence

- **trip_historical_weather**: Historical weather data
  - trip_id (STRING): Trip ID
  - historical_stats (STRING): JSON data of historical records

- **packing_lists**: Packing lists
  - list_id (STRING): Packing list ID
  - trip_id (STRING): Trip ID
  - packing_list (STRING): JSON structured packing list

## Weather Prediction System

The system uses historical weather data to predict weather conditions for upcoming trips:

1. Historical data is collected for the specific dates from previous years
2. Data is analyzed for patterns and trends
3. Predictions are made with confidence scores
4. Results are stored for quick retrieval

## Packing List Generation

The AI-powered packing list generator:

1. Combines user profile information (age, gender)
2. Analyzes trip details (destination, purpose, dates)
3. Factors in weather predictions
4. Considers luggage type constraints
5. Uses Gemini to generate contextually appropriate packing suggestions

## Recommendation Engine

The collaborative filtering recommendation system:

1. Identifies similar trips based on destination, weather, and purpose
2. Analyzes items packed by travelers with similar profiles
3. Calculates popularity percentages for items
4. Recommends items not in the current packing list
5. Categorizes recommendations for better usability

## License

This project is licensed under the MIT License - see the LICENSE file for details.
