#!/usr/bin/env python3
"""
Debug script to test Camera service authentication.
"""

import os
import sys

# Add the camera service to Python path
sys.path.append("/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-cameras/src")

from security.auth import AuthenticationService, CameraPermission, CameraRole


def test_authentication():
    """Test the camera authentication logic."""

    auth_service = AuthenticationService()

    # Test tokens
    node_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU0NjQzMTM0fQ.58uLZ8Ux1aruouskQXxJrAIsD-xA-xvvgMu3EQkeE_Q"
    camera_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZW1vX2FkbWluaXN0cmF0b3IiLCJleHAiOjE3NTQ3MTcxNzMsImlhdCI6MTc1NDYzMDc3MywicGVybWlzc2lvbnMiOlsiY2FtZXJhczpzZXR0aW5nczp1cGRhdGUiLCJjYW1lcmFzOnZpZXciLCJjYW1lcmFzOnJlY29yZDp2aWV3IiwiY2FtZXJhczpyZWNvcmQ6ZGVsZXRlIiwiY2FtZXJhczpjb25maWd1cmUiLCJjYW1lcmFzOnJlY29yZDpzdGFydCIsImNhbWVyYXM6cmVjb3JkOnN0b3AiLCJjYW1lcmFzOnN0cmVhbTpzdGFydCIsImNhbWVyYXM6c3RyZWFtOnN0b3AiLCJjYW1lcmFzOnNlc3Npb25zOm1hbmFnZSIsImNhbWVyYXM6c3RyZWFtOnZpZXciLCJjYW1lcmFzOmFkbWluIiwiY2FtZXJhczpjb25uZWN0IiwiY2FtZXJhczpkZXRlY3QiLCJjYW1lcmFzOmRpc2Nvbm5lY3QiXSwic2VydmljZSI6InBwbC1tZXRhLWNhbWVyYXMifQ.SW0FwGE64E1HbofYrYbOXaLwLG3sNeevgDFK0JrRohY"

    print("=== Testing Node Service Token ===")
    try:
        payload = auth_service.verify_token(node_token)
        print(f"✅ Token verified successfully: {payload}")

        # Test permission check
        has_detect = auth_service.has_permission(
            node_token, CameraPermission.DETECT_CAMERAS
        )
        print(f"✅ Has cameras:detect permission: {has_detect}")

    except Exception as e:
        print(f"❌ Node token failed: {e}")

    print("\n=== Testing Camera Service Token ===")
    try:
        payload = auth_service.verify_token(camera_token)
        print(f"✅ Token verified successfully: {payload}")

        # Test permission check
        has_detect = auth_service.has_permission(
            camera_token, CameraPermission.DETECT_CAMERAS
        )
        print(f"✅ Has cameras:detect permission: {has_detect}")

    except Exception as e:
        print(f"❌ Camera token failed: {e}")

    print("\n=== Permission Constants ===")
    print(f"DETECT_CAMERAS permission: '{CameraPermission.DETECT_CAMERAS}'")
    print(f"ADMINISTRATOR role permissions: {CameraRole.ADMINISTRATOR}")


if __name__ == "__main__":
    test_authentication()
