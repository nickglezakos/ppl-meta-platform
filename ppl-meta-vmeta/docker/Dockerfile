FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/base.txt

# Copy application code
COPY src/ src/

# Bake DeepFace weights so first face never downloads from GitHub at runtime.
COPY docker/download_deepface_weights.sh /tmp/download_deepface_weights.sh
RUN chmod +x /tmp/download_deepface_weights.sh \
 && /tmp/download_deepface_weights.sh \
 && rm -f /tmp/download_deepface_weights.sh

# /app/src so `shared.service_discovery` resolves (vendored under src/shared/)
ENV PYTHONPATH=/app/src \
    DEEPFACE_HOME=/root/.deepface

# Expose port
EXPOSE 8008

# Run the application
CMD ["python", "src/main.py"]
