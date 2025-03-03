from fastapi import APIRouter, HTTPException, status, Form, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from google.cloud import bigquery
from typing import Optional
import os
import uuid
from dotenv import load_dotenv
from datetime import datetime, timedelta
from jose import JWTError, jwt

load_dotenv()

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY") 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

USER_DATASET_ID = os.getenv("USER_DATASET_ID")
USERNAME_TABLE_ID = os.getenv("USERNAME_TABLE_ID")
USER_INFO_TABLE_ID = os.getenv("USER_INFO_TABLE_ID")

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Use OAuth2PasswordBearer for token handling
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/token",  # Full path including prefix
    scheme_name="JWT",
)

client = bigquery.Client()
dataset_id = USER_DATASET_ID
user_table_id = USERNAME_TABLE_ID
user_table_ref = client.dataset(dataset_id).table(user_table_id)

user_info_id = USER_INFO_TABLE_ID
user_info_ref = client.dataset(dataset_id).table(user_info_id)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify user exists in database
    query = f"SELECT id FROM `{dataset_id}.{user_table_id}` WHERE id = @user_id"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
        ]
    )
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    if results.total_rows == 0:
        raise credentials_exception
    
    return user_id

# User Registration Endpoint
@router.post("/register",
    summary="Register new user",
    description="Create a new user account. After registration, use the /token endpoint to get an access token.")
async def register(username: str = Form(...), password: str = Form(...), name: str = Form(...), age: int = Form(...), gender: Optional[str] = Form(None)):
    query = f"SELECT username FROM `{dataset_id}.{user_table_id}` WHERE username = @username"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("username", "STRING", username)
        ]
    )
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    if results.total_rows > 0:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = pwd_context.hash(password)
    user_id = str(uuid.uuid4())

    user_rows = [
        {u"id": user_id, u"username": username, u"password": hashed_password}
    ]

    user_errors = client.insert_rows_json(user_table_ref, user_rows)

    if user_errors:
        raise HTTPException(status_code=500, detail=str(user_errors))

    info_rows = [
        {u"user_id": user_id, u"name": name, u"age": age, u"gender": gender}
    ]

    info_errors = client.insert_rows_json(user_info_ref, info_rows)
    
    if info_errors:
        raise HTTPException(status_code=500, detail=str(info_errors))

    return {"message": "User registered successfully"}

# Token endpoint for login
@router.post("/token", 
    summary="Get access token",
    description="""
    Use this endpoint to get a JWT access token for authentication.
    
    Steps to use:
    1. Enter your username and password
    2. Click Execute
    3. Copy the access_token from the response
    4. Click the 'Authorize' button at the top of the page
    5. In the popup, paste ONLY the token (without 'Bearer')
    6. Click Authorize
    """)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    query = f"SELECT id, username, password FROM `{dataset_id}.{user_table_id}` WHERE username = @username"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("username", "STRING", form_data.username)
        ]
    )
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    if results.total_rows == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_data = [row for row in results][0]
    if not pwd_context.verify(form_data.password, user_data["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data["id"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Logout endpoint (client-side should remove the token)
@router.post("/logout",
    summary="Logout user",
    description="This endpoint is for client-side use. The client should remove the stored token.")
async def logout():
    return {"message": "Successfully logged out"}