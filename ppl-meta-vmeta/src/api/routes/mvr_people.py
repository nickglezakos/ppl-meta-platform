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

import logging
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
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
    IndividualAppearance,
)

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
    - threshold: Similarity threshold (default: 0.85)
    - auto_merge: Automatically merge matches above threshold (default: false)
    - max_results: Maximum results to return (default: 10)
    
    **Returns:**
    - 200 OK: List of matching Individuals with similarity scores
    - 404 Not Found: Individual not found
    """
    logger.info(f"Matching Individual {individual_uuid} (user: {current_user.get('email')})")
    
    # Parse request
    threshold = 0.85
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
            default_matching_threshold=config.get('similarity_threshold', 0.85),
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
    - threshold: Similarity threshold (default: 0.85)
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
      "threshold": 0.85,
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
                    IndividualAppearance(
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
                    IndividualAppearance(
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
            
            # Build the final query
            query = f"""
                SELECT
                    iva.video_uuid,
                    iva.person_object_uuid,
                    iva.start_timestamp,
                    iva.end_timestamp,
                    iva.confidence
                FROM individual_video_appearances iva
                WHERE {' AND '.join(query_conditions)}
                ORDER BY iva.start_timestamp ASC
            """
            
            appearances_rows = await conn.fetch(query, *query_params)
            
            if not appearances_rows:
                return {
                    "individual_uuid": individual_uuid,
                    "total_appearances": 0,
                    "unique_videos": 0,
                    "appearances": []
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
            
            return {
                "individual_uuid": individual_uuid,
                "total_appearances": len(appearances),
                "unique_videos": unique_videos,
                "first_seen": first_seen.isoformat(),
                "last_seen": last_seen.isoformat(),
                "appearances": appearances
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
                    "appearances": []
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
            
            return {
                "mvr_person_uuid": mvr_person_uuid,
                "individual_uuids": individual_uuids,
                "total_appearances": len(appearances),
                "unique_videos": unique_videos,
                "first_seen": first_seen.isoformat(),
                "last_seen": last_seen.isoformat(),
                "appearances": appearances
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
# Router Export
# ============================================================================

__all__ = ["router"]

