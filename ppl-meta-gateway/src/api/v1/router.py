"""
API v1 Router - Main API Gateway Router
"""

import os
import sys
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from jose import JWTError, jwt

# Add shared modules to path
parent_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
sys.path.append(parent_dir)

api_router = APIRouter()

# JWT Configuration (should match Node service config)
JWT_SECRET_KEY = "default-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"


def extract_user_from_token(request: Request) -> Dict[str, Any]:
    """Extract user information from JWT token in Authorization header."""
    try:
        # Get Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401, detail="Missing or invalid authorization header"
            )

        # Extract token
        token = auth_header.split(" ")[1]

        # Decode JWT token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "email": payload.get("email"),
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation error: {str(e)}")


# Service endpoints configuration
SERVICES = {
    "node": "http://localhost:8001",
    "media": "http://localhost:8000",
    "orchestrator": "http://localhost:8002",
}

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


async def _proxy_to_node_service(request: Request) -> JSONResponse:
    """Helper function to proxy requests to the Node service."""
    try:
        # Get the original path and method
        path = str(request.url.path)
        method = request.method

        # Construct the target URL
        target_url = f"{SERVICES['node']}{path}"

        # Get request body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()

        # Get headers (exclude host to avoid conflicts)
        headers = dict(request.headers)
        headers.pop("host", None)

        # Make the proxy request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            )

            # Determine response content type
            content_type = response.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                response_content = response.json()
            else:
                response_content = {"data": response.text}

            # Return the response from the Node service
            return JSONResponse(
                content=response_content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal proxy error: {str(e)}")


@api_router.post("/users/register")
async def register_user(request: Request):
    """Proxy user registration to Node service."""
    return await _proxy_to_node_service(request)


@api_router.post("/users/login")
async def login_user(request: Request):
    """Proxy user login to Node service."""
    return await _proxy_to_node_service(request)


@api_router.post("/users/logout")
async def logout_user(request: Request):
    """Proxy user logout to Node service."""
    return await _proxy_to_node_service(request)


@api_router.get("/users/me")
async def get_current_user(request: Request):
    """Proxy get current user to Node service."""
    return await _proxy_to_node_service(request)


@api_router.put("/users/me")
async def update_current_user(request: Request):
    """Proxy update current user to Node service."""
    return await _proxy_to_node_service(request)


@api_router.delete("/users/me")
async def delete_current_user(request: Request):
    """Proxy delete current user to Node service."""
    return await _proxy_to_node_service(request)


@api_router.post("/users/verify-email")
async def verify_email(request: Request):
    """Proxy email verification to Node service."""
    return await _proxy_to_node_service(request)


@api_router.post("/users/reset-password")
async def reset_password(request: Request):
    """Proxy password reset to Node service."""
    return await _proxy_to_node_service(request)


@api_router.post("/users/change-password")
async def change_password(request: Request):
    """Proxy password change to Node service."""
    return await _proxy_to_node_service(request)


@api_router.post("/users/update-password")
async def update_password(request: Request):
    """Proxy password update to Node service."""
    return await _proxy_to_node_service(request)


@api_router.get("/users/profile")
async def get_user_profile(request: Request):
    """Proxy get user profile to Node service."""
    return await _proxy_to_node_service(request)


@api_router.get("/users/")
async def list_users(request: Request):
    """Proxy list users to Node service."""
    return await _proxy_to_node_service(request)


@api_router.get("/test-profile")
async def test_profile_endpoint():
    """Test endpoint to verify routing is working."""
    return {"message": "Profile route test successful", "status": "working"}


@api_router.get("/user/profile")
async def get_user_profile_singular(request: Request):
    """Proxy get user profile (singular form) to Node service."""
    # Rewrite the URL to use the correct plural form for Node service
    corrected_path = "/api/v1/users/profile"
    target_url = f"{SERVICES['node']}{corrected_path}"

    try:
        # Get headers (exclude host to avoid conflicts)
        headers = dict(request.headers)
        headers.pop("host", None)

        # Make the proxy request to Node service
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=dict(request.query_params),
            )

            # Determine response content type
            content_type = response.headers.get("content-type", "")
            if content_type.startswith("application/json"):
                response_content = response.json()
            else:
                response_content = {"data": response.text}

            # Return the response from the Node service
            return JSONResponse(
                content=response_content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal proxy error: {str(e)}")


async def _proxy_to_media_service(request: Request) -> Response:
    """Helper function to proxy requests to the Media service."""
    try:
        # Get the original path and method
        path = str(request.url.path)
        method = request.method

        # Construct the target URL
        target_url = f"{SERVICES['media']}{path}"

        # Get request body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()

        # Get headers (exclude host to avoid conflicts)
        headers = dict(request.headers)
        headers.pop("host", None)

        # Make the proxy request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            )

            # Return the raw response for media content
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get(
                    "content-type", "application/octet-stream"
                ),
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503, detail=f"Media service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal media proxy error: {str(e)}"
        )


# Capabilities Service Routes
@api_router.get("/capabilities/my-capabilities")
async def get_my_capabilities(request: Request):
    """Proxy get my capabilities to Node service."""
    return await _proxy_to_node_service(request)


