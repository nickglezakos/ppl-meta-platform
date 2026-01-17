"""
API v1 Router - Main API Gateway Router
"""

import os
import sys
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from jose import JWTError, jwt

# Add shared modules to path
parent_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
sys.path.append(parent_dir)

api_router = APIRouter()


async def _stream_proxy_response(target_url: str, headers: dict, query_params):
    """Stream proxy response for MJPEG video streaming."""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "GET", target_url, headers=headers, params=dict(query_params)
            ) as response:
                # Forward the response headers
                response_headers = dict(response.headers)

                async def generate():
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        yield chunk

                return StreamingResponse(
                    generate(),
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get(
                        "content-type", "application/octet-stream"
                    ),
                )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503, detail=f"Media streaming service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal streaming proxy error: {str(e)}"
        )


# JWT Configuration (should match Node service config)
JWT_SECRET_KEY = "ppl-meta-secret-key-development-only-change-in-production"
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
    "vision": "http://localhost:8003",
    "cameras": "http://localhost:8005",
    "vmeta": "http://localhost:8008",
    "communications": "http://localhost:8009",
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


@api_router.get("/users/storage-preferences")
async def get_user_storage_preferences(request: Request):
    """Proxy get user storage preferences to Media service."""
    return await _proxy_to_media_service(request)


@api_router.put("/users/storage-preferences")
async def update_user_storage_preferences(request: Request):
    """Proxy update user storage preferences to Media service."""
    return await _proxy_to_media_service(request)


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
    import logging
    logger = logging.getLogger(__name__)
    
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
        
        # 🔍 DEBUG: Log authorization header status
        auth_header = headers.get("authorization", "MISSING")
        logger.info(f"🔐 [MEDIA-PROXY] {method} {path} - Auth header: {'Present' if auth_header != 'MISSING' else 'MISSING'}")

        # Check if this is a streaming endpoint
        is_streaming = "/stream/video/" in path

        if is_streaming:
            # Handle streaming responses with proper streaming proxy
            return await _stream_proxy_response(
                target_url, headers, request.query_params
            )
        else:
            # Handle regular media responses
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


# NEW: Embedded face detection streaming endpoints
@api_router.get("/stream/video/{media_id}")
async def stream_video_with_embedded_faces(request: Request):
    """Proxy embedded face detection video streaming to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/stream/info/{media_id}/faces")
async def get_embedded_face_detection_info(request: Request):
    """Proxy embedded face detection info to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/stream/faces/{media_id}/frame/{frame_number}")
async def get_faces_at_frame(request: Request):
    """Proxy real-time frame face detection to Media service (Issue 052)."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/thumbnail/{media_id}")
async def get_media_thumbnail(request: Request):
    """Proxy media thumbnail to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/{media_id}/frame/{frame_number}")
async def extract_video_frame(request: Request):
    """Proxy video frame extraction to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/{media_id}/video-properties")
async def get_video_properties(request: Request):
    """Proxy video properties to Media service (Issue 044)."""
    return await _proxy_to_media_service(request)


@api_router.post("/media/collections")
async def create_media_collection(request: Request):
    """Proxy create media collection to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/collections")
async def get_media_collections(request: Request):
    """Proxy get media collections to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/media/collections/{collection_id}")
async def get_media_collection(request: Request):
    """Proxy get single media collection to Media service."""
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


@api_router.post("/media/collections/{collection_id}/bulk-add")
async def bulk_add_to_collection(request: Request):
    """Proxy bulk add media to collection to Media service."""
    return await _proxy_to_media_service(request)


@api_router.delete("/media/collections/{collection_id}")
async def delete_collection(request: Request):
    """Proxy delete collection to Media service."""
    return await _proxy_to_media_service(request)


@api_router.delete("/media/collections/{collection_id}/remove/{media_id}")
async def remove_media_from_collection(request: Request):
    """Proxy remove media from collection to Media service."""
    return await _proxy_to_media_service(request)


# ============================================================================
# Signage Service Routes - Video List Management & Device Control
# ============================================================================

@api_router.post("/signage/video-lists")
async def create_video_list(request: Request):
    """Proxy create video list to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/signage/video-lists")
async def list_video_lists(request: Request):
    """Proxy list video lists to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/signage/video-lists/{list_uuid}")
async def get_video_list(request: Request):
    """Proxy get video list details to Media service."""
    return await _proxy_to_media_service(request)


@api_router.put("/signage/video-lists/{list_uuid}")
async def update_video_list(request: Request):
    """Proxy update video list to Media service."""
    return await _proxy_to_media_service(request)


@api_router.delete("/signage/video-lists/{list_uuid}")
async def delete_video_list(request: Request):
    """Proxy delete video list to Media service."""
    return await _proxy_to_media_service(request)


@api_router.post("/signage/video-lists/{list_uuid}/sync")
async def sync_video_list(request: Request):
    """Proxy sync video list to devices to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/signage/devices")
