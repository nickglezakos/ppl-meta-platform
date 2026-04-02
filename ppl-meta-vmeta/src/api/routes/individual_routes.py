"""
Individual Routes API Routes
Paginated endpoints for retrieving route point data per individual.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.dependencies import get_current_user
from database.mvr_repository import MVRRepository, MVRRepositoryError
from models.individual_routes import (
    CameraRouteMetadata,
    CameraRoutePageResponse,
    CameraRoutesGroup,
    RouteMetadataResponse,
    RoutePage,
    RoutePageResponse,
    RoutePoint,
    RoutePointWithCamera,
    RoutesByCameraResponse,
    RoutesMetadataByCameraResponse,
    RouteSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/individuals", tags=["individual-routes"])

_MAX_PAGE_SIZE = 2000
_DEFAULT_PAGE_SIZE = 500


def _parse_individual_uuid(individual_uuid: str) -> UUID:
    try:
        return UUID(individual_uuid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid individual_uuid: {individual_uuid!r}",
        )


async def _get_mvr_repo() -> MVRRepository:
    """Dependency: return the shared MVRRepository or raise 503."""
    import main

    if not main.mvr_repository:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MVR-People services not initialized",
        )
    return main.mvr_repository


@router.get(
    "/{individual_uuid}/routes",
    response_model=RoutePageResponse,
    summary="Get paginated route points for an individual",
)
async def get_individual_routes(
    request: Request,
    individual_uuid: str,
    page_index: int = Query(0, ge=0, description="Zero-based page index"),
    page_size: int = Query(
        _DEFAULT_PAGE_SIZE,
        ge=1,
        le=_MAX_PAGE_SIZE,
        description=f"Points per page (max {_MAX_PAGE_SIZE})",
    ),
    camera_id: Optional[str] = Query(
        None, description="Filter by camera source_identifier"
    ),
    start_time_ms: Optional[int] = Query(
        None, description="Lower bound on timestamp_ms (inclusive)"
    ),
    end_time_ms: Optional[int] = Query(
        None, description="Upper bound on timestamp_ms (inclusive)"
    ),
    _current_user: dict = Depends(get_current_user),
    repo: MVRRepository = Depends(_get_mvr_repo),
) -> RoutePageResponse:
    """
    Return a page of route points for the given individual.

    Route points are drawn from `individual_video_appearances`. Supply `page_index` and `page_size`
    to walk through large result sets.  When `has_more` is `true` in the
    returned `page` envelope, increment `page_index` to fetch the next page.
    """
    individual_uuid_obj = _parse_individual_uuid(individual_uuid)

    try:
        result = await repo.get_individual_routes_paged(
            individual_uuid=individual_uuid_obj,
            page_index=page_index,
            page_size=page_size,
            camera_id=camera_id,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            auth_header=request.headers.get("Authorization"),
        )
    except MVRRepositoryError as exc:
        logger.error(f"Route paging error for {individual_uuid}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve route data",
        )

    total_points = result["total_points"]
    loaded_so_far = page_index * page_size + len(result["points"])
    has_more = loaded_so_far < total_points

    points = [RoutePoint(**pt) for pt in result["points"]]

    return RoutePageResponse(
        individual_uuid=individual_uuid,
        route_summary=RouteSummary(
            total_points=total_points,
            total_appearances=result["total_appearances"],
            start_time_ms=result.get("start_time_ms"),
            end_time_ms=result.get("end_time_ms"),
        ),
        page=RoutePage(
            page_index=page_index,
            page_size=page_size,
            total_points=total_points,
            has_more=has_more,
        ),
        points=points,
    )


@router.get(
    "/{individual_uuid}/routes/by-camera",
    response_model=RoutesByCameraResponse,
    summary="Get paginated route points grouped by camera for an individual",
)
async def get_individual_routes_by_camera(
    request: Request,
    individual_uuid: str,
    page_index: int = Query(0, ge=0, description="Zero-based page index"),
    page_size: int = Query(
        _DEFAULT_PAGE_SIZE,
        ge=1,
        le=_MAX_PAGE_SIZE,
        description=f"Points per page within each camera group (max {_MAX_PAGE_SIZE})",
    ),
    camera_id: Optional[str] = Query(
        None, description="Filter to a specific camera source_identifier"
    ),
    start_time_ms: Optional[int] = Query(
        None, description="Lower bound on timestamp_ms (inclusive)"
    ),
    end_time_ms: Optional[int] = Query(
        None, description="Upper bound on timestamp_ms (inclusive)"
    ),
    _current_user: dict = Depends(get_current_user),
    repo: MVRRepository = Depends(_get_mvr_repo),
) -> RoutesByCameraResponse:
    """Return paginated route points grouped by camera, then by individual."""
    individual_uuid_obj = _parse_individual_uuid(individual_uuid)

    try:
        result = await repo.get_individual_routes_by_camera_paged(
            individual_uuid=individual_uuid_obj,
            page_index=page_index,
            page_size=page_size,
            camera_id=camera_id,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            auth_header=request.headers.get("Authorization"),
        )
    except MVRRepositoryError as exc:
        logger.error(f"Camera-grouped route paging error for {individual_uuid}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve route data grouped by camera",
        )

    camera_groups = []
    for camera in result.get("cameras", []):
        individuals = []
        for individual in camera.get("individuals", []):
            points = [RoutePointWithCamera(**pt) for pt in individual.get("points", [])]
            individuals.append(
                CameraRoutePageResponse(
                    individual_uuid=individual["individual_uuid"],
                    route_summary=RouteSummary(
                        total_points=individual["total_points"],
                        total_appearances=individual["total_appearances"],
                        start_time_ms=individual.get("start_time_ms"),
                        end_time_ms=individual.get("end_time_ms"),
                    ),
                    page=RoutePage(
                        page_index=page_index,
                        page_size=page_size,
                        total_points=individual["total_points"],
                        has_more=individual["has_more"],
                    ),
                    points=points,
                )
            )

        camera_groups.append(
            CameraRoutesGroup(
                camera_id=camera["camera_id"],
                camera_name=camera.get("camera_name"),
                total_points_across_individuals=camera.get(
                    "total_points_across_individuals", 0
                ),
                total_appearances_across_individuals=camera.get(
                    "total_appearances_across_individuals", 0
                ),
                has_more=camera.get("has_more", False),
                individuals=individuals,
            )
        )

    return RoutesByCameraResponse(
        requested_individual_uuid=individual_uuid,
        cameras=camera_groups,
    )


@router.get(
    "/{individual_uuid}/routes/metadata",
    response_model=RouteMetadataResponse,
    summary="Get route metadata for an individual (no point payload)",
)
async def get_individual_routes_metadata(
    request: Request,
    individual_uuid: str,
    camera_id: Optional[str] = Query(
        None, description="Filter by camera source_identifier"
    ),
    start_time_ms: Optional[int] = Query(
        None, description="Lower bound on timestamp_ms (inclusive)"
    ),
    end_time_ms: Optional[int] = Query(
        None, description="Upper bound on timestamp_ms (inclusive)"
    ),
    _current_user: dict = Depends(get_current_user),
    repo: MVRRepository = Depends(_get_mvr_repo),
) -> RouteMetadataResponse:
    """
    Return lightweight route metadata for the given individual.

    No point-level data is transferred.  Useful for initialising UI
    skeleton state before the first page of points has loaded.
    """
    individual_uuid_obj = _parse_individual_uuid(individual_uuid)

    try:
        result = await repo.get_individual_routes_metadata(
            individual_uuid=individual_uuid_obj,
            camera_id=camera_id,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            auth_header=request.headers.get("Authorization"),
        )
    except MVRRepositoryError as exc:
        logger.error(f"Route metadata error for {individual_uuid}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve route metadata",
        )

    return RouteMetadataResponse(
        individual_uuid=individual_uuid,
        total_points=result["total_points"],
        total_appearances=result["total_appearances"],
        start_time_ms=result.get("start_time_ms"),
        end_time_ms=result.get("end_time_ms"),
        per_video_counts=result.get("per_video_counts", []),
    )


@router.get(
    "/{individual_uuid}/routes/metadata/by-camera",
    response_model=RoutesMetadataByCameraResponse,
    summary="Get route metadata grouped by camera for an individual",
)
async def get_individual_routes_metadata_by_camera(
    request: Request,
    individual_uuid: str,
    camera_id: Optional[str] = Query(
        None, description="Filter to a specific camera source_identifier"
    ),
    start_time_ms: Optional[int] = Query(
        None, description="Lower bound on timestamp_ms (inclusive)"
    ),
    end_time_ms: Optional[int] = Query(
        None, description="Upper bound on timestamp_ms (inclusive)"
    ),
    _current_user: dict = Depends(get_current_user),
    repo: MVRRepository = Depends(_get_mvr_repo),
) -> RoutesMetadataByCameraResponse:
    """Return metadata grouped by camera for an individual without route points."""
    individual_uuid_obj = _parse_individual_uuid(individual_uuid)

    try:
        result = await repo.get_individual_routes_metadata_by_camera(
            individual_uuid=individual_uuid_obj,
            camera_id=camera_id,
            start_time_ms=start_time_ms,
            end_time_ms=end_time_ms,
            auth_header=request.headers.get("Authorization"),
        )
    except MVRRepositoryError as exc:
        logger.error(f"Camera-grouped route metadata error for {individual_uuid}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve route metadata grouped by camera",
        )

    return RoutesMetadataByCameraResponse(
        requested_individual_uuid=individual_uuid,
        cameras=[
            CameraRouteMetadata(
                camera_id=camera["camera_id"],
                camera_name=camera.get("camera_name"),
                total_points=camera.get("total_points", 0),
                total_appearances=camera.get("total_appearances", 0),
                start_time_ms=camera.get("start_time_ms"),
                end_time_ms=camera.get("end_time_ms"),
            )
            for camera in result.get("cameras", [])
        ],
    )
