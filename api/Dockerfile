# =============================================================================
# InfraIQ Demo API
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI for container management
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://get.docker.com | sh \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY api/ ./api/
COPY frontend/ ./frontend/

WORKDIR /app/api

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
