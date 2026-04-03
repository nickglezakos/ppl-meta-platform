"""
PPL Meta Orchestrator - Workflow Settings API Endpoints
REST API for managing workflow configuration settings.

Provides endpoints to get and update workflow settings like velocity sensitivity
for face tracking temporal grouping.
"""

import logging
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from database import get_db
from services.workflow_settings_service import WorkflowSettingsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings/workflow", tags=["workflow-settings"])

# Authentication
security = HTTPBearer()

INTERNAL_SERVICE_TOKEN = os.getenv(
    "INTERNAL_SERVICE_TOKEN",
    "ppl-meta-internal-service-secret-key-change-in-production"
)


def get_auth_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_service_name: Optional[str] = Header(None, alias="X-Service-Name"),
) -> str:
    """
    Extract and validate authentication token.
    
    Accepts both:
    1. User authentication tokens (from mobile/web apps)
    2. Internal service tokens (from other microservices)
    
    Raises HTTPException if no valid auth provided.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Check if it's an internal service token
    if x_service_name and token == INTERNAL_SERVICE_TOKEN:
        return token
    
    # Otherwise assume it's a user token (validated by Node service)
    return token


# Request/Response Models

class VelocitySensitivityUpdate(BaseModel):
    """Request model for updating velocity sensitivity."""
    
    value: float = Field(
        ...,
        description="Velocity sensitivity percentage (5.0-50.0)",
        ge=5.0,
        le=50.0
    )
    updated_by: str = Field(
        default="user",
        description="Who updated the setting"
    )
    
    @validator('value')
    def validate_value(cls, v):
        if not (5.0 <= v <= 50.0):
            raise ValueError('Value must be between 5.0 and 50.0')
        return round(v, 1)  # Round to 1 decimal place
    
    class Config:
        schema_extra = {
            "example": {
                "value": 25.0,
                "updated_by": "admin@pplmeta.com"
            }
        }


class VelocitySensitivityResponse(BaseModel):
    """Response model for velocity sensitivity."""
    
    value: float
    min_value: float
    max_value: float
    description: str
    recommendation: str


class SettingsListResponse(BaseModel):
    """Response model for listing all settings."""
    
    settings: Dict[str, Any]
    count: int


class MVRMergeSettingsResponse(BaseModel):
    """Response model for MVR merge settings."""

    merge_rule: str
    merge_threshold: float
    min_threshold: float
    max_threshold: float


class MVRMergeSettingsUpdate(BaseModel):
    """Request model for updating MVR merge settings."""

    merge_rule: Optional[str] = Field(
        default=None,
        description="MVR merge rule: none, semi, auto",
    )
    merge_threshold: Optional[float] = Field(
        default=None,
        ge=0.30,
        le=0.95,
        description="Default threshold for MVR merge operations",
    )
    updated_by: str = Field(default="user", description="Who updated the setting")

    @validator("merge_rule")
    def validate_merge_rule(cls, value):
        if value is None:
            return value
        allowed = {"none", "semi", "auto"}
        if value not in allowed:
            raise ValueError("merge_rule must be one of: none, semi, auto")
        return value

    @validator("merge_threshold")
    def round_threshold(cls, value):
        if value is None:
            return value
        return round(float(value), 2)


# Endpoints

@router.get(
    "/velocity-sensitivity",
    response_model=VelocitySensitivityResponse,
    summary="Get velocity sensitivity setting",
    description="""
    Retrieve the current velocity sensitivity setting for face tracking.
    
    Returns the percentage tolerance used for temporal grouping of faces
    across video frames. This setting controls how much movement is allowed
    between frames when identifying the same person.
    
    **Authentication Required**: Bearer token or internal service token
    """
)
async def get_velocity_sensitivity(
    db: Session = Depends(get_db),
    auth_token: str = Depends(get_auth_token)
):
    """Get current velocity sensitivity setting."""
    try:
        service = WorkflowSettingsService(db)
        value = await service.get_velocity_sensitivity()
        
        recommendation = _get_recommendation(value)
        
        return VelocitySensitivityResponse(
            value=value,
            min_value=5.0,
            max_value=50.0,
            description="Face tracking tolerance percentage for temporal grouping",
            recommendation=recommendation
        )
        
    except Exception as e:
        logger.error(f"Error retrieving velocity sensitivity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve setting: {str(e)}"
        )


@router.put(
    "/velocity-sensitivity",
    response_model=Dict[str, Any],
    summary="Update velocity sensitivity setting",
    description="""
    Update the velocity sensitivity setting for face tracking.
    
    The setting is validated (must be between 5.0 and 50.0) and stored immediately,
    affecting all future person objects workflows.
    
    - **Lower values (5-15%)**: Stricter matching for slow-moving subjects
    - **Default (20%)**: Balanced for normal walking speed
    - **Higher values (30-50%)**: Looser matching for fast motion
    
    **Authentication Required**: Bearer token or internal service token
    """
)
async def update_velocity_sensitivity(
    request: VelocitySensitivityUpdate,
    db: Session = Depends(get_db),
    auth_token: str = Depends(get_auth_token)
):
    """Update velocity sensitivity setting."""
    try:
        service = WorkflowSettingsService(db)
        result = await service.update_setting(
            key='velocity_sensitivity',
            value=request.value,
            updated_by=request.updated_by
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return {
            "success": True,
            "message": result["message"],
            "value": result["value"],
            "recommendation": _get_recommendation(result["value"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating velocity sensitivity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update setting: {str(e)}"
        )


@router.get(
    "/all",
    response_model=SettingsListResponse,
    summary="Get all workflow settings",
    description="""
    Retrieve all workflow settings with their current values and metadata.
    
    **Authentication Required**: Bearer token or internal service token
    """
)
async def get_all_settings(
    db: Session = Depends(get_db),
    auth_token: str = Depends(get_auth_token)
):
    """Get all workflow settings."""
    try:
        service = WorkflowSettingsService(db)
        settings = await service.get_all_settings()
        
        return SettingsListResponse(
            settings=settings,
            count=len(settings)
        )
        
    except Exception as e:
        logger.error(f"Error retrieving all settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve settings: {str(e)}"
        )


@router.get(
    "/mvr-merge",
    response_model=MVRMergeSettingsResponse,
    summary="Get MVR merge settings",
    description="Get backend-managed MVR merge mode and default threshold.",
)
async def get_mvr_merge_settings(
    db: Session = Depends(get_db),
    auth_token: str = Depends(get_auth_token),
):
    try:
        service = WorkflowSettingsService(db)
        settings = await service.get_mvr_merge_settings()
        return MVRMergeSettingsResponse(**settings)
    except Exception as e:
        logger.error(f"Error retrieving MVR merge settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve MVR merge settings: {str(e)}",
        )


@router.put(
    "/mvr-merge",
    response_model=Dict[str, Any],
    summary="Update MVR merge settings",
    description="Update backend-managed MVR merge mode and/or threshold.",
)
async def update_mvr_merge_settings(
    request: MVRMergeSettingsUpdate,
    db: Session = Depends(get_db),
    auth_token: str = Depends(get_auth_token),
):
    try:
        if request.merge_rule is None and request.merge_threshold is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide merge_rule and/or merge_threshold",
            )

        service = WorkflowSettingsService(db)
        result = await service.update_mvr_merge_settings(
            merge_rule=request.merge_rule,
            merge_threshold=request.merge_threshold,
            updated_by=request.updated_by,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to update MVR merge settings"),
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating MVR merge settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update MVR merge settings: {str(e)}",
        )


# Helper Functions

def _get_recommendation(value: float) -> str:
    """Generate recommendation text based on sensitivity value."""
    if value <= 15:
        return "Recommended for stationary or slow-moving subjects"
    elif value <= 25:
        return "Recommended for normal walking speed (default)"
    elif value <= 40:
        return "Recommended for fast-moving subjects or running"
    else:
        return "Recommended for very fast motion or unstable cameras"
