from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, trips, dashboard, packing
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PackWise API", description="Backend for PackWise travel assistant.", version="1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Add your React frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Register routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(trips.router, prefix="/trips", tags=["Trips"])
app.include_router(packing.router, prefix="/packing", tags=["Packing"])

@app.get("/")
def home():
    return {"message": "Welcome to PackWise API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

