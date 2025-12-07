"""
MVR-People API Routes

This module implements 14 REST API endpoints for the MVR-People (Machine Vision Representation)
system, providing CRUD operations, similarity search, matching/merging, and background task
monitoring.

All endpoints require JWT authentication via Authorization header.

Author: PPL Meta Platform
Date: October 31, 2025
Version: 1.0.0
"""

import asyncio
import logging
import os
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Request
from fastapi.responses import JSONResponse

# Database and services
from database.mvr_repository import MVRRepository
from services.mvr_service import MVRService
from services.mvr_matcher import MVRMatcher
from background.mvr_background_processor import MVRBackgroundProcessor

# Models
from api.models.mvr_people import (
    CreateMVRRequest,
    CreateMVRResponse,
    MVRPeopleResponse,
    SearchSimilarRequest,
    SearchSimilarResponse,
    SearchDemographicsRequest,
    SearchDemographicsResponse,
    LinkIndividualRequest,
    LinkIndividualResponse,
    BatchCreateRequest,
    BatchCreateResponse,
    MVRStatusResponse,
    MatchIndividualRequest,
    MatchIndividualResponse,
    MergeIndividualsRequest,
    MergeIndividualsResponse,
    MergeHistoryResponse,
    OrphanedMVRResponse,
    MatchingConfigUpdate,
    MatchingConfigResponse,
)

# Batch merge models
from api.models.batch_merge import (
    BatchMatchAndMergeRequest,
    BatchMatchAndMergeResponse,
    MergeDetail,
)

# MVR search models
from api.models.mvr_search_models import (
    MVRPeopleSearchRequest,
    MVRPeopleSearchResponse,
    MVRPersonResult,
    IndividualAppearance as MVRIndividualAppearance,
)

# Process media models
from api.models.process_media import ProcessMediaRequest

# Dependencies
from api.dependencies import (
    get_mvr_repository,
    get_mvr_service,
    get_mvr_matcher,
    get_mvr_background_processor,
    get_current_user,
)

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(
    prefix="/api/v1/mvr-people",
    tags=["mvr-people"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
    },
)


# ============================================================================
# ENDPOINT 1: Create MVR-People for Individual
# ============================================================================

@router.post(
    "/individuals/{individual_uuid}/create",
    response_model=CreateMVRResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create MVR-People for Individual",
    description="Create Machine Vision Representation for an Individual. "
                "Supports both synchronous and asynchronous processing.",
)
async def create_mvr_for_individual(
    individual_uuid: UUID,
    request: Optional[CreateMVRRequest] = Body(default=None),
    mvr_service: MVRService = Depends(get_mvr_service),
    background_processor: MVRBackgroundProcessor = Depends(get_mvr_background_processor),
    current_user: dict = Depends(get_current_user),
):
    """
    Create MVR-People representation for an individual.
    
    **Processing Modes:**
    - **Background (default):** Returns immediately with status "pending"
    - **Synchronous:** Set background_processing=false for immediate processing
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuid: UUID of the Individual
    - background_processing: Enable async processing (default: true)
    - force_recreate: Recreate if already exists (default: false)
    
    **Returns:**
    - 202 Accepted (background): MVR creation queued
    - 200 OK (synchronous): MVR created with full details
    - 400 Bad Request: Invalid Individual UUID or already exists
    - 404 Not Found: Individual not found
    """
    logger.info(f"Creating MVR-People for Individual {individual_uuid} (user: {current_user.get('email')})")
    
    # Parse request body (use defaults if not provided)
    background_processing = True
    force_recreate = False
    if request:
        background_processing = request.background_processing
        force_recreate = request.force_recreate
    
    try:
        # Check if MVR already exists
        existing_mvr = await mvr_service.get_mvr_people_for_individual(
            individual_uuid
        )
        
        if existing_mvr and not force_recreate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"MVR-People already exists for Individual {individual_uuid}. "
                       f"Use force_recreate=true to recreate."
            )
        
        # Background processing
        if background_processing:
            # Queue background task
            task_info = await background_processor.process_individual(
                individual_uuid=individual_uuid,
                auto_match=False,  # Don't auto-match on creation
            )
            
            return CreateMVRResponse(
                mvr_people_uuid=None,  # Not created yet
                individual_uuid=individual_uuid,
                status="pending",
                message="MVR-People creation queued for background processing",
                estimated_completion_seconds=10,
            )
        
        # Synchronous processing
        else:
            # Create MVR-People immediately
            mvr_result = await mvr_service.create_mvr_people_from_individual(individual_uuid)
            
            if not mvr_result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create MVR-People"
                )
            
            return CreateMVRResponse(
                mvr_people_uuid=mvr_result['mvr_people_uuid'],
                individual_uuid=individual_uuid,
                status="completed",
                face_embedding=mvr_result.get('face_embedding'),
                age_estimate=mvr_result.get('age_estimate'),
                gender_estimate=mvr_result.get('gender_estimate'),
                representative_individual_uuid=mvr_result.get('featured_individual_uuid'),
                quality_score=mvr_result.get('quality_score'),
                created_at=mvr_result.get('created_at'),
                updated_at=mvr_result.get('updated_at'),
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating MVR-People for Individual {individual_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create MVR-People: {str(e)}"
        )


# ============================================================================
# ENDPOINT 2: Get MVR-People by UUID
# ============================================================================

@router.get(
    "/{mvr_people_uuid}",
    response_model=MVRPeopleResponse,
    summary="Get MVR-People by UUID",
    description="Retrieve complete MVR-People record by UUID",
)
async def get_mvr_people_by_uuid(
    mvr_people_uuid: UUID,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieve MVR-People record by UUID.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - mvr_people_uuid: UUID of the MVR-People record
    
    **Returns:**
    - 200 OK: MVR-People record with all linked Individuals
    - 404 Not Found: MVR-People not found
    """
    logger.info(f"Retrieving MVR-People {mvr_people_uuid} (user: {current_user.get('email')})")
    
    try:
        # Get MVR-People record
        mvr_record = await mvr_repository.get_mvr_people_by_uuid(mvr_people_uuid)
        
        if not mvr_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MVR-People {mvr_people_uuid} not found"
            )
        
        # Get linked Individuals
        linked_individuals = await mvr_repository.get_individuals_for_mvr(mvr_people_uuid)
        
        return MVRPeopleResponse(
            mvr_people_uuid=mvr_record['mvr_people_uuid'],
            status=mvr_record.get('processing_status', 'completed'),
            face_embedding=mvr_record.get('face_embedding'),
            age_estimate=mvr_record.get('age_estimate'),
            gender_estimate=mvr_record.get('gender_estimate'),
            representative_individual_uuid=mvr_record.get('featured_individual_uuid'),
            representative_face_uuid=mvr_record.get('representative_face_uuid'),
            quality_score=mvr_record.get('quality_score'),
            total_linked_individuals=len(linked_individuals),
            linked_individuals=linked_individuals,
            created_at=mvr_record.get('created_at'),
            updated_at=mvr_record.get('updated_at'),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving MVR-People {mvr_people_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve MVR-People: {str(e)}"
        )


# ============================================================================
# ENDPOINT 3: Get MVR-People for Individual
# ============================================================================

@router.get(
    "/individuals/{individual_uuid}",
    response_model=MVRPeopleResponse,
    summary="Get MVR-People for Individual",
    description="Retrieve MVR-People linked to an Individual",
)
async def get_mvr_for_individual(
    individual_uuid: UUID,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user),
):
    """
    Get MVR-People linked to an Individual.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuid: UUID of the Individual
    
    **Returns:**
    - 200 OK: MVR-People record
    - 404 Not Found: No MVR-People found for Individual
    """
    logger.info(f"Retrieving MVR-People for Individual {individual_uuid} (user: {current_user.get('email')})")
    
    try:
        # Get MVR-People for Individual
        mvr_record = await mvr_service.get_mvr_for_individual(individual_uuid)
        
        if not mvr_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No MVR-People found for Individual {individual_uuid}",
            )
        
        return MVRPeopleResponse(
            individual_uuid=individual_uuid,
            mvr_people=mvr_record,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving MVR-People for Individual {individual_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve MVR-People: {str(e)}"
        )


# ============================================================================
# ENDPOINT 4: Search Similar MVR-People
# ============================================================================

@router.post(
    "/search/similar",
    response_model=SearchSimilarResponse,
    summary="Search Similar MVR-People",
    description="Find similar people using face embedding similarity (pgvector)",
)
async def search_similar_mvr_people(
    request: SearchSimilarRequest,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user),
):
    """
    Find similar people using face embedding similarity.
    
    **Similarity Algorithm:** Cosine similarity via pgvector extension
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - mvr_people_uuid OR face_embedding: Source for similarity search
    - similarity_threshold: Minimum cosine similarity (0-1, default: 0.7)
    - max_results: Maximum results to return (default: 10)
    - include_demographics: Include age/gender filters (default: true)
    
    **Returns:**
    - 200 OK: List of similar MVR-People with similarity scores
    - 400 Bad Request: Invalid request (missing mvr_people_uuid and face_embedding)
    """
    logger.info(f"Searching similar MVR-People (user: {current_user.get('email')})")
    
    try:
        # Validate request
        if not request.mvr_people_uuid and not request.face_embedding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either mvr_people_uuid or face_embedding must be provided"
            )
        
        # Search by MVR UUID
        if request.mvr_people_uuid:
            results = await mvr_service.search_similar_mvr(
                mvr_uuid=request.mvr_people_uuid,
                threshold=request.similarity_threshold or 0.7,
                limit=request.max_results or 10,
            )
        
        # Search by face embedding
        else:
            results = await mvr_service.search_similar_by_embedding(
                face_embedding=request.face_embedding,
                threshold=request.similarity_threshold or 0.7,
                limit=request.max_results or 10,
            )
        
        return SearchSimilarResponse(
            query_mvr_people_uuid=request.mvr_people_uuid,
            total_results=len(results),
            results=results,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching similar MVR-People: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search similar MVR-People: {str(e)}"
        )


# ============================================================================
# ENDPOINT 5: Search MVR-People by Demographics
# ============================================================================

@router.post(
    "/search/demographics",
    response_model=SearchDemographicsResponse,
    summary="Search MVR-People by Demographics",
    description="Search MVR-People by age/gender filters",
)
async def search_mvr_by_demographics(
    request: SearchDemographicsRequest,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user),
):
    """
    Search MVR-People by age and gender filters.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - age_min: Minimum age (optional)
    - age_max: Maximum age (optional)
    - gender: Gender filter ("male", "female", "unknown") (optional)
    - min_confidence: Minimum confidence for age/gender (default: 0.7)
    - page: Page number (default: 1)
    - page_size: Results per page (default: 20)
    
    **Returns:**
    - 200 OK: Paginated list of MVR-People matching demographics
    """
    logger.info(f"Searching MVR-People by demographics (user: {current_user.get('email')})")
    
    try:
        # Search by demographics
        results = await mvr_service.search_by_demographics(
            age_min=request.age_min,
            age_max=request.age_max,
            gender=request.gender,
            min_confidence=request.min_confidence or 0.7,
            page=request.page or 1,
            page_size=request.page_size or 20,
        )
        
        return SearchDemographicsResponse(
            total_results=results['total'],
            page=results['page'],
            page_size=results['page_size'],
            results=results['data'],
        )
    
    except Exception as e:
        logger.error(f"Error searching MVR-People by demographics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search by demographics: {str(e)}"
        )


# ============================================================================
# ENDPOINT 6: Link Individual to Existing MVR-People
# ============================================================================

@router.post(
    "/{mvr_people_uuid}/link-individual",
    response_model=LinkIndividualResponse,
    summary="Link Individual to MVR-People",
    description="Link an Individual to existing MVR-People (person re-identification)",
)
async def link_individual_to_mvr(
    mvr_people_uuid: UUID,
    request: LinkIndividualRequest,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Link an Individual to existing MVR-People.
    
    **Use Case:** Person re-identification across videos/sessions
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - mvr_people_uuid: UUID of the MVR-People
    - individual_uuid: UUID of the Individual to link
    - confidence_score: Similarity confidence (0-1)
    
    **Returns:**
    - 200 OK: Individual linked successfully
    - 404 Not Found: MVR-People or Individual not found
    - 400 Bad Request: Individual already linked
    """
    logger.info(
        f"Linking Individual {request.individual_uuid} to MVR-People {mvr_people_uuid} "
        f"(user: {current_user.get('email')})"
    )
    
    try:
        # Link Individual to MVR-People
        result = await mvr_repository.link_individual_to_mvr(
            individual_uuid=request.individual_uuid,
            mvr_uuid=mvr_people_uuid,
            confidence_score=request.confidence_score,
            is_representative=False,  # Not the original Individual
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to link Individual to MVR-People"
            )
        
        # Get updated MVR-People
        mvr_record = await mvr_repository.get_mvr_people_by_uuid(mvr_people_uuid)
        
        return LinkIndividualResponse(
            mvr_people_uuid=mvr_people_uuid,
            individual_uuid=request.individual_uuid,
            linked_at=result['linked_at'],
            confidence_score=request.confidence_score,
            total_linked_individuals=mvr_record.get('total_linked_individuals', 0),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking Individual to MVR-People: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link Individual: {str(e)}"
        )


# ============================================================================
# ENDPOINT 7: Batch Create MVR-People
# ============================================================================

@router.post(
    "/batch/create",
    response_model=BatchCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch Create MVR-People",
    description="Create MVR-People for multiple Individuals (batch processing)",
)
async def batch_create_mvr_people(
    request: BatchCreateRequest,
    background_processor: MVRBackgroundProcessor = Depends(get_mvr_background_processor),
    current_user: dict = Depends(get_current_user),
):
    """
    Create MVR-People for multiple Individuals in batch.
    
    **Processing:** Always uses background processing for efficiency
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuids: List of Individual UUIDs
    - background_processing: Enable async processing (default: true)
    
    **Returns:**
    - 202 Accepted: Batch creation queued
    - 400 Bad Request: Invalid request (empty list, etc.)
    """
    logger.info(
        f"Batch creating MVR-People for {len(request.individual_uuids)} Individuals "
        f"(user: {current_user.get('email')})"
    )
    
    try:
        if not request.individual_uuids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="individual_uuids list cannot be empty"
            )
        
        # Queue batch processing tasks
        batch_id = None  # TODO: Implement batch tracking
        
        for individual_uuid in request.individual_uuids:
            await background_processor.process_individual(
                individual_uuid=individual_uuid,
                auto_match=False,
            )
        
        # Estimate completion time (10 seconds per Individual)
        estimated_seconds = len(request.individual_uuids) * 10
        
        return BatchCreateResponse(
            total_queued=len(request.individual_uuids),
            batch_id=batch_id,
            status="processing",
            individual_uuids=request.individual_uuids,
            estimated_completion_seconds=estimated_seconds,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch creating MVR-People: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch create MVR-People: {str(e)}"
        )


# ============================================================================
# ENDPOINT 8: Get MVR-People Processing Status
# ============================================================================

@router.get(
    "/{mvr_people_uuid}/status",
    response_model=MVRStatusResponse,
    summary="Get MVR-People Processing Status",
    description="Check processing status of MVR-People creation",
)
async def get_mvr_processing_status(
    mvr_people_uuid: UUID,
    background_processor: MVRBackgroundProcessor = Depends(get_mvr_background_processor),
    current_user: dict = Depends(get_current_user),
):
    """
    Check processing status of MVR-People creation.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - mvr_people_uuid: UUID of the MVR-People
    
    **Returns:**
    - 200 OK: Processing status
    - 404 Not Found: MVR-People not found
    """
    logger.info(f"Checking status of MVR-People {mvr_people_uuid} (user: {current_user.get('email')})")
    
    try:
        # Get task status from background processor
        # TODO: Implement task status tracking by MVR UUID
        
        return MVRStatusResponse(
            mvr_people_uuid=mvr_people_uuid,
            status="completed",  # Placeholder
            created_at=datetime.now(),
            started_at=datetime.now(),
            completed_at=datetime.now(),
            processing_error=None,
            progress_percentage=100,
            current_step="Completed",
        )
    
    except Exception as e:
        logger.error(f"Error getting MVR-People status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


# ============================================================================
# ENDPOINT 9: Match Individuals (Find Similar)
# ============================================================================

@router.post(
    "/individuals/{individual_uuid}/match",
    response_model=MatchIndividualResponse,
    summary="Match Individuals",
    description="Find other Individuals that match the given Individual based on face similarity",
)
async def match_individual(
    individual_uuid: UUID,
    request: Optional[MatchIndividualRequest] = Body(default=None),
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher),
    current_user: dict = Depends(get_current_user),
):
    """
    Find other Individuals that match the given Individual.
    
    **Matching Algorithm:** Uses MVRMatcher with configurable threshold
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuid: UUID of the Individual to match
    - threshold: Similarity threshold (default: 0.7)
    - auto_merge: Automatically merge matches above threshold (default: false)
    - max_results: Maximum results to return (default: 10)
    
    **Returns:**
    - 200 OK: List of matching Individuals with similarity scores
    - 404 Not Found: Individual not found
    """
    logger.info(f"Matching Individual {individual_uuid} (user: {current_user.get('email')})")
    
    # Parse request
    threshold = 0.7
    auto_merge = False
    max_results = 10
    
    if request:
        threshold = request.threshold or threshold
        auto_merge = request.auto_merge
        max_results = request.max_results or max_results
    
    try:
        # Find matches
        matches = await mvr_matcher.find_matching_mvr(
            individual_uuid=individual_uuid,
            threshold=threshold,
        )
        
        # Auto-merge if enabled
        if auto_merge and matches:
            # TODO: Implement auto-merge logic
            logger.info(f"Auto-merge enabled, merging {len(matches)} matches")
        
        # Calculate matches above threshold
        matches_above_threshold = sum(
            1 for match in matches if match['similarity_score'] >= threshold
        )
        
        return MatchIndividualResponse(
            individual_uuid=individual_uuid,
            matches=matches[:max_results],
            total_matches=len(matches),
            matches_above_threshold=matches_above_threshold,
            threshold_used=threshold,
        )
    
    except Exception as e:
        logger.error(f"Error matching Individual {individual_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to match Individual: {str(e)}"
        )


# ============================================================================
# ENDPOINT 10: Merge Individuals to Single MVR-People
# ============================================================================

@router.post(
    "/merge",
    response_model=MergeIndividualsResponse,
    summary="Merge Individuals",
    description="Manually merge two Individuals to single MVR-People (predominant based on quality)",
)
async def merge_individuals(
    request: MergeIndividualsRequest,
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher),
    current_user: dict = Depends(get_current_user),
):
    """
    Merge two Individuals to single MVR-People.
    
    **Merge Logic:** Predominant MVR selected by quality score (higher wins)
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_a_uuid: First Individual UUID
    - individual_b_uuid: Second Individual UUID
    - similarity_score: Similarity score for audit trail
    - triggered_by: Trigger source (default: "manual")
    
    **Returns:**
    - 200 OK: Merge completed successfully
    - 400 Bad Request: Invalid request (same Individual, etc.)
    - 404 Not Found: One or both Individuals not found
    """
    logger.info(
        f"Merging Individuals {request.individual_a_uuid} and {request.individual_b_uuid} "
        f"(user: {current_user.get('email')})"
    )
    
    try:
        # Validate request
        if request.individual_a_uuid == request.individual_b_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot merge an Individual with itself"
            )
        
        # Execute merge
        merge_result = await mvr_matcher.merge_individuals(
            individual_a_uuid=request.individual_a_uuid,
            individual_b_uuid=request.individual_b_uuid,
            similarity_score=request.similarity_score,
            triggered_by=request.triggered_by or "manual",
        )
        
        if not merge_result or not merge_result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to merge Individuals"
            )
        
        return MergeIndividualsResponse(
            success=True,
            predominant_mvr_uuid=merge_result['predominant_mvr_uuid'],
            orphaned_mvr_uuid=merge_result['orphaned_mvr_uuid'],
            reassigned_individual_uuid=merge_result['reassigned_individual_uuid'],
            similarity_score=request.similarity_score,
            predominant_quality_score=merge_result.get('predominant_quality_score'),
            orphaned_quality_score=merge_result.get('orphaned_quality_score'),
            merged_at=merge_result.get('merged_at', datetime.now()),
            message=merge_result.get('message'),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error merging Individuals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to merge Individuals: {str(e)}"
        )


