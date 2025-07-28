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
        return face_detection_service.get_face_detection_info()
    except Exception as e:
        logger.error(f"Error getting face detection info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-video")
async def analyze_video_faces(file: UploadFile = File(...)):
    """
    Analyze faces in uploaded video file.
    Returns video info and face count summary.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Supported: mp4, avi, mov, mkv"
        )

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Get video info
        video_info = face_detection_service.get_video_info(tmp_path)
        if "error" in video_info:
            raise HTTPException(status_code=400, detail=video_info["error"])

        # Analyze faces frame by frame
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Cannot open video")

        total_faces = 0
        frame_count = 0
        face_detections = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            faces = face_detection_service.detect_faces_two_stage(frame)
            total_faces += len(faces)

            if faces:
                face_detections.append(
                    {"frame": frame_count, "face_count": len(faces), "faces": faces}
                )

        cap.release()

        # Cleanup
        import os

        os.unlink(tmp_path)

        return {
            "video_info": video_info,
            "analysis": {
                "total_frames": frame_count,
                "total_faces_detected": total_faces,
                "frames_with_faces": len(face_detections),
                "average_faces_per_frame": (
                    total_faces / frame_count if frame_count > 0 else 0
                ),
            },
            "face_detections": face_detections[:10],  # First 10 frames only
        }

    except Exception as e:
        logger.error(f"Error analyzing video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream-faces")
async def stream_video_with_faces(file: UploadFile = File(...)):
    """
    Stream video frames with face detection overlay.
    Compatible with media service endpoint format.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Supported: mp4, avi, mov, mkv"
        )

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        def generate_frames():
            cap = cv2.VideoCapture(tmp_path)
            if not cap.isOpened():
                return

            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Process frame with face detection overlay
                    processed_frame, faces = (
                        face_detection_service.process_frame_with_overlay(
                            frame, confidence_threshold=0.5, draw_overlay=True
                        )
                    )

                    # Encode frame as JPEG
                    _, buffer = cv2.imencode(".jpg", processed_frame)
                    frame_bytes = buffer.tobytes()

                    # Yield frame in multipart format
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                    )

            finally:
                cap.release()
                # Cleanup temp file
                import os

                os.unlink(tmp_path)

        return StreamingResponse(
            generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame"
        )

    except Exception as e:
        logger.error(f"Error streaming video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-and-analyze")