@api_router.get("/capabilities/by-role/{role_id}")
async def get_capabilities_by_role(request: Request):
    """Proxy get capabilities by role to Node service."""
    return await _proxy_to_node_service(request)


@api_router.get("/capabilities/by-user/{user_id}")
async def get_capabilities_by_user(request: Request):
    """Proxy get capabilities by user to Node service."""
    return await _proxy_to_node_service(request)


# Media Service Routes
@api_router.post("/media/upload")
async def upload_media(request: Request):
    """Proxy media upload to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/search")
async def search_media(request: Request):
    """Proxy media search to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/analytics")
async def get_media_analytics(request: Request):
    """Return analytics data for the authenticated user."""
    try:
        # First, get user profile to get the UUID (this also validates the JWT)
        profile_url = f"{SERVICES['node']}/api/v1/users/profile"
        headers = dict(request.headers)
        headers.pop("host", None)

        async with httpx.AsyncClient(timeout=30.0) as client:
            profile_response = await client.get(profile_url, headers=headers)

            if profile_response.status_code != 200:
                raise HTTPException(
                    status_code=profile_response.status_code,
                    detail="Authentication failed",
                )

            profile_data = profile_response.json()
            user_guid = profile_data.get("guid")

            if not user_guid:
                raise HTTPException(status_code=400, detail="User GUID not found")

            # Now get user media stats from media service
            stats_url = f"{SERVICES['media']}/api/v1/media/user/{user_guid}/stats"

            stats_response = await client.get(stats_url, headers=headers)

            if stats_response.status_code == 200:
                backend_stats = stats_response.json()

                # Transform backend stats to match frontend MediaAnalytics format
                analytics_data = {
                    "totalItems": backend_stats.get("total_count", 0),
                    "totalSize": backend_stats.get("total_size_bytes", 0),
                    "averageFileSize": float(
                        backend_stats.get("total_size_bytes", 0)
                        / max(backend_stats.get("total_count", 1), 1)
                    ),
                    "itemsByType": {
                        "image": backend_stats.get("by_type", {}).get("picture", 0),
                        "video": backend_stats.get("by_type", {}).get("video", 0),
                        "audio": backend_stats.get("by_type", {}).get("audio", 0),
                        "document": backend_stats.get("by_type", {}).get("document", 0),
                    },
                    "uploadsByDay": backend_stats.get("uploads_by_day", {}),
                    "accessesByDay": backend_stats.get("access_by_day", {}),
                    "popularTags": backend_stats.get("popular_tags", []),
                    "mostAccessedItem": backend_stats.get("most_accessed_item"),
                }

                return analytics_data
            else:
                # Fallback to empty analytics if backend fails
                return {
                    "totalItems": 0,
                    "totalSize": 0,
                    "averageFileSize": 0.0,
                    "itemsByType": {"image": 0, "video": 0, "audio": 0, "document": 0},
                    "uploadsByDay": {},
                    "accessesByDay": {},
                    "popularTags": [],
                    "mostAccessedItem": None,
                }

    except HTTPException:
        raise
    except Exception as e:
        # Return empty analytics on any error to prevent frontend crashes
        return {
            "totalItems": 0,
            "totalSize": 0,
            "averageFileSize": 0.0,
            "itemsByType": {"image": 0, "video": 0, "audio": 0, "document": 0},
            "uploadsByDay": {},
            "accessesByDay": {},
            "popularTags": [],
            "mostAccessedItem": None,
        }


@api_router.get("/media/{media_id}")
async def get_media(request: Request):
    """Proxy get media to Media service."""
    return await _proxy_to_media_service(request)


@api_router.delete("/media/{media_id}")
async def delete_media(request: Request):
    """Proxy delete media to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/download/{media_id}")
async def download_media(request: Request):
    """Proxy media download to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/stream/{media_id}")
async def stream_media(request: Request):
    """Proxy media streaming to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/stream-token/{media_id}")
async def stream_media_with_token(request: Request):
    """Proxy media streaming with token to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/thumbnail/{media_id}")
async def get_media_thumbnail(request: Request):
    """Proxy media thumbnail to Media service."""
    return await _proxy_to_media_service(request)


@api_router.post("/media/collections")
async def create_media_collection(request: Request):
    """Proxy create media collection to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/collections")
async def get_media_collections(request: Request):
    """Proxy get media collections to Media service."""
    return await _proxy_to_media_service(request)


@api_router.put("/media/collections/{collection_id}")
async def update_media_collection(request: Request):
    """Proxy update media collection to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/collections/{collection_id}/items")
async def get_collection_items(request: Request):
    """Proxy get collection items to Media service."""
    return await _proxy_to_media_service(request)


@api_router.post("/media/collections/{collection_id}/add/{media_id}")
async def add_media_to_collection(request: Request):
    """Proxy add media to collection to Media service."""
    return await _proxy_to_media_service(request)


@api_router.delete("/media/collections/{collection_id}/remove/{media_id}")
async def remove_media_from_collection(request: Request):
    """Proxy remove media from collection to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/debug-user-profile")
async def debug_user_profile():
    """Debug route for user profile testing."""
    return {"message": "Debug user profile route working", "endpoint": "/user/profile"}