async def list_signage_devices(request: Request):
    """Proxy list signage devices to Media service."""
    return await _proxy_to_media_service(request)


@api_router.post("/signage/devices/register")
async def register_signage_device(request: Request):
    """Proxy register signage device to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/signage/devices/{device_uuid}")
async def get_signage_device(request: Request):
    """Proxy get signage device details to Media service."""
    return await _proxy_to_media_service(request)


@api_router.put("/signage/devices/{device_uuid}")
async def update_signage_device(request: Request):
    """Proxy update signage device to Media service."""
    return await _proxy_to_media_service(request)


@api_router.delete("/signage/devices/{device_uuid}")
async def delete_signage_device(request: Request):
    """Proxy delete signage device to Media service."""
    return await _proxy_to_media_service(request)


@api_router.post("/signage/playback/control")
async def playback_control(request: Request):
    """Proxy playback control commands to Media service."""
    return await _proxy_to_media_service(request)


@api_router.post("/signage/devices/{device_uuid}/playback")
async def control_device_playback(request: Request):
    """Proxy playback control commands to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/signage/sync-history")
async def get_sync_history(request: Request):
    """Proxy get sync history to Media service."""
    return await _proxy_to_media_service(request)


@api_router.post("/signage/etl/sync")
async def sync_video_list_etl(request: Request):
    """Proxy ETL sync request to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/signage/etl/jobs")
async def get_etl_jobs(request: Request):
    """Proxy get ETL jobs status to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/signage/etl/jobs/{job_id}")
async def get_etl_job_status(request: Request):
    """Proxy get ETL job status to Media service."""
    return await _proxy_to_media_service(request)


# Trigger Routes - Proxy to Media service
@api_router.get("/triggers/")
async def list_triggers(request: Request):
    """Proxy list triggers to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/triggers/{trigger_id}")
async def get_trigger(request: Request):
    """Proxy get trigger to Media service."""
    return await _proxy_to_media_service(request)


@api_router.post("/triggers/")
async def create_trigger(request: Request):
    """Proxy create trigger to Media service."""
    return await _proxy_to_media_service(request)


@api_router.put("/triggers/{trigger_id}")
async def update_trigger(request: Request):
    """Proxy update trigger to Media service."""
    return await _proxy_to_media_service(request)


@api_router.delete("/triggers/{trigger_id}")
async def delete_trigger(request: Request):
    """Proxy delete trigger to Media service."""
    return await _proxy_to_media_service(request)


@api_router.patch("/triggers/{trigger_id}/toggle")
async def toggle_trigger(request: Request):
    """Proxy toggle trigger to Media service."""
    return await _proxy_to_media_service(request)


# User Actions Routes - Proxy to Media service
@api_router.get("/user-actions/")
async def list_user_actions(request: Request):
    """Proxy list user actions to Media service."""
    return await _proxy_to_media_service(request)


@api_router.get("/user-actions/{action_id}")
async def get_user_action(request: Request):
    """Proxy get user action to Media service."""
    return await _proxy_to_media_service(request)


@api_router.post("/user-actions/")
async def create_user_action(request: Request):
    """Proxy create user action to Media service."""
    return await _proxy_to_media_service(request)


@api_router.put("/user-actions/{action_id}")
async def update_user_action(request: Request):
    """Proxy update user action to Media service."""
    return await _proxy_to_media_service(request)


@api_router.delete("/user-actions/{action_id}")
async def delete_user_action(request: Request):
    """Proxy delete user action to Media service."""
    return await _proxy_to_media_service(request)


# Email Settings Routes (Communications Service)
async def _proxy_to_communications_service(request: Request) -> Response:
    """Helper function to proxy requests to the Communications service."""
    try:
        # Build target URL - keep full path including /api/v1
        path = request.url.path
        target_url = f"{SERVICES['communications']}{path}"

        # Forward query parameters
        if request.url.query:
            target_url += f"?{request.url.query}"

        # Prepare headers (forward authorization)
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in ["host", "content-length"]
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=await request.body(),
                timeout=30.0,
            )

            # Filter out CORS and other headers that should be set by gateway middleware
            filtered_headers = {
                key: value
                for key, value in response.headers.items()
                if key.lower() not in [
                    "access-control-allow-origin",
                    "access-control-allow-credentials",
                    "access-control-allow-methods",
                    "access-control-allow-headers",
                    "access-control-expose-headers",
                ]
            }

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=filtered_headers,
                media_type=response.headers.get("content-type", "application/json"),
            )

    except httpx.RequestError as e:
        logger.error(f"Communications service request error: {e}")
        raise HTTPException(status_code=503, detail=f"Communications service unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Communications service proxy error: {e}")
        raise HTTPException(status_code=500, detail=f"Gateway error: {str(e)}")


@api_router.get("/settings/email")
async def get_email_settings(request: Request):
    """Proxy get email settings to Communications service."""
    return await _proxy_to_communications_service(request)


@api_router.put("/settings/email")
async def update_email_settings(request: Request):
    """Proxy update email settings to Communications service."""
    return await _proxy_to_communications_service(request)


@api_router.post("/settings/email/test")
async def test_email_settings(request: Request):
    """Proxy test email settings to Communications service."""
    return await _proxy_to_communications_service(request)


@api_router.get("/debug-user-profile")
async def debug_user_profile():
    """Debug route for user profile testing."""
    return {"message": "Debug user profile route working", "endpoint": "/user/profile"}


async def _proxy_to_vision_service(request: Request) -> Response:
    """Helper function to proxy requests to the Vision service."""
    try:
        # Build target URL
        path = request.url.path.replace("/api/v1/vision", "")
        target_url = f"{SERVICES['vision']}{path}"

        # Forward query parameters
        if request.url.query:
            target_url += f"?{request.url.query}"

        # Prepare headers (forward authorization and other important headers)
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in ["host", "content-length"]
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=await request.body(),
                timeout=30.0,
            )

            # Return the raw response for vision content
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type", "application/json"),
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503, detail=f"Vision service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal vision proxy error: {str(e)}"
        )


# Vision Service Routes
@api_router.get("/vision/health")
async def get_vision_health(request: Request):
    """Proxy vision health to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.post("/vision/detect")
