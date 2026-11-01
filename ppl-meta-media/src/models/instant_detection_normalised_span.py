"""
Derived Instant Detection normalisation spans.

Separate from immutable `instant_detection_logs`. Re-running a span upserts
the same (camera, span_start, merge_threshold) row without touching raw logs.
"""

from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from .base import BaseModel


class InstantDetectionNormalisedSpan(BaseModel):
    """Cross-flush people merge for one fixed calendar span."""

    __tablename__ = "instant_detection_normalised_spans"
    __table_args__ = (
        UniqueConstraint(
            "camera_device_id",
            "span_start",
            "merge_threshold",
            name="uq_instant_norm_span_camera_start_threshold",
        ),
    )

    camera_device_id = Column(String(255), nullable=False, index=True)
    span_start = Column(DateTime(timezone=True), nullable=False, index=True)
    span_end = Column(DateTime(timezone=True), nullable=False)
    span_seconds = Column(Integer, nullable=False, default=300)
    merge_threshold = Column(Float, nullable=False, default=0.70)
    people_count = Column(Integer, nullable=False, default=0)
    source_log_ids = Column(JSONB().with_variant(JSON, "sqlite"), nullable=False, default=list)
    payload_json = Column(JSONB().with_variant(JSON, "sqlite"), nullable=False, default=dict)
    computed_at = Column(DateTime(timezone=True), nullable=False)
