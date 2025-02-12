from fastapi import FastAPI
from app.api import auth, trips, packing, weather, shopping

app = FastAPI(title="PackWise API", description="Backend for PackWise travel assistant.", version="1.0")

# Register routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(trips.router, prefix="/trips", tags=["Trips"])
app.include_router(packing.router, prefix="/packing", tags=["Packing"])
app.include_router(weather.router, prefix="/weather", tags=["Weather"])
app.include_router(shopping.router, prefix="/shopping", tags=["Shopping"])

@app.get("/")
def home():
    return {"message": "Welcome to PackWise API"}

if __name__ == "__main__":
    import gunicorn
    gunicorn.run(app, host="0.0.0.0", port=8000)

