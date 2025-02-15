from fastapi import FastAPI
from app.api import auth, trips, dashboard
#packing, weather, shopping, dashboard
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PackWise API", description="Backend for PackWise travel assistant.", version="1.0")

# Adds session middleware with a secure secret key
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))

# Register routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(trips.router, prefix="/trips", tags=["Trips"])
# app.include_router(packing.router, prefix="/packing", tags=["Packing"])
# app.include_router(weather.router, prefix="/weather", tags=["Weather"])
# app.include_router(shopping.router, prefix="/shopping", tags=["Shopping"])

@app.get("/")
def home():
    return {"message": "Welcome to PackWise API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

