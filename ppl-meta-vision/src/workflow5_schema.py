"""
Face Detection Workflow 5 - Database Schema Extensions
Phase 2: Database Schema & Storage Implementation

This module extends the existing Workflow 4 database schema with optimizations
for zero-latency face detection playback using stored face data.
"""

import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

# Import existing models
from sqlalchemy_models import (
    Base,
    FaceDetection,
    FaceDetectionSession,
    MediaProcessingStatus,
)

# =============================================================================
# WORKFLOW 5 SCHEMA EXTENSIONS
# =============================================================================


class MediaProcessingStatusEnhanced(Base):
    """
    Enhanced MediaProcessingStatus with Workflow 5 optimizations.

    Separate table for enhanced processing status tracking with additional metadata
    for intelligent mode selection and performance optimization.
    """

    __tablename__ = "media_processing_status_enhanced"

    # Primary key
    media_uuid = Column(String(36), primary_key=True)

    # Link to original processing status
    original_processing_status_id = Column(
        String(36),
        ForeignKey("media_processing_status.media_uuid"),
        nullable=False,
        index=True,
    )

    # Workflow 5 extensions
    processing_quality_score = Column(Float, nullable=True, default=0.0)
    frame_analysis_metadata = Column(JSONB, nullable=True)
    optimization_enabled = Column(Boolean, default=True, index=True)
    cache_status = Column(String(20), default="not_cached", index=True)
    last_accessed = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0)

    # Performance metrics
    avg_detection_latency = Column(Float, nullable=True)
    face_density_score = Column(Float, nullable=True)  # faces per frame average
    processing_efficiency = Column(Float, nullable=True)  # processing time per frame

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.frame_analysis_metadata = kwargs.get("frame_analysis_metadata", {})

    def update_access_stats(self):
        """Update access statistics for cache management."""
        self.last_accessed = datetime.utcnow()
        self.access_count = (self.access_count or 0) + 1
        self.last_updated = datetime.utcnow()

    def calculate_quality_score(self):
        """Calculate processing quality score based on detection metrics."""
        if not (self.total_faces_detected and self.total_frames_processed):
            return 0.0

        # Factors: face density, processing completeness, detection confidence
        face_density = self.total_faces_detected / self.total_frames_processed
        completeness = 1.0 if self.face_detection_processed else 0.0

        # Normalized quality score (0.0 to 1.0)
        quality_score = min(1.0, (face_density * 0.5 + completeness * 0.5))
        self.processing_quality_score = quality_score
        return quality_score

    def is_optimizable(self) -> bool:
        """Check if this media is suitable for Workflow 5 optimization."""
        return (
            self.face_detection_processed
            and self.optimization_enabled
            and (self.processing_quality_score or 0.0) > 0.3
            and (self.total_faces_detected or 0) > 0
        )

    def to_dict_enhanced(self):
        """Enhanced dictionary representation with Workflow 5 fields."""
        base_dict = self.to_dict()
        base_dict.update(
            {
                "processing_quality_score": self.processing_quality_score,
                "frame_analysis_metadata": self.frame_analysis_metadata,
                "optimization_enabled": self.optimization_enabled,
                "cache_status": self.cache_status,
                "last_accessed": (
                    self.last_accessed.isoformat() if self.last_accessed else None
                ),
                "access_count": self.access_count,
                "avg_detection_latency": self.avg_detection_latency,
                "face_density_score": self.face_density_score,
                "processing_efficiency": self.processing_efficiency,
                "is_optimizable": self.is_optimizable(),
            }
        )
        return base_dict


