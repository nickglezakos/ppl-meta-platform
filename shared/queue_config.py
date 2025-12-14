# Queue Configuration for PPL Meta Platform
# Shared configuration for Redis and Celery workers

import logging
import os

import redis
from celery import Celery

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis connection configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Redis client
redis_client = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
)

# Celery app configuration
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
BACKEND_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

celery_app = Celery("ppl_workflows", broker=BROKER_URL, backend=BACKEND_URL)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "trigger_ppl_thread": {"queue": "ppl_thread_queue"},
        "monitor_face_detection": {"queue": "monitoring_queue"},
        "instant_detection.process_frames": {"queue": "instant_detection_queue"},
    },
    # Task retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,  # 10 minutes
)


def test_redis_connection():
    """Test Redis connection"""
    try:
        redis_client.ping()
        logger.info("✅ Redis connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False


if __name__ == "__main__":
    # Test configuration
    print("🔧 Testing queue configuration...")
    if test_redis_connection():
        print("✅ Queue configuration ready")
    else:
        print("❌ Queue configuration failed")
