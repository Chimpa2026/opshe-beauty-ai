# ══════════════════════════════════════════════════
# OPSHE Beauty AI — Dockerfile
# ══════════════════════════════════════════════════

FROM python:3.12-slim

# Install system dependencies for OpenCV / MediaPipe
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1-mesa-glx \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create necessary directories
RUN mkdir -p logs uploads models

# Expose port
EXPOSE 8000

# Start server
CMD ["python", "run.py"]