# ============================================================================
# ENDPOINT 11: Get Merge History for Individual
# ============================================================================

@router.get(
    "/individuals/{individual_uuid}/merge-history",
    response_model=MergeHistoryResponse,
    summary="Get Merge History",
    description="Get all merge operations involving this Individual",
)
async def get_merge_history(
    individual_uuid: UUID,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Get all merge operations involving this Individual.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuid: UUID of the Individual
    
    **Returns:**
    - 200 OK: Merge history with current and previous MVR-People
    - 404 Not Found: Individual not found
    """
    logger.info(f"Retrieving merge history for Individual {individual_uuid} (user: {current_user.get('email')})")
    
    try:
        # Get current MVR-People
        current_mvr = await mvr_repository.get_mvr_people_by_individual(individual_uuid)
        
        # Get previous MVR-People (orphaned)
        previous_mvr = await mvr_repository.get_orphaned_mvr_for_individual(individual_uuid)
        
        # Get merge events
        merge_events = await mvr_repository.get_merge_audit_log(individual_uuid=individual_uuid)
        
        return MergeHistoryResponse(
            individual_uuid=individual_uuid,
            current_mvr_people=current_mvr,
            previous_mvr_people=previous_mvr,
            merge_events=merge_events,
            total_merges=len(merge_events),
        )
    
    except Exception as e:
        logger.error(f"Error retrieving merge history for Individual {individual_uuid}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve merge history: {str(e)}"
        )


# ============================================================================
# ENDPOINT 12: Get Orphaned MVR-People
# ============================================================================

@router.get(
    "/orphaned",
    response_model=OrphanedMVRResponse,
    summary="Get Orphaned MVR-People",
    description="List all orphaned MVR-People (for audit/cleanup)",
)
async def get_orphaned_mvr_people(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Results per page"),
    orphaned_after: Optional[datetime] = Query(None, description="Filter by orphaned_at date"),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    List all orphaned MVR-People.
    
    **Use Case:** Audit trail and cleanup of merged MVR-People
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - page: Page number (default: 1)
    - page_size: Results per page (default: 20, max: 100)
    - orphaned_after: Filter by orphaned_at date (optional)
    
    **Returns:**
    - 200 OK: Paginated list of orphaned MVR-People
    """
    logger.info(f"Retrieving orphaned MVR-People (user: {current_user.get('email')})")
    
    try:
        # Get orphaned MVR-People
        orphaned_mvr = await mvr_repository.get_orphaned_mvr_people(
            page=page,
            page_size=page_size,
            orphaned_after=orphaned_after,
        )
        
        return OrphanedMVRResponse(
            total_orphaned=orphaned_mvr['total'],
            page=page,
            page_size=page_size,
            results=orphaned_mvr['data'],
        )
    
    except Exception as e:
        logger.error(f"Error retrieving orphaned MVR-People: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve orphaned MVR-People: {str(e)}"
        )


# ============================================================================
# ENDPOINT 13: Update Matching Configuration
# ============================================================================

@router.put(
    "/config/matching",
    response_model=MatchingConfigResponse,
    summary="Update Matching Configuration",
    description="Update matching threshold and other configuration",
)
async def update_matching_config(
    config: MatchingConfigUpdate,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Update matching configuration.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - default_matching_threshold: Similarity threshold (0-1)
    - auto_merge_enabled: Enable auto-merge on match
    - min_quality_threshold: Minimum quality score (0-1)
    
    **Returns:**
    - 200 OK: Updated configuration
    - 400 Bad Request: Invalid configuration values
    """
    logger.info(f"Updating matching configuration (user: {current_user.get('email')})")
    
    try:
        # Update configuration
        updated_config = await mvr_repository.update_matching_config(
            similarity_threshold=config.default_matching_threshold,
            auto_merge_enabled=config.auto_merge_enabled,
            min_quality_threshold=config.min_quality_threshold,
        )
        
        return MatchingConfigResponse(
            success=True,
            updated_config=updated_config,
            updated_at=datetime.now(),
        )
    
    except Exception as e:
        logger.error(f"Error updating matching configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


# ============================================================================
# ENDPOINT 14: Get Matching Configuration
# ============================================================================

@router.get(
    "/config/matching",
    response_model=MatchingConfigResponse,
    summary="Get Matching Configuration",
    description="Get current matching configuration",
)
async def get_matching_config(
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Get current matching configuration.
    
    **Authentication:** Requires valid JWT token
    
    **Returns:**
    - 200 OK: Current configuration
    """
    logger.info(f"Retrieving matching configuration (user: {current_user.get('email')})")
    
    try:
        # Get current configuration
        config = await mvr_repository.get_matching_config()
        
        return MatchingConfigResponse(
            default_matching_threshold=config.get('similarity_threshold', 0.7),
            auto_merge_enabled=config.get('auto_merge_enabled', True),
            min_quality_threshold=config.get('min_quality_threshold', 0.6),
            age_range_tolerance=config.get('age_range_tolerance', 10),
            gender_match_required=config.get('gender_match_required', False),
            orphan_retention_days=config.get('orphan_retention_days', 365),
            last_updated=config.get('updated_at'),
        )
    
    except Exception as e:
        logger.error(f"Error retrieving matching configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration: {str(e)}"
        )


# ============================================================================
# ENDPOINT 15: MVR-People System Health Check
# ============================================================================

@router.get(
    "/health",
    response_model=None,  # Dynamic response based on health status
    status_code=status.HTTP_200_OK,
    summary="MVR-People System Health Check",
    description="Comprehensive health check for MVR-People system including database, "
                "ML models, processing queue, and statistics. "
                "Does NOT require authentication for monitoring tools.",
)
async def mvr_health_check():
    """
    Get comprehensive health status of MVR-People system.
    
    **Components Checked:**
    - Database connection and performance
    - ML models (FaceNet, Age, Gender)
    - Background processing queue
    - System statistics
    
    **No Authentication Required** - Public endpoint for monitoring
    
    **Response Status:**
    - "healthy" - All systems operational
    - "degraded" - Some components have issues but system functional
    - "unhealthy" - Critical components failing
    
    **Returns:**
    - 200 OK: Health status with detailed metrics
    - 503 Service Unavailable: Critical failure
    """
    import time
    from datetime import datetime
    import main
    
    start_time = time.time()
    warnings = []
    errors = []
    overall_status = "healthy"
    
    # Check if MVR services are initialized
    if not main.mvr_repository or not main.mvr_service or not main.mvr_background_processor:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "errors": ["MVR-People services not initialized - check service startup logs"],
                "warnings": [],
                "database": {
                    "connected": False,
                    "pool_size": 0,
                    "idle_connections": 0,
                    "response_time_ms": 0,
                    "pgvector_available": False,
                },
                "ml_models": {
                    "facenet_loaded": False,
                    "age_model_loaded": False,
                    "gender_model_loaded": False,
                    "total_models_loaded": 0,
                    "model_load_time_ms": 0,
                },
                "processing_queue": {
                    "queue_size": 0,
                    "processing_tasks": 0,
                    "pending_tasks": 0,
                    "failed_tasks_last_hour": 0,
                    "average_processing_time_ms": 0,
                },
                "statistics": {
                    "total_mvr_people": 0,
                    "active_mvr_people": 0,
                    "orphaned_mvr_people": 0,
                    "individuals_with_mvr": 0,
                    "total_merge_operations": 0,
                    "average_quality_score": 0.0,
                },
                "uptime_seconds": 0,
                "last_mvr_created_at": None,
                "last_merge_at": None,
            }
        )
    
    mvr_repository = main.mvr_repository
    mvr_service = main.mvr_service
    mvr_background_processor = main.mvr_background_processor
    
    try:
        # ====================================================================
        # 1. Database Health Check
        # ====================================================================
        db_start = time.time()
        try:
            # Test database connection with simple query
            pool_stats = await mvr_repository.pool.execute(
                "SELECT COUNT(*) FROM mvr_people"
            )
            db_response_time = (time.time() - db_start) * 1000  # ms
            
            # Get pool statistics
            pool_size = mvr_repository.pool.get_size()
            idle_connections = mvr_repository.pool.get_idle_size()
            
            # Check pgvector extension
            pgvector_check = await mvr_repository.pool.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            
            database_health = {
                "connected": True,
                "pool_size": pool_size,
                "idle_connections": idle_connections,
                "response_time_ms": round(db_response_time, 2),
                "pgvector_available": pgvector_check,
            }
            
            if db_response_time > 1000:  # > 1 second
                warnings.append(f"Database slow response: {db_response_time:.0f}ms")
                overall_status = "degraded"
                
            if not pgvector_check:
                errors.append("pgvector extension not available")
                overall_status = "unhealthy"
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            database_health = {
                "connected": False,
                "pool_size": 0,
                "idle_connections": 0,
                "response_time_ms": 0,
                "pgvector_available": False,
            }
            errors.append(f"Database connection failed: {str(e)}")
            overall_status = "unhealthy"
        
        # ====================================================================
        # 2. ML Models Health Check
        # ====================================================================
        ml_start = time.time()
        try:
            # Check if ML processor is available
            ml_processor = mvr_service.ml_processor
            
            # Check model availability
            facenet_loaded = hasattr(ml_processor, 'face_model') and ml_processor.face_model is not None
            age_loaded = hasattr(ml_processor, 'age_model') and ml_processor.age_model is not None
            gender_loaded = hasattr(ml_processor, 'gender_model') and ml_processor.gender_model is not None
            
            total_loaded = sum([facenet_loaded, age_loaded, gender_loaded])
            ml_load_time = (time.time() - ml_start) * 1000  # ms
            
            ml_models_health = {
                "facenet_loaded": facenet_loaded,
                "age_model_loaded": age_loaded,
                "gender_model_loaded": gender_loaded,
                "total_models_loaded": total_loaded,
                "model_load_time_ms": round(ml_load_time, 2),
            }
            
            if total_loaded < 3:
                warnings.append(f"Only {total_loaded}/3 ML models loaded")
                overall_status = "degraded"
                
        except Exception as e:
            logger.error(f"ML models health check failed: {e}")
            ml_models_health = {
                "facenet_loaded": False,
                "age_model_loaded": False,
                "gender_model_loaded": False,
                "total_models_loaded": 0,
                "model_load_time_ms": 0,
            }
            warnings.append(f"ML models check failed: {str(e)}")
            overall_status = "degraded"
        
        # ====================================================================
        # 3. Processing Queue Health Check
        # ====================================================================
        try:
            # Get background processor statistics (await since it's async)
            stats = await mvr_background_processor.get_statistics()
            
            processing_queue_health = {
                "queue_size": stats.get('total_tasks', 0),
                "processing_tasks": stats.get('successful_tasks', 0),
                "pending_tasks": stats.get('total_tasks', 0) - stats.get('successful_tasks', 0),
                "failed_tasks_last_hour": stats.get('failed_tasks', 0),
                "average_processing_time_ms": stats.get('average_processing_time', 0) * 1000,
            }
            
            if processing_queue_health['failed_tasks_last_hour'] > 10:
                warnings.append(f"High failure rate: {processing_queue_health['failed_tasks_last_hour']} failures")
                overall_status = "degraded"
                
        except Exception as e:
            logger.error(f"Processing queue health check failed: {e}")
            processing_queue_health = {
                "queue_size": 0,
                "processing_tasks": 0,
                "pending_tasks": 0,
                "failed_tasks_last_hour": 0,
                "average_processing_time_ms": 0,
            }
            warnings.append(f"Queue check failed: {str(e)}")
        
        # ====================================================================
        # 4. System Statistics
        # ====================================================================
        try:
            # Get MVR-People statistics from database
            total_mvr = await mvr_repository.pool.fetchval(
                "SELECT COUNT(*) FROM mvr_people"
            )
            active_mvr = await mvr_repository.pool.fetchval(
                "SELECT COUNT(*) FROM mvr_people WHERE is_orphaned = FALSE"
            )
            orphaned_mvr = await mvr_repository.pool.fetchval(
                "SELECT COUNT(*) FROM mvr_people WHERE is_orphaned = TRUE"
            )
            individuals_with_mvr = await mvr_repository.pool.fetchval(
                "SELECT COUNT(*) FROM individual_mvr_mapping"
            )
            total_merges = await mvr_repository.pool.fetchval(
                "SELECT COUNT(*) FROM mvr_merge_audit_log"
            )
            avg_quality = await mvr_repository.pool.fetchval(
                "SELECT AVG(quality_score) FROM mvr_people WHERE is_orphaned = FALSE"
            )
            
            # Get last MVR creation time
            last_mvr_created = await mvr_repository.pool.fetchval(
                "SELECT MAX(created_at) FROM mvr_people"
            )
            
            # Get last merge time
            last_merge = await mvr_repository.pool.fetchval(
                "SELECT MAX(merge_timestamp) FROM mvr_merge_audit_log"
            )
            
            statistics = {
                "total_mvr_people": total_mvr or 0,
                "active_mvr_people": active_mvr or 0,
                "orphaned_mvr_people": orphaned_mvr or 0,
                "individuals_with_mvr": individuals_with_mvr or 0,
                "total_merge_operations": total_merges or 0,
                "average_quality_score": round(float(avg_quality or 0.0), 3),
            }
            
        except Exception as e:
            logger.error(f"Statistics collection failed: {e}")
            statistics = {
                "total_mvr_people": 0,
                "active_mvr_people": 0,
                "orphaned_mvr_people": 0,
                "individuals_with_mvr": 0,
                "total_merge_operations": 0,
                "average_quality_score": 0.0,
            }
            last_mvr_created = None
            last_merge = None
            warnings.append(f"Statistics collection failed: {str(e)}")
        
        # ====================================================================
        # 5. Build Response
        # ====================================================================
        total_time = time.time() - start_time
        
        response = {
            "status": overall_status,
            "timestamp": datetime.utcnow(),
            "version": "1.0.0",
            "database": database_health,
            "ml_models": ml_models_health,
            "processing_queue": processing_queue_health,
            "statistics": statistics,
            "uptime_seconds": round(total_time, 2),
            "last_mvr_created_at": last_mvr_created,
            "last_merge_at": last_merge,
            "warnings": warnings,
            "errors": errors,
        }
        
        # Return 503 if unhealthy
        if overall_status == "unhealthy":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=response
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response
        )
        
    except Exception as e:
        logger.error(f"Health check failed critically: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "errors": [f"Critical health check failure: {str(e)}"],
                "warnings": [],
            }
        )


