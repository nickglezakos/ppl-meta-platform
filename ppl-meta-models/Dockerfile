FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psycopg2-binary

COPY src/ ./src/

RUN mkdir -p /app/artifact_store \
    && useradd -m -u 1000 models \
    && chown -R models:models /app

USER models

EXPOSE 8013

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8013/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8013", "--app-dir", "/app/src"]
