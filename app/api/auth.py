from fastapi import APIRouter, HTTPException, status, Form
from starlette.requests import Request
from starlette.responses import RedirectResponse
from passlib.context import CryptContext
from google.cloud import bigquery
from typing import Optional
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

USER_DATASET_ID = os.getenv("USER_DATASET_ID")
USERNAME_TABLE_ID = os.getenv("USERNAME_TABLE_ID")
USER_INFO_TABLE_ID = os.getenv("USER_INFO_TABLE_ID")

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

client = bigquery.Client()
dataset_id = USER_DATASET_ID
user_table_id = USERNAME_TABLE_ID
user_table_ref = client.dataset(dataset_id).table(user_table_id)

user_info_id = USER_INFO_TABLE_ID
user_info_ref = client.dataset(dataset_id).table(user_info_id)

# User Registration Endpoint
@router.post("/register")
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

# User Login Endpoint
@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    query = f"SELECT id, username, password FROM `{dataset_id}.{user_table_id}` WHERE username = @username"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("username", "STRING", username)
        ]
    )
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    if results.total_rows == 0:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    user_data = [row for row in results][0]
    if not pwd_context.verify(password, user_data["password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Set session
    request.session["user"] = user_data["id"]

    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

# Logout Endpoint
@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}