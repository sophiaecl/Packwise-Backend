# Step 1: Use the official Python image as a base image
FROM python:3.11-slim

# Step 2: Set environment variables (optional)
# Set the working directory inside the container
WORKDIR /app

# Step 3: Copy requirements.txt and install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Step 4: Copy your application code into the container
COPY . /app
COPY .env /app/.env

# Step 5: Expose the port that the FastAPI app will run on
EXPOSE 8080

# Step 6: Specify the command to run the FastAPI app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]