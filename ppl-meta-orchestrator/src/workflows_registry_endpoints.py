"""
PPL Meta Orchestrator - Workflows Registry Endpoints
REST API endpoints for workflow registry management.
"""

import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from workflows_registry import (
    WorkflowDefinition,
    WorkflowCategory,
    get_workflow_registry
)

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflows Registry"])
security = HTTPBearer(auto_error=False)

# Internal service token for inter-service communication.
# Security hardening (Proposal §10.2 C2): must be set via env var.
# No default value — fails fast if misconfigured.
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "")
if not INTERNAL_SERVICE_TOKEN:
    raise RuntimeError(
        "INTERNAL_SERVICE_TOKEN environment variable must be set. "
        "Generate a unique token for this deployment."
    )


def get_auth_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_service_name: Optional[str] = Header(None, alias="X-Service-Name"),
) -> str:
    """
    Extract and validate authentication token (optional for workflow registry).
    
    Accepts both:
    1. User authentication tokens (from mobile/web apps)
    2. Internal service tokens (from other microservices)
    
    Returns empty string if no auth provided (registry is public but supports auth).
    """
    if not credentials:
        return ""
    
    token = credentials.credentials
    
    # Check if it's an internal service token
    if x_service_name and token == INTERNAL_SERVICE_TOKEN:
        return token
    
    # Otherwise assume it's a user token (will be validated by downstream services if needed)
    return token


@router.get("/registry", response_model=List[WorkflowDefinition])
async def list_workflows(
    category: Optional[WorkflowCategory] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    auth_token: str = Depends(get_auth_token)
):
    """
    Get list of all available workflows in the platform.
    
    This endpoint returns the complete registry of workflows that can be
    used with triggers and automation. Each workflow includes metadata,
    parameters, and execution statistics.
    
    Args:
        category: Optional category filter (detection, tracking, analytics, etc.)
        is_active: Optional filter for active/inactive workflows
        
    Returns:
        List of workflow definitions with full metadata
    """
    registry = get_workflow_registry()
    workflows = registry.list_workflows(category=category, is_active=is_active)
    return workflows


@router.get("/count")
async def get_workflow_count(auth_token: str = Depends(get_auth_token)):
    """
    Get total count of registered workflows.
    
    Returns:
        Dictionary with workflow count
    """
    registry = get_workflow_registry()
    return {
        "total_workflows": registry.get_workflow_count(),
        "categories": {
            "detection": len(registry.list_workflows(category=WorkflowCategory.DETECTION)),
            "tracking": len(registry.list_workflows(category=WorkflowCategory.TRACKING)),
            "analytics": len(registry.list_workflows(category=WorkflowCategory.ANALYTICS)),
            "automation": len(registry.list_workflows(category=WorkflowCategory.AUTOMATION)),
            "lifecycle": len(registry.list_workflows(category=WorkflowCategory.LIFECYCLE)),
        }
    }


@router.get("/categories")
async def list_categories(auth_token: str = Depends(get_auth_token)):
    """
    Get list of all workflow categories.
    
    Returns:
        List of available categories
    """
    return {
        "categories": [
            {
                "id": cat.value,
                "name": cat.value.replace("_", " ").title()
            }
            for cat in WorkflowCategory
        ]
    }


@router.get("/registry/{workflow_id}", response_model=WorkflowDefinition)
async def get_workflow(
    workflow_id: str,
    auth_token: str = Depends(get_auth_token)
):
    """
    Get detailed information about a specific workflow.
    
    Args:
        workflow_id: Unique workflow identifier
        
    Returns:
        Complete workflow definition
        
    Raises:
        HTTPException: 404 if workflow not found
    """
    registry = get_workflow_registry()
    workflow = registry.get_workflow(workflow_id)
    
    if not workflow:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{workflow_id}' not found in registry"
        )
    
    return workflow