async def detect_faces(request: Request):
    """Proxy face detection to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.get("/vision/faces/media/{media_id}/frame/{frame_number}")
async def get_video_frame_faces(request: Request):
    """Proxy video frame face detection to Vision service."""
    return await _proxy_to_vision_service(request)


# Person Objects API Routes
@api_router.get("/person-objects/health")
async def get_person_objects_health(request: Request):
    """Proxy person objects health to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.post("/person-objects/workflows/start")
async def start_person_objects_workflow(request: Request):
    """Proxy person objects workflow start to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.get("/person-objects/sessions/{session_uuid}")
async def get_person_objects_session(request: Request):
    """Proxy person objects session retrieval to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.get("/person-objects/workflows/{workflow_id}/status")
async def get_person_objects_workflow_status(request: Request):
    """Proxy person objects workflow status to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.get("/person-objects/sessions/{session_uuid}/statistics")
async def get_person_objects_statistics(request: Request):
    """Proxy person objects statistics to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.get("/person-objects/sessions/{session_uuid}/summary")
async def get_person_objects_summary(request: Request):
    """Proxy person objects summary to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.delete("/person-objects/sessions/{session_uuid}")
async def delete_person_objects_session(request: Request):
    """Proxy person objects session deletion to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.get("/person-objects/media/{media_uuid}/session")
async def find_session_by_media_uuid(request: Request):
    """Proxy session discovery by media UUID to Vision service."""
    return await _proxy_to_vision_service(request)


# Enhanced Workflow Widget API Routes for Vision Service
@api_router.get("/processing-status/{media_uuid}/widget")
async def get_widget_processing_status(request: Request):
    """Proxy widget-optimized processing status to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.get("/processing-status/{media_uuid}/analytics")
async def get_widget_processing_analytics(request: Request):
    """Proxy processing analytics for widgets to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.get("/processing-status/health")
async def get_processing_system_health(request: Request):
    """Proxy processing system health to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.get("/sessions/active/overview")
async def get_active_sessions_overview(request: Request):
    """Proxy active sessions overview to Vision service."""
    return await _proxy_to_vision_service(request)


@api_router.get("/sessions")
async def query_sessions(request: Request):
    """Proxy session queries to Vision service."""
    return await _proxy_to_vision_service(request)


async def _proxy_to_cameras_service(request: Request) -> Response:
    """Helper function to proxy requests to the Cameras service."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get the original path and method
        path = str(request.url.path)
        method = request.method

        # Construct the target URL
        target_url = f"{SERVICES['cameras']}{path}"

        # Get request body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()

        # Get headers (exclude host to avoid conflicts)
        headers = dict(request.headers)
        headers.pop("host", None)
        
        # 🔍 DEBUG: Log authorization header status
        auth_header = headers.get("authorization", "MISSING")
        logger.info(f"🔐 [CAMERAS-PROXY] {method} {path} - Auth header: {'Present' if auth_header != 'MISSING' else 'MISSING'}")

        # Make the proxy request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            )

            # Return the raw response for cameras content
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type", "application/json"),
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503, detail=f"Cameras service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal cameras proxy error: {str(e)}"
        )


