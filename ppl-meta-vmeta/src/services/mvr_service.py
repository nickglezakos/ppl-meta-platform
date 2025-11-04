"""
MVR-People Service Layer
PPL Meta Platform - vmeta service

Main service for MVR-People operations including creation, matching, and merging.

Created: October 31, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
import numpy as np

from database.mvr_repository import MVRRepository, MVRRepositoryError
from ml.mvr_processor import MVRProcessor
from services.quality_selector import (
    select_best_quality_object,
    calculate_quality_score
)

logger = logging.getLogger(__name__)


class MVRServiceError(Exception):
    """Custom exception for MVR service operations."""
    pass


class MVRService:
    """
    MVR-People Service.
    
    Coordinates MVR-People creation, matching, merging, and search.
    """
    
    def __init__(
        self,
        repository: MVRRepository,
        ml_processor: MVRProcessor,
        orchestrator_client: Optional[Any] = None
    ):
        """
        Initialize MVR service.
        
        Args:
            repository: MVR database repository
            ml_processor: ML processor for embeddings/demographics
            orchestrator_client: Client for fetching person objects
        """
        self.repository = repository
        self.ml_processor = ml_processor
        self.orchestrator_client = orchestrator_client
        logger.info("MVRService initialized")
    
    # ===================================================================
    # MVR-People Creation
    # ===================================================================
    
    async def create_mvr_people_from_individual(
        self,
        individual_uuid: UUID,
        person_objects: Optional[List[Dict[str, Any]]] = None,
        auto_created: bool = True
    ) -> Dict[str, Any]:
        """
        Create MVR-People from Individual (automatic 1:1 creation).
        
        Args:
            individual_uuid: Individual UUID
            person_objects: List of person objects (fetched if not provided)
            auto_created: True if auto-created on Individual insert
            
        Returns:
            Dict with mvr_people_uuid and processing results
        """
        try:
            logger.info(
                f"Creating MVR-People for Individual {individual_uuid}"
            )
            
            # Fetch person objects if not provided
            if not person_objects:
                if not self.orchestrator_client:
                    raise MVRServiceError(
                        "Orchestrator client required to fetch person objects"
                    )
                
                person_objects = (
                    await self._fetch_person_objects_for_individual(
                        individual_uuid
                    )
                )
            
            if not person_objects:
                raise MVRServiceError(
                    f"No person objects found for Individual {individual_uuid}"
                )
            
            # Select best quality person object
            best_person = select_best_quality_object(person_objects)
            
            if not best_person:
                raise MVRServiceError("Failed to select best person object")
            
            logger.info(
                f"Selected best person object: "
                f"{best_person.get('person_object_uuid')}"
            )
            
            # Process through ML models
            ml_result = await asyncio.to_thread(
                self.ml_processor.process_person_object,
                best_person
            )
            
            if not ml_result or not ml_result['success']:
                errors = ml_result.get('errors', ['Unknown error'])
                raise MVRServiceError(
                    f"ML processing failed: {', '.join(errors)}"
                )
            
            # Extract biometric features
            face_embedding = np.array(ml_result['face_embedding'])
            age_est = ml_result.get('age_estimate')
            gender_est = ml_result.get('gender_estimate')
            
            # Calculate quality scores
            quality_score = calculate_quality_score(best_person)
            confidence_score = best_person.get('confidence_score', 0.5)
            face_quality = best_person.get('face_quality', quality_score)
            
            # Create MVR-People record
            mvr_data = await self.repository.create_mvr_people(
                face_embedding=face_embedding,
                featured_individual_uuid=individual_uuid,
                age_min=age_est['min_age'] if age_est else None,
                age_max=age_est['max_age'] if age_est else None,
                age_confidence=age_est['confidence'] if age_est else None,
                gender=gender_est['gender'] if gender_est else None,
                gender_confidence=(
                    gender_est['confidence'] if gender_est else None
                ),
                quality_score=quality_score,
                confidence_score=confidence_score,
                face_quality=face_quality,
                featured_person_object_uuid=(
                    best_person.get('person_object_uuid')
                ),
                featured_video_uuid=best_person.get('video_uuid'),
                auto_created=auto_created
            )
            
            mvr_uuid = mvr_data['mvr_people_uuid']
            
            # Create Individual-MVR mapping
            await self.repository.create_individual_mvr_mapping(
                individual_uuid=individual_uuid,
                mvr_people_uuid=mvr_uuid,
                confidence_score=confidence_score,
                quality_score=quality_score,
                is_representative=True,  # First individual is featured
                link_method='auto_create'
            )
            
            logger.info(
                f"✅ Created MVR-People {mvr_uuid} for "
                f"Individual {individual_uuid}"
            )
            
            return {
                'success': True,
                'mvr_people_uuid': mvr_uuid,
                'individual_uuid': individual_uuid,
                'quality_score': quality_score,
                'face_embedding_size': len(face_embedding),
                'has_age_estimate': age_est is not None,
                'has_gender_estimate': gender_est is not None,
                'created_at': mvr_data['created_at']
            }
            
        except MVRRepositoryError as e:
            logger.error(f"Repository error creating MVR-People: {e}")
            raise MVRServiceError(f"Database error: {e}")
        except Exception as e:
            logger.error(f"Failed to create MVR-People: {e}")
            raise MVRServiceError(f"Failed to create MVR-People: {e}")
    
    async def _fetch_person_objects_for_individual(
        self,
        individual_uuid: UUID
    ) -> List[Dict[str, Any]]:
        """
        Fetch person objects from Orchestrator for Individual.
        
        Args:
            individual_uuid: Individual UUID
            
        Returns:
            List of person object dicts
        """
        # TODO: Implement Orchestrator API call
        # For now, return empty list (will be implemented in Phase 4)
        logger.warning(
            "Orchestrator client not implemented, returning empty list"
        )
        return []
    
    # ===================================================================
    # MVR-People Retrieval
    # ===================================================================
    
    async def get_mvr_people(
        self,
        mvr_people_uuid: UUID,
        include_linked_individuals: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get MVR-People by UUID.
        
        Args:
            mvr_people_uuid: MVR-People UUID
            include_linked_individuals: Include linked Individuals list
            
        Returns:
            MVR-People dict or None
        """
        try:
            mvr = await self.repository.get_mvr_people_by_uuid(
                mvr_people_uuid
            )
            
            if not mvr:
                return None
            
            # Convert embedding from list to numpy array for consistency
            if 'face_embedding' in mvr:
                mvr['face_embedding'] = np.array(mvr['face_embedding'])
            
            # Include linked individuals if requested
            if include_linked_individuals:
                individuals = (
                    await self.repository.get_linked_individuals(
                        mvr_people_uuid
                    )
                )
                mvr['linked_individuals'] = individuals
                mvr['linked_individuals_count'] = len(individuals)
            
            return mvr
            
        except MVRRepositoryError as e:
            logger.error(f"Failed to get MVR-People: {e}")
            raise MVRServiceError(f"Failed to get MVR-People: {e}")
    
    async def get_mvr_people_for_individual(
        self,
        individual_uuid: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get MVR-People for an Individual.
        
        Args:
            individual_uuid: Individual UUID
            
        Returns:
            MVR-People dict or None
        """
        try:
            mvr = await self.repository.get_mvr_people_by_individual(
                individual_uuid
            )
            
            if mvr and 'face_embedding' in mvr:
                mvr['face_embedding'] = np.array(mvr['face_embedding'])
            
            return mvr
            
        except MVRRepositoryError as e:
            logger.error(f"Failed to get MVR for Individual: {e}")
            raise MVRServiceError(f"Failed to get MVR for Individual: {e}")
    
    # ===================================================================
    # Similarity Search
    # ===================================================================
    
    async def find_similar_people(
        self,
        face_embedding: np.ndarray,
        similarity_threshold: Optional[float] = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find similar MVR-People using face embedding.
        
        Args:
            face_embedding: Query face embedding
            similarity_threshold: Override default threshold
            max_results: Maximum number of results
            
        Returns:
            List of similar MVR-People with scores
        """
        try:
            # Get threshold from config if not provided
            if similarity_threshold is None:
                config = await self.repository.get_matching_config()
                similarity_threshold = config['similarity_threshold']
            
            results = await self.repository.find_similar_mvr_people(
                face_embedding=face_embedding,
                similarity_threshold=similarity_threshold,
                max_results=max_results,
                exclude_orphaned=True
            )
            
            return results
            
        except MVRRepositoryError as e:
            logger.error(f"Similarity search failed: {e}")
            raise MVRServiceError(f"Similarity search failed: {e}")
    
    async def search_by_demographics(
        self,
        age_min: Optional[int] = None,
        age_max: Optional[int] = None,
        gender: Optional[str] = None,
        min_quality: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search MVR-People by demographic criteria.
        
        Args:
            age_min: Minimum age
            age_max: Maximum age
            gender: Gender (male/female/unknown)
            min_quality: Minimum quality score
            limit: Maximum results
            
        Returns:
            List of matching MVR-People
        """
        try:
            results = await self.repository.search_by_demographics(
                age_min=age_min,
                age_max=age_max,
                gender=gender,
                min_quality=min_quality,
                limit=limit
            )
            
            return results
            
        except MVRRepositoryError as e:
            logger.error(f"Demographic search failed: {e}")
            raise MVRServiceError(f"Demographic search failed: {e}")
    
    # ===================================================================
    # Configuration
    # ===================================================================
    
    async def get_matching_config(self) -> Dict[str, Any]:
        """Get current matching configuration."""
        try:
            return await self.repository.get_matching_config()
        except MVRRepositoryError as e:
            logger.error(f"Failed to get config: {e}")
            raise MVRServiceError(f"Failed to get config: {e}")
    
    async def update_matching_config(
        self,
        **kwargs
    ) -> bool:
        """Update matching configuration."""
        try:
            return await self.repository.update_matching_config(**kwargs)
        except MVRRepositoryError as e:
            logger.error(f"Failed to update config: {e}")
            raise MVRServiceError(f"Failed to update config: {e}")
