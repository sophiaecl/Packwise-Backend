# PackWise Backend

## Overview
This is the backend for the PackWise web application, built using **FastAPI** and deployed on **Google Cloud Platform (GCP)**. It handles authentication, trip management, packing list generation, weather integration, and shopping recommendations.

## Tech Stack
- **FastAPI** - For the backend API
- **Firebase Firestore** - For database storage
- **Firebase Authentication** - For user authentication
- **Weatherstack API** - For weather data integration
- **Canopy API** - For shopping recommendations
- **Google Cloud Platform (GCP)** - For deployment

## Project Structure
```
backend/
│── app/
│   ├── api/
│   │   ├── auth.py          # User authentication
│   │   ├── trips.py         # Trip management
│   │   ├── packing.py       # Packing list management
│   │   ├── weather.py       # Weather API integration
│   │   ├── shopping.py      # Shopping recommendations
│   ├── core/
│   │   ├── config.py        # Configuration & environment variables
│   │   ├── database.py      # Firestore database connection
│   │   ├── security.py      # Authentication & JWT handling
│   ├── models/
│   ├── services/
│   ├── main.py              # FastAPI entry point
│── tests/
│── requirements.txt
│── .env
│── README.md
```

## Setup Instructions
### 1. Clone the Repository
```sh
git clone https://github.com/yourusername/packwise-backend.git
cd packwise-backend
```

### 2. Create a Virtual Environment
```sh
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### 3. Install Dependencies
```sh
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the `backend/` directory and add the following:
```
FIREBASE_API_KEY=your_firebase_api_key
WEATHERSTACK_API_KEY=your_weatherstack_api_key
CANOPY_API_KEY=your_canopy_api_key
```

### 5. Run the Server
```sh
uvicorn app.main:app --reload
```

### 6. Access API Documentation
Once the server is running, open the browser and go to:
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Deployment
This backend is deployed on **Google Cloud Run**. To deploy manually:
```sh
gcloud builds submit --tag gcr.io/your-project-id/packwise-backend
gcloud run deploy packwise-backend --image gcr.io/your-project-id/packwise-backend --platform managed
```

## Testing
Run unit tests using:
```sh
pytest tests/
```

## API Endpoints
| Method | Endpoint | Description |
|--------|---------|-------------|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Authenticate user |
| `POST` | `/trips/` | Create a new trip (fetches weather) |
| `GET` | `/trips/{trip_id}` | Retrieve trip details |
| `DELETE` | `/trips/{trip_id}` | Delete a trip |
| `GET` | `/weather/{destination}` | Fetch weather forecast |

## License
This project is licensed under the MIT License.

## Contributors
- **Sophia Cervantes Llamas** - [GitHub Profile](https://github.com/sophiaecl)