async def upload_and_analyze_video(
    file: UploadFile = File(...),
    max_faces_per_frame: int = 10,
    proximity_threshold: float = 50.0,
    confidence_threshold: float = Query(
        0.5, description="Face detection confidence threshold"
    ),
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
        )

    except Exception as e:
        logger.error(f"Error in upload-and-analyze: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def analyze_video_from_path(
    video_path: str,
    max_faces_per_frame: int = 10,
    proximity_threshold: float = 50.0,
    confidence_threshold: float = 0.5,
):
    """
    Analyze video from a file path (like our successful curl test).
    """
    try:
        logger.info(f"Analyzing video from path: {video_path}")

        # Verify file exists and is readable
        if not os.path.exists(video_path):
            raise HTTPException(status_code=400, detail="Video file not found")

        file_size = os.path.getsize(video_path)
        logger.info(f"File size on disk: {file_size} bytes")

        # Get video info
        video_info = face_detection_service.get_video_info(video_path)
        logger.info(f"Video info: {video_info}")
        if "error" in video_info:
            raise HTTPException(status_code=400, detail=video_info["error"])

        # Extract faces using smart frame sampling
        logger.info("Extracting faces from stored video file...")
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video file: {video_path}")
            raise HTTPException(status_code=400, detail="Cannot open video")

        # Get total frame count for smart sampling
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"Total frames in video: {total_frames}")
        logger.info(f"Video properties - FPS: {fps}, " f"Resolution: {width}x{height}")

        # Test reading the first frame
        ret, test_frame = cap.read()
        if not ret or test_frame is None:
            logger.error(f"Cannot read first frame from video: {video_path}")
            cap.release()
            raise HTTPException(status_code=400, detail="Cannot read video frames")
        logger.info(f"Successfully read first frame: {test_frame.shape}")

        # Reset to beginning
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        all_face_data = []
        total_faces = 0

        # Smart frame sampling strategy (same as before)
        frame_interval = 15
        frames_to_analyze = list(range(0, total_frames, frame_interval))

        # Also include key frames from the working range (105+)
        if total_frames > 105:
            strategic_frames = list(range(105, min(total_frames, 400), 15))
            frames_to_analyze.extend(strategic_frames)

        # Remove duplicates and sort
        frames_to_analyze = sorted(list(set(frames_to_analyze)))

        logger.info(
            f"Analyzing {len(frames_to_analyze)} strategically "
            f"sampled frames out of {total_frames} total frames"
        )
        logger.info(
            f"Frames to analyze: {frames_to_analyze[:10]}..."
            f"{'(truncated)' if len(frames_to_analyze) > 10 else ''}"
        )

        for frame_number in frames_to_analyze:
            # Seek to specific frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"Could not read frame {frame_number}")
                continue

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
                    all_face_data.append(face_data)
            else:
                logger.debug(f"Frame {frame_number}: No faces detected")

        cap.release()

        # Group faces using clustering algorithm
        logger.info(f"Grouping {len(all_face_data)} detected faces...")
        if all_face_data:
            # Create DataFrame for grouping
            df = pd.DataFrame([face.dict() for face in all_face_data])

            # Apply advanced grouping
            grouping_result = face_grouping_engine.apply_advanced_grouping(
                df,
                max_faces_per_frame=max_faces_per_frame,
                proximity_threshold=proximity_threshold,
            )
        else:
            grouping_result = {
                "regrouped_data": [],
                "group_tracking": [],
                "summary": {"total_groups": 0, "faces_processed": 0},
            }

        # Return complete analysis
        frames_processed = len(frames_to_analyze)
        logger.info("Video analysis complete!")

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
            },
            "face_grouping": grouping_result,
            "analysis_parameters": {
                "max_faces_per_frame": max_faces_per_frame,
                "proximity_threshold": proximity_threshold,
                "confidence_threshold": confidence_threshold,
            },
            "pipeline_steps": [
                "✅ Video uploaded and stored permanently",
                f"✅ Processed {frames_processed} strategic frames "
                f"out of {total_frames}",
                f"✅ Detected {total_faces} faces total",
                f"✅ Grouped faces into "
                f"{grouping_result.get('summary', {}).get('total_groups', 0)} "
                f"clusters",
                "✅ Analysis complete",
            ],
            "file_info": {
                "storage_path": video_path,
                "file_size": file_size,
            },
        }

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

        # Step 3: Extract faces using smart frame sampling
        logger.info("Extracting faces from video frames...")
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video file: {tmp_path}")
            # Try to get more info about the error
            logger.error(f"OpenCV backend: {cap.getBackendName()}")
            raise HTTPException(status_code=400, detail="Cannot open video")

        # Get total frame count for smart sampling
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        logger.info(f"Total frames in video: {total_frames}")
        logger.info(f"Video properties - FPS: {fps}, Resolution: {width}x{height}")

        # Test reading the first frame to verify video integrity
        ret, test_frame = cap.read()
        if not ret or test_frame is None:
            logger.error(f"Cannot read first frame from video: {tmp_path}")
            cap.release()
            raise HTTPException(status_code=400, detail="Cannot read video frames")
        logger.info(f"Successfully read first frame: {test_frame.shape}")

        # Reset to beginning
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

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
        logger.info(
            f"Frames to analyze: {frames_to_analyze[:10]}..."
            f"{'(truncated)' if len(frames_to_analyze) > 10 else ''}"
        )

        for frame_number in frames_to_analyze:
            # Seek to specific frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"Could not read frame {frame_number}")
                continue

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
                    all_face_data.append(face_data)
            else:
                logger.debug(f"Frame {frame_number}: No faces detected")

        cap.release()

        # Step 4: Group faces using clustering algorithm
        logger.info(f"Grouping {len(all_face_data)} detected faces...")
        if all_face_data:
            # Create DataFrame for grouping
            df = pd.DataFrame([face.dict() for face in all_face_data])

            # Apply advanced grouping
            grouping_result = face_grouping_engine.apply_advanced_grouping(
                df,
                max_faces_per_frame=max_faces_per_frame,
                proximity_threshold=proximity_threshold,
            )
        else:
            grouping_result = {
                "regrouped_data": [],
                "group_tracking": [],
                "summary": {"total_groups": 0, "faces_processed": 0},
            }

        # Cleanup temp file
        import os

        os.unlink(tmp_path)

        # Step 5: Return complete analysis
        frames_processed = len(frames_to_analyze)
        logger.info("Video analysis complete!")

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
            },
            "face_grouping": grouping_result,
            "analysis_parameters": {
                "max_faces_per_frame": max_faces_per_frame,
                "proximity_threshold": proximity_threshold,
                "confidence_threshold": confidence_threshold,
            },
            "pipeline_steps": [
                "✅ Video uploaded and validated",
                f"✅ Processed {frames_processed} strategic frames "
                f"out of {total_frames}",
                f"✅ Detected {total_faces} faces total",
                f"✅ Grouped faces into "
                f"{grouping_result.get('summary', {}).get('total_groups', 0)} "
                f"clusters",
                "✅ Analysis complete",
            ],
        }

    except Exception as e:
        logger.error(f"Error in complete video analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def analytics_info():
    return {
        "service": "Face Analytics Engine",
        "version": "1.0.0",
        "capabilities": ["advanced_face_grouping", "trajectory_analysis"],
    }


@router.post("/group-faces")
async def group_faces(request: GroupingRequest):
    """Group faces using clustering algorithms."""
    try:
        engine = face_grouping_engine
        df = pd.DataFrame([face.dict() for face in request.face_data])

        # Group faces using clustering
        result = engine.apply_advanced_grouping(
            df, max_faces_per_frame=10, proximity_threshold=50
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Error in face grouping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo-data")
async def get_demo_data():
    demo_data = [
        {"Frame_Number": 1, "Face_ID": "A", "Position_X": 100, "Position_Y": 200},
        {"Frame_Number": 1, "Face_ID": "B", "Position_X": 300, "Position_Y": 180},
        {"Frame_Number": 2, "Face_ID": "A", "Position_X": 110, "Position_Y": 210},
        {"Frame_Number": 2, "Face_ID": "B", "Position_X": 290, "Position_Y": 190},
        {"Frame_Number": 3, "Face_ID": "C", "Position_X": 105, "Position_Y": 205},
        {"Frame_Number": 3, "Face_ID": "D", "Position_X": 295, "Position_Y": 185},
    ]
    return {
        "description": "Sample face detection data for testing",
        "data": demo_data,
        "usage": "Use this data to test the grouping endpoints",
    }


@router.post("/analyze-coordinates")
async def analyze_coordinates(face_data: List[FaceDetectionData]):
    """Analyze face detection coordinates and provide insights."""
    try:
        df = pd.DataFrame([face.dict() for face in face_data])

        analysis = {
            "total_detections": len(df),
            "unique_faces": df["Face_ID"].nunique(),
            "frame_range": {
                "min": int(df["Frame_Number"].min()),
                "max": int(df["Frame_Number"].max()),
                "total_frames": int(df["Frame_Number"].nunique()),
            },
            "position_stats": {
                "x_range": {
                    "min": float(df["Position_X"].min()),
                    "max": float(df["Position_X"].max()),
                    "mean": float(df["Position_X"].mean()),
                },
                "y_range": {
                    "min": float(df["Position_Y"].min()),
                    "max": float(df["Position_Y"].max()),
                    "mean": float(df["Position_Y"].mean()),
                },
            },
            "faces_per_frame": df.groupby("Frame_Number")["Face_ID"]
            .nunique()
            .to_dict(),
        }

        return JSONResponse(content=analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