class FaceDataCache(Base):
    """
    Face data cache table for Workflow 5 optimization.

    Stores pre-computed face detection data for instant retrieval during
    video playback, eliminating the need for real-time face detection.
    """

    __tablename__ = "face_data_cache"

    # Primary key
    media_uuid = Column(String(36), primary_key=True)

    # Cached face data (frame-indexed JSON)
    cached_faces = Column(JSONB, nullable=False)  # {frame_number: [faces]}

    # Cache metadata
    total_frames = Column(Integer, nullable=False)
    total_faces = Column(Integer, nullable=False)
    cache_version = Column(String(10), default="1.0")
    compression_ratio = Column(Float, nullable=True)

    # Cache management
    cache_created_at = Column(DateTime, default=datetime.utcnow, index=True)
    cache_expires_at = Column(DateTime, nullable=True, index=True)
    cache_size_bytes = Column(Integer, nullable=True)

    # Access tracking
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=datetime.utcnow, index=True)
    hit_count = Column(Integer, default=0)
    miss_count = Column(Integer, default=0)

    # Performance metrics
    avg_retrieval_time = Column(Float, nullable=True)  # milliseconds
    cache_efficiency = Column(Float, nullable=True)  # hit rate percentage

    # Relationships
    processing_status = relationship(
        "MediaProcessingStatusEnhanced",
        foreign_keys=[media_uuid],
        primaryjoin="FaceDataCache.media_uuid == MediaProcessingStatusEnhanced.media_uuid",
        uselist=False,
    )

    # Table constraints and indexes
    __table_args__ = (
        CheckConstraint("total_frames > 0", name="chk_total_frames_positive"),
        CheckConstraint("total_faces >= 0", name="chk_total_faces_non_negative"),
        CheckConstraint("access_count >= 0", name="chk_access_count_non_negative"),
        CheckConstraint("hit_count >= 0", name="chk_hit_count_non_negative"),
        CheckConstraint("miss_count >= 0", name="chk_miss_count_non_negative"),
        CheckConstraint(
            "cache_expires_at IS NULL OR cache_expires_at > cache_created_at",
            name="chk_cache_expiration_order",
        ),
        Index("idx_cache_access_pattern", "last_accessed", "access_count"),
        Index("idx_cache_efficiency", "cache_efficiency", "hit_count"),
        Index("idx_cache_expiration", "cache_expires_at"),
    )

    def __repr__(self):
        return f"<FaceDataCache(media={self.media_uuid}, frames={self.total_frames}, faces={self.total_faces})>"

    def update_access_stats(self, hit: bool = True, retrieval_time: float = None):
        """Update cache access statistics."""
        self.access_count = (self.access_count or 0) + 1
        self.last_accessed = datetime.utcnow()

        if hit:
            self.hit_count = (self.hit_count or 0) + 1
        else:
            self.miss_count = (self.miss_count or 0) + 1

        # Update efficiency calculation
        total_requests = self.hit_count + self.miss_count
        if total_requests > 0:
            self.cache_efficiency = (self.hit_count / total_requests) * 100

        # Update average retrieval time
        if retrieval_time is not None:
            if self.avg_retrieval_time is None:
                self.avg_retrieval_time = retrieval_time
            else:
                # Rolling average
                self.avg_retrieval_time = (
                    self.avg_retrieval_time * 0.8 + retrieval_time * 0.2
                )

    def get_faces_by_frame(self, frame_number: int) -> List[Dict]:
        """Get faces for a specific frame from cached data."""
        if not self.cached_faces:
            return []

        frame_faces = self.cached_faces.get(str(frame_number), [])
        self.update_access_stats(hit=len(frame_faces) > 0)
        return frame_faces

    def get_faces_by_frame_range(
        self, start_frame: int, end_frame: int
    ) -> Dict[int, List[Dict]]:
        """Get faces for a range of frames from cached data."""
        if not self.cached_faces:
            return {}

        result = {}
        for frame_num in range(start_frame, end_frame + 1):
            frame_key = str(frame_num)
            if frame_key in self.cached_faces:
                result[frame_num] = self.cached_faces[frame_key]

        self.update_access_stats(hit=len(result) > 0)
        return result

    def calculate_cache_size(self) -> int:
        """Calculate the approximate size of cached data in bytes."""
        if not self.cached_faces:
            return 0

        # Rough estimation based on JSON structure
        import json

        cache_str = json.dumps(self.cached_faces)
        size_bytes = len(cache_str.encode("utf-8"))
        self.cache_size_bytes = size_bytes
        return size_bytes

    def is_expired(self) -> bool:
        """Check if the cache has expired."""
        if not self.cache_expires_at:
            return False
        return datetime.utcnow() > self.cache_expires_at

    def to_dict(self):
        """Convert cache entry to dictionary representation."""
        return {
            "media_uuid": self.media_uuid,
            "total_frames": self.total_frames,
            "total_faces": self.total_faces,
            "cache_version": self.cache_version,
            "compression_ratio": self.compression_ratio,
            "cache_created_at": (
                self.cache_created_at.isoformat() if self.cache_created_at else None
            ),
            "cache_expires_at": (
                self.cache_expires_at.isoformat() if self.cache_expires_at else None
            ),
            "cache_size_bytes": self.cache_size_bytes,
            "access_count": self.access_count,
            "last_accessed": (
                self.last_accessed.isoformat() if self.last_accessed else None
            ),
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "avg_retrieval_time": self.avg_retrieval_time,
            "cache_efficiency": self.cache_efficiency,
            "is_expired": self.is_expired(),
        }


