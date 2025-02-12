import os
import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Initialize Firebase Admin
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

auth_scheme = HTTPBearer()

def verify_token(auth_credentials: HTTPAuthorizationCredentials = Security(auth_scheme)):
    """Verifies the Firebase authentication token."""
    token = auth_credentials.credentials
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
