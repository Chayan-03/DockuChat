# Backend Dockerfile
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose backend port
EXPOSE 8000

# Run FastAPI (or uvicorn)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
