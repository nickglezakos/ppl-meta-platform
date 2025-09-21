#!/usr/bin/env python3
"""
Debug script to test JWT token generation
"""

import os
import time

import jwt
import requests

# Environment setup
NODE_SECRET = "RA6XfYJZqhz-_MAbGMhGCoQz1KGIKecLTb3RkLVOUr4"
USER_ID = "7"


def test_token_generation():
    """Test different token generation approaches"""

    print("🧪 JWT Token Generation Debug")
    print("=" * 50)
    print(f"NODE_SECRET: {NODE_SECRET[:10]}...")
    print(f"USER_ID: {USER_ID}")
    print()

    # Method 1: Simple payload (current approach)
    print("1️⃣ Simple payload (current orchestrator approach):")
    payload1 = {"sub": str(USER_ID), "exp": int(time.time()) + 3600}
    token1 = jwt.encode(payload1, NODE_SECRET, algorithm="HS256")
    print(f"Payload: {payload1}")
    print(f"Token: {token1[:50]}...")

    # Test this token
    print("Testing token with camera service...")
    try:
        response = requests.get(
            f"http://localhost:8005/api/v1/cameras/mobile_TKQ1.221114.001/settings",
            params={"user_id": USER_ID},
            headers={"Authorization": f"Bearer {token1}"},
            timeout=5,
        )
        print(f"✅ Status: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

    print()

    # Method 2: Try to match the working token from logs
    print("2️⃣ Trying to reverse-engineer working token from logs:")
    # From logs: Payload: {'sub': '7', 'exp': 1758380205}
    # That exp is: Fri Jan 10 2025 16:16:45 GMT+0000
    working_exp = 1758380205
    payload2 = {"sub": USER_ID, "exp": working_exp}  # Note: not str() conversion
    token2 = jwt.encode(payload2, NODE_SECRET, algorithm="HS256")
    print(f"Payload: {payload2}")
    print(f"Token: {token2[:50]}...")

    # Test this token
    print("Testing token with camera service...")
    try:
        response = requests.get(
            f"http://localhost:8005/api/v1/cameras/mobile_TKQ1.221114.001/settings",
            params={"user_id": USER_ID},
            headers={"Authorization": f"Bearer {token2}"},
            timeout=5,
        )
        print(f"✅ Status: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

    print()

    # Method 3: Check if we can decode a working token
    print("3️⃣ Let's get a working token from the node service and analyze it:")
    try:
        # First login to get a working token
        login_response = requests.post(
            "http://localhost:8001/auth/login",
            json={"email": "testuser@example.com", "password": "testpassword123"},
            timeout=5,
        )
        if login_response.status_code == 200:
            working_token = login_response.json()["access_token"]
            print(f"Working token: {working_token[:50]}...")

            # Decode it
            decoded = jwt.decode(working_token, NODE_SECRET, algorithms=["HS256"])
            print(f"Decoded payload: {decoded}")

            # Test this working token with camera service
            print("Testing working token with camera service...")
            response = requests.get(
                f"http://localhost:8005/api/v1/cameras/mobile_TKQ1.221114.001/settings",
                params={"user_id": USER_ID},
                headers={"Authorization": f"Bearer {working_token}"},
                timeout=5,
            )
            print(f"✅ Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Working token verified!")
            else:
                print(f"❌ Error: {response.text}")

        else:
            print(f"❌ Login failed: {login_response.status_code}")

    except Exception as e:
        print(f"❌ Failed to get working token: {e}")


if __name__ == "__main__":
    test_token_generation()
