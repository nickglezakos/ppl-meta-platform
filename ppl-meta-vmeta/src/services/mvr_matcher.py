"""
MVR-People Matching and Merging Logic
PPL Meta Platform - vmeta service

Implements automatic matching and merging of MVR-People based on
face embedding similarity and quality scores.

Created: October 31, 2025
Author: PPL Meta Platform Team
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
import numpy as np

from database.mvr_repository import MVRRepository, MVRRepositoryError
from ml.mvr_processor import MVRProcessor

logger = logging.getLogger(__name__)


class MVRMatcherError(Exception):
    """Custom exception for matching/merging operations."""
    pass


class MVRMatcher:
    """
    MVR-People Matcher and Merger.
    
    Implements the 5-stage matching and merging workflow:
    1. Find candidate matches using similarity search
    2. Select best match based on similarity threshold
    3. Compare quality scores to determine winner
    4. Execute merge (reassign, orphan, update, audit)
    5. Post-merge cleanup and statistics update
    """
    
    def __init__(
        self,
        repository: MVRRepository,
        ml_processor: MVRProcessor
    ):
        """
        Initialize matcher.
        
        Args:
            repository: MVR database repository
            ml_processor: ML processor for similarity calc
        """
        self.repository = repository
        self.ml_processor = ml_processor
        logger.info("MVRMatcher initialized")
    
    # ===================================================================
    # Stage 1 & 2: Find and Select Match
    # ===================================================================
    
    async def find_matching_mvr(
        self,
        individual_uuid: UUID,
        face_embedding: np.ndarray,
        similarity_threshold: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find matching MVR-People for a new Individual.
        
        Implements Stage 1 & 2:
        - Find candidates using pgvector similarity search
        - Select best match above threshold
        
        Args:
            individual_uuid: New Individual UUID
            face_embedding: Face embedding to match
            similarity_threshold: Override default threshold
            
        Returns:
            Best matching MVR-People dict or None if no match
        """
        try:
            # Get matching config
            config = await self.repository.get_matching_config()
            
            if similarity_threshold is None:
                similarity_threshold = config['similarity_threshold']
            
            max_candidates = config['max_candidates_to_check']
            
            logger.info(
                f"Finding matches for Individual {individual_uuid} "
                f"(threshold: {similarity_threshold})"
            )
            
            # Find similar MVR-People
            candidates = await self.repository.find_similar_mvr_people(
                face_embedding=face_embedding,
                similarity_threshold=similarity_threshold,
                max_results=max_candidates,
                exclude_orphaned=True
            )
            
            if not candidates:
                logger.info("No matching MVR-People found")
                return None
            
            # Select best candidate (highest similarity)
            best_match = max(
                candidates,
                key=lambda x: x['similarity_score']
            )
            
            logger.info(
                f"✅ Found match: MVR {best_match['mvr_people_uuid']} "
                f"(similarity: {best_match['similarity_score']:.3f})"
            )
            
            return best_match
            
        except MVRRepositoryError as e:
            logger.error(f"Failed to find matching MVR: {e}")
            raise MVRMatcherError(f"Failed to find matching MVR: {e}")
    
    # ===================================================================
    # Stage 3: Quality Comparison
    # ===================================================================
    
    def should_merge_based_on_quality(
        self,
        new_quality_score: float,
        existing_quality_score: float
    ) -> Tuple[bool, str]:
        """
        Determine if merge should occur based on quality comparison.
        
        Implements Stage 3 quality-based merge decision.
        
        Args:
            new_quality_score: New Individual's quality
            existing_quality_score: Existing MVR's quality
            
        Returns:
            (should_merge, reason)
        """
        # Always merge, but decide which MVR to keep
        # Higher quality MVR becomes the winner
        
        if new_quality_score > existing_quality_score:
            reason = (
                f"New individual has higher quality "
                f"({new_quality_score:.3f} > {existing_quality_score:.3f})"
            )
        else:
            reason = (
                f"Existing MVR has higher quality "
                f"({existing_quality_score:.3f} >= {new_quality_score:.3f})"
            )
        
        return True, reason
    
    # ===================================================================
    # Stage 4: Execute Merge
    # ===================================================================
    
    async def merge_mvr_people(
        self,
        new_individual_uuid: UUID,
        new_mvr_uuid: UUID,
        existing_mvr_uuid: UUID,
        similarity_score: float,
        new_quality_score: float,
        existing_quality_score: float,
        new_face_embedding: Optional[np.ndarray] = None,
        new_demographics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute MVR-People merge operation.
        
        Implements Stage 4:
        - Determine winner (highest quality)
        - Reassign Individuals to winner
        - Mark loser as orphaned
        - Update winner's features if new is better
        - Create audit log
        
        Args:
            new_individual_uuid: New Individual triggering merge
            new_mvr_uuid: New MVR-People UUID
            existing_mvr_uuid: Existing MVR-People UUID (match)
            similarity_score: Face similarity score
            new_quality_score: New MVR quality
            existing_quality_score: Existing MVR quality
            new_face_embedding: New embedding (if new is better)
            new_demographics: New demographics (if new is better)
            
        Returns:
            Dict with merge results
        """
        try:
            logger.info(
                f"Merging MVR-People: new={new_mvr_uuid}, "
                f"existing={existing_mvr_uuid}"
            )
            
            # Determine winner
            new_is_winner = new_quality_score > existing_quality_score
            
            if new_is_winner:
                winner_uuid = new_mvr_uuid
                loser_uuid = existing_mvr_uuid
                winner_quality = new_quality_score
                loser_quality = existing_quality_score
                merge_reason = "new_higher_quality"
            else:
                winner_uuid = existing_mvr_uuid
                loser_uuid = new_mvr_uuid
                winner_quality = existing_quality_score
                loser_quality = new_quality_score
                merge_reason = "existing_higher_quality"
            
            logger.info(
                f"Winner: {winner_uuid} "
                f"(quality: {winner_quality:.3f})"
            )
            
            # Get matching threshold
            config = await self.repository.get_matching_config()
            matching_threshold = config['similarity_threshold']
            
            # Step 1: Reassign Individuals from loser to winner
            reassigned_count = (
                await self.repository.reassign_individuals_to_mvr(
                    source_mvr_uuid=loser_uuid,
                    target_mvr_uuid=winner_uuid,
                    similarity_score=similarity_score
                )
            )
            
            logger.info(
                f"Reassigned {reassigned_count} individuals "
                f"from {loser_uuid} to {winner_uuid}"
            )
            
            # Step 2: Mark loser as orphaned
            orphaned = await self.repository.mark_mvr_as_orphaned(
                source_mvr_uuid=loser_uuid,
                target_mvr_uuid=winner_uuid
            )
            
            if not orphaned:
                logger.warning(f"Failed to mark {loser_uuid} as orphaned")
            
            # Step 3: Update winner if new is better
            if new_is_winner and new_face_embedding is not None:
                update_fields = {
                    'face_embedding': new_face_embedding.tolist(),
                    'quality_score': new_quality_score,
                    'featured_individual_uuid': new_individual_uuid
                }
                
                # Add demographics if provided
                if new_demographics:
                    if 'age_estimate' in new_demographics:
                        age = new_demographics['age_estimate']
                        update_fields['age_min'] = age.get('min_age')
                        update_fields['age_max'] = age.get('max_age')
                        update_fields['age_confidence'] = age.get(
                            'confidence'
                        )
                    
                    if 'gender_estimate' in new_demographics:
                        gender = new_demographics['gender_estimate']
                        update_fields['gender'] = gender.get('gender')
                        update_fields['gender_confidence'] = gender.get(
                            'confidence'
                        )
                
                updated = await self.repository.update_mvr_people(
                    mvr_people_uuid=winner_uuid,
                    **update_fields
                )
                
                logger.info(
                    f"Updated winner MVR {winner_uuid} with "
                    f"new features: {updated}"
                )
            
            # Step 4: Create audit log
            audit_uuid = await self.repository.create_merge_audit_log(
                source_mvr_uuid=loser_uuid,
                target_mvr_uuid=winner_uuid,
                source_individual_uuid=new_individual_uuid,
                merge_action='merged',
                merge_reason=merge_reason,
                similarity_score=similarity_score,
                matching_threshold=matching_threshold,
                source_quality_score=loser_quality,
                target_quality_score=winner_quality,
                winner_mvr_uuid=winner_uuid,
                system_mode='automatic',
                metadata={
                    'reassigned_individuals': reassigned_count,
                    'new_is_winner': new_is_winner
                }
            )
            
            logger.info(f"✅ Merge completed, audit log: {audit_uuid}")

            # People-counters invalidation (proposal §5.7): both winner and
            # loser identities may appear in tagged batch results — flag those
            # batches so the orchestrator worker recomputes them.
            try:
                stale_count = await self.repository.mark_batches_stale_for_mvr_people(
                    [str(winner_uuid), str(loser_uuid)]
                )
                if stale_count:
                    logger.info(
                        "people-counters: marked %d batch(es) stale after merge %s→%s",
                        stale_count,
                        loser_uuid,
                        winner_uuid,
                    )
            except Exception as stale_err:
                logger.warning(
                    "people-counters: failed to invalidate batches after merge: %s",
                    stale_err,
                )

            return {
                'success': True,
                'winner_mvr_uuid': winner_uuid,
                'loser_mvr_uuid': loser_uuid,
                'new_is_winner': new_is_winner,
                'similarity_score': similarity_score,
                'winner_quality': winner_quality,
                'loser_quality': loser_quality,
                'reassigned_individuals': reassigned_count,
                'audit_uuid': audit_uuid,
                'merge_reason': merge_reason
            }
            
        except MVRRepositoryError as e:
            logger.error(f"Merge failed: {e}")
            raise MVRMatcherError(f"Merge failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected merge error: {e}")
            raise MVRMatcherError(f"Unexpected merge error: {e}")
    
    # ===================================================================
    # Complete Workflow: Match & Merge
    # ===================================================================
    
    async def match_and_merge_if_needed(
        self,
        individual_uuid: UUID,
        new_mvr_uuid: UUID,
        face_embedding: np.ndarray,
        quality_score: float,
        demographics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete matching and merging workflow for new Individual.
        
        Executes all 5 stages:
        1. Find candidate matches
        2. Select best match
        3. Compare quality
        4. Execute merge
        5. Return results
        
        Args:
            individual_uuid: New Individual UUID
            new_mvr_uuid: Newly created MVR UUID
            face_embedding: Face embedding
            quality_score: Quality score
            demographics: Age/gender estimates
            
        Returns:
            Dict with match/merge results
        """
        try:
            # Stage 1 & 2: Find matching MVR
            match = await self.find_matching_mvr(
                individual_uuid=individual_uuid,
                face_embedding=face_embedding
            )
            
            if not match:
                logger.info(
                    f"No match found for Individual {individual_uuid}, "
                    f"keeping MVR {new_mvr_uuid}"
                )
                return {
                    'matched': False,
                    'merged': False,
                    'mvr_people_uuid': new_mvr_uuid,
                    'message': 'No similar MVR-People found'
                }
            
            existing_mvr_uuid = match['mvr_people_uuid']
            similarity_score = match['similarity_score']
            existing_quality = match['quality_score']
            
            # Stage 3: Quality comparison
            should_merge, reason = self.should_merge_based_on_quality(
                new_quality_score=quality_score,
                existing_quality_score=existing_quality
            )
            
            if not should_merge:
                logger.info(
                    f"Match found but merge rejected: {reason}"
                )
                return {
                    'matched': True,
                    'merged': False,
                    'match_mvr_uuid': existing_mvr_uuid,
                    'similarity_score': similarity_score,
                    'reason': reason
                }
            
            # Stage 4: Execute merge
            merge_result = await self.merge_mvr_people(
                new_individual_uuid=individual_uuid,
                new_mvr_uuid=new_mvr_uuid,
                existing_mvr_uuid=existing_mvr_uuid,
                similarity_score=similarity_score,
                new_quality_score=quality_score,
                existing_quality_score=existing_quality,
                new_face_embedding=face_embedding,
                new_demographics=demographics
            )
            
            return {
                'matched': True,
                'merged': True,
                'mvr_people_uuid': merge_result['winner_mvr_uuid'],
                **merge_result
            }
            
        except Exception as e:
            logger.error(f"Match and merge workflow failed: {e}")
            raise MVRMatcherError(
                f"Match and merge workflow failed: {e}"
            )
