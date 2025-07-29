"""
Analytics API endpoints for PPL Meta Mini.
"""

import io
import logging
import os
import shutil
import tempfile
from typing import Any, Dict, List

import cv2
import numpy as np
import pandas as pd
from core.face_detection import MiniFaceDetectionService
from core.face_grouping import FaceGroupingEngine
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from services.video_preprocessor import VideoPreprocessor

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
face_detection_service = MiniFaceDetectionService()
face_grouping_engine = FaceGroupingEngine()
video_preprocessor = VideoPreprocessor()


class FaceDetectionData(BaseModel):
    """Face detection data structure."""

    frame_number: int
    face_id: str
    position_x: float
    position_y: float


class GroupingRequest(BaseModel):
    """Request for face grouping."""

    face_data: List[FaceDetectionData]


@router.get("/face-detection/info")
async def get_face_detection_info():
    """Get face detection service information."""
    try:
        info = {
            "service": "PPL Meta Mini Face Detection",
            "version": "2.6.0",
            "capabilities": [
                "autonomous_face_detection",
                "two_stage_detection",
                "haar_cascade_detection",
                "dlib_detection",
                "vision_compatible_detection",
            ],
            "supported_formats": ["mp4", "avi", "mov", "mkv"],
            "default_confidence": 0.5,
            "max_faces_per_frame": 10,
        }
        return info
    except Exception as e:
        logger.error(f"Error getting face detection info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/face-detection/frame/{frame_number}")
async def detect_faces_in_frame(
    frame_number: int,
    video_path: str = Query(..., description="Path to video file"),
    confidence_threshold: float = Query(
        0.5, description="Face detection confidence threshold"
    ),
):
    """
    Detect faces in a specific frame of a video.
    This endpoint allows precise control over which frame to analyze.
    """
    try:
        logger.info(f"Detecting faces in frame {frame_number} of {video_path}")

        # Validate video file exists
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Video file not found")

        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open video file")

        try:
            # Set frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()

            if not ret:
                return {
                    "faces": [],
                    "frame_number": frame_number,
                    "detection_time": 0.0,
                    "method": "frame_extraction_failed",
                    "error": f"Could not extract frame {frame_number}",
                }

            # Perform autonomous face detection with hardcoded parameters
            import time

            start_time = time.time()

            faces = face_detection_service.detect_faces_vision_compatible(
                frame, confidence_threshold
            )

            detection_time = time.time() - start_time

            # Determine the actual method used
            actual_method = "autonomous_two_stage_haar_dlib"
            if faces and len(faces) > 0:
                actual_method = faces[0].get("method", "autonomous_two_stage_haar_dlib")

            return {
                "faces": faces,
                "frame_number": frame_number,
                "detection_time": detection_time,
                "method": actual_method,
                "total_faces": len(faces),
            }

        finally:
            cap.release()

    except Exception as e:
        logger.error(f"Autonomous frame detection error: {e}")
        return {
            "faces": [],
            "frame_number": frame_number,
            "detection_time": 0.0,
            "method": "error",
            "error": str(e),
        }


