"""
Orchestrator Client

HTTP client for communicating with Orchestrator service to fetch person objects
and appearance data.

Author: PPL Meta Platform
Date: October 31, 2025
Version: 1.0.0
"""

import logging
import httpx
from typing import Optional, List, Dict
from uuid import UUID

logger = logging.getLogger(__name__)

# Orchestrator service configuration
ORCHESTRATOR_BASE_URL = "http://localhost:8002"  # TODO: Load from env
ORCHESTRATOR_TIMEOUT = 30.0  # seconds


class OrchestratorClient:
    """
    HTTP client for Orchestrator service.
    
    **Service Architecture:**
    vmeta service → Orchestrator service → Person Objects / Appearances
    """
    
    def __init__(
        self,
        base_url: str = ORCHESTRATOR_BASE_URL,
        timeout: float = ORCHESTRATOR_TIMEOUT
    ):
        """
        Initialize Orchestrator client.
        
        Args:
            base_url: Orchestrator service base URL
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
        )
        logger.info(f"OrchestratorClient initialized: {self.base_url}")
    
    async def get_person_objects_for_individual(
        self,
        individual_uuid: UUID
    ) -> List[Dict]:
        """
        Get all person objects linked to an Individual.
        
        **Endpoint:** GET /api/v1/individuals/{uuid}/person-objects
        
        Args:
            individual_uuid: Individual UUID
            
        Returns:
            List[Dict]: Person objects with appearance data
        """
        try:
            response = await self.client.get(
                f"/api/v1/individuals/{individual_uuid}/person-objects"
            )
            response.raise_for_status()
            
            data = response.json()
            person_objects = data.get('person_objects', [])
            
            logger.info(
                f"Retrieved {len(person_objects)} person objects "
                f"for Individual {individual_uuid}"
            )
            return person_objects
        
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error getting person objects for {individual_uuid}: "
                f"{e.response.status_code}"
            )
            return []
        except Exception as e:
            logger.error(
                f"Error getting person objects for {individual_uuid}: {e}"
            )
            return []
    
    async def get_person_object_appearances(
        self,
        person_object_uuid: UUID
    ) -> List[Dict]:
        """
        Get all appearances for a person object.
        
        **Endpoint:** GET /api/v1/person-objects/{uuid}/appearances
        
        Args:
            person_object_uuid: Person object UUID
            
        Returns:
            List[Dict]: Appearances with face crops and quality scores
        """
        try:
            response = await self.client.get(
                f"/api/v1/person-objects/{person_object_uuid}/appearances"
            )
            response.raise_for_status()
            
            data = response.json()
            appearances = data.get('appearances', [])
            
            logger.debug(
                f"Retrieved {len(appearances)} appearances "
                f"for person object {person_object_uuid}"
            )
            return appearances
        
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error getting appearances for {person_object_uuid}: "
                f"{e.response.status_code}"
            )
            return []
        except Exception as e:
            logger.error(
                f"Error getting appearances for {person_object_uuid}: {e}"
            )
            return []
    
    async def get_best_face_crop_for_individual(
        self,
        individual_uuid: UUID
    ) -> Optional[Dict]:
        """
        Get the best quality face crop for an Individual.
        
        **Process:**
        1. Get all person objects for Individual
        2. Get all appearances for each person object
        3. Find appearance with highest quality score
        4. Return face crop data
        
        Args:
            individual_uuid: Individual UUID
            
        Returns:
            Optional[Dict]: Best face crop with quality score, or None
        """
        try:
            # Get person objects
            person_objects = await self.get_person_objects_for_individual(
                individual_uuid
            )
            
            if not person_objects:
                logger.warning(
                    f"No person objects found for Individual {individual_uuid}"
                )
                return None
            
            # Collect all appearances with quality scores
            all_appearances = []
            for person_obj in person_objects:
                person_uuid = person_obj.get('person_object_uuid')
                if not person_uuid:
                    continue
                
                appearances = await self.get_person_object_appearances(
                    person_uuid
                )
                all_appearances.extend(appearances)
            
            if not all_appearances:
                logger.warning(
                    f"No appearances found for Individual {individual_uuid}"
                )
                return None
            
            # Find best quality appearance
            best_appearance = max(
                all_appearances,
                key=lambda x: x.get('quality_score', 0.0)
            )
            
            logger.info(
                f"Found best face crop for Individual {individual_uuid} "
                f"(quality: {best_appearance.get('quality_score')})"
            )
            
            return {
                'face_crop': best_appearance.get('face_crop'),
                'face_crop_path': best_appearance.get('face_crop_path'),
                'quality_score': best_appearance.get('quality_score'),
                'appearance_uuid': best_appearance.get('appearance_uuid'),
                'person_object_uuid': best_appearance.get(
                    'person_object_uuid'
                ),
            }
        
        except Exception as e:
            logger.error(
                f"Error getting best face crop for {individual_uuid}: {e}"
            )
            return None
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# ============================================================================
# Singleton Instance
# ============================================================================

_orchestrator_client: Optional[OrchestratorClient] = None


def get_orchestrator_client() -> OrchestratorClient:
    """
    Get singleton Orchestrator client instance.
    
    **Singleton Pattern:** Reuse HTTP client across requests
    
    Returns:
        OrchestratorClient: Shared client instance
    """
    global _orchestrator_client
    
    if _orchestrator_client is None:
        _orchestrator_client = OrchestratorClient()
    
    return _orchestrator_client


async def close_orchestrator_client():
    """Close Orchestrator client (for cleanup on shutdown)."""
    global _orchestrator_client
    
    if _orchestrator_client is not None:
        await _orchestrator_client.close()
        _orchestrator_client = None


# ============================================================================
# Export
# ============================================================================

__all__ = [
    "OrchestratorClient",
    "get_orchestrator_client",
    "close_orchestrator_client",
]