# Cameras Service Routes
@api_router.get("/cameras")
async def get_cameras(request: Request):
    """Proxy get cameras to Cameras service."""
    # Validate authentication first
    extract_user_from_token(request)
    return await _proxy_to_cameras_service(request)


@api_router.get("/cameras/")
async def get_cameras_with_slash(request: Request):
    """Proxy get cameras to Cameras service (with trailing slash)."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Validate authentication first
        logger.info(f"🔐 [CAMERAS-ROUTE] Validating auth for {request.url.path}")
        extract_user_from_token(request)
        logger.info(f"🔐 [CAMERAS-ROUTE] Auth validation passed, proxying request")
        return await _proxy_to_cameras_service(request)
    except HTTPException as e:
        logger.error(f"🔐 [CAMERAS-ROUTE] Auth failed: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        logger.error(f"🔐 [CAMERAS-ROUTE] Unexpected error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@api_router.post("/cameras/detect")
async def detect_cameras_post(request: Request):
    """Proxy camera detection to Cameras service (POST method)."""
    # Validate authentication first
    extract_user_from_token(request)
    return await _proxy_to_cameras_service(request)


@api_router.get("/cameras/detect")
async def detect_cameras(request: Request):
    """Proxy camera detection to Cameras service."""
    # Validate authentication first
    extract_user_from_token(request)
    return await _proxy_to_cameras_service(request)


@api_router.get("/cameras/{camera_id}")
async def get_camera(request: Request):
    """Proxy get camera by ID to Cameras service."""
    # Validate authentication first
    extract_user_from_token(request)
    return await _proxy_to_cameras_service(request)


@api_router.put("/cameras/{camera_id}")
async def update_camera(request: Request):
    """Proxy update camera to Cameras service."""
    # Validate authentication first
    extract_user_from_token(request)
    return await _proxy_to_cameras_service(request)


@api_router.delete("/cameras/{camera_id}")
async def delete_camera(request: Request):
    """Proxy delete camera to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.post("/cameras/{camera_id}/snapshot")
async def capture_snapshot(request: Request):
    """Proxy capture camera snapshot to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.post("/cameras/{camera_id}/connect")
async def connect_camera(request: Request):
    """Proxy camera connection to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.post("/cameras/{camera_id}/disconnect")
async def disconnect_camera(request: Request):
    """Proxy camera disconnection to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.get("/cameras/active")
async def get_active_cameras(request: Request):
    """Proxy get active cameras to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.post("/cameras/disconnect-all")
async def disconnect_all_cameras(request: Request):
    """Proxy disconnect all cameras to Cameras service."""
    return await _proxy_to_cameras_service(request)


# RTSP Camera Routes
@api_router.post("/cameras/rtsp")
async def add_rtsp_camera(request: Request):
    """Proxy add RTSP camera to Cameras service."""
    # Validate authentication first
    extract_user_from_token(request)
    return await _proxy_to_cameras_service(request)


@api_router.put("/cameras/rtsp/{device_id}")
async def update_rtsp_camera(request: Request):
    """Proxy update RTSP camera to Cameras service."""
    # Validate authentication first
    extract_user_from_token(request)
    return await _proxy_to_cameras_service(request)


@api_router.delete("/cameras/rtsp/{device_id}")
async def delete_rtsp_camera(request: Request):
    """Proxy delete RTSP camera to Cameras service."""
    # Validate authentication first
    extract_user_from_token(request)
    return await _proxy_to_cameras_service(request)


@api_router.get("/cameras/rtsp/{device_id}")
async def get_rtsp_camera(request: Request):
    """Proxy get RTSP camera by device ID to Cameras service."""
    # Validate authentication first
    extract_user_from_token(request)
    return await _proxy_to_cameras_service(request)


# Streaming Service Routes
@api_router.post("/streaming/{device_id}/start")
async def start_streaming(request: Request):
    """Proxy start streaming to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.post("/streaming/{device_id}/stop")
async def stop_streaming(request: Request):
    """Proxy stop streaming to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.get("/streaming/{device_id}/status")
async def get_streaming_status(request: Request):
    """Proxy get streaming status to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.get("/streaming/{device_id}/snapshot")
async def get_streaming_snapshot(request: Request):
    """Proxy get streaming snapshot to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.post("/streaming/{device_id}/snapshot")
