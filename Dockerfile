# fxmoonlight - Moonlight Dashboard
# Docker image for running the dashboard on Linux/Docker

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements-docker.txt requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY templates/ templates/
COPY static/ static/
COPY config.example.json .

# Create data directory for persistent storage
RUN mkdir -p /data

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV CONFIG_FILE=/data/config.json
ENV DATA_FILE=/data/workstations.json

# Expose the default port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

# Run with waitress (production WSGI server)
CMD ["python", "-m", "waitress", "--host=0.0.0.0", "--port=5000", "app:app"]
