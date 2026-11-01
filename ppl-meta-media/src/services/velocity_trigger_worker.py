"""
Backward-compatible shim: velocity trigger renamed to motion.

Prefer importing from src.services.motion_trigger_worker.
"""

from src.services.motion_trigger_worker import (  # noqa: F401
    MotionTriggerWorker,
    VelocityTriggerWorker,
    get_motion_trigger_worker,
    get_velocity_trigger_worker,
)