async def post_streaming_snapshot(request: Request):
    """Proxy enhanced streaming snapshot to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.get("/streaming/{device_id}/video")
async def get_streaming_video(request: Request):
    """Proxy get streaming video to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.get("/streaming/{device_id}/video-session/{session_id}")
async def get_streaming_video_session(request: Request):
    """Proxy authenticated video streaming session to Cameras service."""
    return await _proxy_to_cameras_service(request)


# Auth Streaming Session Routes (for camera service authentication)
@api_router.post("/auth/streaming-session/{device_id}")
async def create_streaming_session(request: Request):
    """Proxy create streaming session to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.get("/auth/streaming-sessions")
async def get_streaming_sessions(request: Request):
    """Proxy get streaming sessions to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.delete("/auth/streaming-session/{session_id}")
async def delete_streaming_session(request: Request):
    """Proxy delete streaming session to Cameras service."""
    return await _proxy_to_cameras_service(request)


# Recording Service Routes
@api_router.post("/streaming/{device_id}/record/start")
async def start_recording(request: Request):
    """Proxy start recording to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.post("/streaming/{device_id}/record/stop")
async def stop_recording(request: Request):
    """Proxy stop recording to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.get("/streaming/{device_id}/record/status")
async def get_recording_status(request: Request):
    """Proxy get recording status to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.get("/streaming/{device_id}/record/debug")
async def get_recording_debug(request: Request):
    """Proxy get recording debug state to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.post("/streaming/{device_id}/record/clear-state")
async def clear_recording_state(request: Request):
    """Proxy clear recording state to Cameras service."""
    return await _proxy_to_cameras_service(request)


# Instant Detection Service Routes
@api_router.get("/instant-detection/status")
async def get_instant_detection_status(request: Request):
    """Proxy get instant detection status to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.get("/instant-detection/results/{camera_id}")
async def get_instant_detection_results(request: Request):
    """Proxy get instant detection results to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.get("/instant-detection/results")
async def get_all_instant_detection_results(request: Request):
    """Proxy get all instant detection results to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.post("/instant-detection/{camera_id}/start")
async def start_instant_detection(request: Request):
    """Proxy start instant detection to Cameras service."""
    return await _proxy_to_cameras_service(request)


@api_router.post("/instant-detection/{camera_id}/stop")
async def stop_instant_detection(request: Request):
    """Proxy stop instant detection to Cameras service."""
    return await _proxy_to_cameras_service(request)


async def _proxy_to_orchestrator_service(request: Request) -> Response:
    """Helper function to proxy requests to the Orchestrator service."""
    try:
        # Get the original path and method
        path = str(request.url.path)
        method = request.method

        # Remove the /api/orchestrator prefix and forward to orchestrator service
        # Transform /api/orchestrator/workflows/... to /workflows/...
        if path.startswith("/api/v1/orchestrator/"):
            orchestrator_path = path.replace("/api/v1/orchestrator", "")
        elif path.startswith("/api/orchestrator/"):
            orchestrator_path = path.replace("/api/orchestrator", "")
        else:
            orchestrator_path = path

        # Construct the target URL
        target_url = f"{SERVICES['orchestrator']}{orchestrator_path}"

        # Get request body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()

        # Get headers (exclude host to avoid conflicts)
        headers = dict(request.headers)
        headers.pop("host", None)

        # Make the proxy request
        async with httpx.AsyncClient(
            timeout=60.0
        ) as client:  # Longer timeout for workflow operations
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

            # Return the response from the Orchestrator service
            return JSONResponse(
                content=response_content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503, detail=f"Orchestrator service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal orchestrator proxy error: {str(e)}"
        )


# Orchestrator Service Routes
@api_router.post("/orchestrator/orchestrate")
async def orchestrate_workflow(request: Request):
    """Proxy orchestrate workflow to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/validate")
async def validate_orchestrator(request: Request):
    """Proxy validate to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


# Face Detection Session Routes
@api_router.post("/orchestrator/face-detection")
async def create_face_detection_session(request: Request):
    """Proxy face detection session creation to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


# Workflow Management Routes
@api_router.post("/orchestrator/workflows/camera/events")
async def create_camera_workflow_event(request: Request):
    """Proxy camera workflow events to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.post("/orchestrator/workflows/face-detection/bulk-process")
async def start_face_detection_workflow(request: Request):
    """Proxy face detection bulk process to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/workflows/face-detection/status/{workflow_id}")
