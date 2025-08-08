#!/usr/bin/env python3
"""
CAM-TEST-001: Complete Cross-Service Authentication Integration Test
Tests the integration between Node service authentication and Camera service access.
"""

import json
import sys

import requests


def main():
    print("🎯 CAM-TEST-001: COMPLETE CROSS-SERVICE AUTHENTICATION TEST")
    print("=" * 60)
    print()

    # Step 1: Authenticate with Node service
    print("🔍 Step 1: Node Service Authentication")
    print("=" * 40)

    try:
        node_auth_data = {
            "username": "fresh.user@example.com",
            "password": "NewPassword234!",
        }

        response = requests.post(
            "http://localhost:8001/api/v1/users/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=node_auth_data,
            timeout=5,
        )

        print(f"Node Auth Status: {response.status_code}")

        if response.status_code == 200:
            auth_result = response.json()
            jwt_token = auth_result["access_token"]
            print("✅ SUCCESS: Node authentication successful")
            print(f"   Token: {jwt_token[:40]}...")
            print(f"   Full response: {json.dumps(auth_result, indent=2)}")
        else:
            print(f"❌ FAILED: Node authentication failed - {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ ERROR: Node authentication error - {e}")
        return False

    # Step 2: Test Camera Detection with Node JWT
    print()
    print("🎥 Step 2: Camera Detection with Cross-Service JWT")
    print("=" * 50)

    try:
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            "http://localhost:8005/api/v1/cameras/detect", headers=headers, timeout=10
        )

        print(f"Camera Detection Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            camera_result = response.json()
            print("✅ SUCCESS: Camera detection successful")
            print(f"   Response: {json.dumps(camera_result, indent=2)}")
        else:
            print(f"❌ FAILED: Camera detection failed - {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ ERROR: Camera detection error - {e}")
        return False

    # Step 3: Test Results Summary
    print()
    print("🎯 Step 3: Test Results Summary")
    print("=" * 35)
    print("✅ SUCCESS: Cross-service authentication working!")
    print("✅ SUCCESS: Camera detection endpoint accessible with Node JWT")
    print("✅ SUCCESS: CAM-TEST-001 PASSED")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
