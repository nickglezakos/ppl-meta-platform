"""
vmeta Service Proxy for MVR-People Endpoints.

Proxies requests to vmeta service for MVR-People operations.
"""

import logging
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.auth import AuthUser, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mvr-people", tags=["vmeta-proxy"])

# vmeta service URL - hardcoded for now
VMETA_BASE_URL = 'http://localhost:8008'


class BatchMatchAndMergeRequest(BaseModel):
    """Request model for batch match and merge."""
    individual_uuids: List[str] = Field(
        ..., description="List of individual UUIDs"
    )
    threshold: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Match threshold"
    )
    triggered_by: str = Field(
        default="cross_video_tracking_session",
        description="Source that triggered merge"
    )
    session_uuid: Optional[str] = Field(
        None, description="Optional session UUID"
    )


@router.post("/batch-match-and-merge")
async def batch_match_and_merge(
    request_data: BatchMatchAndMergeRequest,
    request: Request,
    current_user: AuthUser = Depends(get_current_user)
):
    """
    Proxy batch match and merge to vmeta service.
    
    Forwards the request to vmeta's batch-match-and-merge endpoint.
    """
    try:
        # Extract the authorization header from the incoming request
        auth_header = request.headers.get("Authorization")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            vmeta_url = (
                f"{VMETA_BASE_URL}/api/v1/mvr-people/"
                "batch-match-and-merge"
            )
            
            headers = {"Content-Type": "application/json"}
            # Forward authentication header if present
            if auth_header:
                headers["Authorization"] = auth_header
            
            logger.info(f"Proxying batch merge to vmeta: {vmeta_url}")
            logger.debug(f"Request: {request_data.model_dump()}")
            
            response = await client.post(
                vmeta_url,
                json=request_data.model_dump(),
                headers=headers,
            )
            
            if response.status_code != 200:
                logger.error(
                    f"vmeta status {response.status_code}: "
                    f"{response.text}"
                )
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"vmeta error: {response.text}"
                )
            
            result = response.json()
            unique = result.get('unique_count')
            original = result.get('original_count')
            logger.info(
                f"Batch merge complete: {unique} unique "
                f"from {original} original"
            )
            
            return result
            
    except HTTPException:
        # Re-raise FastAPI HTTPExceptions (don't catch our own errors)
        raise
    except httpx.TimeoutException:
        logger.error("vmeta service timeout")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="vmeta service timeout"
        )
    except httpx.HTTPError as e:
        logger.error(f"vmeta HTTP error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"vmeta unavailable: {str(e)}"
        )
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Unexpected error proxying to vmeta: {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error: {type(e).__name__}: {str(e)}"
        )
