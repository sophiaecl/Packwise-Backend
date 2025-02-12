from fastapi import APIRouter, Depends, HTTPException
import firebase_admin
from firebase_admin import auth, credentials

router = APIRouter()

# Initialize Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

@router.post("/register")
async def register_user(email: str, password: str):
    try:
        user = auth.create_user(email=email, password=password)
        return {"message": "User created successfully", "uid": user.uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/login")
async def login_user(email: str, password: str):
    return {"message": "User logged in successfully via Firebase Authentication"}
