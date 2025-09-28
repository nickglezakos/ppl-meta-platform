"""
PPL Meta Vision Service - Phase 4: Enhanced Face Data Manager
Enhanced face data management for quality analysis and face crop storage.

This module provides internal functionality for:
- Storing face detections with optional pre-computed face crops
- Managing face crop data for quality analysis
- Internal quality score calculation without external dependencies
- Database optimization for person objects workflow
"""

import asyncio
import base64
import io
import logging

# Import VisionDatabase from parent directory - fix for circular import
import os

# Import VisionDatabase from parent module
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import psycopg2.extras

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database import VisionDatabase

logger = logging.getLogger(__name__)


class FaceDataManager:
    """
    Enhanced face data management for quality analysis.

    This manager provides internal Vision Service functionality for storing
    and retrieving face detection data with quality analysis capabilities,
    eliminating the need for external frame extraction in person objects workflows.
    """

    def __init__(self, database: VisionDatabase):
        self.db = database
        self.quality_weights = {
            "sharpness": 0.4,
            "exposure": 0.3,
            "contrast": 0.2,
            "noise": 0.1,
        }

    async def store_face_detection_with_crop(
        self,
        face_detection_data: Dict,
        face_crop_base64: Optional[str] = None,
        frame_image: Optional[np.ndarray] = None,
    ) -> bool:
        """
        Store face detection with optional pre-computed face crop.

        This allows quality analysis without re-extracting frames from media service.

        Args:
            face_detection_data: Standard face detection record
            face_crop_base64: Optional base64 encoded face crop image
            frame_image: Optional source frame for crop extraction

        Returns:
            bool: Success status
        """
        try:
            # Store main face detection record (existing functionality)
            await self._store_face_detection(face_detection_data)

            # Handle face crop storage if provided
            if face_crop_base64 or frame_image is not None:
                crop_data = face_crop_base64

                # Extract crop from frame if needed
                if not crop_data and frame_image is not None:
                    crop_data = await self._extract_and_encode_face_crop(
                        frame_image, face_detection_data
                    )

                # Store face crop with quality analysis
                if crop_data:
                    await self._store_face_crop_with_quality(
                        face_detection_data["id"], crop_data
                    )

            return True

        except Exception as e:
            logger.error(f"Failed to store face detection with crop: {e}")
            return False

    async def get_face_detection_with_quality_data(
        self, face_id: str
    ) -> Optional[Dict]:
        """
        Retrieve face detection with all data needed for quality analysis.

        Returns bbox coordinates and pre-stored crop if available.
        This eliminates need for external frame extraction in person objects workflow.

        Args:
            face_id: Face detection identifier

        Returns:
            Dict with face detection data and quality information, or None
        """
        try:
            async with self.db.connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cursor:
                query = """
                SELECT 
                    fd.*,
                    fc.crop_base64,
                    fc.pre_computed_quality_score,
                    fc.crop_width,
                    fc.crop_height,
                    fc.created_at as crop_created_at
                FROM face_detections fd
                LEFT JOIN face_crops fc ON fd.id = fc.face_detection_id
                WHERE fd.id = %s
                """

                await cursor.execute(query, (face_id,))
                result = await cursor.fetchone()

                if result:
                    return dict(result)
                return None

        except Exception as e:
            logger.error(f"Failed to get face detection with quality data: {e}")
            return None

    async def get_or_calculate_face_crop(
        self, face_record: Dict
    ) -> Optional[np.ndarray]:
        """
        Get face crop from stored data or calculate from bbox if needed.

        This method provides internal face crop access for quality analysis
        without requiring external media service calls.

        Args:
            face_record: Face detection record with bbox and optional crop data

        Returns:
            numpy.ndarray: Face crop image, or None if unavailable
        """
        try:
            # Try to use pre-stored crop first
            if face_record.get("crop_base64"):
                crop_bytes = base64.b64decode(face_record["crop_base64"])
                crop_array = np.frombuffer(crop_bytes, np.uint8)
                face_crop = cv2.imdecode(crop_array, cv2.IMREAD_COLOR)

                if face_crop is not None and face_crop.size > 0:
                    return face_crop

            # If no stored crop, we cannot extract without frame
            # This is expected for older face detections
            logger.debug(f"No face crop available for face {face_record.get('id')}")
            return None

        except Exception as e:
            logger.error(f"Failed to get face crop for {face_record.get('id')}: {e}")
            return None

    async def calculate_and_store_quality_score(
        self, face_id: str, face_crop: Optional[np.ndarray] = None
    ) -> Optional[float]:
        """
        Calculate quality score using stored bbox data or provided crop.

        This internal method eliminates need for external frame extraction
        by using pre-stored face crop data when available.

        Args:
            face_id: Face detection identifier
            face_crop: Optional pre-computed face crop

        Returns:
            float: Quality score (0.0 to 1.0), or None if unavailable
        """
        try:
            # Get face record if crop not provided
            if face_crop is None:
                face_record = await self.get_face_detection_with_quality_data(face_id)
                if not face_record:
                    return None

                # Use stored quality score if available
                if face_record.get("pre_computed_quality_score") is not None:
                    return face_record["pre_computed_quality_score"]

                # Get face crop
                face_crop = await self.get_or_calculate_face_crop(face_record)
                if face_crop is None:
                    return None

            # Calculate quality score using same algorithm as Phase 2
            quality_score = self._calculate_quality_score_internal(face_crop)

            # Store calculated quality score for future use
            await self._update_face_crop_quality_score(face_id, quality_score)

            return quality_score

        except Exception as e:
            logger.error(f"Failed to calculate quality score for {face_id}: {e}")
            return None

    async def batch_analyze_face_quality(self, face_ids: List[str]) -> Dict[str, float]:
        """
        Batch analyze quality scores for multiple faces.

        Optimized for person objects workflow performance.

        Args:
            face_ids: List of face detection identifiers

        Returns:
            Dict mapping face_id to quality_score
        """
        quality_scores = {}

        try:
            # Get all face records in batch
            async with self.db.connection.cursor(
                cursor_factory=psycopg2.extras.RealDictCursor
            ) as cursor:
                query = """
                SELECT 
                    fd.id,
                    fd.bbox_x1, fd.bbox_y1, fd.bbox_x2, fd.bbox_y2,
                    fc.crop_base64,
                    fc.pre_computed_quality_score
                FROM face_detections fd
                LEFT JOIN face_crops fc ON fd.id = fc.face_detection_id
                WHERE fd.id = ANY(%s)
                """

                await cursor.execute(query, (face_ids,))
                results = await cursor.fetchall()

                # Process each face
                for face_record in results:
                    face_id = face_record["id"]

                    # Use pre-computed score if available
                    if face_record["pre_computed_quality_score"] is not None:
                        quality_scores[face_id] = face_record[
                            "pre_computed_quality_score"
                        ]
                        continue

                    # Calculate quality if crop is available
                    face_crop = await self.get_or_calculate_face_crop(dict(face_record))
                    if face_crop is not None:
                        quality_score = self._calculate_quality_score_internal(
                            face_crop
                        )
                        quality_scores[face_id] = quality_score

                        # Store for future use
                        await self._update_face_crop_quality_score(
                            face_id, quality_score
                        )
                    else:
                        # Default quality score if no crop available
                        quality_scores[face_id] = 0.5

                return quality_scores

        except Exception as e:
            logger.error(f"Failed to batch analyze face quality: {e}")
            return quality_scores

    def _calculate_quality_score_internal(self, face_crop: np.ndarray) -> float:
        """
        Internal quality score calculation using same algorithm as Phase 2.

        Matches VisionFaceGroupingEngine.calculate_quality_score exactly.
        """
        try:
            if face_crop.size == 0:
                return 0.0

            # Convert to grayscale if needed
            if len(face_crop.shape) == 3:
                gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            else:
                gray = face_crop

            # Sharpness calculation (Laplacian variance)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            normalized_sharpness = min(sharpness / 1000.0, 1.0)

            # Exposure calculation (histogram analysis)
            mean_intensity = np.mean(gray)
            exposure_score = 1.0 / (1.0 + abs(mean_intensity - 128) / 128)

            # Contrast calculation (dynamic range)
            contrast = gray.max() - gray.min()
            normalized_contrast = contrast / 255.0

            # Noise calculation (inverted standard deviation)
            noise_level = np.std(gray)
            noise_score = max(0, 1.0 - (noise_level / 128.0))

            # Weighted combination
            quality_score = (
                self.quality_weights["sharpness"] * normalized_sharpness
                + self.quality_weights["exposure"] * exposure_score
                + self.quality_weights["contrast"] * normalized_contrast
                + self.quality_weights["noise"] * noise_score
            )

            return min(max(quality_score, 0.0), 1.0)

        except Exception as e:
            logger.error(f"Internal quality calculation failed: {e}")
            return 0.0

    async def _extract_and_encode_face_crop(
        self, frame_image: np.ndarray, face_detection_data: Dict
    ) -> Optional[str]:
        """
        Extract face crop from frame and encode as base64.

        Args:
            frame_image: Source frame image
            face_detection_data: Face detection with bbox coordinates

        Returns:
            str: Base64 encoded face crop, or None if extraction fails
        """
        try:
            x1 = int(face_detection_data["bbox_x1"])
            y1 = int(face_detection_data["bbox_y1"])
            x2 = int(face_detection_data["bbox_x2"])
            y2 = int(face_detection_data["bbox_y2"])

            # Validate bbox coordinates
            h, w = frame_image.shape[:2]
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(x1 + 1, min(x2, w))
            y2 = max(y1 + 1, min(y2, h))

            # Extract face crop
            face_crop = frame_image[y1:y2, x1:x2]

            if face_crop.size == 0:
                return None

            # Encode as base64
            _, buffer = cv2.imencode(".jpg", face_crop, [cv2.IMWRITE_JPEG_QUALITY, 85])
            crop_base64 = base64.b64encode(buffer).decode("utf-8")

            return crop_base64

        except Exception as e:
            logger.error(f"Failed to extract and encode face crop: {e}")
            return None

    async def _store_face_detection(self, face_detection_data: Dict) -> bool:
        """Store standard face detection record."""
        # This would integrate with existing face detection storage
        # Implementation depends on current database schema
        pass

    async def _store_face_crop_with_quality(
        self, face_id: str, crop_base64: str
    ) -> bool:
        """
        Store face crop with pre-computed quality analysis.

        Args:
            face_id: Face detection identifier
            crop_base64: Base64 encoded face crop

        Returns:
            bool: Success status
        """
        try:
            # Decode crop to calculate quality
            crop_bytes = base64.b64decode(crop_base64)
            crop_array = np.frombuffer(crop_bytes, np.uint8)
            face_crop = cv2.imdecode(crop_array, cv2.IMREAD_COLOR)

            # Calculate quality score
            quality_score = None
            crop_width = None
            crop_height = None

            if face_crop is not None and face_crop.size > 0:
                quality_score = self._calculate_quality_score_internal(face_crop)
                crop_height, crop_width = face_crop.shape[:2]

            # Store in face_crops table
            async with self.db.connection.cursor() as cursor:
                insert_query = """
                INSERT INTO face_crops (
                    face_detection_id, crop_base64, pre_computed_quality_score,
                    crop_width, crop_height, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (face_detection_id) DO UPDATE SET
                    crop_base64 = EXCLUDED.crop_base64,
                    pre_computed_quality_score = EXCLUDED.pre_computed_quality_score,
                    crop_width = EXCLUDED.crop_width,
                    crop_height = EXCLUDED.crop_height,
                    created_at = EXCLUDED.created_at
                """

                await cursor.execute(
                    insert_query,
                    (
                        face_id,
                        crop_base64,
                        quality_score,
                        crop_width,
                        crop_height,
                        datetime.now(),
                    ),
                )

                await self.db.connection.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to store face crop with quality: {e}")
            await self.db.connection.rollback()
            return False

    async def _update_face_crop_quality_score(
        self, face_id: str, quality_score: float
    ) -> bool:
        """
        Update pre-computed quality score for face crop.

        Args:
            face_id: Face detection identifier
            quality_score: Calculated quality score

        Returns:
            bool: Success status
        """
        try:
            async with self.db.connection.cursor() as cursor:
                update_query = """
                UPDATE face_crops 
                SET pre_computed_quality_score = %s
                WHERE face_detection_id = %s
                """

                await cursor.execute(update_query, (quality_score, face_id))
                await self.db.connection.commit()
                return True

        except Exception as e:
            logger.error(f"Failed to update face crop quality score: {e}")
            await self.db.connection.rollback()
            return False


async def initialize_face_crops_table(database: VisionDatabase) -> bool:
    """
    Initialize face_crops table for Phase 4 enhancement.

    This table supports quality analysis without external frame extraction.

    Args:
        database: Vision database instance

    Returns:
        bool: Success status
    """
    try:
        async with database.connection.cursor() as cursor:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS face_crops (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                face_detection_id TEXT NOT NULL UNIQUE,
                crop_base64 TEXT,
                pre_computed_quality_score REAL,
                crop_width INTEGER,
                crop_height INTEGER,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (face_detection_id) REFERENCES face_detections(id)
            );
            
            -- Create indexes for performance
            CREATE INDEX IF NOT EXISTS idx_face_crops_face_detection_id 
                ON face_crops(face_detection_id);
            CREATE INDEX IF NOT EXISTS idx_face_crops_quality_score 
                ON face_crops(pre_computed_quality_score DESC);
            """

            await cursor.execute(create_table_query)
            await database.connection.commit()

            logger.info("✅ Face crops table initialized for Phase 4")
            return True

    except Exception as e:
        logger.error(f"Failed to initialize face crops table: {e}")
        await database.connection.rollback()
        return False


# Export for Phase 4 integration
__all__ = ["FaceDataManager", "initialize_face_crops_table"]
