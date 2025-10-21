"""
Analytics API endpoints for PPL Meta Mini.
Enhanced with graceful cancellation support.
"""

import asyncio
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
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, Request
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


@router.post("/upload-and-analyze")
async def upload_and_analyze_video(
    request: Request,
    file: UploadFile = File(...),
    max_faces_per_frame: int = 10,
    proximity_threshold: float = 50.0,
    confidence_threshold: float = Query(
        0.5, description="Face detection confidence threshold"
    ),
    frame_interval: int = Query(15, description="Frame sampling interval"),
):
    """
    Upload video file first, then analyze from stored location with graceful cancellation support.
    This follows the Media service pattern to test if temporary file
    handling is causing issues.
    
    Args:
        request: FastAPI Request object for cancellation detection
        file: Uploaded video file
        max_faces_per_frame: Maximum faces to detect per frame
        proximity_threshold: Face proximity threshold for grouping
        confidence_threshold: Face detection confidence threshold
        frame_interval: Frame sampling interval
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    if not file.filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
        raise HTTPException(
            status_code=400, detail="Invalid file type. Supported: mp4, avi, mov, mkv"
        )

    try:
        # Check if client disconnected before starting
        if await request.is_disconnected():
            logger.info("⚠️ Client disconnected before video analysis started")
            return {"status": "cancelled", "message": "Request was cancelled by client"}
        
        logger.info("Upload-and-analyze for: %s", file.filename)
        logger.info("File content type: %s", file.content_type)
        logger.info("File size: %s", file.size)

        # Step 0: Cleanup old files - keep only the last 3 files in both directories
        def cleanup_old_files(directory_path, keep_count=3):
            """
            Remove old files keeping only the most recent ones based on timestamp prefix.
            """
            if not os.path.exists(directory_path):
                return

            try:
                # Get all files in the directory
                files = []
                for filename in os.listdir(directory_path):
                    filepath = os.path.join(directory_path, filename)
                    if os.path.isfile(filepath):
                        # Extract timestamp from filename (first part before underscore)
                        try:
                            if "_" in filename:
                                timestamp_str = filename.split("_")[0]
                                # Handle preprocessed files (remove 'preprocessed_' prefix)
                                if filename.startswith("preprocessed_"):
                                    timestamp_str = filename.replace(
                                        "preprocessed_", ""
                                    ).split("_")[0]
                                timestamp = int(timestamp_str)
                                files.append((timestamp, filepath, filename))
                        except (ValueError, IndexError):
                            # Skip files that don't have valid timestamp format
                            continue

                # Sort by timestamp (newest first) and keep only the most recent ones
                files.sort(key=lambda x: x[0], reverse=True)
                files_to_delete = files[keep_count:]

                # Delete old files
                for timestamp, filepath, filename in files_to_delete:
                    try:
                        os.remove(filepath)
                        logger.info(f"🗑️ Cleaned up old file: {filename}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {filename}: {e}")

                if files_to_delete:
                    logger.info(
                        f"✅ Cleanup complete: Removed {len(files_to_delete)} old files from {directory_path}"
                    )

            except Exception as e:
                logger.warning(f"Cleanup failed for {directory_path}: {e}")

        # Cleanup storage directories
        storage_dir = "/tmp/ppl-mini-storage"
        preprocessor_temp_dir = video_preprocessor.temp_dir

        logger.info("🧹 Starting cleanup of old video files...")
        cleanup_old_files(storage_dir, keep_count=3)
        cleanup_old_files(str(preprocessor_temp_dir), keep_count=3)

        # Step 1: Save to a permanent location (like Media service)
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

        # Step 3: Now analyze from the final video path with cancellation support
        return await analyze_video_from_path(
            final_video_path,
            max_faces_per_frame,
            proximity_threshold,
            confidence_threshold,
            frame_interval,
            request=request,
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
    request: Request = None,
):
    """
    Analyze video from file path - this is the core analysis function.
    Enhanced with graceful cancellation support when request is provided.
    
    Args:
        video_path: Path to the video file
        max_faces_per_frame: Maximum faces to detect per frame
        proximity_threshold: Face proximity threshold for grouping
        confidence_threshold: Face detection confidence threshold
        frame_interval: Frame sampling interval
        request: Optional FastAPI Request object for cancellation detection
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
            # Check for client disconnection during frame processing (if request provided)
            if request and await request.is_disconnected():
                logger.info("⚠️ Client disconnected during frame processing, stopping analysis...")
                cap.release()
                return {
                    "status": "cancelled", 
                    "message": "Request was cancelled during video analysis"
                }
            
            logger.debug("Processing frame %d", frame_number)

            # Set frame position
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()

            if not ret:
                logger.warning("Could not read frame %d", frame_number)
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
