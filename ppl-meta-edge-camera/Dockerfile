# Edge Camera Dockerfile for Raspberry Pi 5 (ARM64)
FROM python:3.11-slim-bullseye

# Install system dependencies for OpenCV, camera, and GStreamer
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libopencv-dev \
    python3-opencv \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    v4l-utils \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create logs directory
RUN mkdir -p /app/logs

# Expose port
EXPOSE 9001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:9001/health || exit 1

# Set PYTHONPATH and change to src directory to avoid platform module conflict
ENV PYTHONPATH=/app/src
WORKDIR /app/src

# Run application
CMD ["python", "main.py"]
