FROM python:3.11-slim

WORKDIR /app

# Enable unbuffered logging
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

# Remove any private packages like emergentintegrations if they exist in requirements
RUN sed -i '/emergentintegrations/d' requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Explicitly install uvicorn in case it's missing from requirements
RUN pip install --no-cache-dir uvicorn fastapi

COPY . .

# Expose the API port
EXPOSE 8000

# Start Uvicorn
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
