"""
PPL Meta Vision Service - SQLAlchemy Database Models
Session-based face detection models for Workflow 4

This module provides SQLAlchemy ORM models for the session-based face detection
functionality. These models complement the existing PostgreSQL implementation
and provide a more structured approach to database operations.

Usage:
    from sqlalchemy_models import FaceDetectionSession, MediaProcessingStatus, FaceDetection

    # Create session
    session = FaceDetectionSession(
        session_uuid=str(uuid.uuid4()),
        media_uuid="media-123",
        session_type="streaming"
    )
"""

import uuid
from datetime import datetime
from typing import List, Optional

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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

# Base class for all models
Base = declarative_base()


class FaceDetectionSession(Base):
    """
    SQLAlchemy model for face detection sessions.

    Tracks complete face detection sessions with full traceability from
    camera device to individual face detections.
    """

    __tablename__ = "face_detection_sessions"

    # Primary key
    session_uuid = Column(String(36), primary_key=True)

    # Core session data
    media_uuid = Column(String(36), nullable=False, index=True)
    camera_device_uuid = Column(String(36), nullable=True, index=True)
    session_type = Column(String(20), nullable=False, default="streaming", index=True)

    # Session timing
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    ended_at = Column(DateTime, nullable=True)

    # Session statistics
    total_faces_detected = Column(Integer, default=0)
    processing_status = Column(String(20), nullable=False, default="active", index=True)

    # Additional metadata
    session_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    face_detections = relationship(
        "FaceDetection", back_populates="session", lazy="dynamic"
    )
    media_processing_status = relationship(
        "MediaProcessingStatus", back_populates="session", uselist=False
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            session_type.in_(["streaming", "bulk_processing"]), name="chk_session_type"
        ),
        CheckConstraint(
            processing_status.in_(["active", "completed", "failed"]),
            name="chk_processing_status",
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at", name="chk_session_time_order"
        ),
        CheckConstraint("total_faces_detected >= 0", name="chk_faces_count_positive"),
        CheckConstraint(
            "LENGTH(session_uuid) = 36 AND session_uuid ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'",
            name="chk_session_uuid_format",
        ),
        # Additional indexes for performance
        Index("idx_session_media_status", "media_uuid", "processing_status"),
        Index("idx_session_camera_type", "camera_device_uuid", "session_type"),
    )

    def __repr__(self):
        return f"<FaceDetectionSession(uuid={self.session_uuid}, media={self.media_uuid}, status={self.processing_status})>"

    def to_dict(self):
        """Convert session to dictionary representation."""
        return {
            "session_uuid": self.session_uuid,
            "media_uuid": self.media_uuid,
            "camera_device_uuid": self.camera_device_uuid,
            "session_type": self.session_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "total_faces_detected": self.total_faces_detected,
            "processing_status": self.processing_status,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.processing_status == "active"

    def is_completed(self) -> bool:
        """Check if session is completed."""
        return self.processing_status == "completed"

    def get_duration_seconds(self) -> Optional[float]:
        """Get session duration in seconds."""
        if self.started_at and self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None


class MediaProcessingStatus(Base):
    """
    SQLAlchemy model for media processing status.

    Tracks whether media files have been processed for face detection
    to enable optimized playback with pre-computed face data.
    """

    __tablename__ = "media_processing_status"

    # Primary key
    media_uuid = Column(String(36), primary_key=True)

    # Processing status
    face_detection_processed = Column(Boolean, default=False, index=True)
    face_detection_session_uuid = Column(
        String(36),
        ForeignKey("face_detection_sessions.session_uuid", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Processing metadata
    processing_completed_at = Column(DateTime, nullable=True)
    total_frames_processed = Column(Integer, nullable=True)
    total_faces_detected = Column(Integer, nullable=True)
    processing_method = Column(String(50), nullable=True)

    # Timestamp
    last_updated = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True
    )

    # Relationships
    session = relationship(
        "FaceDetectionSession", back_populates="media_processing_status"
    )

    def __repr__(self):
        return f"<MediaProcessingStatus(media={self.media_uuid}, processed={self.face_detection_processed})>"

    def to_dict(self):
        """Convert processing status to dictionary representation."""
        return {
            "media_uuid": self.media_uuid,
            "face_detection_processed": self.face_detection_processed,
            "face_detection_session_uuid": self.face_detection_session_uuid,
            "processing_completed_at": (
                self.processing_completed_at.isoformat()
                if self.processing_completed_at
                else None
            ),
            "total_frames_processed": self.total_frames_processed,
            "total_faces_detected": self.total_faces_detected,
            "processing_method": self.processing_method,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
        }

    def mark_as_processed(
        self, session_uuid: str, total_frames: int, total_faces: int, method: str
    ):
        """Mark media as fully processed."""
        self.face_detection_processed = True
        self.face_detection_session_uuid = session_uuid
        self.processing_completed_at = datetime.utcnow()
        self.total_frames_processed = total_frames
        self.total_faces_detected = total_faces
        self.processing_method = method
        self.last_updated = datetime.utcnow()


class FaceDetection(Base):
    """
    SQLAlchemy model for individual face detections.

    Enhanced version of the existing face_detections table with session support.
    This model includes the session_uuid for complete traceability.
    """

    __tablename__ = "face_detections"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Media reference
    media_id = Column(
        String(36), nullable=False, index=True
    )  # Keep existing column name for compatibility

    # Frame information
    frame_number = Column(Integer, nullable=True, index=True)
    timestamp = Column(Float, nullable=True, index=True)

    # Bounding box coordinates
    bbox_x1 = Column(Integer, nullable=False)
    bbox_y1 = Column(Integer, nullable=False)
    bbox_x2 = Column(Integer, nullable=False)
    bbox_y2 = Column(Integer, nullable=False)

    # Detection metadata
    confidence = Column(Float, nullable=False)
    method = Column(String(50), nullable=False)

    # Session reference (NEW)
    session_uuid = Column(
        String(36),
        ForeignKey("face_detection_sessions.session_uuid", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("FaceDetectionSession", back_populates="face_detections")

    # Additional indexes for performance
    __table_args__ = (
        Index("idx_face_detections_session_frame", "session_uuid", "frame_number"),
        Index("idx_face_detections_media_frame", "media_id", "frame_number"),
        Index("idx_face_detections_confidence", "confidence"),
    )

    def __repr__(self):
        return f"<FaceDetection(id={self.id}, media={self.media_id}, session={self.session_uuid})>"

    def to_dict(self):
        """Convert face detection to dictionary representation."""
        return {
            "id": self.id,
            "media_id": self.media_id,
            "frame_number": self.frame_number,
            "timestamp": self.timestamp,
            "bbox": [self.bbox_x1, self.bbox_y1, self.bbox_x2, self.bbox_y2],
            "confidence": self.confidence,
            "method": self.method,
            "session_uuid": self.session_uuid,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def get_bbox_dict(self):
        """Get bounding box as dictionary."""
        return {
            "x1": self.bbox_x1,
            "y1": self.bbox_y1,
            "x2": self.bbox_x2,
            "y2": self.bbox_y2,
            "width": self.bbox_x2 - self.bbox_x1,
            "height": self.bbox_y2 - self.bbox_y1,
        }

    def get_bbox_list(self):
        """Get bounding box as list [x1, y1, x2, y2]."""
        return [self.bbox_x1, self.bbox_y1, self.bbox_x2, self.bbox_y2]


class DatabaseManager:
    """
    SQLAlchemy database manager for session-based face detection.

    Provides high-level database operations using SQLAlchemy ORM models.
    This complements the existing PostgreSQL implementation.
    """

    def __init__(self, database_url: str = None):
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL. If None, will construct from environment variables.
        """
        if database_url is None:
            import os

            database_url = (
                f"postgresql://{os.getenv('DB_USER', 'nickgklezakos')}:"
                f"{os.getenv('DB_PASSWORD', 'change-this-password')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '5432')}/"
                f"{os.getenv('DB_NAME', 'ppl_vision_db')}"
            )

        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """Get a new database session."""
        return self.SessionLocal()

    # Session management operations
    def create_face_detection_session(
        self,
        media_uuid: str,
        camera_device_uuid: str = None,
        session_type: str = "streaming",
        metadata: dict = None,
    ) -> FaceDetectionSession:
        """Create a new face detection session."""
        session_uuid = str(uuid.uuid4())

        session = FaceDetectionSession(
            session_uuid=session_uuid,
            media_uuid=media_uuid,
            camera_device_uuid=camera_device_uuid,
            session_type=session_type,
            metadata=metadata,
        )

        db_session = self.get_session()
        try:
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)
            return session
        finally:
            db_session.close()

    def get_session_by_uuid(self, session_uuid: str) -> Optional[FaceDetectionSession]:
        """Get session by UUID."""
        db_session = self.get_session()
        try:
            return (
                db_session.query(FaceDetectionSession)
                .filter(FaceDetectionSession.session_uuid == session_uuid)
                .first()
            )
        finally:
            db_session.close()

    def close_face_detection_session(self, session_uuid: str, total_faces: int) -> bool:
        """Close a face detection session."""
        db_session = self.get_session()
        try:
            session = (
                db_session.query(FaceDetectionSession)
                .filter(FaceDetectionSession.session_uuid == session_uuid)
                .first()
            )

            if session:
                session.ended_at = datetime.utcnow()
                session.processing_status = "completed"
                session.total_faces_detected = total_faces
                db_session.commit()
                return True
            return False
        finally:
            db_session.close()

    def store_face_detection(
        self,
        session_uuid: str,
        media_id: str,
        bbox: List[int],
        confidence: float,
        method: str,
        frame_number: int = None,
        timestamp: float = None,
    ) -> FaceDetection:
        """Store a face detection with session context."""
        face_detection = FaceDetection(
            media_id=media_id,
            session_uuid=session_uuid,
            frame_number=frame_number,
            timestamp=timestamp,
            bbox_x1=bbox[0],
            bbox_y1=bbox[1],
            bbox_x2=bbox[2],
            bbox_y2=bbox[3],
            confidence=confidence,
            method=method,
        )

        db_session = self.get_session()
        try:
            db_session.add(face_detection)
            db_session.commit()
            db_session.refresh(face_detection)
            return face_detection
        finally:
            db_session.close()

    def get_faces_by_session(self, session_uuid: str) -> List[FaceDetection]:
        """Get all face detections for a session."""
        db_session = self.get_session()
        try:
            return (
                db_session.query(FaceDetection)
                .filter(FaceDetection.session_uuid == session_uuid)
                .order_by(FaceDetection.frame_number)
                .all()
            )
        finally:
            db_session.close()

    def get_faces_by_media(self, media_uuid: str) -> List[FaceDetection]:
        """Get all face detections for a media file."""
        db_session = self.get_session()
        try:
            return (
                db_session.query(FaceDetection)
                .filter(FaceDetection.media_id == media_uuid)
                .order_by(FaceDetection.frame_number)
                .all()
            )
        finally:
            db_session.close()

    def get_processing_status(self, media_uuid: str) -> Optional[MediaProcessingStatus]:
        """Get processing status for a media file."""
        db_session = self.get_session()
        try:
            return (
                db_session.query(MediaProcessingStatus)
                .filter(MediaProcessingStatus.media_uuid == media_uuid)
                .first()
            )
        finally:
            db_session.close()

    def mark_media_as_processed(
        self,
        media_uuid: str,
        session_uuid: str,
        total_frames: int,
        total_faces: int,
        method: str,
    ) -> MediaProcessingStatus:
        """Mark media as fully processed for face detection."""
        db_session = self.get_session()
        try:
            status = (
                db_session.query(MediaProcessingStatus)
                .filter(MediaProcessingStatus.media_uuid == media_uuid)
                .first()
            )

            if not status:
                status = MediaProcessingStatus(media_uuid=media_uuid)
                db_session.add(status)

            status.mark_as_processed(session_uuid, total_frames, total_faces, method)
            db_session.commit()
            db_session.refresh(status)
            return status
        finally:
            db_session.close()


# Example usage and testing functions
def example_usage():
    """Example of how to use the SQLAlchemy models."""
    # Initialize database manager
    db_manager = DatabaseManager()

    # Create tables (if they don't exist)
    db_manager.create_tables()

    # Create a face detection session
    session = db_manager.create_face_detection_session(
        media_uuid="media-12345",
        camera_device_uuid="camera-67890",
        session_type="streaming",
        metadata={"user_id": "user123", "detection_method": "two_stage"},
    )

    print(f"Created session: {session.session_uuid}")

    # Store face detections
    face1 = db_manager.store_face_detection(
        session_uuid=session.session_uuid,
        media_id="media-12345",
        bbox=[100, 100, 200, 200],
        confidence=0.95,
        method="two_stage",
        frame_number=1,
        timestamp=0.033,
    )

    face2 = db_manager.store_face_detection(
        session_uuid=session.session_uuid,
        media_id="media-12345",
        bbox=[300, 150, 400, 250],
        confidence=0.87,
        method="two_stage",
        frame_number=15,
        timestamp=0.5,
    )

    print(f"Stored face detections: {face1.id}, {face2.id}")

    # Close session
    db_manager.close_face_detection_session(session.session_uuid, 2)

    # Mark media as processed
    status = db_manager.mark_media_as_processed(
        media_uuid="media-12345",
        session_uuid=session.session_uuid,
        total_frames=100,
        total_faces=2,
        method="two_stage",
    )

    print(f"Media processing status: {status.face_detection_processed}")

    # Query session data
    retrieved_session = db_manager.get_session_by_uuid(session.session_uuid)
    faces = db_manager.get_faces_by_session(session.session_uuid)

    print(f"Retrieved session: {retrieved_session.to_dict()}")
    print(f"Session faces: {[face.to_dict() for face in faces]}")


if __name__ == "__main__":
    example_usage()