async def get_face_detection_status(request: Request):
    """Proxy face detection status to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/workflows/face-detection/lifecycles/{workflow_id}")
async def get_face_detection_lifecycles(request: Request):
    """Proxy face detection lifecycles to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/workflows/user/{user_id}/workflows")
async def get_user_workflows(request: Request):
    """Proxy user workflows to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/workflows/camera/{camera_device_id}/workflows")
async def get_camera_workflows(request: Request):
    """Proxy camera workflows to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/workflows/camera/{camera_device_id}/analytics")
async def get_camera_workflow_analytics(request: Request):
    """Proxy camera workflow analytics to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/workflows/analytics")
async def get_workflow_analytics(request: Request):
    """Proxy workflow analytics to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/workflows/health")
async def get_workflows_health(request: Request):
    """Proxy workflows health to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


# Session Management Routes
@api_router.get("/orchestrator/sessions/")
async def get_sessions(request: Request):
    """Proxy get sessions to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.post("/orchestrator/sessions/")
async def create_session(request: Request):
    """Proxy create session to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/sessions/overview")
async def get_sessions_overview(request: Request):
    """Proxy sessions overview to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/sessions/{session_id}")
async def get_session(request: Request):
    """Proxy get session to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.put("/orchestrator/sessions/{session_id}")
async def update_session(request: Request):
    """Proxy update session to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.delete("/orchestrator/sessions/{session_id}")
async def delete_session(request: Request):
    """Proxy delete session to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


# Recording Session Routes
@api_router.post("/orchestrator/recording-sessions/")
async def create_recording_session(request: Request):
    """Proxy create recording session to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/recording-sessions/")
async def list_recording_sessions(request: Request):
    """Proxy list recording sessions to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/recording-sessions/{session_uuid}")
async def get_recording_session(request: Request):
    """Proxy get recording session to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/recording-sessions/camera/{camera_device_id}")
async def get_camera_recording_sessions(request: Request):
    """Proxy get camera recording sessions to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


# Camera Events Routes
@api_router.post(
    "/orchestrator/camera-events/cameras/{camera_device_id}/webhook/register"
)
async def register_camera_webhook(request: Request):
    """Proxy register camera webhook to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.delete(
    "/orchestrator/camera-events/cameras/{camera_device_id}/webhook/unregister"
)
async def unregister_camera_webhook(request: Request):
    """Proxy unregister camera webhook to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.post("/orchestrator/camera-events/webhook")
async def camera_events_webhook(request: Request):
    """Proxy camera events webhook to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/camera-events/cameras/{camera_device_id}/stats")
async def get_camera_events_stats(request: Request):
    """Proxy camera events stats to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.post("/orchestrator/camera-events/users/{user_id}/cameras/register-all")
async def register_all_user_cameras(request: Request):
    """Proxy register all user cameras to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.post("/orchestrator/camera-events/cameras/{camera_device_id}/polling/start")
async def start_camera_polling(request: Request):
    """Proxy start camera polling to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.post("/orchestrator/camera-events/cameras/{camera_device_id}/polling/stop")
async def stop_camera_polling(request: Request):
    """Proxy stop camera polling to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/camera-events/health")
async def get_camera_events_health(request: Request):
    """Proxy camera events health to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


# Methods Routes
@api_router.post("/orchestrator/methods/cameras/{camera_device_id}/initialize")
async def initialize_camera_methods(request: Request):
    """Proxy initialize camera methods to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.post("/orchestrator/methods/cameras/{camera_device_id}/execute")
async def execute_camera_method(request: Request):
    """Proxy execute camera method to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/methods/cameras/{camera_device_id}/status")
async def get_camera_methods_status(request: Request):
    """Proxy camera methods status to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get(
    "/orchestrator/methods/cameras/{camera_device_id}/methods/{method_name}/status"
)
async def get_camera_method_status(request: Request):
    """Proxy camera method status to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/methods/cameras/{camera_device_id}/analytics")
async def get_camera_methods_analytics(request: Request):
    """Proxy camera methods analytics to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.put(
    "/orchestrator/methods/cameras/{camera_device_id}/methods/{method_name}/config"
)
async def update_camera_method_config(request: Request):
    """Proxy update camera method config to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.post(
    "/orchestrator/methods/cameras/{camera_device_id}/methods/{method_name}/reset"
)
async def reset_camera_method(request: Request):
    """Proxy reset camera method to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/methods/health")
async def get_methods_health(request: Request):
    """Proxy methods health to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get(
    "/orchestrator/methods/cameras/{camera_device_id}/methods/{method_name}/logs"
)
async def get_camera_method_logs(request: Request):
    """Proxy camera method logs to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


