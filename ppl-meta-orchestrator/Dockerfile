# Multi-stage build for PPL Meta Orchestrator Service
# Stage 1: Build stage with all dependencies
FROM python:3.11-alpine AS builder

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    python3-dev \
    libffi-dev \
    openssl-dev

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-warn-script-location -r requirements.txt

# Stage 2: Runtime stage with minimal footprint
FROM python:3.11-alpine AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Install only runtime dependencies
RUN apk add --no-cache \
    postgresql-libs \
    curl \
    && addgroup -g 1001 -S appuser \
    && adduser -S -D -H -u 1001 -h /home/appuser -s /sbin/nologin -G appuser appuser

# Set working directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY src/ ./

# Set working directory to src
WORKDIR /app

# Set permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add debugging to check file structure
RUN ls -la /app && echo "Python path check:" && python -c "import sys; print(sys.path)"

# Expose port
EXPOSE 8002

# Health check with improved settings
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
