"""
MVR-People Service Layer
PPL Meta Platform - vmeta service

Main service for MVR-People operations including creation, matching, and merging.

Created: October 31, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
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
        self.gender_conflict_min_confidence = 0.80
        self.contamination_similarity_threshold = 0.70
        logger.info("MVRService initialized")

    def _normalize_gender(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        gender = str(value).strip().lower()
        if gender in {"male", "female"}:
            return gender
        return None

    def _safe_float(self, value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _can_auto_merge_by_gender(
        self,
        person1: Dict[str, Any],
        person2: Dict[str, Any]
    ) -> bool:
        gender1 = self._normalize_gender(person1.get("gender"))
        gender2 = self._normalize_gender(person2.get("gender"))

        if gender1 is None or gender2 is None:
            return True

        if gender1 == gender2:
            return True

        conf1 = self._safe_float(person1.get("gender_confidence"))
        conf2 = self._safe_float(person2.get("gender_confidence"))
        if conf1 is None or conf2 is None:
            return True

        return not (
            conf1 >= self.gender_conflict_min_confidence
            and conf2 >= self.gender_conflict_min_confidence
            and gender1 != gender2
        )

    def _is_contamination_suspect(
        self,
        person1: Dict[str, Any],
        person2: Dict[str, Any],
        similarity: float
    ) -> bool:
        gender1 = self._normalize_gender(person1.get("gender"))
        gender2 = self._normalize_gender(person2.get("gender"))

        one_unknown_one_known = (gender1 is None) != (gender2 is None)
        if not one_unknown_one_known:
            return False

        known_conf = (
            self._safe_float(person2.get("gender_confidence"))
            if gender1 is None
            else self._safe_float(person1.get("gender_confidence"))
        )
        if known_conf is None:
            return False

        return (
            known_conf >= self.gender_conflict_min_confidence
            and similarity >= self.contamination_similarity_threshold
        )
    
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
    
    # ===================================================================
    # Single-Media MVR Processing
    # ===================================================================
    
    async def process_single_media_for_mvr(
        self,
        media_uuid: UUID,
        media_type: str,
        person_objects: List[Dict[str, Any]],
        similarity_threshold: float = 0.7,
        min_face_quality: float = 0.2,
        include_demographics: bool = True,
        include_route_data: bool = True,
        media_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Process a single media (photo or video) to generate MVR people independently.
        
        This method processes each media in isolation - no cross-media merging.
        
        Args:
            media_uuid: Media UUID
            media_type: "photo" or "video"
            person_objects: Person objects from Orchestrator
            similarity_threshold: Similarity threshold for within-media matching
            min_face_quality: Minimum face quality threshold
            include_demographics: Whether to estimate demographics
            include_route_data: Whether to include route data
            
        Returns:
            Dict with MVR people created for this media
        """
        import time
        from sklearn.metrics.pairwise import cosine_similarity as compute_cosine_similarity
        
        start_time = time.time()
        
        logger.info(
            f"Processing {media_type} {media_uuid} independently: "
            f"{len(person_objects)} person objects"
        )
        logger.info(f"[MVRService DEBUG] RECEIVED {len(person_objects)} person_objects")
        logger.info(f"[MVRService DEBUG] person_objects type: {type(person_objects)}")
        logger.info(f"[MVRService DEBUG] person_objects sample: {person_objects[:1] if person_objects else 'EMPTY'}")
        
        if not person_objects:
            return {
                "media_uuid": str(media_uuid),
                "media_type": media_type,
                "status": "completed",
                "mvr_people": [],
                "total_faces_detected": 0,
                "mvr_people_count": 0,
                "processing_time_ms": 0
            }
        
        # Step 1: Process person objects through ML pipeline (FULL ML PROCESSING - IDENTICAL TO OTHER ENDPOINTS)
        # This generates embeddings, age estimates, and gender predictions
        individuals_data = []
        total_faces = sum(po.get('face_count', 1) for po in person_objects)
        
        for person_obj in person_objects:
            try:
                # Check face quality (Orchestrator returns 0-100, database expects 0.0-1.0)
                raw_quality = person_obj.get('quality_score', 80.0)
                face_quality = raw_quality / 100.0 if raw_quality > 1.0 else raw_quality
                logger.warning(f"[QUALITY CHECK] Person {person_obj.get('person_object_uuid')}: quality={face_quality:.3f} (raw={raw_quality:.2f}), threshold={min_face_quality}")
                print(f"[MVR DEBUG] Quality check: {face_quality:.3f} >= {min_face_quality}?", flush=True)
                
                if face_quality < min_face_quality:
                    logger.warning(
                        f"[SKIPPED] Low-quality person object: {face_quality:.2f} < {min_face_quality}"
                    )
                    print(f"[MVR DEBUG] SKIPPED: quality too low", flush=True)
                    continue
                
                logger.warning(f"[ML START] Processing person object {person_obj.get('person_object_uuid')} through ML models...")
                print(f"[MVR DEBUG] Starting ML processing...", flush=True)
                
                # Process through ML models (facenet + age/gender)
                ml_result = await asyncio.to_thread(
                    self.ml_processor.process_person_object,
                    person_obj
                )
                
                logger.warning(f"[ML COMPLETE] ML result received: {ml_result is not None}, success={ml_result.get('success') if ml_result else 'N/A'}")
                print(f"[MVR DEBUG] ML result: {ml_result}", flush=True)
                
                # DEBUG: Log ML result details
                logger.warning(
                    f"[ML DEBUG] Person {person_obj.get('person_object_uuid')}: "
                    f"ml_result={'None' if not ml_result else ml_result.get('success', 'no success key')}, "
                    f"has_face_crop={'best_face_crop' in person_obj}"
                )
                
                if not ml_result or not ml_result.get('success'):
                    errors = ml_result.get('errors', ['Unknown error']) if ml_result else ['ML processing failed']
                    logger.warning(
                        f"ML processing failed for person object {person_obj.get('person_object_uuid')}: "
                        f"{', '.join(errors)}"
                    )
                    continue
                
                # Extract ML results
                face_embedding = np.array(ml_result['face_embedding'])
                age_est = ml_result.get('age_estimate')
                gender_est = ml_result.get('gender_estimate')
                
                # Build individual data
                individual_data = {
                    'person_object_uuid': person_obj['person_object_uuid'],
                    'media_uuid': str(media_uuid),
                    'face_embedding': face_embedding,
                    'quality_score': face_quality,
                    'confidence_score': person_obj.get('confidence_score', 0.9),
                    'face_count': person_obj.get('face_count', 1),
                    'person_id': person_obj.get('person_id'),
                    # Forward face metadata so it can be persisted into
                    # individual_video_appearances.representative_faces. Both the
                    # best-image (mvr_image_manager) and routes
                    # (_expand_with_orchestrator_route_points) flows rely on this
                    # column to match orchestrator person_groups; without it,
                    # thumbnails and routes both render empty.
                    'representative_faces': person_obj.get('representative_faces') or [],
                }
                
                # Add demographics if included
                if include_demographics:
                    if age_est:
                        individual_data.update({
                            'age_min': age_est['min_age'],
                            'age_max': age_est['max_age'],
                            'age_confidence': age_est['confidence']
                        })
                    if gender_est:
                        individual_data.update({
                            'gender': gender_est['gender'],
                            'gender_confidence': gender_est['confidence']
                        })
                
                individuals_data.append(individual_data)
                
                logger.debug(
                    f"Processed person object {person_obj.get('person_object_uuid')}: "
                    f"embedding shape={face_embedding.shape}, "
                    f"age={age_est.get('min_age')}-{age_est.get('max_age') if age_est else 'N/A'}, "
                    f"gender={gender_est.get('gender') if gender_est else 'N/A'}"
                )
                
            except Exception as e:
                logger.error(
                    f"Failed to process person object {person_obj.get('person_object_uuid')}: {e}"
                )
                continue
        
        logger.info(
            f"ML processing completed: {len(individuals_data)}/{len(person_objects)} person objects "
            f"successfully processed"
        )
        
        if not individuals_data:
            logger.warning(f"No valid individuals after quality filtering")
            return {
                "media_uuid": str(media_uuid),
                "media_type": media_type,
                "status": "completed",
                "mvr_people": [],
                "total_faces_detected": 0,
                "mvr_people_count": 0,
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
        
        # Step 2: Match faces WITHIN this media only
        uuids = [ind['person_object_uuid'] for ind in individuals_data]
        embeddings_matrix = np.array([ind['face_embedding'] for ind in individuals_data])
        
        # Compute pairwise similarities
        similarities = compute_cosine_similarity(embeddings_matrix)
        
        logger.info(
            f"Computed similarity matrix: {similarities.shape}, "
            f"threshold={similarity_threshold}"
        )
        
        # Step 3: Find connected components (merge groups)
        similar_to = {str(uuid_val): [] for uuid_val in uuids}
        
        blocked_gender_pairs = 0
        contamination_blocked = 0

        for i in range(len(uuids)):
            for j in range(i + 1, len(uuids)):
                similarity = float(similarities[i][j])
                if similarity < similarity_threshold:
                    continue

                if not self._can_auto_merge_by_gender(
                    individuals_data[i],
                    individuals_data[j]
                ):
                    blocked_gender_pairs += 1
                    continue

                if self._is_contamination_suspect(
                    individuals_data[i],
                    individuals_data[j],
                    similarity
                ):
                    contamination_blocked += 1
                    logger.warning(
                        "Blocked contamination-suspect single-media merge: "
                        f"{str(uuids[i])[:8]} "
                        f"(gender={individuals_data[i].get('gender')}, "
                        f"conf={individuals_data[i].get('gender_confidence')}) <-> "
                        f"{str(uuids[j])[:8]} "
                        f"(gender={individuals_data[j].get('gender')}, "
                        f"conf={individuals_data[j].get('gender_confidence')}) "
                        f"similarity={similarity:.3f}"
                    )
                    continue

                similar_to[str(uuids[i])].append(str(uuids[j]))
                similar_to[str(uuids[j])].append(str(uuids[i]))

        if blocked_gender_pairs > 0:
            logger.info(
                f"Blocked {blocked_gender_pairs} high-confidence cross-gender "
                f"pair(s) from single-media clustering"
            )
        if contamination_blocked > 0:
            logger.info(
                f"Blocked {contamination_blocked} contamination-suspect pair(s) "
                f"from single-media clustering"
            )
        
        # Find connected components using DFS
        visited = set()
        clusters = []
        
        def dfs(uuid_val, component):
            if uuid_val in visited:
                return
            visited.add(uuid_val)
            component.append(uuid_val)
            for neighbor in similar_to[uuid_val]:
                if neighbor not in visited:
                    dfs(neighbor, component)
        
        for uuid_val in similar_to.keys():
            if uuid_val not in visited:
                component = []
                dfs(uuid_val, component)
                if component:
                    clusters.append(component)
        
        logger.info(
            f"Found {len(clusters)} clusters from {len(individuals_data)} individuals"
        )
        
        # Step 4: Create MVR people (one per cluster)
        mvr_people_created = []
        
        for cluster_uuids in clusters:
            try:
                # Get individuals in this cluster
                cluster_individuals = [
                    ind for ind in individuals_data
                    if str(ind['person_object_uuid']) in cluster_uuids
                ]
                
                # Compute canonical embedding (quality-weighted average)
                embeddings = [ind['face_embedding'] for ind in cluster_individuals]
                quality_scores = [ind['quality_score'] for ind in cluster_individuals]
                
                canonical_embedding = np.average(
                    embeddings,
                    axis=0,
                    weights=quality_scores
                )
                canonical_embedding = canonical_embedding / np.linalg.norm(canonical_embedding)
                
                # Select best quality individual as featured
                best_ind = max(cluster_individuals, key=lambda x: x['quality_score'])
                
                # Demographics already processed per individual - aggregate from individuals
                # Calculate average scores and demographics
                avg_confidence = np.mean([ind['confidence_score'] for ind in cluster_individuals])
                avg_quality = np.mean([ind['quality_score'] for ind in cluster_individuals])
                
                # Aggregate demographics from individuals if included
                demographics = None
                if include_demographics and any('age_min' in ind for ind in cluster_individuals):
                    # Use demographics from best quality individual
                    demographics = {
                        'age_min': best_ind.get('age_min'),
                        'age_max': best_ind.get('age_max'),
                        'age_confidence': best_ind.get('age_confidence'),
                        'gender': best_ind.get('gender'),
                        'gender_confidence': best_ind.get('gender_confidence')
                    }
                
                # Create individual record for single-media processing
                # This maintains the relationship chain: MVR → Individual → Person Objects → Routes
                individual_uuid = uuid4()
                individual_id = f"isolated_{individual_uuid.hex[:8]}"
                persisted_age_estimate = None
                if demographics and demographics.get('age_min') is not None:
                    age_min = demographics.get('age_min')
                    age_max = demographics.get('age_max', age_min)
                    if age_max is None:
                        age_max = age_min
                    persisted_age_estimate = int(round((age_min + age_max) / 2))
                persisted_gender_estimate = (
                    demographics.get('gender') if demographics else None
                )
                
                try:
                    # Use repository's pool connection
                    pool = self.repository.pool
                    
                    await pool.execute("""
                        INSERT INTO individuals 
                        (individual_uuid, individual_id, confidence_score, 
                         spatial_signature, temporal_signature, gender_estimate, age_estimate)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        individual_uuid,
                        individual_id,
                        float(avg_confidence),
                        json.dumps({}),  # Empty for single-media
                        json.dumps({}),  # Empty for single-media
                        persisted_gender_estimate,
                        persisted_age_estimate,
                    )
                    
                    appearance_timestamp = media_timestamp
                    if isinstance(appearance_timestamp, str):
                        try:
                            appearance_timestamp = datetime.fromisoformat(
                                appearance_timestamp.replace('Z', '+00:00')
                            )
                        except ValueError:
                            logger.warning(
                                'Invalid media_timestamp string for %s: %s; falling back to now()',
                                media_uuid,
                                appearance_timestamp,
                            )
                            appearance_timestamp = None

                    if appearance_timestamp is None:
                        appearance_timestamp = datetime.utcnow()
                    elif appearance_timestamp.tzinfo is not None:
                        appearance_timestamp = appearance_timestamp.astimezone(timezone.utc).replace(tzinfo=None)

                    # Link person objects to this individual via video appearances
                    for ind in cluster_individuals:
                        po_uuid = UUID(ind['person_object_uuid'])
                        rep_faces = ind.get('representative_faces') or []
                        rep_faces_json = (
                            json.dumps(rep_faces) if rep_faces else None
                        )
                        await pool.execute("""
                            INSERT INTO individual_video_appearances 
                            (individual_uuid, video_uuid, person_object_uuid, 
                             start_timestamp, end_timestamp, confidence,
                             representative_faces)
                            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                            ON CONFLICT (individual_uuid, video_uuid, person_object_uuid) DO NOTHING
                        """,
                            individual_uuid,
                            media_uuid,
                            po_uuid,
                            appearance_timestamp,
                            appearance_timestamp,
                            float(ind['confidence_score']),
                            rep_faces_json,
                        )
                    
                    logger.info(f"Created individual {individual_uuid} for single-media MVR with {len(cluster_individuals)} person objects")
                    
                except Exception as e:
                    logger.error(f"Failed to create individual for single-media processing: {e}")
                    # Use placeholder if individual creation fails
                    individual_uuid = UUID('00000000-0000-0000-0000-000000000000')
                
                # Create MVR person record in database
                # Normalize face_quality to 0.0-1.0 range (orchestrator returns 0-100)
                best_quality = best_ind['quality_score']
                normalized_face_quality = best_quality / 100.0 if best_quality > 1.0 else best_quality
                
                mvr_result = await self.repository.create_mvr_people(
                    face_embedding=canonical_embedding,
                    featured_individual_uuid=individual_uuid,
                    age_min=demographics.get('age_min') if demographics else None,
                    age_max=demographics.get('age_max') if demographics else None,
                    age_confidence=demographics.get('age_confidence') if demographics else None,
                    gender=demographics.get('gender') if demographics else None,
                    gender_confidence=demographics.get('gender_confidence') if demographics else None,
                    quality_score=float(avg_quality / 100.0 if avg_quality > 1.0 else avg_quality),
                    confidence_score=float(avg_confidence),
                    face_quality=float(normalized_face_quality),
                    featured_person_object_uuid=UUID(best_ind['person_object_uuid']),
                    featured_video_uuid=media_uuid,
                    auto_created=False,
                    is_isolated=True,  # Mark as isolated for single-media processing
                    source_media_uuid=media_uuid
                )
                
                mvr_people_uuid = mvr_result['mvr_people_uuid']
                
                # CRITICAL FIX: Link the individual to the MVR person via individual_mvr_mapping
                try:
                    await pool.execute("""
                        INSERT INTO individual_mvr_mapping 
                        (individual_uuid, mvr_people_uuid, confidence_score, quality_score, 
                         is_representative, link_method, linked_at)
                        VALUES ($1, $2, $3, $4, TRUE, 'auto_create', NOW())
                        ON CONFLICT (individual_uuid, mvr_people_uuid) DO NOTHING
                    """,
                        individual_uuid,
                        mvr_people_uuid,
                        float(avg_confidence),
                        float(avg_quality)
                    )
                    
                    logger.info(
                        f"Linked individual {individual_uuid} to MVR person {mvr_people_uuid} "
                        f"(confidence: {avg_confidence:.2f}, quality: {avg_quality:.2f})"
                    )
                    
                except Exception as link_error:
                    logger.error(f"Failed to link individual to MVR person: {link_error}")
                    # Continue - MVR person still created, just not linked properly
                
                # Build MVR person response object with correct individual_uuid
                mvr_person = {
                    "mvr_people_uuid": str(mvr_people_uuid),
                    "individual_uuids": [str(individual_uuid)],  # Fixed: use actual individual_uuid, not person_object_uuids
                    "total_appearances": len(cluster_individuals),
                    "unique_videos": 1,  # Always 1 for single-media processing
                    "confidence_score": float(avg_confidence),
                    "quality_score": float(avg_quality),
                    "is_isolated": True,
                    "source_media_uuid": str(media_uuid)
                }
                
                # Add demographics if available
                if demographics:
                    mvr_person["demographics"] = demographics
                
                mvr_people_created.append(mvr_person)
                
            except Exception as e:
                logger.error(f"Failed to create MVR for cluster: {e}")
                continue
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return {
            "media_uuid": str(media_uuid),
            "media_type": media_type,
            "status": "completed",
            "mvr_people": mvr_people_created,
            "total_faces_detected": len(individuals_data),
            "mvr_people_count": len(mvr_people_created),
            "processing_time_ms": processing_time
        }
