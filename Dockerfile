FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first 
COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Copy app code 
COPY app/ ./app/
COPY scripts/ ./scripts/

# Security: non-root user
RUN useradd -m appuser
USER appuser

# Port
EXPOSE 8000

# Run 
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]