# Multi-stage build for PPL Meta Media Service
# Stage 1: Build stage with all dependencies
FROM python:3.11-slim-bookworm AS builder

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    gcc \
    g++ \
    make \
    pkg-config \
    libpq-dev \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libgl1-mesa-dri \
    libglx-mesa0 \
    libglx0 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    libx11-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies (dlib-bin provides pre-built wheels, no source compilation needed)
COPY requirements.txt .
RUN pip install --user --no-warn-script-location -r requirements.txt

# Stage 2: Runtime stage with minimal footprint
FROM python:3.11-slim-bookworm AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/app/.local/bin:$PATH"

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    libgl1-mesa-dri \
    libglx-mesa0 \
    libglx0 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 1001 app \
    && useradd -m -u 1001 -g app -s /usr/sbin/nologin app

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/app/.local

# Copy application code
COPY src/ ./src/

# Set permissions
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check with improved settings
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