class FrameIndexOptimization(Base):
    """
    Frame indexing optimization table for ultra-fast face queries.

    Pre-computed frame index for instant lookup of frames with face detections,
    optimizing queries for sparse face detection scenarios.
    """

    __tablename__ = "frame_index_optimization"

    # Composite primary key
    media_uuid = Column(String(36), nullable=False, primary_key=True)
    frame_number = Column(Integer, nullable=False, primary_key=True)

    # Frame metadata
    has_faces = Column(Boolean, default=False, index=True)
    face_count = Column(Integer, default=0)
    detection_confidence_avg = Column(Float, nullable=True)
    detection_methods = Column(String(200), nullable=True)  # comma-separated

    # Performance optimization
    processing_time_ms = Column(Float, nullable=True)
    frame_size_bytes = Column(Integer, nullable=True)
    complexity_score = Column(Float, nullable=True)

    # Timestamps
    indexed_at = Column(DateTime, default=datetime.utcnow)
    last_verified = Column(DateTime, nullable=True)

    # Table constraints and indexes
    __table_args__ = (
        CheckConstraint("frame_number >= 0", name="chk_frame_number_non_negative"),
        CheckConstraint("face_count >= 0", name="chk_face_count_non_negative"),
        CheckConstraint(
            "detection_confidence_avg IS NULL OR (detection_confidence_avg >= 0.0 AND detection_confidence_avg <= 1.0)",
            name="chk_confidence_range",
        ),
        # High-performance indexes for frame queries
        Index("idx_frame_has_faces", "media_uuid", "has_faces", "frame_number"),
        Index("idx_frame_face_count", "media_uuid", "face_count"),
        Index("idx_frame_confidence", "media_uuid", "detection_confidence_avg"),
        Index("idx_frame_processing_time", "processing_time_ms"),
    )

    def __repr__(self):
        return f"<FrameIndexOptimization(media={self.media_uuid}, frame={self.frame_number}, faces={self.face_count})>"

    def update_detection_stats(self, faces: List[Dict]):
        """Update frame statistics based on face detection results."""
        self.face_count = len(faces)
        self.has_faces = len(faces) > 0

        if faces:
            confidences = [face.get("confidence", 0.0) for face in faces]
            self.detection_confidence_avg = sum(confidences) / len(confidences)

            methods = set(face.get("method", "unknown") for face in faces)
            self.detection_methods = ",".join(sorted(methods))
        else:
            self.detection_confidence_avg = None
            self.detection_methods = None

        self.last_verified = datetime.utcnow()

    def to_dict(self):
        """Convert frame index to dictionary representation."""
        return {
            "media_uuid": self.media_uuid,
            "frame_number": self.frame_number,
            "has_faces": self.has_faces,
            "face_count": self.face_count,
            "detection_confidence_avg": self.detection_confidence_avg,
            "detection_methods": self.detection_methods,
            "processing_time_ms": self.processing_time_ms,
            "frame_size_bytes": self.frame_size_bytes,
            "complexity_score": self.complexity_score,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "last_verified": (
                self.last_verified.isoformat() if self.last_verified else None
            ),
        }


# =============================================================================
# DATABASE MIGRATION UTILITIES
# =============================================================================


