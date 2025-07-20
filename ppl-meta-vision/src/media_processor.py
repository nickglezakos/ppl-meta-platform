"""
PPL Meta Vision Service - Media Processing Service
Enhanced media processing with database integration and overlay generation
"""

import logging
import os
import tempfile
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import requests
from database import vision_db
from extracted_face_detector import ExtractedFaceDetector
from models import (
    FaceDetectionResult,
    MediaProcessingRequest,
    MediaProcessingResponse,
    MediaRecord,
    OverlayRectangle,
    OverlayRequest,
    OverlayResponse,
    TimelineRequest,
    TimelineResponse,
    TimelineSegment,
    VideoFrame,
)

logger = logging.getLogger(__name__)


class MediaProcessingService:
    """Enhanced media processing service with database integration."""

    def __init__(self, face_detector: ExtractedFaceDetector):
        """Initialize with face detector."""
        self.face_detector = face_detector
        self.media_service_url = "http://localhost:8000"
        self.supported_image_formats = [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]
        self.supported_video_formats = [".mp4", ".avi", ".mov", ".mkv", ".webm"]

    async def process_media_from_url(
        self, request: MediaProcessingRequest
    ) -> MediaProcessingResponse:
        """Process media from URL with full pipeline."""
        start_time = datetime.now()

        try:
            # Create media record
            media_record = MediaRecord(
                media_id=request.media_id,
                media_type=request.media_type,
                media_url=request.media_url,
                processing_status="processing",
            )

            # Store media record
            if request.store_results:
                vision_db.store_media_record(media_record)

            # Fetch media content
            media_response = requests.get(request.media_url, timeout=30, stream=True)

            if media_response.status_code != 200:
                raise Exception(
                    f"Failed to fetch media: HTTP {media_response.status_code}"
                )

            # Process based on media type
            if request.media_type == "image":
                detections, video_info = await self._process_image(
                    media_response.content, request
                )
            elif request.media_type == "video":
                detections, video_info = await self._process_video(
                    media_response.content, request
                )
            else:
                raise Exception(f"Unsupported media type: {request.media_type}")

            # Store detections in database
            if request.store_results:
                for detection in detections:
                    vision_db.store_face_detection(detection)

                # Update media record
                media_record.processing_status = "completed"
                media_record.total_faces = len(detections)
                media_record.processed_at = datetime.now()

                if video_info:
                    media_record.total_frames = video_info.get("total_frames")
                    media_record.video_duration = video_info.get("duration")
                    media_record.video_fps = video_info.get("fps")

                vision_db.store_media_record(media_record)

            processing_time = (datetime.now() - start_time).total_seconds()

            return MediaProcessingResponse(
                success=True,
                media_id=request.media_id,
                media_type=request.media_type,
                total_faces=len(detections),
                total_frames=video_info.get("total_frames") if video_info else 1,
                processing_time=processing_time,
                detections=detections,
                video_info=video_info,
                message=f"Successfully processed {request.media_type} with {len(detections)} faces detected",
            )

        except Exception as e:
            # Update media record with error status
            if request.store_results:
                media_record.processing_status = "failed"
                vision_db.store_media_record(media_record)

            logger.error(f"❌ Media processing failed: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()

            return MediaProcessingResponse(
                success=False,
                media_id=request.media_id,
                media_type=request.media_type,
                total_faces=0,
                processing_time=processing_time,
                detections=[],
                message=f"Processing failed: {str(e)}",
            )

    async def _process_image(
        self, image_data: bytes, request: MediaProcessingRequest
    ) -> Tuple[List[FaceDetectionResult], Optional[Dict[str, Any]]]:
        """Process a single image."""
        detections = []

        try:
            # Decode image
            image_array = np.asarray(bytearray(image_data), dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

            if image is None:
                raise Exception("Failed to decode image")

            height, width = image.shape[:2]

            # Run face detection
            results = self.face_detector.detect_faces_multi_method(image)

            # Convert to detection results
            for method, result in results.items():
                if result.get("success", False):
                    for detection in result.get("detections", []):
                        face_result = FaceDetectionResult(
                            media_id=request.media_id,
                            media_type="image",
                            bbox=detection["bbox"],
                            confidence=detection["confidence"],
                            method=detection["method"],
                            frame_info=VideoFrame(
                                frame_number=0,
                                timestamp=0.0,
                                width=width,
                                height=height,
                            ),
                        )
                        detections.append(face_result)

            return detections, {"width": width, "height": height, "total_frames": 1}

        except Exception as e:
            logger.error(f"❌ Image processing failed: {e}")
            return [], None

    async def _process_video(
        self, video_data: bytes, request: MediaProcessingRequest
    ) -> Tuple[List[FaceDetectionResult], Optional[Dict[str, Any]]]:
        """Process video with frame-by-frame analysis."""
        detections = []
        video_info = {}

        # Save video to temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            temp_file.write(video_data)
            temp_video_path = temp_file.name

        try:
            # Open video
            cap = cv2.VideoCapture(temp_video_path)

            if not cap.isOpened():
                raise Exception("Failed to open video file")

            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = total_frames / fps if fps > 0 else 0

            video_info = {
                "fps": fps,
                "total_frames": total_frames,
                "width": width,
                "height": height,
                "duration": duration,
            }

            # Process frames (sample every N frames for performance)
            frame_interval = max(1, int(fps / 2)) if fps > 0 else 10  # 2 FPS sampling
            frame_number = 0

            logger.info(
                f"🎬 Processing video: {total_frames} frames, {fps:.2f} FPS, {duration:.2f}s"
            )

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Process every frame_interval frames
                if frame_number % frame_interval == 0:
                    timestamp = frame_number / fps if fps > 0 else 0

                    # Run face detection on frame
                    results = self.face_detector.detect_faces_multi_method(frame)

                    # Convert to detection results
                    for method, result in results.items():
                        if result.get("success", False):
                            for detection in result.get("detections", []):
                                face_result = FaceDetectionResult(
                                    media_id=request.media_id,
                                    media_type="video",
                                    frame_number=frame_number,
                                    timestamp=timestamp,
                                    bbox=detection["bbox"],
                                    confidence=detection["confidence"],
                                    method=detection["method"],
                                    frame_info=VideoFrame(
                                        frame_number=frame_number,
                                        timestamp=timestamp,
                                        width=width,
                                        height=height,
                                    ),
                                )
                                detections.append(face_result)

                frame_number += 1

                # Log progress every 100 frames
                if frame_number % 100 == 0:
                    progress = (frame_number / total_frames) * 100
                    logger.info(
                        f"📊 Video processing: {progress:.1f}% ({frame_number}/{total_frames})"
                    )

            cap.release()

            logger.info(
                f"✅ Video processing complete: {len(detections)} faces detected"
            )
            return detections, video_info

        except Exception as e:
            logger.error(f"❌ Video processing failed: {e}")
            return [], video_info

        finally:
            # Clean up temporary file
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)

    def generate_overlay_data(self, request: OverlayRequest) -> OverlayResponse:
        """Generate overlay data for frontend display."""
        try:
            # Get face detections from database
            detections = vision_db.get_face_detections(
                media_id=request.media_id,
                frame_number=request.frame_number,
                timestamp=request.timestamp,
                confidence_threshold=request.confidence_threshold or 0.5,
            )

            # Get media info
            media_record = vision_db.get_media_record(request.media_id)

            # Default overlay style
            default_style = {
                "border": "2px solid #00ff00",
                "backgroundColor": "rgba(0, 255, 0, 0.1)",
                "borderRadius": "4px",
            }

            # Override with custom style if provided
            if request.overlay_style:
                default_style.update(request.overlay_style)

            # Create overlay rectangles
            overlays = []
            for detection in detections:
                overlay = OverlayRectangle(
                    id=detection["id"],
                    bbox=[
                        detection["bbox_x1"],
                        detection["bbox_y1"],
                        detection["bbox_x2"],
                        detection["bbox_y2"],
                    ],
                    confidence=detection["confidence"],
                    method=detection["method"],
                    style=default_style.copy(),
                    frame_number=detection.get("frame_number"),
                    timestamp=detection.get("timestamp"),
                )
                overlays.append(overlay)

            # Frame info
            frame_info = {
                "total_overlays": len(overlays),
                "confidence_threshold": request.confidence_threshold or 0.5,
            }

            # Video info if available
            video_info = None
            if media_record and media_record.get("video_duration"):
                video_info = {
                    "duration": media_record["video_duration"],
                    "fps": media_record["video_fps"],
                    "total_frames": media_record["total_frames"],
                }

            return OverlayResponse(
                success=True,
                media_id=request.media_id,
                overlays=overlays,
                frame_info=frame_info,
                video_info=video_info,
                message=f"Generated {len(overlays)} overlay rectangles",
            )

        except Exception as e:
            logger.error(f"❌ Overlay generation failed: {e}")
            return OverlayResponse(
                success=False,
                media_id=request.media_id,
                overlays=[],
                message=f"Overlay generation failed: {str(e)}",
            )

    def generate_timeline_data(self, request: TimelineRequest) -> TimelineResponse:
        """Generate timeline data for video scrubbing."""
        try:
            # Get media record
            media_record = vision_db.get_media_record(request.media_id)
            if not media_record:
                raise Exception(f"Media record not found: {request.media_id}")

            # Get timeline segments
            timeline_data = vision_db.get_face_timeline(
                media_id=request.media_id,
                time_resolution=request.time_resolution or 1.0,
                confidence_threshold=request.confidence_threshold or 0.5,
            )

            # Convert to timeline segments
            segments = []
            for segment_data in timeline_data:
                segment = TimelineSegment(
                    start_time=segment_data["start_time"],
                    end_time=segment_data["end_time"],
                    face_count=segment_data["face_count"],
                    max_confidence=segment_data["max_confidence"],
                    detections=segment_data["detection_ids"],
                )
                segments.append(segment)

            # Calculate summary statistics
            total_faces = sum(s.face_count for s in segments)
            avg_confidence = (
                sum(s.max_confidence for s in segments) / len(segments)
                if segments
                else 0
            )

            summary = {
                "total_segments": len(segments),
                "total_faces": total_faces,
                "average_confidence": avg_confidence,
                "face_density": (
                    total_faces / media_record["video_duration"]
                    if media_record.get("video_duration")
                    else 0
                ),
            }

            return TimelineResponse(
                success=True,
                media_id=request.media_id,
                total_duration=media_record.get("video_duration"),
                timeline=segments,
                summary=summary,
                message=f"Generated timeline with {len(segments)} segments",
            )

        except Exception as e:
            logger.error(f"❌ Timeline generation failed: {e}")
            return TimelineResponse(
                success=False,
                media_id=request.media_id,
                timeline=[],
                summary={},
                message=f"Timeline generation failed: {str(e)}",
            )

    def get_media_analytics(self, media_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics for processed media."""
        try:
            # Get basic statistics
            stats = vision_db.get_media_statistics(media_id)

            # Get media record
            media_record = vision_db.get_media_record(media_id)

            if media_record:
                stats["media_info"] = {
                    "media_type": media_record["media_type"],
                    "processing_status": media_record["processing_status"],
                    "total_frames": media_record.get("total_frames"),
                    "video_duration": media_record.get("video_duration"),
                    "video_fps": media_record.get("video_fps"),
                    "processed_at": media_record.get("processed_at"),
                }

            return stats

        except Exception as e:
            logger.error(f"❌ Analytics generation failed: {e}")
            return {}
