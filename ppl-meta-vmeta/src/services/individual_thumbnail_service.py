"""
Individual Thumbnail Service
Generates and manages thumbnails for individuals.
"""

import base64
import io
import logging
from typing import Optional, Tuple

import httpx
from PIL import Image

logger = logging.getLogger(__name__)


class IndividualThumbnailService:
    """
    Manages thumbnail generation and retrieval for individuals.
    
    This service:
    - Generates thumbnails from best quality frames
    - Stores thumbnail URLs
    - Provides fallback placeholders
    - Handles thumbnail optimization
    """
    
    def __init__(
        self,
        db_client,
        media_service_url: str = "http://localhost:8000",
        orchestrator_service_url: str = "http://localhost:8002",
        thumbnail_sizes: dict = None,
    ):
        """
        Initialize the thumbnail service.
        
        Args:
            db_client: VmetaDatabaseClient instance
            media_service_url: URL of the media service
            orchestrator_service_url: URL of the orchestrator service
            thumbnail_sizes: Dict of size presets (small, medium, large)
        """
        self.db = db_client
        self.media_service_url = media_service_url
        self.orchestrator_service_url = orchestrator_service_url
        self.thumbnail_sizes = thumbnail_sizes or {
            "small": (128, 128),
            "medium": (256, 256),
            "large": (512, 512),
        }
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("IndividualThumbnailService initialized")
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()
    
    async def generate_thumbnail(
        self, individual_id: str, size: str = "medium"
    ) -> Optional[str]:
        """
        Generate a thumbnail for an individual from their best quality frame.
        
        Args:
            individual_id: Individual identifier
            size: Thumbnail size preset (small, medium, large)
            
        Returns:
            Base64-encoded thumbnail image data or None if generation fails
        """
        logger.info(f"Generating {size} thumbnail for individual {individual_id}")
        
        try:
            # Get best quality frame for this individual
            best_frame_result = await self._get_best_quality_frame(individual_id)
            
            if not best_frame_result:
                logger.warning(f"No frame data found for individual {individual_id}")
                return None
            
            best_frame_data_bytes = best_frame_result["frame_data"]
            best_frame_metadata = {
                "video_uuid": best_frame_result["video_uuid"],
                "frame_number": best_frame_result["frame_number"],
                "quality": best_frame_result["quality"]
            }
            
            # Resize image to thumbnail size
            thumbnail = self._resize_image(
                best_frame_data_bytes, self.thumbnail_sizes.get(size, (256, 256))
            )
            
            # Convert to base64
            thumbnail_base64 = self._image_to_base64(thumbnail)
            
            # Store thumbnail in database with metadata
            await self._store_thumbnail_url(
                individual_id, 
                thumbnail_base64,
                size=size,
                source_video=best_frame_metadata.get("video_uuid"),
                source_frame=best_frame_metadata.get("frame_number"),
                quality_score=best_frame_metadata.get("quality", 0.0)
            )
            
            logger.info(f"Thumbnail generated successfully for {individual_id}")
            return thumbnail_base64
            
        except Exception as e:
            logger.error(f"Error generating thumbnail for {individual_id}: {e}")
            return None
    
    async def get_thumbnail_url(self, individual_id: str, size: str = "medium") -> Optional[str]:
        """
        Get the thumbnail URL for an individual.
        
        Args:
            individual_id: Individual identifier
            size: Thumbnail size (small, medium, large)
            
        Returns:
            Thumbnail data URL or None if not available
        """
        try:
            # Query database for cached thumbnail
            query = """
            SELECT thumbnail_data, generated_at, quality_score
            FROM individual_thumbnails
            WHERE individual_uuid = $1 AND size = $2
            """
            
            async with self.db.pool.acquire() as conn:
                row = await conn.fetchrow(query, individual_id, size)
            
            if row:
                logger.debug(
                    f"Retrieved cached {size} thumbnail for {individual_id} "
                    f"(quality={row['quality_score']:.2f})"
                )
                return row["thumbnail_data"]
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving thumbnail URL for {individual_id}: {e}")
            return None
    
    async def get_thumbnail_data(
        self, individual_id: str, size: str = "medium"
    ) -> Optional[bytes]:
        """
        Get thumbnail image data for an individual.
        
        Args:
            individual_id: Individual identifier
            size: Thumbnail size preset
            
        Returns:
            Thumbnail image bytes or None
        """
        # Check if thumbnail exists
        thumbnail_url = await self.get_thumbnail_url(individual_id)
        
        if thumbnail_url:
            # Decode base64 if stored as base64
            if thumbnail_url.startswith("data:image"):
                # Extract base64 data
                base64_data = thumbnail_url.split(",")[1]
                return base64.b64decode(base64_data)
            return thumbnail_url.encode()
        
        # Generate new thumbnail if not exists
        thumbnail_base64 = await self.generate_thumbnail(individual_id, size=size)
        
        if thumbnail_base64:
            if thumbnail_base64.startswith("data:image"):
                base64_data = thumbnail_base64.split(",")[1]
                return base64.b64decode(base64_data)
            return base64.b64decode(thumbnail_base64)
        
        return None
    
    async def update_thumbnail(
        self, individual_id: str, image_data: bytes
    ) -> Optional[str]:
        """
        Update thumbnail with custom image data.
        
        Args:
            individual_id: Individual identifier
            image_data: Raw image bytes
            
        Returns:
            Base64-encoded thumbnail or None on failure
        """
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Resize to medium size
            thumbnail = self._resize_image(image, self.thumbnail_sizes["medium"])
            
            # Convert to base64
            thumbnail_base64 = self._image_to_base64(thumbnail)
            
            # Store in database (custom upload, no source video/frame)
            await self._store_thumbnail_url(
                individual_id, 
                thumbnail_base64,
                size="medium",
                source_video=None,
                source_frame=None,
                quality_score=1.0  # Custom uploads considered high quality
            )
            
            logger.info(f"Thumbnail updated for individual {individual_id}")
            return thumbnail_base64
            
        except Exception as e:
            logger.error(f"Error updating thumbnail for {individual_id}: {e}")
            return None
    
    async def _get_best_quality_frame(self, individual_id: str) -> Optional[dict]:
        """
        Get the best quality frame for an individual.
        
        This queries the individual's video appearances and fetches the best 
        representative face from the Orchestrator service.
        
        Args:
            individual_id: Individual identifier (UUID)
            
        Returns:
            Dict with keys: frame_data (bytes), video_uuid, frame_number, quality
            or None if no frame found
        """
        try:
            logger.debug(f"Fetching best frame for individual {individual_id}")
            
            # Query for videos where this individual appears
            query = """
            SELECT 
                video_uuid,
                confidence
            FROM individual_video_appearances
            WHERE individual_uuid = $1
                AND confidence >= 0.5
            ORDER BY confidence DESC
            LIMIT 5
            """
            
            async with self.db.pool.acquire() as conn:
                rows = await conn.fetch(query, individual_id)
            
            if not rows:
                logger.warning(
                    f"No video appearances found for individual {individual_id}"
                )
                return None
            
            # Try each video to find the best frame
            best_frame = None
            best_score = 0.0
            
            for row in rows:
                video_uuid = str(row["video_uuid"])
                
                try:
                    # Fetch person objects from Orchestrator
                    response = await self.http_client.get(
                        f"{self.orchestrator_service_url}/api/v1/orchestrator/"
                        f"person-objects/{video_uuid}",
                        headers={"Authorization": "Bearer system_token"}
                    )
                    
                    if response.status_code != 200:
                        logger.warning(
                            f"Orchestrator returned {response.status_code} for video {video_uuid}"
                        )
                        continue
                    
                    data = response.json()
                    
                    if not data.get("success") or not data.get("person_groups"):
                        continue
                    
                    # Find this individual in the person groups
                    for person_group in data["person_groups"]:
                        rep_faces = person_group.get("representative_faces", [])
                        
                        if not rep_faces:
                            continue
                        
                        # Get the best quality face (rank 1)
                        for face in rep_faces:
                            face_data = face.get("face_data", {})
                            quality = face.get("quality_score", 0.0)
                            frame_num = face_data.get("frame_number")
                            
                            if frame_num is not None and quality > best_score:
                                best_score = quality
                                best_frame = {
                                    "video_uuid": video_uuid,
                                    "frame_number": frame_num,
                                    "quality": quality
                                }
                                break  # Take first (best ranked) face
                        
                        if best_frame:
                            break  # Found a good frame
                    
                except Exception as e:
                    logger.error(
                        f"Error fetching person objects for video {video_uuid}: {e}"
                    )
                    continue
                
                # Stop if we found a high-quality frame
                if best_frame and best_score > 50.0:
                    break
            
            if not best_frame:
                logger.warning(
                    f"No valid frames found for individual {individual_id}"
                )
                return None
            
            logger.info(
                f"Best frame for {individual_id}: video={best_frame['video_uuid']}, "
                f"frame={best_frame['frame_number']}, quality={best_frame['quality']:.2f}"
            )
            
            # Fetch frame from Media service
            try:
                response = await self.http_client.get(
                    f"{self.media_service_url}/api/v1/media/"
                    f"{best_frame['video_uuid']}/frame/{best_frame['frame_number']}",
                    params={"format": "jpeg", "quality": 90, "size": "medium"},
                    headers={"Authorization": "Bearer system_token"}
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully fetched frame for individual {individual_id}")
                    return {
                        "frame_data": response.content,
                        "video_uuid": best_frame["video_uuid"],
                        "frame_number": best_frame["frame_number"],
                        "quality": best_frame["quality"]
                    }
                else:
                    logger.error(
                        f"Media service returned {response.status_code} for "
                        f"individual {individual_id}"
                    )
                    return None
                    
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error fetching frame for {individual_id}: {e.response.status_code}"
                )
                return None
            
        except Exception as e:
            logger.error(f"Error fetching best frame for {individual_id}: {e}")
            return None
    
    def _resize_image(self, image_data, target_size: Tuple[int, int]) -> Image.Image:
        """
        Resize image to target size while maintaining aspect ratio.
        
        Args:
            image_data: PIL Image or bytes
            target_size: (width, height) tuple
            
        Returns:
            Resized PIL Image
        """
        if isinstance(image_data, bytes):
            image = Image.open(io.BytesIO(image_data))
        else:
            image = image_data
        
        # Convert to RGB if necessary
        if image.mode != "RGB":
            image = image.convert("RGB")
        
        # Calculate aspect ratio
        aspect = image.width / image.height
        target_aspect = target_size[0] / target_size[1]
        
        if aspect > target_aspect:
            # Image is wider, fit to width
            new_width = target_size[0]
            new_height = int(new_width / aspect)
        else:
            # Image is taller, fit to height
            new_height = target_size[1]
            new_width = int(new_height * aspect)
        
        # Resize with high-quality resampling
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Create thumbnail with padding if needed
        thumbnail = Image.new("RGB", target_size, (240, 240, 240))  # Light gray background
        paste_x = (target_size[0] - new_width) // 2
        paste_y = (target_size[1] - new_height) // 2
        thumbnail.paste(resized, (paste_x, paste_y))
        
        return thumbnail
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """
        Convert PIL Image to base64 data URL.
        
        Args:
            image: PIL Image
            
        Returns:
            Base64-encoded data URL string
        """
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85, optimize=True)
        img_bytes = buffer.getvalue()
        img_base64 = base64.b64encode(img_bytes).decode()
        return f"data:image/jpeg;base64,{img_base64}"
    
    async def _store_thumbnail_url(
        self, 
        individual_id: str, 
        thumbnail_url: str,
        size: str = "medium",
        source_video: Optional[str] = None,
        source_frame: Optional[int] = None,
        quality_score: Optional[float] = None
    ):
        """
        Store thumbnail URL in database.
        
        Args:
            individual_id: Individual identifier
            thumbnail_url: Base64 data URL or external URL
            size: Thumbnail size (small, medium, large)
            source_video: UUID of source video
            source_frame: Frame number in source video
            quality_score: Quality score of source frame
        """
        try:
            query = """
            INSERT INTO individual_thumbnails (
                individual_uuid, size, thumbnail_data,
                source_video_uuid, source_frame_number, quality_score
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (individual_uuid, size)
            DO UPDATE SET
                thumbnail_data = EXCLUDED.thumbnail_data,
                source_video_uuid = EXCLUDED.source_video_uuid,
                source_frame_number = EXCLUDED.source_frame_number,
                quality_score = EXCLUDED.quality_score,
                generated_at = NOW()
            """
            
            async with self.db.pool.acquire() as conn:
                await conn.execute(
                    query,
                    individual_id,
                    size,
                    thumbnail_url,
                    source_video,
                    source_frame,
                    quality_score
                )
            
            logger.debug(
                f"Stored {size} thumbnail for individual {individual_id} "
                f"(quality={quality_score:.2f if quality_score else 0:.2f})"
            )
            
        except Exception as e:
            logger.error(f"Error storing thumbnail for {individual_id}: {e}")
    
    def generate_fallback_placeholder(
        self, size: str = "medium", color: str = "#4A90E2"
    ) -> str:
        """
        Generate a fallback placeholder image.
        
        Args:
            size: Size preset (small, medium, large)
            color: Hex color code for gradient
            
        Returns:
            Base64-encoded placeholder image
        """
        target_size = self.thumbnail_sizes.get(size, (256, 256))
        
        # Create gradient image
        image = Image.new("RGB", target_size, color)
        
        # TODO: Add person icon overlay
        # This would use PIL ImageDraw to draw a person icon
        
        return self._image_to_base64(image)