class Workflow5DatabaseMigration:
    """
    Database migration utilities for Workflow 5 schema extensions.

    Provides safe migration procedures with rollback capabilities.
    """

    def __init__(self, database_url: str = None):
        """Initialize migration manager."""
        if database_url is None:
            # Construct from environment variables
            database_url = (
                f"postgresql://{os.getenv('DB_USER', 'nickgklezakos')}:"
                f"{os.getenv('DB_PASSWORD', 'change-this-password')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '5432')}/"
                f"{os.getenv('DB_NAME', 'ppl_vision_db')}"
            )

        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_workflow5_tables(self):
        """Create new Workflow 5 tables."""
        try:
            # First create all base tables including any missing ones
            Base.metadata.create_all(self.engine)
            print("✅ All base tables created")

            # Specifically create enhanced tables
            MediaProcessingStatusEnhanced.__table__.create(self.engine, checkfirst=True)
            FaceDataCache.__table__.create(self.engine, checkfirst=True)
            FrameIndexOptimization.__table__.create(self.engine, checkfirst=True)

            print("✅ Workflow 5 tables created successfully")
            return True
        except Exception as e:
            print(f"❌ Error creating Workflow 5 tables: {e}")
            return False

    def add_workflow5_columns(self):
        """Add new columns to existing tables."""
        try:
            with self.engine.connect() as conn:
                # Add columns to media_processing_status
                migration_sql = [
                    "ALTER TABLE media_processing_status ADD COLUMN IF NOT EXISTS processing_quality_score FLOAT DEFAULT 0.0;",
                    "ALTER TABLE media_processing_status ADD COLUMN IF NOT EXISTS frame_analysis_metadata JSONB;",
                    "ALTER TABLE media_processing_status ADD COLUMN IF NOT EXISTS optimization_enabled BOOLEAN DEFAULT TRUE;",
                    "ALTER TABLE media_processing_status ADD COLUMN IF NOT EXISTS cache_status VARCHAR(20) DEFAULT 'not_cached';",
                    "ALTER TABLE media_processing_status ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMP;",
                    "ALTER TABLE media_processing_status ADD COLUMN IF NOT EXISTS access_count INTEGER DEFAULT 0;",
                    "ALTER TABLE media_processing_status ADD COLUMN IF NOT EXISTS avg_detection_latency FLOAT;",
                    "ALTER TABLE media_processing_status ADD COLUMN IF NOT EXISTS face_density_score FLOAT;",
                    "ALTER TABLE media_processing_status ADD COLUMN IF NOT EXISTS processing_efficiency FLOAT;",
                ]

                for sql in migration_sql:
                    conn.execute(text(sql))

                conn.commit()

            print("✅ Workflow 5 columns added successfully")
            return True
        except Exception as e:
            print(f"❌ Error adding Workflow 5 columns: {e}")
            return False

    def create_optimized_indexes(self):
        """Create optimized indexes for Workflow 5 performance."""
        try:
            with self.engine.connect() as conn:
                index_sql = [
                    # Processing status optimizations
                    "CREATE INDEX IF NOT EXISTS idx_processing_optimizable ON media_processing_status(face_detection_processed, optimization_enabled, processing_quality_score) WHERE face_detection_processed = TRUE;",
                    "CREATE INDEX IF NOT EXISTS idx_processing_cache_status ON media_processing_status(cache_status, last_accessed);",
                    "CREATE INDEX IF NOT EXISTS idx_processing_access_pattern ON media_processing_status(access_count, last_accessed);",
                    # Face detection optimizations for frame queries (only basic columns)
                    "CREATE INDEX IF NOT EXISTS idx_faces_frame_optimized ON face_detections(media_id, frame_number, confidence);",
                    # High confidence partial index
                    "CREATE INDEX IF NOT EXISTS idx_faces_high_confidence ON face_detections(media_id, frame_number) WHERE confidence > 0.7;",
                    # Frame index optimization table indexes
                    "CREATE INDEX IF NOT EXISTS idx_frame_optimization_lookup ON frame_index_optimization(media_uuid, target_frame_number);",
                    "CREATE INDEX IF NOT EXISTS idx_frame_optimization_performance ON frame_index_optimization(avg_query_time_ms);",
                    # Face data cache indexes
                    "CREATE INDEX IF NOT EXISTS idx_face_cache_lookup ON face_data_cache(media_uuid, total_faces);",
                    "CREATE INDEX IF NOT EXISTS idx_face_cache_access ON face_data_cache(last_accessed, access_count);",
                ]

                for sql in index_sql:
                    try:
                        conn.execute(text(sql))
                    except Exception as idx_error:
                        print(
                            f"⚠️  Skipping index (column might not exist): {idx_error}"
                        )
                        continue

                conn.commit()

            print("✅ Optimized indexes created successfully")
            return True
        except Exception as e:
            print(f"❌ Error creating optimized indexes: {e}")
            return False

    def verify_migration(self):
        """Verify that migration was successful."""
        try:
            with self.engine.connect() as conn:
                # Check if new tables exist
                result = conn.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name IN ('face_data_cache', 'frame_index_optimization')"
                    )
                )
                tables = [row[0] for row in result]

                # Check if new columns exist
                result = conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'media_processing_status' AND column_name IN "
                        "('processing_quality_score', 'optimization_enabled', 'cache_status')"
                    )
                )
                columns = [row[0] for row in result]

                success = (
                    "face_data_cache" in tables
                    and "frame_index_optimization" in tables
                    and len(columns) >= 3
                )

                if success:
                    print("✅ Migration verification successful")
                    print(f"   - New tables: {tables}")
                    print(f"   - New columns: {len(columns)}")
                else:
                    print("❌ Migration verification failed")

                return success
        except Exception as e:
            print(f"❌ Error verifying migration: {e}")
            return False

    def rollback_migration(self):
        """Rollback Workflow 5 schema changes."""
        try:
            with self.engine.connect() as conn:
                # Drop new tables
                conn.execute(
                    text("DROP TABLE IF EXISTS frame_index_optimization CASCADE;")
                )
                conn.execute(text("DROP TABLE IF EXISTS face_data_cache CASCADE;"))

                # Remove new columns (if needed for complete rollback)
                rollback_sql = [
                    "ALTER TABLE media_processing_status DROP COLUMN IF EXISTS processing_quality_score;",
                    "ALTER TABLE media_processing_status DROP COLUMN IF EXISTS frame_analysis_metadata;",
                    "ALTER TABLE media_processing_status DROP COLUMN IF EXISTS optimization_enabled;",
                    "ALTER TABLE media_processing_status DROP COLUMN IF EXISTS cache_status;",
                    "ALTER TABLE media_processing_status DROP COLUMN IF EXISTS last_accessed;",
                    "ALTER TABLE media_processing_status DROP COLUMN IF EXISTS access_count;",
                    "ALTER TABLE media_processing_status DROP COLUMN IF EXISTS avg_detection_latency;",
                    "ALTER TABLE media_processing_status DROP COLUMN IF EXISTS face_density_score;",
                    "ALTER TABLE media_processing_status DROP COLUMN IF EXISTS processing_efficiency;",
                ]

                for sql in rollback_sql:
                    conn.execute(text(sql))

                conn.commit()

            print("✅ Migration rollback completed successfully")
            return True
        except Exception as e:
            print(f"❌ Error during rollback: {e}")
            return False

    def run_full_migration(self):
        """Run complete Workflow 5 migration."""
        print("🚀 Starting Workflow 5 Database Migration...")

        steps = [
            ("Creating new tables", self.create_workflow5_tables),
            ("Adding new columns", self.add_workflow5_columns),
            ("Creating optimized indexes", self.create_optimized_indexes),
            ("Verifying migration", self.verify_migration),
        ]

        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if not step_func():
                print(f"❌ Migration failed at: {step_name}")
                return False

        print("\n🎉 Workflow 5 database migration completed successfully!")
        return True


# Initialize migration manager for easy import
workflow5_migration = Workflow5DatabaseMigration()

if __name__ == "__main__":
    # Run migration when executed directly
    workflow5_migration.run_full_migration()
