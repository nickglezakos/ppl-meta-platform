# Multi-stage build for PPL Meta Node Service
# Stage 1: Build stage with all dependencies
FROM python:3.11-alpine AS builder

# Set environment variables for build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies for compilation
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    python3-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust

# Set work directory
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

# Install only runtime dependencies + Tailscale CLI (talks to host socket)
ARG TAILSCALE_VERSION=1.80.3
RUN apk add --no-cache \
    postgresql-libs \
    curl \
    ca-certificates \
    && addgroup -g 1001 -S appuser \
    && adduser -S -D -H -u 1001 -h /home/appuser -s /sbin/nologin -G appuser appuser \
    && curl -fsSL "https://pkgs.tailscale.com/stable/tailscale_${TAILSCALE_VERSION}_amd64.tgz" \
      | tar -xz -C /tmp \
    && mv "/tmp/tailscale_${TAILSCALE_VERSION}_amd64/tailscale" /usr/local/bin/tailscale \
    && chmod 755 /usr/local/bin/tailscale \
    && rm -rf "/tmp/tailscale_${TAILSCALE_VERSION}_amd64"

# Set work directory
WORKDIR /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY src/ ./src/

# Create logs directory and set permissions
RUN mkdir -p /app/src/logs /var/lib/tailscale && \
    chown -R appuser:appuser /app /var/lib/tailscale

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8001

# Health check with improved settings
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:8001/api/v1/health/ || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
