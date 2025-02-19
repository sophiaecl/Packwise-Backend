from fastapi import APIRouter, HTTPException, status, Form
from starlette.requests import Request
from starlette.responses import RedirectResponse
from passlib.context import CryptContext
from google.cloud import bigquery
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

USER_DATASET_ID = os.getenv("USER_DATASET_ID")
USERNAME_TABLE_ID = os.getenv("USERNAME_TABLE_ID")

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

client = bigquery.Client()
dataset_id = USER_DATASET_ID
table_id = USERNAME_TABLE_ID
table_ref = client.dataset(dataset_id).table(table_id)

# User Registration Endpoint
@router.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    query = f"SELECT username FROM `{dataset_id}.{table_id}` WHERE username = @username"
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

    rows_to_insert = [
        {u"id": user_id, u"username": username, u"password": hashed_password}
    ]
    errors = client.insert_rows_json(table_ref, rows_to_insert)
    if errors:
        raise HTTPException(status_code=500, detail=str(errors))

    return {"message": "User registered successfully"}

# User Login Endpoint
@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    query = f"SELECT id, username, password FROM `{dataset_id}.{table_id}` WHERE username = @username"
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