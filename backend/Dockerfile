# NetScout Celery worker (optional). Build from project root: docker build -f backend/Dockerfile .
FROM python:3.11-slim

WORKDIR /app

# Install system deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project (context is project root)
COPY backend/requirements.txt backend/
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/ backend/
COPY src/ src/
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt || true

ENV PYTHONPATH=/app
WORKDIR /app/backend
CMD ["celery", "-A", "app.celery_app", "worker", "-l", "info"]