# ============================================================================
# ENDPOINT 15: Batch Match and Merge Individuals
# ============================================================================

@router.post(
    "/batch-match-and-merge",
    response_model=BatchMatchAndMergeResponse,
    summary="Batch Match and Merge Individuals",
    description="Batch operation to match and merge multiple individuals "
                "from a tracking session",
)
async def batch_match_and_merge(
    request: BatchMatchAndMergeRequest,
    mvr_matcher: MVRMatcher = Depends(get_mvr_matcher),
    current_user: dict = Depends(get_current_user),
):
    """
    Batch match and merge all individuals from a tracking session.
    
    This endpoint:
    1. Takes a list of individual UUIDs (from tracking session)
    2. For each individual, finds matching individuals (face similarity)
    3. Merges duplicates above the similarity threshold
    4. Returns original count vs unique count
    
    **Use Case:** Get unique individual count after cross-video tracking
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - individual_uuids: List of individual UUIDs to process
    - threshold: Similarity threshold (default: 0.7)
    - triggered_by: Source identifier (default: "batch_auto_match")
    - session_uuid: Optional tracking session UUID for audit
    
    **Returns:**
    - 200 OK: Batch merge completed with statistics
    - 400 Bad Request: Invalid request (empty list, invalid UUIDs)
    - 500 Internal Server Error: Processing failed
    
    **Example:**
    ```
    POST /api/v1/mvr-people/batch-match-and-merge
    {
      "individual_uuids": ["uuid-1", "uuid-2", ..., "uuid-15"],
      "threshold": 0.7,
      "triggered_by": "cross_video_tracking_session",
      "session_uuid": "session-abc-123"
    }
    
    Response:
    {
      "success": true,
      "original_count": 15,
      "unique_count": 12,
      "merge_count": 3,
      "merges": [...],
      "processing_time_seconds": 2.34
    }
    ```
    """
    import time
    start_time = time.time()
    
    logger.info(
        f"Batch match and merge: {len(request.individual_uuids)} individuals "
        f"(threshold: {request.threshold}, "
        f"user: {current_user.get('email')})"
    )
    
    original_count = len(request.individual_uuids)
    processed_individuals = set()
    merge_count = 0
    merges = []
    skipped_count = 0
    
    try:
        # Process each individual
        for individual_uuid in request.individual_uuids:
            individual_uuid_str = str(individual_uuid)
            
            # Skip if already processed (was orphaned in a previous merge)
            if individual_uuid_str in processed_individuals:
                logger.debug(
                    f"Skipping {individual_uuid_str} (already processed)"
                )
                continue
            
            try:
                # Get or create MVR record for this individual
                mvr_record = await mvr_matcher.repository.get_mvr_people_by_individual(
                    individual_uuid=individual_uuid_str
                )
                
                # If no MVR exists, create one from the individual
                if not mvr_record:
                    logger.info(
                        f"No MVR record for {individual_uuid_str}, "
                        f"creating MVR from individual"
                    )
                    try:
                        # Get mvr_service dependency
                        from background.mvr_helper import get_mvr_service
                        mvr_svc = get_mvr_service()
                        if not mvr_svc:
                            logger.warning(
                                f"MVR service not available, skipping "
                                f"{individual_uuid_str}"
                            )
                            skipped_count += 1
                            continue
                        
                        # Create MVR from individual
                        mvr_result = await mvr_svc.create_mvr_people_from_individual(
                            individual_uuid=individual_uuid_str
                        )
                        
                        if not mvr_result or not mvr_result.get('success'):
                            logger.warning(
                                f"Failed to create MVR for "
                                f"{individual_uuid_str}, skipping"
                            )
                            skipped_count += 1
                            continue
                        
                        # Now get the created MVR record
                        mvr_record = await mvr_matcher.repository.get_mvr_people_by_individual(
                            individual_uuid=individual_uuid_str
                        )
                        
                        if not mvr_record:
                            logger.warning(
                                f"Created MVR but couldn't retrieve it for "
                                f"{individual_uuid_str}, skipping"
                            )
                            skipped_count += 1
                            continue
                            
                    except Exception as create_error:
                        logger.error(
                            f"Error creating MVR for {individual_uuid_str}: "
                            f"{create_error}"
                        )
                        skipped_count += 1
                        continue
                
                # Extract face embedding
                face_embedding_data = mvr_record.get('face_embedding')
                if not face_embedding_data:
                    logger.warning(
                        f"No face embedding for {individual_uuid_str}, "
                        f"skipping"
                    )
                    skipped_count += 1
                    continue
                
                # Convert to numpy array if needed
                import numpy as np
                if isinstance(face_embedding_data, list):
                    face_embedding = np.array(
                        face_embedding_data, dtype=np.float32
                    )
                elif isinstance(face_embedding_data, np.ndarray):
                    face_embedding = face_embedding_data
                else:
                    logger.warning(
                        f"Invalid embedding format for {individual_uuid_str}, "
                        f"skipping"
                    )
                    skipped_count += 1
                    continue
                
                # Find matches for this individual
                match = await mvr_matcher.find_matching_mvr(
                    individual_uuid=individual_uuid_str,
                    face_embedding=face_embedding,
                    similarity_threshold=request.threshold,
                )
                
                # Convert single match to list for loop compatibility
                matches = [match] if match else []
                
                logger.debug(
                    f"Found {len(matches)} potential matches for "
                    f"{individual_uuid_str}"
                )
                
                # Merge each match above threshold
                for match in matches:
                    match_uuid = str(match.get('individual_uuid'))
                    similarity = match.get('similarity_score', 0.0)
                    
                    # Skip if already processed
                    if match_uuid in processed_individuals:
                        continue
                    
                    # Only merge if above threshold
                    if similarity >= request.threshold:
                        logger.info(
                            f"Merging {individual_uuid_str} with {match_uuid} "
                            f"(similarity: {similarity:.3f})"
                        )
                        
                        try:
                            # Execute merge
                            merge_result = await mvr_matcher.merge_individuals(
                                individual_a_uuid=individual_uuid_str,
                                individual_b_uuid=match_uuid,
                                similarity_score=similarity,
                                triggered_by=request.triggered_by,
                            )
                            
                            if merge_result and merge_result.get('success'):
                                # Track the orphaned individual
                                orphaned_mvr_uuid = merge_result.get(
                                    'orphaned_mvr_uuid'
                                )
                                predominant_mvr_uuid = merge_result.get(
                                    'predominant_mvr_uuid'
                                )
                                reassigned_uuid = merge_result.get(
                                    'reassigned_individual_uuid'
                                )
                                
                                processed_individuals.add(str(reassigned_uuid))
                                merge_count += 1
                                
                                # Record merge details
                                merges.append(MergeDetail(
                                    predominant_individual_uuid=individual_uuid,
                                    orphaned_individual_uuid=match_uuid,
                                    predominant_mvr_uuid=predominant_mvr_uuid,
                                    orphaned_mvr_uuid=orphaned_mvr_uuid,
                                    similarity_score=similarity,
                                    merged_at=merge_result.get(
                                        'merged_at', datetime.now()
                                    ),
                                ))
                                
                                logger.info(
                                    f"Successfully merged: {reassigned_uuid} "
                                    f"is now orphaned"
                                )
                            else:
                                logger.warning(
                                    f"Merge failed for {individual_uuid_str} "
                                    f"and {match_uuid}"
                                )
                                skipped_count += 1
                                
                        except Exception as merge_error:
                            logger.error(
                                f"Error merging {individual_uuid_str} with "
                                f"{match_uuid}: {merge_error}"
                            )
                            skipped_count += 1
                            # Continue with next match
                            continue
                
                # Mark current individual as processed
                processed_individuals.add(individual_uuid_str)
                
            except Exception as match_error:
                logger.error(
                    f"Error finding matches for {individual_uuid_str}: "
                    f"{match_error}"
                )
                skipped_count += 1
                # Continue with next individual
                continue
        
        # Calculate final counts
        unique_count = original_count - merge_count
        processing_time = time.time() - start_time
        
        logger.info(
            f"Batch merge complete: {original_count} → {unique_count} unique "
            f"({merge_count} merged, {skipped_count} skipped) "
            f"in {processing_time:.2f}s"
        )
        
        return BatchMatchAndMergeResponse(
            success=True,
            original_count=original_count,
            unique_count=unique_count,
            merge_count=merge_count,
            merges=merges,
            skipped_count=skipped_count,
            processing_time_seconds=round(processing_time, 2),
            message=(
                f"Successfully merged {merge_count} duplicates from "
                f"{original_count} individuals"
            ),
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Batch merge failed: {e}", exc_info=True)
        
        # Return partial results if we made any progress
        if merge_count > 0:
            unique_count = original_count - merge_count
            return BatchMatchAndMergeResponse(
                success=False,
                original_count=original_count,
                unique_count=unique_count,
                merge_count=merge_count,
                merges=merges,
                skipped_count=skipped_count,
                processing_time_seconds=round(processing_time, 2),
                message=(
                    f"Partial completion: {merge_count} merged before error: "
                    f"{str(e)}"
                ),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Batch merge failed: {str(e)}"
            )


# ============================================================================
# ENDPOINT: Search Existing MVR People by Video UUIDs
# ============================================================================

@router.post(
    "/search/by-videos",
    response_model=MVRPeopleSearchResponse,
    summary="Search Existing MVR People by Video UUIDs",
    description="Search for existing MVR people detected in specific videos. "
                "Returns cached/existing data without triggering any merge "
                "operations. Only queries VMeta's own database.",
)
async def search_mvr_people_by_videos(
    video_uuids: List[str] = Body(
        ..., embed=True, description="List of video UUIDs to search"
    ),
    start_time: Optional[datetime] = Body(
        None, description="Optional start time filter"
    ),
    end_time: Optional[datetime] = Body(
        None, description="Optional end time filter"
    ),
    limit: int = Body(100, description="Max results (default: 100, max: 500)"),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Search for existing MVR people detected in specific videos.
    
    This endpoint fetches EXISTING MVR people and their linked individuals
    that appear in the provided video UUIDs. It does NOT trigger any merge
    operations - it only retrieves cached data.
    
    **Use Case:** Fetch existing MVR analysis results for a collection's
    videos without reprocessing.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - video_uuids: List of video UUIDs to search
    - start_time: Optional start time filter (ISO 8601)
    - end_time: Optional end time filter (ISO 8601)
    - limit: Maximum results to return (default: 100, max: 500)
    
    **Returns:**
    - 200 OK: List of MVR people with aggregated data
    - 400 Bad Request: Invalid parameters
    - 500 Internal Server Error: Database error
    """
    logger.info(
        f"Searching existing MVR people for {len(video_uuids)} videos "
        f"(user: {current_user.get('email')})"
    )
    
    try:
        if not video_uuids:
            return MVRPeopleSearchResponse(
                success=True,
                total_results=0,
                mvr_people=[],
                search_parameters={
                    "video_uuids": [],
                    "start_time": (
                        start_time.isoformat() if start_time else None
                    ),
                    "end_time": (
                        end_time.isoformat() if end_time else None
                    ),
                    "limit": limit
                },
                message="No videos provided"
            )
        
        # Convert string UUIDs to UUID objects
        video_uuid_objs = [UUID(vid) for vid in video_uuids]
        
        # Get database connection from the repository's pool
        async with mvr_repository.pool.acquire() as conn:
            # Find all individuals that appear in these videos
            # NOTE: When video UUIDs are provided, we search by video UUID only.
            # The start_time/end_time parameters are IGNORED because they represent
            # video creation times (from media service), but individual_video_appearances
            # stores appearance timestamps WITHIN the video (e.g., "person at 2.5 seconds").
            # These are different timestamp domains and should not be mixed.
            individuals_query = """
                SELECT DISTINCT individual_uuid
                FROM individual_video_appearances
                WHERE video_uuid = ANY($1::uuid[])
            """
            
            individual_rows = await conn.fetch(
                individuals_query,
                video_uuid_objs
            )
            
            if not individual_rows:
                logger.info("No individuals found in provided videos")
                return MVRPeopleSearchResponse(
                    success=True,
                    total_results=0,
                    mvr_people=[],
                    search_parameters={
                        "video_uuids": video_uuids,
                        "start_time": (
                            start_time.isoformat() if start_time else None
                        ),
                        "end_time": (
                            end_time.isoformat() if end_time else None
                        ),
                        "limit": limit
                    },
                    message="No individuals found in videos"
                )
            
            individual_uuids = [
                str(row['individual_uuid']) for row in individual_rows
            ]
            
            # Find MVR people linked to these individuals
            mvr_query = """
                SELECT DISTINCT
                    mp.mvr_people_uuid,
                    mp.quality_score,
                    mp.confidence_score,
                    mp.age_min,
                    mp.age_max,
                    mp.gender,
                    mp.created_at,
                    mp.updated_at
                FROM mvr_people mp
                INNER JOIN individual_mvr_mapping imm
                  ON mp.mvr_people_uuid = imm.mvr_people_uuid
                WHERE imm.individual_uuid = ANY($1::uuid[])
                    AND mp.is_orphaned = false
                ORDER BY mp.created_at DESC
                LIMIT $2
            """
            
            mvr_records = await conn.fetch(
                mvr_query,
                individual_uuids,
                limit
            )
            
            results = []
            
            # For each MVR person, get all linked individuals & appearances
            for mvr_record in mvr_records:
                mvr_uuid = str(mvr_record['mvr_people_uuid'])
                
                # Get all linked individual UUIDs for this MVR person
                linked_individuals_query = """
                    SELECT individual_uuid
                    FROM individual_mvr_mapping
                    WHERE mvr_people_uuid = $1
                """
                linked_rows = await conn.fetch(
                    linked_individuals_query, mvr_uuid
                )
                linked_individual_uuids = [
                    str(row['individual_uuid']) for row in linked_rows
                ]
                
                # Get appearances for these individuals in our target videos
                # NOTE: We do NOT filter by start_time/end_time here because:
                # 1. We already filtered by video_uuid (which is the correct filter)
                # 2. Appearance timestamps are WITHIN video (relative), not video creation times
                # 3. Flutter sends Athens local time, DB has UTC - comparison would fail
                appearances_query = """
                    SELECT
                        iva.video_uuid,
                        iva.person_object_uuid,
                        iva.start_timestamp,
                        iva.end_timestamp,
                        iva.confidence
                    FROM individual_video_appearances iva
                    WHERE iva.individual_uuid = ANY($1::uuid[])
                        AND iva.video_uuid = ANY($2::uuid[])
                    ORDER BY iva.start_timestamp ASC
                """
                
                appearances_rows = await conn.fetch(
                    appearances_query,
                    linked_individual_uuids,
                    video_uuid_objs
                )
                
                if not appearances_rows:
                    # Skip MVR people with no appearances in target videos
                    continue
                
                # Build appearance objects
                appearances = [
                    MVRIndividualAppearance(
                        video_uuid=str(row['video_uuid']),
                        person_object_uuid=str(row['person_object_uuid']),
                        start_timestamp=row['start_timestamp'],
                        end_timestamp=row['end_timestamp'],
                        confidence=float(row['confidence'])
                    )
                    for row in appearances_rows
                ]
                
                # Calculate aggregate statistics
                unique_videos = len(set(app.video_uuid for app in appearances))
                first_seen = min(app.start_timestamp for app in appearances)
                last_seen = max(app.end_timestamp for app in appearances)
                
                # Format age range if available
                age_display = None
                if mvr_record['age_min'] and mvr_record['age_max']:
                    age_display = (
                        f"{mvr_record['age_min']}-{mvr_record['age_max']}"
                    )
                
                # Create result object
                result = MVRPersonResult(
                    mvr_people_uuid=mvr_uuid,
                    individual_uuids=linked_individual_uuids,
                    total_appearances=len(appearances),
                    unique_videos=unique_videos,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    confidence_score=float(
                        mvr_record['confidence_score'] or 0.0
                    ),
                    quality_score=float(mvr_record['quality_score'] or 0.0),
                    appearances=appearances,
                    estimated_age=age_display,
                    estimated_gender=mvr_record['gender']
                )
                
                results.append(result)
            
            logger.info(
                f"Found {len(results)} existing MVR people in videos"
            )
            
            return MVRPeopleSearchResponse(
                success=True,
                total_results=len(results),
                mvr_people=results,
                search_parameters={
                    "video_uuids": video_uuids,
                    "video_count": len(video_uuids),
                    "start_time": (
                        start_time.isoformat() if start_time else None
                    ),
                    "end_time": end_time.isoformat() if end_time else None,
                    "limit": limit
                },
                message=f"Found {len(results)} existing MVR people"
            )
            
    except Exception as e:
        logger.error(
            f"Error searching MVR people by videos: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search MVR people: {str(e)}"
        )


# ============================================================================
# ENDPOINT: Search Existing MVR People by Collection (DEPRECATED)
# ============================================================================
# NOTE: This endpoint cannot filter by collection without cross-database
# queries. Use /search/by-videos instead.

@router.post(
    "/search/by-collection",
    response_model=MVRPeopleSearchResponse,
    summary="Search Existing MVR People by Collection (DEPRECATED)",
    deprecated=True,
    description="Search for existing MVR people created within a date range "
                "for a specific collection. Returns cached/existing data "
                "without triggering any merge operations.",
)
async def search_mvr_people_by_collection(
    request: MVRPeopleSearchRequest,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Search for existing MVR people by collection and date range.
    
    This endpoint fetches EXISTING MVR people and their linked individuals
    that were created within the specified time range for a collection.
    It does NOT trigger any merge operations - it only retrieves cached data.
    
    **Use Case:** Fetch existing MVR analysis results for display in
    the cross-video analysis screen without reprocessing.
    
    **Authentication:** Requires valid JWT token
    
    **Parameters:**
    - collection_name: Collection identifier (camera device ID or UUID)
    - start_time: Start of search time range (ISO 8601)
    - end_time: End of search time range (ISO 8601)
    - limit: Maximum results to return (default: 100, max: 500)
    
    **Returns:**
    - 200 OK: List of MVR people with aggregated data
    - 400 Bad Request: Invalid parameters
    - 500 Internal Server Error: Database error
    """
    logger.info(
        f"Searching existing MVR people for collection {request.collection_name} "
        f"from {request.start_time} to {request.end_time} "
        f"(user: {current_user.get('email')})"
    )
    
    try:
        # Convert timezone-aware datetimes to naive (database uses naive timestamps)
        start_time_naive = request.start_time.replace(tzinfo=None)
        end_time_naive = request.end_time.replace(tzinfo=None)
        
        # Get database connection from the repository's pool
        async with mvr_repository.pool.acquire() as conn:
            # Query MVR people created within the time range
            # Note: Collection filtering happens at the video level (Media service)
            # Here we filter by creation timestamp of MVR people
            query = """
                SELECT DISTINCT
                    mp.mvr_people_uuid,
                    mp.quality_score,
                    mp.confidence_score,
                    mp.age_min,
                    mp.age_max,
                    mp.gender,
                    mp.created_at,
                    mp.updated_at
                FROM mvr_people mp
                WHERE mp.created_at >= $1
                    AND mp.created_at <= $2
                    AND mp.is_orphaned = false
                ORDER BY mp.created_at DESC
                LIMIT $3
            """
            
            mvr_records = await conn.fetch(
                query,
                start_time_naive,
                end_time_naive,
                request.limit
            )
            
            results = []
            
            # For each MVR person, get all linked individuals and appearances
            for mvr_record in mvr_records:
                mvr_uuid = str(mvr_record['mvr_people_uuid'])
                
                # Get all linked individual UUIDs
                individuals_query = """
                    SELECT individual_uuid
                    FROM individual_mvr_mapping
                    WHERE mvr_people_uuid = $1
                """
                individual_rows = await conn.fetch(individuals_query, mvr_uuid)
                individual_uuids = [str(row['individual_uuid']) for row in individual_rows]
                
                # Get all appearances for these individuals
                # Note: Cannot filter by collection_name here as videos table
                # is in a different database (Media service)
                appearances_query = """
                    SELECT 
                        iva.video_uuid,
                        iva.person_object_uuid,
                        iva.start_timestamp,
                        iva.end_timestamp,
                        iva.confidence
                    FROM individual_video_appearances iva
                    WHERE iva.individual_uuid = ANY($1::uuid[])
                        AND iva.start_timestamp >= $2
                        AND iva.end_timestamp <= $3
                    ORDER BY iva.start_timestamp ASC
                """
                
                appearances_rows = await conn.fetch(
                    appearances_query,
                    individual_uuids,
                    start_time_naive,
                    end_time_naive
                )
                
                if not appearances_rows:
                    # Skip MVR people with no appearances in the time range
                    continue
                
                # Build appearance objects
                appearances = [
                    MVRIndividualAppearance(
                        video_uuid=str(row['video_uuid']),
                        person_object_uuid=str(row['person_object_uuid']),
                        start_timestamp=row['start_timestamp'],
                        end_timestamp=row['end_timestamp'],
                        confidence=float(row['confidence'])
                    )
                    for row in appearances_rows
                ]
                
                # Calculate aggregate statistics
                unique_videos = len(set(app.video_uuid for app in appearances))
                first_seen = min(app.start_timestamp for app in appearances)
                last_seen = max(app.end_timestamp for app in appearances)
                
                # Format age range if available
                age_display = None
                if mvr_record['age_min'] and mvr_record['age_max']:
                    age_display = f"{mvr_record['age_min']}-{mvr_record['age_max']}"
                
                # Create result object
                result = MVRPersonResult(
                    mvr_people_uuid=mvr_uuid,
                    individual_uuids=individual_uuids,
                    total_appearances=len(appearances),
                    unique_videos=unique_videos,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    confidence_score=float(mvr_record['confidence_score'] or 0.0),
                    quality_score=float(mvr_record['quality_score'] or 0.0),
                    appearances=appearances,
                    estimated_age=age_display,
                    estimated_gender=mvr_record['gender']
                )
                
                results.append(result)
            
            logger.info(
                f"Found {len(results)} existing MVR people in time range"
            )
            
            return MVRPeopleSearchResponse(
                success=True,
                total_results=len(results),
                mvr_people=results,
                search_parameters={
                    "collection_name": request.collection_name,
                    "start_time": request.start_time.isoformat(),
                    "end_time": request.end_time.isoformat(),
                    "limit": request.limit
                },
                message=f"Found {len(results)} existing MVR people"
            )
            
    except Exception as e:
        logger.error(f"Error searching MVR people by collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search MVR people: {str(e)}"
        )


# ============================================================================
# ENDPOINT 16: Get Individual Analysis Without Session
# ============================================================================

@router.get(
    "/individuals/{individual_uuid}/analysis",
    summary="Get Individual Analysis Without Session",
    description=(
        "Get individual appearance analysis without requiring a "
        "tracking session. Returns all appearances for the individual "
        "across all videos. Optionally filter by date range."
    ),
)
async def get_individual_analysis_no_session(
    individual_uuid: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Get individual appearance analysis without session filtering.
    
    This endpoint fetches all video appearances for an individual
    without requiring a tracking session UUID. Useful for MVR search results
    where individuals may not be associated with a specific session.
    
    Returns:
    - individual_uuid: UUID of the individual
    - total_appearances: Total number of appearances across all videos
    - unique_videos: Number of unique videos
    - first_seen: Timestamp of first appearance
    - last_seen: Timestamp of last appearance
    - appearances: List of all video appearances with details
    """
    logger.info(
        "Fetching analysis for individual %s (user: %s)",
        individual_uuid,
        current_user.get('email')
    )
    
    try:
        # Get database connection from the repository's pool
        async with mvr_repository.pool.acquire() as conn:
            # Build query with optional date filtering
            query_conditions = ["iva.individual_uuid = $1"]
            query_params: list = [individual_uuid]
            
            # Add date range filtering if provided
            if start_time:
                # Convert to naive if timezone-aware
                start_naive = (
                    start_time.replace(tzinfo=None)
                    if start_time.tzinfo
                    else start_time
                )
                query_conditions.append(
                    f"iva.start_timestamp >= ${len(query_params) + 1}"
                )
                query_params.append(start_naive)
            
            if end_time:
                # Convert to naive if timezone-aware
                end_naive = (
                    end_time.replace(tzinfo=None)
                    if end_time.tzinfo
                    else end_time
                )
                query_conditions.append(
                    f"iva.end_timestamp <= ${len(query_params) + 1}"
                )
                query_params.append(end_naive)
            
            # Build the final query with demographics
            query = f"""
                SELECT
                    iva.video_uuid,
                    iva.person_object_uuid,
                    iva.start_timestamp,
                    iva.end_timestamp,
                    iva.confidence,
                    mvr.gender,
                    mvr.gender_confidence,
                    mvr.age_min,
                    mvr.age_max,
                    mvr.age_confidence
                FROM individual_video_appearances iva
                LEFT JOIN individual_mvr_mapping imm ON iva.individual_uuid = imm.individual_uuid
                LEFT JOIN mvr_people mvr ON imm.mvr_people_uuid = mvr.mvr_people_uuid
                    AND mvr.is_orphaned = FALSE
                WHERE {' AND '.join(query_conditions)}
                ORDER BY iva.start_timestamp ASC
            """
            
            appearances_rows = await conn.fetch(query, *query_params)
            
            if not appearances_rows:
                return {
                    "individual_uuid": individual_uuid,
                    "total_appearances": 0,
                    "unique_videos": 0,
                    "appearances": [],
                    "demographics": None
                }
            
            # Build appearances list
            appearances = [
                {
                    "video_uuid": str(row['video_uuid']),
                    "person_object_uuid": str(row['person_object_uuid']),
                    "start_timestamp": row['start_timestamp'].isoformat(),
                    "end_timestamp": row['end_timestamp'].isoformat(),
                    "confidence": float(row['confidence'])
                }
                for row in appearances_rows
            ]
            
            # Calculate statistics
            unique_videos = len(
                set(app['video_uuid'] for app in appearances)
            )
            first_seen = min(
                row['start_timestamp'] for row in appearances_rows
            )
            last_seen = max(row['end_timestamp'] for row in appearances_rows)
            
            # Extract demographics from first row (all rows should have same demographics)
            demographics = None
            first_row = appearances_rows[0]
            if first_row['gender'] is not None:
                # Calculate age mean if age_min and age_max are available
                age_mean = None
                if first_row['age_min'] is not None and first_row['age_max'] is not None:
                    age_mean = (first_row['age_min'] + first_row['age_max']) / 2.0
                
                demographics = {
                    "gender": first_row['gender'],
                    "gender_confidence": float(first_row['gender_confidence']) if first_row['gender_confidence'] else None,
                    "age_min": first_row['age_min'],
                    "age_max": first_row['age_max'],
                    "age_mean": age_mean,
                    "age_confidence": float(first_row['age_confidence']) if first_row['age_confidence'] else None
                }
            
            return {
                "individual_uuid": individual_uuid,
                "total_appearances": len(appearances),
                "unique_videos": unique_videos,
                "first_seen": first_seen.isoformat(),
                "last_seen": last_seen.isoformat(),
                "appearances": appearances,
                "demographics": demographics
            }
            
    except Exception as e:
        logger.error(
            "Error fetching individual analysis: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch individual analysis: {str(e)}"
        ) from e


# ============================================================================
# ENDPOINT 17: Get MVR Person Analysis (Consolidated Individual Data)
# ============================================================================

@router.get(
    "/mvr-person/{mvr_person_uuid}/analysis",
    summary="Get MVR Person Analysis",
    description=(
        "Get consolidated analysis for an MVR person, which represents "
        "multiple individuals merged into a single identity. Returns "
        "aggregated data across all constituent individuals."
    ),
)
async def get_mvr_person_analysis(
    mvr_person_uuid: str,
    request: Request,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Get consolidated analysis for an MVR person.
    
    An MVR person represents multiple individuals that have been merged
    based on face recognition similarity. This endpoint returns aggregated
    data across all constituent individuals.
    
    Returns:
    - mvr_person_uuid: UUID of the MVR person
    - individual_uuids: List of constituent individual UUIDs
    - total_appearances: Total appearances across all individuals
    - unique_videos: Number of unique videos
    - first_seen: Earliest appearance timestamp
    - last_seen: Latest appearance timestamp
    - appearances: Consolidated list of all appearances
    """
    logger.info(
        "Fetching MVR person analysis for %s (user: %s)",
        mvr_person_uuid,
        current_user.get('email')
    )
    
    try:
        async with mvr_repository.pool.acquire() as conn:
            # Get all individuals for this MVR person
            individuals_query = """
                SELECT individual_uuid
                FROM individual_mvr_mapping
                WHERE mvr_people_uuid = $1
            """
            
            individual_rows = await conn.fetch(
                individuals_query, mvr_person_uuid
            )
            
            if not individual_rows:
                return {
                    "mvr_person_uuid": mvr_person_uuid,
                    "individual_uuids": [],
                    "total_appearances": 0,
                    "unique_videos": 0,
                    "appearances": []
                }
            
            individual_uuids = [
                str(row['individual_uuid']) for row in individual_rows
            ]
            
            # Build query to get all appearances for these individuals
            query_conditions = [
                f"iva.individual_uuid = ANY(${1})"
            ]
            query_params: list = [individual_uuids]
            
            # Add date range filtering if provided
            if start_time:
                start_naive = (
                    start_time.replace(tzinfo=None)
                    if start_time.tzinfo
                    else start_time
                )
                query_conditions.append(
                    f"iva.start_timestamp >= ${len(query_params) + 1}"
                )
                query_params.append(start_naive)
            
            if end_time:
                end_naive = (
                    end_time.replace(tzinfo=None)
                    if end_time.tzinfo
                    else end_time
                )
                query_conditions.append(
                    f"iva.end_timestamp <= ${len(query_params) + 1}"
                )
                query_params.append(end_naive)
            
            # Get demographics from mvr_people table
            demographics_query = """
                SELECT
                    gender,
                    gender_confidence,
                    age_min,
                    age_max,
                    age_confidence
                FROM mvr_people
                WHERE mvr_people_uuid = $1
                    AND is_orphaned = FALSE
            """
            demographics_row = await conn.fetchrow(demographics_query, mvr_person_uuid)
            
            # Prepare demographics object
            demographics = None
            if demographics_row and demographics_row['gender'] is not None:
                # Calculate age mean if age_min and age_max are available
                age_mean = None
                if demographics_row['age_min'] is not None and demographics_row['age_max'] is not None:
                    age_mean = (demographics_row['age_min'] + demographics_row['age_max']) / 2.0
                
                demographics = {
                    "gender": demographics_row['gender'],
                    "gender_confidence": float(demographics_row['gender_confidence']) if demographics_row['gender_confidence'] else None,
                    "age_min": demographics_row['age_min'],
                    "age_max": demographics_row['age_max'],
                    "age_mean": age_mean,
                    "age_confidence": float(demographics_row['age_confidence']) if demographics_row['age_confidence'] else None
                }
            
            # Query all appearances
            appearances_query = f"""
                SELECT
                    iva.individual_uuid,
                    iva.video_uuid,
                    iva.person_object_uuid,
                    iva.start_timestamp,
                    iva.end_timestamp,
                    iva.confidence
                FROM individual_video_appearances iva
                WHERE {' AND '.join(query_conditions)}
                ORDER BY iva.start_timestamp ASC
            """
            
            appearances_rows = await conn.fetch(
                appearances_query, *query_params
            )
            
            if not appearances_rows:
                return {
                    "mvr_person_uuid": mvr_person_uuid,
                    "individual_uuids": individual_uuids,
                    "total_appearances": 0,
                    "unique_videos": 0,
                    "appearances": [],
                    "demographics": demographics
                }
            
            # Build appearances list
            appearances = [
                {
                    "individual_uuid": str(row['individual_uuid']),
                    "video_uuid": str(row['video_uuid']),
                    "person_object_uuid": str(row['person_object_uuid']),
                    "start_timestamp": row['start_timestamp'].isoformat(),
                    "end_timestamp": row['end_timestamp'].isoformat(),
                    "confidence": float(row['confidence'])
                }
                for row in appearances_rows
            ]
            
            # Calculate statistics
            unique_videos = len(
                set(app['video_uuid'] for app in appearances)
            )
            first_seen = min(
                row['start_timestamp'] for row in appearances_rows
            )
            last_seen = max(
                row['end_timestamp'] for row in appearances_rows
            )
            
            # Calculate average route velocity from orchestrator route data
            avg_route_velocity = None
            try:
                import httpx
                
                gateway_url = os.getenv("PPL_GATEWAY_URL", "http://localhost:8080")
                all_route_points = []
                
                # Get Authorization header from request
                auth_header = request.headers.get("Authorization")
                headers = {}
                if auth_header:
                    headers["Authorization"] = auth_header
                
                # Get unique video UUIDs from appearances
                unique_video_uuids = set(app['video_uuid'] for app in appearances)
                logger.info(f"🚀 VELOCITY CALCULATION STARTED - Fetching routes from {len(unique_video_uuids)} video(s)")
                logger.info(f"🎯 Video UUIDs: {list(unique_video_uuids)}")
                
                # Fetch person objects data for each video to get route points (via gateway)
                async with httpx.AsyncClient(timeout=30.0) as client:
                    for video_uuid in unique_video_uuids:
                        try:
                            response = await client.get(
                                f"{gateway_url}/api/v1/orchestrator/person-objects/{video_uuid}",
                                headers=headers
                            )
                            
                            if response.status_code == 200:
                                person_objects_data = response.json()
                                
                                # Debug: Log what we received
                                logger.info(f"Gateway response keys for video {video_uuid}: {list(person_objects_data.keys())}")
                                logger.info(f"Has person_groups: {('person_groups' in person_objects_data)}")
                                
                                # Handle both response formats
                                person_groups = person_objects_data.get('group_tracking') or person_objects_data.get('person_groups', [])
                                
                                logger.info(f"Extracted {len(person_groups) if person_groups else 0} person groups from video {video_uuid}")
                                
                                for person_group in person_groups:
                                    # Extract route points from movement_tracking
                                    movement_tracking = person_group.get('movement_tracking', {})
                                    route_points = movement_tracking.get('route_points', [])
                                    
                                    for route_point in route_points:
                                        # Use center_x and center_y from gateway response
                                        # Note: timestamp is a float (seconds from video start), keep as-is
                                        all_route_points.append({
                                            'x': float(route_point.get('center_x', route_point.get('x', 0))),
                                            'y': float(route_point.get('center_y', route_point.get('y', 0))),
                                            'timestamp': float(route_point['timestamp']),  # Keep as float
                                            'video_uuid': video_uuid,
                                            'confidence': float(route_point.get('confidence', 1.0))
                                        })
                                
                                logger.info(f"Fetched {len(route_points)} route points from video {video_uuid}")
                            else:
                                logger.warning(f"Orchestrator returned status {response.status_code} for video {video_uuid}")
                        except Exception as e:
                            logger.warning(f"Could not fetch routes from video {video_uuid}: {e}")
                
                logger.info(f"📊 Total route points collected: {len(all_route_points)}")
                if len(all_route_points) >= 2:
                    # Sort by timestamp
                    all_route_points.sort(key=lambda r: r['timestamp'])
                    logger.info(f"✅ Calculating velocities from {len(all_route_points)} points...")
                    
                    # Calculate velocities inline (timestamps are floats, not ISO strings)
                    # Normalize coordinates and calculate velocity between consecutive points
                    width, height = 1920, 1080  # Standard resolution
                    velocities = []
                    
                    for i in range(1, len(all_route_points)):
                        try:
                            prev = all_route_points[i-1]
                            curr = all_route_points[i]
                            
                            # Normalize coordinates
                            x1_norm = prev['x'] / width
                            y1_norm = prev['y'] / height
                            x2_norm = curr['x'] / width
                            y2_norm = curr['y'] / height
                            
                            # Calculate normalized distance
                            dx = x2_norm - x1_norm
                            dy = y2_norm - y1_norm
                            distance_normalized = (dx ** 2 + dy ** 2) ** 0.5
                            
                            # Calculate time difference (timestamps are floats in seconds)
                            time_diff = curr['timestamp'] - prev['timestamp']
                            
                            # Calculate velocity
                            if time_diff > 0:
                                velocity = distance_normalized / time_diff
                                velocities.append(velocity)
                        except (KeyError, ValueError, ZeroDivisionError) as e:
                            logger.warning(f"Error calculating velocity: {e}")
                            continue
                    
                    logger.info(f"🎯 Valid velocities calculated: {len(velocities)}")
                    if velocities:
                        avg_route_velocity = round(sum(velocities) / len(velocities), 6)
                        logger.info(f"✅ VELOCITY CALCULATED: {avg_route_velocity} normalized px/s from {len(all_route_points)} route points")
                    else:
                        logger.warning(f"⚠️ No valid velocities calculated")
                else:
                    logger.warning(f"⚠️ Not enough route points ({len(all_route_points)}) for velocity calculation")
            except Exception as e:
                logger.warning(f"Failed to calculate route velocity for MVR person: {e}")
                import traceback
                logger.warning(f"Traceback: {traceback.format_exc()}")
            
            return {
                "mvr_person_uuid": mvr_person_uuid,
                "individual_uuids": individual_uuids,
                "total_appearances": len(appearances),
                "unique_videos": unique_videos,
                "first_seen": first_seen.isoformat(),
                "last_seen": last_seen.isoformat(),
                "appearances": appearances,
                "demographics": demographics,
                "average_route_velocity": avg_route_velocity
            }
            
    except Exception as e:
        logger.error(
            "Error fetching MVR person analysis: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch MVR person analysis: {str(e)}"
        ) from e


# ============================================================================
# ENDPOINT: Count MVR People by Video UUIDs (Today)
# ============================================================================

@router.post(
    "/count-by-videos",
    summary="Get MVR People Count for Video UUIDs",
    description=(
        "Returns the count of unique MVR people detected in the specified "
        "videos. Only queries VMeta's own database. Useful for getting "
        "per-camera or per-collection counts."
    ),
)
async def get_videos_mvr_people_count(
    video_uuids: List[str] = Body(
        ..., embed=True, description="List of video UUIDs"
    ),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    _current_user: dict = Depends(get_current_user)
):
    """
    Get count of unique MVR people detected in specific videos.

    Request Body:
        {
            "video_uuids": ["uuid1", "uuid2", "uuid3"]
        }

    Returns:
        {
            "count": 5,
            "video_count": 3
        }
    """
    try:
        if not video_uuids:
            return {
                "count": 0,
                "video_count": 0
            }

        logger.info(
            "Fetching MVR people count for %d videos", len(video_uuids)
        )

        # Get database connection
        async with mvr_repository.pool.acquire() as conn:
            # Query unique MVR people count for these videos
            # Only uses VMeta's own tables:
            # - individual_video_appearances (has video_uuid, individual_uuid)
            # - individual_mvr_mapping (maps individuals to MVR people)
            count_query = """
                WITH video_individuals AS (
                    -- Get individuals with appearances in these videos
                    SELECT DISTINCT iva.individual_uuid
                    FROM individual_video_appearances iva
                    WHERE iva.video_uuid = ANY($1::uuid[])
                )
                -- Count unique MVR people linked to these individuals
                SELECT COUNT(DISTINCT imm.mvr_people_uuid) as mvr_count
                FROM individual_mvr_mapping imm
                WHERE imm.individual_uuid IN (
                    SELECT individual_uuid FROM video_individuals
                )
            """

            # Convert string UUIDs to UUID array for PostgreSQL
            uuid_array = [UUID(vid) for vid in video_uuids]
            
            count_row = await conn.fetchrow(
                count_query,
                uuid_array
            )

            mvr_count = count_row['mvr_count'] if count_row else 0

            return {
                "count": mvr_count,
                "video_count": len(video_uuids)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching videos MVR people count: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch videos MVR people count: {str(e)}"
        ) from e


# ============================================================================
# ENDPOINT: Count MVR People by Video UUIDs with Demographics
# ============================================================================

@router.post(
    "/count-by-videos-demographics",
    summary="Get MVR People Count with Demographics for Video UUIDs",
    description=(
        "Returns the count of unique MVR people with demographic breakdowns "
        "(gender, age) detected in the specified videos."
    ),
)
async def get_videos_mvr_people_count_with_demographics(
    video_uuids: List[str] = Body(
        ..., embed=True, description="List of video UUIDs"
    ),
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    _current_user: dict = Depends(get_current_user)
):
    """
    Get count of unique MVR people with demographic breakdowns.

    Request Body:
        {
            "video_uuids": ["uuid1", "uuid2", "uuid3"]
        }

    Returns:
        {
            "count": 15,
            "video_count": 3,
            "demographics": {
                "total_male": 9,
                "total_female": 6,
                "percent_male": 60.0,
                "percent_female": 40.0,
                "total_young": 4,
                "total_adult": 11,
                "percent_young": 26.7,
                "percent_adult": 73.3
            }
        }
    """
    try:
        if not video_uuids:
            return {
                "count": 0,
                "video_count": 0,
                "demographics": {
                    "total_male": 0,
                    "total_female": 0,
                    "percent_male": 0.0,
                    "percent_female": 0.0,
                    "total_young": 0,
                    "total_adult": 0,
                    "percent_young": 0.0,
                    "percent_adult": 0.0
                }
            }

        logger.info(
            "Fetching MVR people count with demographics for %d videos", len(video_uuids)
        )

        # Get database connection
        async with mvr_repository.pool.acquire() as conn:
            # Query MVR people with demographics
            # Uses aggregated demographics from individuals linked to each MVR person
            demographics_query = """
                WITH video_individuals AS (
                    -- Get individuals with appearances in these videos
                    SELECT DISTINCT iva.individual_uuid
                    FROM individual_video_appearances iva
                    WHERE iva.video_uuid = ANY($1::uuid[])
                ),
                mvr_with_demographics AS (
                    -- Get MVR people with their averaged demographics
                    SELECT DISTINCT
                        imm.mvr_people_uuid,
                        -- Get the most common gender for this MVR person
                        MODE() WITHIN GROUP (ORDER BY i.gender_estimate) as gender,
                        -- Get the average age for this MVR person
                        AVG(i.age_estimate) as avg_age
                    FROM individual_mvr_mapping imm
                    JOIN individuals i ON i.individual_uuid = imm.individual_uuid
                    WHERE imm.individual_uuid IN (
                        SELECT individual_uuid FROM video_individuals
                    )
                    AND i.gender_estimate IS NOT NULL
                    AND i.age_estimate IS NOT NULL
                    GROUP BY imm.mvr_people_uuid
                )
                SELECT 
                    COUNT(*) as total_count,
                    COUNT(*) FILTER (WHERE LOWER(gender) = 'male') as male_count,
                    COUNT(*) FILTER (WHERE LOWER(gender) = 'female') as female_count,
                    COUNT(*) FILTER (WHERE avg_age < 21) as young_count,
                    COUNT(*) FILTER (WHERE avg_age >= 21) as adult_count
                FROM mvr_with_demographics
            """

            # Convert string UUIDs to UUID array for PostgreSQL
            uuid_array = [UUID(vid) for vid in video_uuids]
            
            demo_row = await conn.fetchrow(
                demographics_query,
                uuid_array
            )

            total_count = demo_row['total_count'] if demo_row else 0
            male_count = demo_row['male_count'] if demo_row else 0
            female_count = demo_row['female_count'] if demo_row else 0
            young_count = demo_row['young_count'] if demo_row else 0
            adult_count = demo_row['adult_count'] if demo_row else 0

            # Calculate percentages
            percent_male = (male_count / total_count * 100) if total_count > 0 else 0.0
            percent_female = (female_count / total_count * 100) if total_count > 0 else 0.0
            percent_young = (young_count / total_count * 100) if total_count > 0 else 0.0
            percent_adult = (adult_count / total_count * 100) if total_count > 0 else 0.0

            return {
                "count": total_count,
                "video_count": len(video_uuids),
                "demographics": {
                    "total_male": male_count,
                    "total_female": female_count,
                    "percent_male": round(percent_male, 1),
                    "percent_female": round(percent_female, 1),
                    "total_young": young_count,
                    "total_adult": adult_count,
                    "percent_young": round(percent_young, 1),
                    "percent_adult": round(percent_adult, 1)
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching videos MVR people count with demographics: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch videos MVR people count with demographics: {str(e)}"
        ) from e


# ============================================================================
# ENDPOINT: Count MVR People by Collection (Today) - DEPRECATED
# ============================================================================
# NOTE: This endpoint requires cross-database queries which violates
# microservice boundaries. Use /count-by-videos instead.

@router.get(
    "/count-by-collection/{collection_name}",
    summary="Get Today's MVR People Count for Collection (DEPRECATED)",
    deprecated=True,
    description=(
        "Returns the count of unique MVR people detected today for a "
        "specific collection. Queries MVR people with appearances in "
        "that collection today."
    ),
)
async def get_collection_mvr_people_count(
    collection_name: str,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    _current_user: dict = Depends(get_current_user)
):
    """
    Get count of unique MVR people detected today for a collection.

    Returns:
        {
            "collection_name": "camera-device-123",
            "count": 5,
            "date": "2025-11-16",
            "start_time": "2025-11-16T00:00:00",
            "end_time": "2025-11-16T23:59:59"
        }
    """
    from datetime import time

    try:
        logger.info(
            "Fetching MVR people count for collection: %s", collection_name
        )

        # Get database connection
        async with mvr_repository.pool.acquire() as conn:
            # Get today's date range (00:00:00 to 23:59:59)
            today = datetime.now().date()
            start_time = datetime.combine(today, time.min)  # 00:00:00
            end_time = datetime.combine(today, time.max)  # 23:59:59.999999

            # Convert to naive datetime for database
            # (PostgreSQL timestamps are naive)
            start_time = start_time.replace(tzinfo=None)
            end_time = end_time.replace(tzinfo=None)

            # Query unique MVR people count for collection today
            # We need to:
            # a) Find all media in the collection
            # b) Find all individual_video_appearances for those media
            #    within today's timeframe
            # c) Count unique MVR people associated with those individuals

            count_query = """
                WITH collection_videos AS (
                    -- Get all videos in the collection
                    SELECT v.video_uuid
                    FROM videos v
                    JOIN media_collections mc
                      ON v.collection_uuid = mc.collection_uuid
                    WHERE mc.collection_name = $1
                ),
                today_individuals AS (
                    -- Get all individuals with appearances today
                    SELECT DISTINCT iva.individual_uuid
                    FROM individual_video_appearances iva
                    WHERE iva.video_uuid IN (
                        SELECT video_uuid FROM collection_videos
                    )
                      AND iva.start_timestamp >= $2
                      AND iva.start_timestamp <= $3
                )
                -- Count unique MVR people linked to these individuals
                SELECT COUNT(DISTINCT imm.mvr_people_uuid) as mvr_count
                FROM individual_mvr_mapping imm
                WHERE imm.individual_uuid IN (
                    SELECT individual_uuid FROM today_individuals
                )
            """

            count_row = await conn.fetchrow(
                count_query,
                collection_name,
                start_time,
                end_time
            )

            mvr_count = count_row['mvr_count'] if count_row else 0

            return {
                "collection_name": collection_name,
                "count": mvr_count,
                "date": today.isoformat(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching collection MVR people count: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch collection MVR people count: {str(e)}"
        ) from e


# ============================================================================
# ENDPOINT: Count MVR People by Camera (Today) - DEPRECATED
# ============================================================================
# NOTE: This endpoint requires cross-database queries which isn't supported
# Use /count-by-collection/{collection_name} instead

@router.get(
    "/count-by-camera/{camera_id}",
    summary="Get Today's MVR People Count for Camera (DEPRECATED)",
    description=(
        "DEPRECATED: Use /count-by-collection/{collection_name} instead. "
        "This endpoint requires cross-service database access."
    ),
    deprecated=True,
)
async def get_camera_mvr_people_count(
    camera_id: str,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    _current_user: dict = Depends(get_current_user)
):
    """
    DEPRECATED: Get count of unique MVR people detected today for a camera.

    Please use /count-by-collection/{collection_name} endpoint instead.
    Frontend should map camera_id to collection_name first.
    """
    from datetime import time

    try:
        logger.info("Fetching MVR people count for camera: %s", camera_id)

        # Get database connection
        async with mvr_repository.pool.acquire() as conn:
            # Step 1: Get camera's collection name from media_collections table
            # The media service stores camera_device_id in media_collections
            collection_row = await conn.fetchrow(
                """
                SELECT collection_name
                FROM media_collections
                WHERE camera_device_id = $1
                LIMIT 1
                """,
                camera_id
            )

            if not collection_row:
                return {
                    "camera_id": camera_id,
                    "collection_name": None,
                    "count": 0,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "start_time": None,
                    "end_time": None,
                    "message": "No collection found for this camera"
                }

            collection_name = collection_row['collection_name']
            if not collection_name:
                today_str = datetime.now().strftime("%Y-%m-%d")
                return {
                    "camera_id": camera_id,
                    "collection_name": None,
                    "count": 0,
                    "date": today_str,
                    "start_time": None,
                    "end_time": None,
                    "message": "Camera has no associated collection"
                }

            # Step 2: Get today's date range (00:00:00 to 23:59:59)
            today = datetime.now().date()
            start_time = datetime.combine(today, time.min)  # 00:00:00
            end_time = datetime.combine(today, time.max)  # 23:59:59.999999

            # Convert to naive datetime for database
            # (PostgreSQL timestamps are naive)
            start_time = start_time.replace(tzinfo=None)
            end_time = end_time.replace(tzinfo=None)

            # Step 3: Query unique MVR people count for collection today
            # We need to:
            # a) Find all media in the collection
            # b) Find all individual_video_appearances for those media
            #    within today's timeframe
            # c) Count unique MVR people associated with those individuals

            count_query = """
                WITH collection_videos AS (
                    -- Get all videos in the camera's collection
                    SELECT v.video_uuid
                    FROM videos v
                    JOIN media_collections mc
                      ON v.collection_uuid = mc.collection_uuid
                    WHERE mc.collection_name = $1
                ),
                today_individuals AS (
                    -- Get all individuals with appearances today
                    SELECT DISTINCT iva.individual_uuid
                    FROM individual_video_appearances iva
                    WHERE iva.video_uuid IN (
                        SELECT video_uuid FROM collection_videos
                    )
                      AND iva.start_timestamp >= $2
                      AND iva.start_timestamp <= $3
                )
                -- Count unique MVR people linked to these individuals
                SELECT COUNT(DISTINCT imm.mvr_people_uuid) as mvr_count
                FROM individual_mvr_mapping imm
                WHERE imm.individual_uuid IN (
                    SELECT individual_uuid FROM today_individuals
                )
            """

            count_row = await conn.fetchrow(
                count_query,
                collection_name,
                start_time,
                end_time
            )

            mvr_count = count_row['mvr_count'] if count_row else 0

            return {
                "camera_id": camera_id,
                "collection_name": collection_name,
                "count": mvr_count,
                "date": today.isoformat(),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error fetching camera MVR people count: %s", e, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch camera MVR people count: {str(e)}"
        ) from e


# ============================================================================
# HELPER: Enrich Person Objects with Face Crops
# ============================================================================

async def enrich_person_objects_with_face_crops(
    person_objects: List[Dict[str, Any]],
    media_uuid: UUID,
    auth_token: str,
    vision_url: str = "http://localhost:8003",
    gateway_url: str = "http://localhost:8080"
) -> List[Dict[str, Any]]:
    """
    Enrich person objects with face crops extracted from video frames.
    
    For each person_object:
    1. Get best_face_id and best_face_bbox from person_object
    2. Query Vision service to get frame_number for best_face_id
    3. Fetch frame from Media service via Gateway
    4. Extract face crop using bbox coordinates
    5. Add best_face_crop (numpy array) to person_object
    
    Args:
        person_objects: List of person objects from Vision Face Detection V2
        media_uuid: Media UUID
        auth_token: Auth token for service calls
        vision_url: Vision service URL
        gateway_url: Gateway service URL
        
    Returns:
        List of person objects with best_face_crop added
    """
    import httpx
    import cv2
    import numpy as np
    from PIL import Image
    from io import BytesIO
    
    enriched_objects = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for person_obj in person_objects:
            try:
                # Get frame number and bbox directly from person_object
                # Face Detection V2 already provides best_face_frame
                frame_number = person_obj.get('best_face_frame')
                best_face_bbox = person_obj.get('best_face_bbox')
                
                if frame_number is None or not best_face_bbox:
                    logger.warning(
                        f"Person object missing best_face_frame or bbox: {person_obj.get('person_id')}"
                    )
                    enriched_objects.append(person_obj)
                    continue
                
                # Step 2: Fetch frame from Media service via Gateway
                frame_url = (
                    f"{gateway_url}/api/v1/media/{media_uuid}/frame/{frame_number}?format=jpeg"
                )
                
                frame_response = await client.get(
                    frame_url,
                    headers={'Authorization': f'Bearer {auth_token}'}
                )
                
                if frame_response.status_code != 200:
                    logger.warning(
                        f"Failed to fetch frame {frame_number} for {media_uuid}: "
                        f"{frame_response.status_code}"
                    )
                    enriched_objects.append(person_obj)
                    continue
                
                # Step 3: Decode frame from JPEG bytes
                frame_bytes = frame_response.content
                pil_image = Image.open(BytesIO(frame_bytes))
                frame = np.array(pil_image)
                
                # Convert RGB to BGR (OpenCV format)
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Step 4: Extract face crop using bbox
                # bbox format: [x1, y1, x2, y2]
                x1, y1, x2, y2 = best_face_bbox
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                
                # Validate bbox
                frame_h, frame_w = frame_bgr.shape[:2]
                if x1 < 0 or y1 < 0 or x2 > frame_w or y2 > frame_h or x1 >= x2 or y1 >= y2:
                    logger.warning(
                        f"Invalid bbox for person {person_obj.get('person_id')}: "
                        f"[{x1},{y1},{x2},{y2}] in frame [{frame_w},{frame_h}]"
                    )
                    enriched_objects.append(person_obj)
                    continue
                
                # Crop the face
                face_crop = frame_bgr[y1:y2, x1:x2].copy()
                
                # Step 5: Add face_crop to person_object
                enriched_obj = {
                    **person_obj,
                    'best_face_crop': face_crop  # numpy array for ML processing
                }
                enriched_objects.append(enriched_obj)
                
                logger.info(
                    f"Enriched person {person_obj.get('person_id')} with face crop: "
                    f"{face_crop.shape}"
                )
                
            except Exception as e:
                logger.error(
                    f"Error enriching person object {person_obj.get('person_id')}: {e}"
                )
                # Add without face_crop
                enriched_objects.append(person_obj)
    
    return enriched_objects


# ============================================================================
# ENDPOINT 15: Process Media Independently for MVR People
# ============================================================================

@router.post(
    "/process-media",
    status_code=status.HTTP_200_OK,
    summary="Process Media Independently for MVR People",
    description=(
        "Process photos and videos independently to generate MVR people. "
        "Each media is processed in isolation—no cross-media merging. "
        "Photos produce single-point route data, videos produce multi-point routes."
    ),
)
async def process_media_independently(
    request: "ProcessMediaRequest",
    http_request: Request,
    mvr_service: MVRService = Depends(get_mvr_service),
    current_user: dict = Depends(get_current_user),
):
    """
    Process media (photos/videos) independently for MVR people creation.
    
    Key behaviors:
    - No cross-media merging (each media processed in isolation)
    - Photos: Single-point route data
    - Videos: Multi-point route data with velocity calculation
    - Returns MVR people in standard format
    
    Args:
        request: ProcessMediaRequest with media UUIDs and options
        http_request: FastAPI Request object (for auth header)
        mvr_service: MVR service dependency
        current_user: Authenticated user
        
    Returns:
        ProcessMediaResponse with MVR people for each media
    """
    import time
    from uuid import UUID
    from utils.media_client import MediaClient
    from utils.orchestrator_client import get_orchestrator_client
    from utils.route_data_builder import build_route_data
    from api.models.process_media import (
        ProcessMediaResponse,
        AsyncProcessingResponse,
        MediaResult,
        MVRPerson,
        IndividualAppearance,
        Demographics,
        RouteData,
        AggregateStatistics,
        MediaTypeStatistics,
        MediaProcessingError
    )
    
    logger.info(
        f"Processing {len(request.media_uuids)} media independently "
        f"(user: {current_user.get('email')})"
    )
    
    # Validate request
    if len(request.media_uuids) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 media UUIDs per request"
        )
    
    # Check if async processing requested
    if request.processing_options.async_processing:
        # TODO: Implement async job queue
        job_id = f"job-{UUID.uuid4()}"
        return AsyncProcessingResponse(
            success=True,
            job_id=job_id,
            status="processing",
            total_media=len(request.media_uuids),
            estimated_completion_seconds=len(request.media_uuids) * 2,
            status_endpoint=f"/api/v1/mvr-people/jobs/{job_id}/status"
        )
    
    # Synchronous processing with orchestration
    start_time = time.time()
    
    # Extract auth token from Authorization header
    auth_header = http_request.headers.get('Authorization', '')
    auth_token = auth_header.replace('Bearer ', '') if auth_header.startswith('Bearer ') else None
    
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )
    
    media_client = MediaClient(auth_token=auth_token)
    orchestrator_client = get_orchestrator_client()
    
    # Log the processing options being used
    logger.info(f"[REQUEST DEBUG] Processing options: similarity_threshold={request.processing_options.similarity_threshold}, min_face_quality={request.processing_options.min_face_quality}")
    
    results = []
    
    # Import httpx for Vision service calls
    import httpx
    vision_url = os.getenv("PPL_VISION_URL", "http://localhost:8003")
    gateway_url = os.getenv("PPL_GATEWAY_URL", "http://localhost:8080")
    
    for media_uuid_str in request.media_uuids:
        try:
            media_uuid = UUID(media_uuid_str)
            media_start = time.time()
            
            # Step 1: Fetch media metadata
            media_metadata = await media_client.get_media_metadata(media_uuid)
            
            if not media_metadata:
                results.append(MediaResult(
                    media_uuid=media_uuid_str,
                    media_type="unknown",
                    status="failed",
                    error=MediaProcessingError(
                        code="MEDIA_NOT_FOUND",
                        message=f"Media UUID not found: {media_uuid_str}"
                    )
                ))
                continue
            
            media_type = media_metadata.get('type', 'unknown')
            logger.info(f"Processing {media_type}: {media_uuid_str}")
            
            # Step 2: Trigger Enhanced Face Detection V2 via Orchestrator (synchronous)
            # This works for both photos and videos
            trigger_data = {}  # Initialize outside httpx block for scoping
            orchestrator_url = os.getenv("PPL_ORCHESTRATOR_URL", "http://localhost:8002")
            
            async with httpx.AsyncClient(timeout=180.0) as client:
                # Step 2a: Use Enhanced Logic V2 endpoint (synchronous, no polling needed)
                logger.info(f"Triggering Enhanced Logic V2 face detection for {media_uuid_str}...")
                
                fd_response = await client.get(
                    f"{orchestrator_url}/api/v1/media/{media_uuid_str}/faces/enhanced-v2",
                    headers={'Authorization': f'Bearer {auth_token}'},
                    params={"frame_interval": 10}  # Process every 10th frame for speed
                )
                
                logger.info(f"[VMETA DEBUG] Enhanced Logic V2 response: {fd_response.status_code}")
                
                if fd_response.status_code not in [200, 201]:
                    error_detail = fd_response.text
                    logger.error(
                        f"Enhanced Logic V2 failed for {media_uuid_str}: "
                        f"{fd_response.status_code} - {error_detail}"
                    )
                    logger.info(f"[VMETA DEBUG] Enhanced Logic V2 FAILED")
                    results.append(MediaResult(
                        media_uuid=media_uuid_str,
                        media_type=media_type,
                        status="failed",
                        error=MediaProcessingError(
                            code="FACE_DETECTION_FAILED",
                            message=f"Enhanced Logic V2 face detection failed: {error_detail}"
                        )
                    ))
                    continue
                
                fd_data = fd_response.json()
                faces_count = fd_data.get('total_faces', 0)
                logger.info(f"[VMETA DEBUG] Enhanced Logic V2 completed: {faces_count} faces detected")
                
                # Step 2b: Get person groups directly from Orchestrator's PPL Thread endpoint
                # This preserves Orchestrator's IoU-based grouping instead of Vision re-clustering
                logger.info(f"Fetching person groups from Orchestrator PPL Thread for {media_uuid_str}...")
                
                ppl_thread_response = await client.get(
                    f"{orchestrator_url}/person-objects/{media_uuid_str}",
                    headers={'Authorization': f'Bearer {auth_token}'}
                )
                
                logger.info(f"[VMETA DEBUG] PPL Thread response: {ppl_thread_response.status_code}")
                
                if ppl_thread_response.status_code not in [200, 201]:
                    error_detail = ppl_thread_response.text
                    logger.error(
                        f"PPL Thread failed for {media_uuid_str}: "
                        f"{ppl_thread_response.status_code} - {error_detail}"
                    )
                    logger.info(f"[VMETA DEBUG] PPL Thread FAILED")
                    results.append(MediaResult(
                        media_uuid=media_uuid_str,
                        media_type=media_type,
                        status="failed",
                        error=MediaProcessingError(
                            code="PPL_THREAD_FAILED",
                            message=f"PPL Thread failed: {error_detail}"
                        )
                    ))
                    continue
                
                ppl_data = ppl_thread_response.json()
            
            # Step 3: Extract person groups from Orchestrator's PPL Thread response
            # These groups already use IoU-based face grouping (no re-clustering needed)
            logger.info(
                f"PPL Thread completed for {media_uuid_str}: "
                f"{ppl_data.get('total_persons', 0)} person groups created"
            )
            
            logger.info(f"[VMETA DEBUG] PPL Thread response keys: {ppl_data.keys()}")
            logger.info(f"[VMETA DEBUG] PPL Thread total_persons: {ppl_data.get('total_persons', 0)}")
            logger.info(f"[VMETA DEBUG] PPL Thread full response: {ppl_data}")
            
            person_groups_from_orchestrator = ppl_data.get('person_groups', [])
            logger.info(f"[VMETA DEBUG] person_groups_from_orchestrator count: {len(person_groups_from_orchestrator)}")
            logger.info(f"[VMETA DEBUG] person_groups_from_orchestrator sample: {person_groups_from_orchestrator[:1] if person_groups_from_orchestrator else 'EMPTY'}")
            
            # Transform Orchestrator's person_groups to person_objects format
            # Orchestrator groups faces using IoU, we preserve this grouping
            person_objects_from_vision = []
            for pg in person_groups_from_orchestrator:
                # Extract best face from representative_faces (already sorted by quality)
                representative_faces = pg.get('representative_faces', [])
                best_face = representative_faces[0] if representative_faces else {}
                best_face_data = best_face.get('face_data', {})
                
                # Extract bbox and frame from best face
                bbox = best_face_data.get('bbox', [])
                frame_number = best_face_data.get('frame_number', 0)
                
                person_obj = {
                    'person_id': pg.get('person_id'),
                    'person_uuid': pg.get('person_uuid'),
                    'face_count': pg.get('face_count', 0),
                    'representative_faces': representative_faces,
                    # Use quality_score directly from person_group (Orchestrator provides it at top level)
                    # Fallback to quality_metrics.average_quality if not present, then to 0.85
                    'quality_score': pg.get('quality_score', pg.get('quality_metrics', {}).get('average_quality', 0.85)),
                    'confidence_score': pg.get('average_confidence', 0.9),
                    'spatial_bounds': pg.get('spatial_bounds', {}),
                    'temporal_span': pg.get('temporal_span', {}),
                    'movement_tracking': pg.get('movement_tracking', {}),
                    # Add fields needed for enrichment
                    'best_face_frame': frame_number,
                    'best_face_bbox': bbox if len(bbox) == 4 else None,
                }
                person_objects_from_vision.append(person_obj)
            
            logger.info(
                f"Extracted {len(person_objects_from_vision)} person objects from Orchestrator "
                f"for {media_uuid_str} (preserved IoU-based grouping)"
            )
            logger.info(f"DEBUG: person_objects sample: {person_objects_from_vision[:1] if person_objects_from_vision else 'EMPTY'}")
            logger.info(f"[VMETA DEBUG] person_objects count: {len(person_objects_from_vision)}")
            logger.info(f"[VMETA DEBUG] person_objects sample: {person_objects_from_vision[:1] if person_objects_from_vision else 'EMPTY'}")
            
            if not person_objects_from_vision:
                logger.info(f"No faces detected in {media_uuid_str}")
                results.append(MediaResult(
                    media_uuid=media_uuid_str,
                    media_type=media_type,
                    status="completed",
                    mvr_people=[],
                    total_faces_detected=0,
                    mvr_people_count=0,
                    processing_time_ms=int((time.time() - media_start) * 1000)
                ))
                continue
            
            # Step 4: Enrich person objects with face crops
            # This fetches frames and extracts face crops for ML processing
            logger.info(
                f"Enriching {len(person_objects_from_vision)} person objects with face crops "
                f"for {media_uuid_str}..."
            )
            
            # Re-enable enrichment now that pipeline is confirmed working
            try:
                enriched_person_objects = await enrich_person_objects_with_face_crops(
                    person_objects=person_objects_from_vision,
                    media_uuid=media_uuid,
                    auth_token=auth_token,
                    vision_url=vision_url,
                    gateway_url=gateway_url
                )
            except Exception as enrich_error:
                logger.error(f"Enrichment failed: {enrich_error}", exc_info=True)
                # Fall back to using person_objects without enrichment
                enriched_person_objects = person_objects_from_vision
            
            logger.info(
                f"Face crop enrichment completed for {media_uuid_str}: "
                f"{sum(1 for po in enriched_person_objects if 'best_face_crop' in po)}/{len(enriched_person_objects)} "
                f"person objects have face crops"
            )
            logger.info(f"DEBUG: enriched_person_objects count: {len(enriched_person_objects)}")
            logger.info(f"[VMETA DEBUG] enriched_person_objects: {len(enriched_person_objects)}")
            logger.info(f"[VMETA DEBUG] enriched_person_objects sample: {enriched_person_objects[:1] if enriched_person_objects else 'EMPTY'}")
            
            # Step 5: Transform enriched person objects to MVR format
            # Vision returns person_id, but MVRService needs person_object_uuid
            # MVRService will generate embeddings via ml_processor.process_person_object
            from uuid import uuid4
            person_objects = []
            
            for po in enriched_person_objects:
                # Add required fields for MVRService compatibility
                # Use Vision service's calculated quality score (weighted average of face qualities)
                # Fall back to 0.85 only if quality_score is missing or 0.0
                vision_quality = po.get('quality_score', 0.0)
                
                # Orchestrator returns quality_score in 0-100 range (e.g., 21.09)
                # Individual face quality_scores in representative_faces are also 0-100 (e.g., 23.063)
                # Database constraint requires: CHECK (face_quality >= 0.0 AND face_quality <= 1.0)
                # MUST normalize by dividing by 100
                if vision_quality > 0.0:
                    # Normalize from 0-100 to 0-1 range
                    effective_quality = vision_quality / 100.0
                else:
                    # Fallback quality (already in 0-1 range)
                    effective_quality = 0.85
                
                transformed_po = {
                    **po,
                    'person_object_uuid': str(uuid4()),  # Generate temporary UUID
                    'media_uuid': media_uuid_str,
                    'video_uuid': media_uuid_str,  # Alias for compatibility
                    'face_quality': effective_quality,  # Normalized quality (0.0-1.0)
                    'quality_score': effective_quality,  # Consistent with face_quality
                    'confidence_score': 0.9,  # Default confidence
                    # best_face_crop already added by enrichment function
                }
                person_objects.append(transformed_po)
            
            logger.info(
                f"Transformed {len(person_objects)} person objects for MVR processing "
                f"(media: {media_uuid_str})"
            )
            logger.info(f"DEBUG: person_objects sample after transform: {person_objects[:1] if person_objects else 'EMPTY'}")
            logger.info(f"[VMETA DEBUG] transformed person_objects: {len(person_objects)}")
            
            if not person_objects:
                # No faces detected - valid result
                logger.info(f"No faces detected in {media_uuid_str}")
                results.append(MediaResult(
                    media_uuid=media_uuid_str,
                    media_type=media_type,
                    status="completed",
                    mvr_people=[],
                    total_faces_detected=0,
                    mvr_people_count=0,
                    processing_time_ms=int((time.time() - media_start) * 1000)
                ))
                continue
            
            logger.info(
                f"Found {len(person_objects)} person objects for {media_uuid_str}, "
                f"creating individuals and MVR people..."
            )
            logger.info(f"[VMETA DEBUG] About to call MVR service with {len(person_objects)} person objects")
            logger.info(f"[VMETA DEBUG] person_objects sample: {person_objects[:1] if person_objects else 'EMPTY'}")
            
            # Step 6: Process single media for MVR creation
            # This creates isolated individuals linked to person_objects, then creates MVR people
            # Maintains relationship: MVR → Individual → Person Objects (for routes/appearances)
            result_dict = await mvr_service.process_single_media_for_mvr(
                media_uuid=media_uuid,
                media_type=media_type,
                person_objects=person_objects,
                similarity_threshold=request.processing_options.similarity_threshold,
                min_face_quality=request.processing_options.min_face_quality,
                include_demographics=request.processing_options.include_demographics,
                include_route_data=request.processing_options.include_route_data
            )
            
            logger.info(
                f"MVR creation completed for {media_uuid_str}: "
                f"{len(result_dict.get('mvr_people', []))} MVR people created"
            )
            
            # Convert result to MediaResult model
            mvr_people_models = []
            for mvr_data in result_dict.get('mvr_people', []):
                # Build route data if included
                route_data = None
                if request.processing_options.include_route_data and person_objects:
                    route_data_dict = build_route_data(
                        media_type=media_type,
                        person_objects=person_objects,
                        video_width=media_metadata.get('resolution', {}).get('width', 1920),
                        video_height=media_metadata.get('resolution', {}).get('height', 1080),
                        include_route=True
                    )
                    if route_data_dict:
                        route_data = RouteData(**route_data_dict)
                
                # Build demographics if included
                demographics = None
                if mvr_data.get('demographics'):
                    demographics = Demographics(**mvr_data['demographics'])
                
                # Build appearances (placeholder - would need actual data)
                # Convert to dict format for Pydantic model validation
                appearances = [
                    {
                        'individual_uuid': ind_uuid,
                        'video_uuid': media_uuid_str,
                        'person_object_uuid': ind_uuid,  # Simplified
                        'start_timestamp': media_metadata.get('timestamp', '2025-11-29T00:00:00'),
                        'end_timestamp': media_metadata.get('timestamp', '2025-11-29T00:00:00'),
                        'confidence': mvr_data.get('confidence_score', 0.9)
                    }
                    for ind_uuid in mvr_data.get('individual_uuids', [])
                ]
                
                mvr_person = MVRPerson(
                    mvr_people_uuid=mvr_data['mvr_people_uuid'],
                    individual_uuids=mvr_data.get('individual_uuids', []),
                    total_appearances=mvr_data.get('total_appearances', 1),
                    unique_videos=1,
                    first_seen=media_metadata.get('timestamp', '2025-11-29T00:00:00'),
                    last_seen=media_metadata.get('timestamp', '2025-11-29T00:00:00'),
                    confidence_score=mvr_data.get('confidence_score', 0.9),
                    quality_score=mvr_data.get('quality_score', 0.9),
                    demographics=demographics,
                    appearances=appearances,
                    route_data=route_data,
                    is_isolated=True,
                    source_media_uuid=media_uuid_str
                )
                
                mvr_people_models.append(mvr_person)
            
            results.append(MediaResult(
                media_uuid=media_uuid_str,
                media_type=media_type,
                status="completed",
                mvr_people=mvr_people_models,
                total_faces_detected=result_dict.get('total_faces_detected', 0),
                mvr_people_count=result_dict.get('mvr_people_count', 0),
                processing_time_ms=result_dict.get('processing_time_ms', 0)
            ))
            
        except Exception as e:
            logger.error(f"Error processing media {media_uuid_str}: {e}", exc_info=True)
            results.append(MediaResult(
                media_uuid=media_uuid_str,
                media_type="unknown",
                status="failed",
                error=MediaProcessingError(
                    code="PROCESSING_ERROR",
                    message=str(e)
                )
            ))
    
    # Calculate aggregate statistics
    processing_time = time.time() - start_time
    completed_results = [r for r in results if r.status == "completed"]
    failed_results = [r for r in results if r.status == "failed"]
    
    total_mvr = sum(r.mvr_people_count for r in completed_results)
    total_faces = sum(r.total_faces_detected for r in completed_results)
    
    # Break down by media type
    photos = [r for r in completed_results if r.media_type == "photo"]
    videos = [r for r in completed_results if r.media_type == "video"]
    
    processing_breakdown = {}
    
    if photos:
        processing_breakdown["photos"] = MediaTypeStatistics(
            count=len(photos),
            total_mvr=sum(r.mvr_people_count for r in photos),
            avg_processing_ms=sum(r.processing_time_ms for r in photos) / len(photos)
        )
    
    if videos:
        processing_breakdown["videos"] = MediaTypeStatistics(
            count=len(videos),
            total_mvr=sum(r.mvr_people_count for r in videos),
            avg_processing_ms=sum(r.processing_time_ms for r in videos) / len(videos)
        )
    
    aggregate_stats = AggregateStatistics(
        total_mvr_people_created=total_mvr,
        total_individuals_detected=total_faces,
        total_faces_detected=total_faces,
        average_mvr_per_media=total_mvr / len(completed_results) if completed_results else 0,
        processing_breakdown=processing_breakdown
    ) if request.response_format.aggregate_statistics else None
    
    return ProcessMediaResponse(
        success=True,
        total_media=len(request.media_uuids),
        processed_media=len(completed_results),
        failed_media=len(failed_results),
        processing_time_seconds=processing_time,
        results=results,
        aggregate_statistics=aggregate_stats
    )


# ============================================================================
# Router Export
# ============================================================================

__all__ = ["router"]