# Automation Routes
@api_router.get("/orchestrator/automation/health")
async def get_automation_health(request: Request):
    """Proxy automation health to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.post("/orchestrator/automation/rules")
async def create_automation_rule(request: Request):
    """Proxy create automation rule to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/automation/rules")
async def get_automation_rules(request: Request):
    """Proxy get automation rules to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/automation/rules/{rule_id}")
async def get_automation_rule(request: Request):
    """Proxy get automation rule to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.put("/orchestrator/automation/rules/{rule_id}")
async def update_automation_rule(request: Request):
    """Proxy update automation rule to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.delete("/orchestrator/automation/rules/{rule_id}")
async def delete_automation_rule(request: Request):
    """Proxy delete automation rule to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.post("/orchestrator/automation/rules/{rule_id}/execute")
async def execute_automation_rule(request: Request):
    """Proxy execute automation rule to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.post("/orchestrator/automation/rules/{rule_id}/pause")
async def pause_automation_rule(request: Request):
    """Proxy pause automation rule to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.post("/orchestrator/automation/rules/{rule_id}/resume")
async def resume_automation_rule(request: Request):
    """Proxy resume automation rule to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/automation/executions")
async def get_automation_executions(request: Request):
    """Proxy get automation executions to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/automation/status")
async def get_automation_status(request: Request):
    """Proxy get automation status to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/automation/analytics")
async def get_automation_analytics(request: Request):
    """Proxy get automation analytics to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


# PPL Thread (Person Objects) Routes
@api_router.post("/orchestrator/person-objects/trigger")
async def trigger_ppl_thread_workflow(request: Request):
    """Proxy PPL Thread workflow trigger to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


@api_router.get("/orchestrator/person-objects/{media_id}")
async def get_person_objects_for_media(request: Request):
    """Proxy get person objects data to Orchestrator service."""
    return await _proxy_to_orchestrator_service(request)


# vmeta Service Helper Function
async def _proxy_to_vmeta_service(request: Request) -> Response:
    """Helper function to proxy requests to the vmeta service."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Get the original path and method
        path = str(request.url.path)
        method = request.method

        # Construct the target URL
        target_url = f"{SERVICES['vmeta']}{path}"

        # Get request body if present
        body = None
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            body = await request.body()

        # Prepare headers (forward authorization and other important headers)
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in ["host", "content-length"]
        }
        
        # 🔍 DEBUG: Log authorization header status
        auth_header = headers.get("authorization", "MISSING")
        logger.info(f"🔐 [VMETA-PROXY] {method} {path} - Auth header: {'Present' if auth_header != 'MISSING' else 'MISSING'}")

        # Make the proxy request
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            )

            # Return the response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get(
                    "content-type", "application/json"
                ),
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503, detail=f"vmeta service unavailable: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal vmeta proxy error: {str(e)}"
        )


# vmeta Service Routes - Cross-Video Individual Tracking
@api_router.post("/cross-video/individuals/tracking/sessions")
async def create_cross_video_tracking_session(request: Request):
    """Proxy cross-video tracking session creation to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.get("/cross-video/individuals/tracking/sessions/{session_uuid}")
async def get_cross_video_tracking_session_status(request: Request):
    """Proxy cross-video tracking session status to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.get("/cross-video/individuals/tracking/sessions/{session_uuid}/results")
async def get_cross_video_tracking_session_results(request: Request):
    """Proxy cross-video tracking session results to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.delete("/cross-video/individuals/tracking/sessions/{session_uuid}")
async def cancel_cross_video_tracking_session(request: Request):
    """Proxy cross-video tracking session cancellation to vmeta service."""
    return await _proxy_to_vmeta_service(request)


# Individual Groups API Routes - Proxy to vmeta service
@api_router.get("/individual-groups")
async def list_individual_groups(request: Request):
    """Proxy list individual groups to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/individual-groups")
async def create_individual_group(request: Request):
    """Proxy create individual group to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.get("/individual-groups/{group_id}")
async def get_individual_group(request: Request):
    """Proxy get individual group to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.patch("/individual-groups/{group_id}")
async def update_individual_group(request: Request):
    """Proxy update individual group to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.delete("/individual-groups/{group_id}")
async def delete_individual_group(request: Request):
    """Proxy delete individual group to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.get("/individual-groups/{group_id}/members")
async def get_group_members(request: Request):
    """Proxy get group members to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/individual-groups/{group_id}/members")
async def add_group_members(request: Request):
    """Proxy add group members to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.delete("/individual-groups/{group_id}/members")
async def remove_group_members(request: Request):
    """Proxy remove group members to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.get("/individuals/{individual_id}/groups")
async def get_individual_groups(request: Request):
    """Proxy get individual's groups to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/individual-groups/bulk/add-members")
