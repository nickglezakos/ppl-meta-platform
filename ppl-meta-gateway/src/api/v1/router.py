"""
API v1 Router - Main API Gateway Router
"""

import os
import sys
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))

api_router = APIRouter()

# Add validation support
try:
    from shared.validation import SecurityValidator

    def validate_gateway_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate gateway input data."""
        validated_data = {}

        for key, value in data.items():
            if isinstance(value, str):
                try:
                    SecurityValidator.validate_sql_injection(value, key)
                    SecurityValidator.validate_xss(value, key)
                    validated_data[key] = SecurityValidator.escape_html(value)
                except ValueError as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Security validation failed for {key}: {str(e)}",
                    )
            else:
                validated_data[key] = value

        return validated_data

except ImportError:

    def validate_gateway_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback validation when shared module unavailable."""
        return data


@api_router.get("/status")
async def gateway_status():
    """Gateway status endpoint."""
    return {
        "service": "ppl-meta-gateway",
        "status": "operational",
        "version": "1.0.0",
        "features": ["input_validation", "security_protection", "request_routing"],
    }


@api_router.post("/validate")
async def validate_request(request: Request, data: Dict[str, Any]):
    """Validate incoming request data."""
    try:
        validated_data = validate_gateway_input(data)
        return {
            "status": "valid",
            "validated_data": validated_data,
            "message": "Request validation successful",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Validation processing error: {str(e)}"
        )