@router.get("/face-detection/stream")
async def detect_faces_stream(
    video_path: str = Query(..., description="Path to video file"),
    confidence_threshold: float = Query(
        0.5, description="Face detection confidence threshold"
    ),
    frame_interval: int = Query(15, description="Frame sampling interval"),
):
    """
    Stream face detection results for video analysis.
    Returns face detections with bounding boxes overlaid on frames.
    """
    try:
        logger.info(f"Starting face detection stream for: {video_path}")

        # Validate video file exists
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail="Video file not found")

        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open video file")

        def generate_detection_frames():
            frame_count = 0
            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Process every frame_interval frames
                    if frame_count % frame_interval == 0:
                        # Detect faces
                        faces = face_detection_service.detect_faces_two_stage(frame)

                        # Draw bounding boxes on frame
                        for face in faces:
                            bbox = face["bbox"]
                            x1, y1, x2, y2 = bbox
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                            # Add confidence text
                            confidence = face.get("confidence", 0.0)
                            cv2.putText(
                                frame,
                                f"{confidence:.2f}",
                                (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (0, 255, 0),
                                1,
                            )

                        # Encode frame as JPEG
                        _, buffer = cv2.imencode(".jpg", frame)
                        frame_bytes = buffer.tobytes()

                        # Yield frame in multipart format
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                        )

                    frame_count += 1

            finally:
                cap.release()

        return StreamingResponse(
            generate_detection_frames(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    except Exception as e:
        logger.error(f"Error in face detection stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-and-analyze")
async def upload_and_analyze_video(
    file: UploadFile = File(...),
    max_faces_per_frame: int = 10,
    proximity_threshold: float = 50.0,
    confidence_threshold: float = Query(
        0.5, description="Face detection confidence threshold"
    ),
    frame_interval: int = Query(15, description="Frame sampling interval"),
):
    """
    Upload video file first, then analyze from stored location.
    This follows the Media service pattern to test if temporary file
    handling is causing issues.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Supported: mp4, avi, mov, mkv"
        )

    try:
        logger.info(f"Upload-and-analyze for: {file.filename}")
        logger.info(f"File content type: {file.content_type}")
        logger.info(f"File size: {file.size}")

        # Step 1: Save to a permanent location (like Media service)
        storage_dir = "/tmp/ppl-mini-storage"
        os.makedirs(storage_dir, exist_ok=True)

        # Generate unique filename
        import time

        unique_filename = f"{int(time.time())}_{file.filename}"
        storage_path = os.path.join(storage_dir, unique_filename)

        # Save uploaded file permanently
        await file.seek(0)
        content = await file.read()
        logger.info(f"Read {len(content)} bytes from uploaded file")

        with open(storage_path, "wb") as f:
            f.write(content)

        logger.info(f"File saved to permanent location: {storage_path}")

        # Step 2: Preprocess video if needed to improve face detection
        final_video_path = storage_path
        if video_preprocessor.should_preprocess(storage_path):
            logger.info("Video preprocessing recommended - applying optimizations...")
            preprocessed_path = video_preprocessor.preprocess_video_for_detection(
                storage_path
            )
            if preprocessed_path:
                final_video_path = preprocessed_path
                logger.info(f"Using preprocessed video: {final_video_path}")
            else:
                logger.warning("Video preprocessing failed, using original")
        else:
            logger.info("Video preprocessing not needed")

        # Step 3: Now analyze from the final video path
        return await analyze_video_from_path(
            final_video_path,
            max_faces_per_frame,
            proximity_threshold,
            confidence_threshold,
            frame_interval,
        )

    except Exception as e:
        logger.error(f"Error in upload-and-analyze: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def analyze_video_from_path(
    video_path: str,
    max_faces_per_frame: int = 10,
    proximity_threshold: float = 50.0,
    confidence_threshold: float = 0.5,
    frame_interval: int = 15,
):
    """
    Analyze video from file path - this is the core analysis function.
    """
    try:
        logger.info(f"Starting video analysis from path: {video_path}")

        # Get video info
        video_info = face_detection_service.get_video_info(video_path)
        logger.info(f"Video info: {video_info}")
        if "error" in video_info:
            raise HTTPException(status_code=400, detail=video_info["error"])

        total_frames = video_info["frame_count"]
        file_size = video_info.get("file_size", 0)

        # Open video for frame-by-frame analysis
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open video file")

        # Calculate frames to analyze based on interval
        frames_to_analyze = list(range(0, total_frames, frame_interval))
        logger.info(
            f"Will analyze {len(frames_to_analyze)} frames with interval {frame_interval}"
        )

        all_face_data = []
        total_faces = 0

        for frame_number in frames_to_analyze:
            logger.debug(f"Processing frame {frame_number}")

            # Set frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()

            if not ret:
                logger.warning(f"Could not read frame {frame_number}")
                continue

            # Detect faces in frame
            faces = face_detection_service.detect_faces_vision_compatible(
                frame, confidence_threshold
            )

            total_faces += len(faces)

            if faces:
                logger.info(f"Frame {frame_number}: Found {len(faces)} faces")

                # Convert face detections to FaceDetectionData format
                for i, face in enumerate(faces):
                    bbox = face["bbox"]
                    center_x = (bbox[0] + bbox[2]) / 2
                    center_y = (bbox[1] + bbox[3]) / 2

                    face_data = FaceDetectionData(
                        frame_number=frame_number,
                        face_id=f"frame_{frame_number}_face_{i+1}",
                        position_x=center_x,
                        position_y=center_y,
                    )

                    # Store additional data for quality analysis
                    face_data_dict = face_data.dict()
                    face_data_dict["bbox"] = (
                        bbox  # Store bounding box for face extraction
                    )
                    all_face_data.append(face_data_dict)
            else:
                logger.debug(f"Frame {frame_number}: No faces detected")

        cap.release()

        # Group faces using clustering algorithm
        logger.info(f"Grouping {len(all_face_data)} detected faces...")
        if all_face_data:
            # Create DataFrame for grouping
            df = pd.DataFrame(all_face_data)

            # Apply advanced grouping with quality analysis and age detection
            grouping_result = face_grouping_engine.apply_advanced_grouping(
                df,
                max_faces_per_frame=max_faces_per_frame,
                proximity_threshold=proximity_threshold,
                video_path=video_path,  # Pass video path for quality analysis
            )
        else:
            grouping_result = {
                "regrouped_data": [],
                "group_tracking": [],
                "summary": {"total_groups": 0, "faces_processed": 0},
                "best_quality_faces": {},
            }

        # Return complete analysis
        frames_processed = len(frames_to_analyze)
        logger.info("Video analysis complete!")

        # Extract only the persons data (best quality faces with age detection)
        persons_data = grouping_result.get("best_quality_faces", {})

        return {"persons": persons_data, "file_info": {"storage_path": video_path}}

    except Exception as e:
        logger.error(f"Error analyzing video from path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/complete-video-analysis")
async def complete_video_analysis(
    file: UploadFile = File(...),
    max_faces_per_frame: int = 10,
    proximity_threshold: float = 50.0,
    confidence_threshold: float = Query(
        0.5, description="Face detection confidence threshold"
    ),
):
    """
    Complete video analysis pipeline:
    1. Upload video
    2. Detect faces in all frames
    3. Group faces using clustering
    4. Return complete analysis with merged groups
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Supported: mp4, avi, mov, mkv"
        )

    try:
        logger.info(f"Starting complete video analysis for: {file.filename}")
        logger.info(f"File content type: {file.content_type}")
        logger.info(f"File size: {file.size}")

        # Step 1: Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            # Reset file pointer to beginning (in case it was read before)
            await file.seek(0)
            content = await file.read()
            logger.info(f"Read {len(content)} bytes from uploaded file")

            # Calculate file hash for comparison
            import hashlib

            file_hash = hashlib.sha256(content).hexdigest()
            logger.info(f"File SHA256 hash: {file_hash}")

            tmp.write(content)
            tmp_path = tmp.name

        logger.info(f"Temporary file saved to: {tmp_path}")

        # Verify the saved file can be read
        import os

        saved_size = os.path.getsize(tmp_path)
        logger.info(
            f"Saved file size: {saved_size} bytes "
            f"(matches upload: {saved_size == len(content)})"
        )

        # Step 2: Get video info
        video_info = face_detection_service.get_video_info(tmp_path)
        logger.info(f"Video info: {video_info}")
        if "error" in video_info:
            raise HTTPException(status_code=400, detail=video_info["error"])

        total_frames = video_info["frame_count"]

        # Open video for frame-by-frame analysis
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open video file")

        all_face_data = []
        total_faces = 0

        # Smart frame sampling strategy (same as frontend)
        # Sample every 15 frames to match working detection pattern
        frame_interval = 15
        frames_to_analyze = list(range(0, total_frames, frame_interval))

        # Also include some key frames from the working range (105+)
        if total_frames > 105:
            # Add strategic frames where faces are more likely
            strategic_frames = list(range(105, min(total_frames, 400), 15))
            frames_to_analyze.extend(strategic_frames)

        # Remove duplicates and sort
        frames_to_analyze = sorted(list(set(frames_to_analyze)))

        logger.info(
            f"Analyzing {len(frames_to_analyze)} strategically sampled frames "
            f"out of {total_frames} total frames"
        )

        for frame_number in frames_to_analyze:
            logger.debug(f"Processing frame {frame_number}")

            # Set frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()

            if not ret:
                logger.warning(f"Could not read frame {frame_number}")
                continue

            # Detect faces in frame using optimized detection
            faces = face_detection_service.detect_faces_vision_compatible(
                frame, confidence_threshold
            )

            total_faces += len(faces)

            if faces:
                logger.info(f"Frame {frame_number}: Found {len(faces)} faces")

                # Convert face detections to FaceDetectionData format
                for i, face in enumerate(faces):
                    bbox = face["bbox"]
                    center_x = (bbox[0] + bbox[2]) / 2
                    center_y = (bbox[1] + bbox[3]) / 2

                    face_data = FaceDetectionData(
                        frame_number=frame_number,
                        face_id=f"frame_{frame_number}_face_{i+1}",
                        position_x=center_x,
                        position_y=center_y,
                    )

                    # Store additional data for quality analysis
                    face_data_dict = face_data.dict()
                    face_data_dict["bbox"] = (
                        bbox  # Store bounding box for face extraction
                    )
                    all_face_data.append(face_data_dict)
            else:
                logger.debug(f"Frame {frame_number}: No faces detected")

        cap.release()

        # Step 4: Group faces using clustering algorithm
        logger.info(f"Grouping {len(all_face_data)} detected faces...")
        if all_face_data:
            # Create DataFrame for grouping
            df = pd.DataFrame(all_face_data)

            # Apply advanced grouping with quality analysis and age detection
            grouping_result = face_grouping_engine.apply_advanced_grouping(
                df,
                max_faces_per_frame=max_faces_per_frame,
                proximity_threshold=proximity_threshold,
                video_path=tmp_path,  # Pass video path for quality analysis
            )
        else:
            grouping_result = {
                "regrouped_data": [],
                "group_tracking": [],
                "summary": {"total_groups": 0, "faces_processed": 0},
                "best_quality_faces": {},
            }

        # Cleanup temp file
        import os

        os.unlink(tmp_path)

        # Return complete analysis
        frames_processed = len(frames_to_analyze)
        logger.info("Complete video analysis finished!")

        return {
            "video_info": video_info,
            "detection_summary": {
                "total_frames": total_frames,
                "frames_analyzed": frames_processed,
                "total_faces_detected": total_faces,
                "faces_processed_for_grouping": len(all_face_data),
                "average_faces_per_frame": (
                    total_faces / frames_processed if frames_processed > 0 else 0
                ),
                "strategic_sampling": True,
                "sampling_strategy": "15_frame_interval_plus_strategic_105_400",
            },
            "face_grouping": grouping_result,
            "analysis_parameters": {
                "max_faces_per_frame": max_faces_per_frame,
                "proximity_threshold": proximity_threshold,
                "confidence_threshold": confidence_threshold,
                "strategic_sampling": True,
            },
            "pipeline_steps": [
                "✅ Video uploaded and validated",
                f"✅ Strategically sampled {frames_processed} frames "
                f"out of {total_frames} total",
                f"✅ Detected {total_faces} faces across sampled frames",
                f"✅ Grouped faces into "
                f"{grouping_result.get('summary', {}).get('total_groups', 0)} "
                f"clusters",
                "✅ Complete analysis finished",
            ],
        }

    except Exception as e:
        logger.error(f"Error in complete video analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/group-faces")
async def group_faces(request: GroupingRequest):
    """Group faces using clustering algorithms."""
    try:
        engine = face_grouping_engine
        df = pd.DataFrame([face.dict() for face in request.face_data])

        # Group faces using clustering (no video path available for quality analysis)
        result = engine.apply_advanced_grouping(
            df, max_faces_per_frame=10, proximity_threshold=50, video_path=None
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Error in face grouping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo-data")
async def get_demo_data():
    demo_data = [
        {"Frame_Number": 1, "Face_ID": "A", "Position_X": 100, "Position_Y": 200},
        {"Frame_Number": 1, "Face_ID": "B", "Position_X": 300, "Position_Y": 150},
        {"Frame_Number": 2, "Face_ID": "C", "Position_X": 105, "Position_Y": 205},
        {"Frame_Number": 2, "Face_ID": "D", "Position_X": 295, "Position_Y": 145},
        {"Frame_Number": 3, "Face_ID": "E", "Position_X": 110, "Position_Y": 210},
        {"Frame_Number": 3, "Face_ID": "F", "Position_X": 290, "Position_Y": 140},
    ]

    return {
        "demo_data": demo_data,
        "description": "Sample face detection data for testing grouping algorithms",
        "usage": "Use this data to test the grouping endpoints",
    }
