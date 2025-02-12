from fastapi import APIRouter, Depends, HTTPException, Header
from firebase_admin import auth

router = APIRouter()

def verify_token(authorization: str = Header(None)):
    """Verify Firebase token from the Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    try:
        token = authorization.split(" ")[1]  # Extract token from "Bearer <token>"
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/me")
def get_user_info(user=Depends(verify_token)):
    return {"uid": user["uid"], "email": user.get("email")}