async def bulk_add_members(request: Request):
    """Proxy bulk add members to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/individual-groups/bulk/assign-groups")
async def bulk_assign_groups(request: Request):
    """Proxy bulk assign groups to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/individual-groups/{group_id}/check-duplicates")
async def check_group_duplicates(request: Request):
    """Proxy check for duplicate members to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/individual-groups/{group_id}/merge-members")
async def merge_group_members(request: Request):
    """Proxy merge group members to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/individual-groups/{group_id}/camera-search")
async def group_camera_search(request: Request):
    """Proxy individual groups camera search to vmeta service."""
    return await _proxy_to_vmeta_service(request)


# Individual Thumbnails API Routes - Proxy to vmeta service
@api_router.get("/individuals/{individual_id}/thumbnail")
async def get_individual_thumbnail(request: Request):
    """Proxy get individual thumbnail to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/individuals/{individual_id}/thumbnail/generate")
async def generate_individual_thumbnail(request: Request):
    """Proxy generate individual thumbnail to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/individuals/{individual_id}/thumbnail/upload")
async def upload_individual_thumbnail(request: Request):
    """Proxy upload individual thumbnail to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.get("/individuals/{individual_id}/thumbnail/url")
async def get_individual_thumbnail_url(request: Request):
    """Proxy get individual thumbnail URL to vmeta service."""
    return await _proxy_to_vmeta_service(request)


# Phase 5: Get individuals list from tracking session
@api_router.get("/cross-video/individuals/tracking/sessions/{session_uuid}/individuals")
async def get_session_individuals(request: Request):
    """Proxy request to get individuals list from tracking session to vmeta service."""
    return await _proxy_to_vmeta_service(request)


# Phase 6: Get aggregated analysis for individual
@api_router.get("/cross-video/individuals/tracking/individuals/{individual_uuid}/aggregated-analysis")
async def get_individual_aggregated_analysis(request: Request):
    """Proxy request to get aggregated individual analysis to vmeta service."""
    return await _proxy_to_vmeta_service(request)


# Manual merge endpoint for cross-video individuals
@api_router.post("/cross-video/individuals/tracking/merge")
async def merge_individuals_manual(request: Request):
    """Proxy request to manually merge selected individuals to vmeta service."""
    return await _proxy_to_vmeta_service(request)


# MVR-People Service Routes
@api_router.post("/mvr-people/batch-match-and-merge")
async def batch_match_and_merge(request: Request):
    """Proxy batch match and merge request to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/mvr-people/search/by-collection")
async def search_mvr_people_by_collection(request: Request):
    """Proxy MVR people search by collection request to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/mvr-people/search/by-videos")
async def search_mvr_people_by_videos(request: Request):
    """Proxy MVR people search by videos request to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/mvr-people/count-by-videos")
async def count_mvr_people_by_videos(request: Request):
    """Proxy MVR people count by videos request to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.get("/mvr-people/individuals/{individual_uuid}/analysis")
async def get_individual_analysis_no_session(request: Request):
    """Proxy individual analysis without session to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.get("/mvr-people/mvr-person/{mvr_person_uuid}/analysis")
async def get_mvr_person_analysis(request: Request):
    """Proxy MVR person analysis to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.get("/mvr-people/count-by-camera/{camera_id}")
async def get_camera_mvr_people_count(request: Request):
    """Proxy camera MVR people count request to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.get("/mvr-people/count-by-collection/{collection_name}")
async def get_collection_mvr_people_count(request: Request):
    """Proxy collection MVR people count request to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/mvr-people/merge")
async def merge_mvr_people(request: Request):
    """Proxy MVR people merge request to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.post("/mvr-people/merge/hierarchical")
async def hierarchical_merge_mvr_people(request: Request):
    """Proxy hierarchical MVR people merge request to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.get("/mvr-people/super-individual/{uuid}/hierarchy")
async def get_super_individual_hierarchy(request: Request):
    """Proxy super-individual hierarchy request to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.get("/mvr-people/{mvr_uuid}/best-image")
async def get_mvr_best_image(request: Request):
    """Proxy MVR best image request to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.patch("/mvr-people/{mvr_person_uuid}/name")
async def update_mvr_person_name(request: Request):
    """Proxy MVR person name update request to vmeta service."""
    return await _proxy_to_vmeta_service(request)


@api_router.patch("/mvr-people/{mvr_person_uuid}/gender")
async def update_mvr_person_gender(request: Request):
    """Proxy MVR person gender update request to vmeta service."""
    return await _proxy_to_vmeta_service(request)
    return await _proxy_to_vmeta_service(request)
