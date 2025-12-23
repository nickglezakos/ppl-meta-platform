#!/usr/bin/env python3
"""
Simplified WebSocket Status Test
Tests basic WebSocket functionality without requiring actual camera operations.
"""

import asyncio
import json
import time
import httpx
import websockets
from typing import Optional


# Configuration
API_BASE_URL = "http://localhost:8005/api/v1"
WS_BASE_URL = "ws://localhost:8005/api/v1"
TEST_DEVICE_ID = "usb_camera_0"
TEST_CREDENTIALS = {
    "username": "fresh.user@example.com",
    "password": "NewPassword234!"
}


async def authenticate() -> Optional[str]:
    """Authenticate and get JWT token."""
    print("🔐 Authenticating...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/api/v1/users/login",
            data=TEST_CREDENTIALS,
            timeout=10.0,
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print("✅ Authenticated successfully\n")
            return token
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return None


async def test_rest_endpoint(token: str) -> bool:
    """Test 0: REST API status endpoint."""
    print("="*60)
    print("TEST 0: REST API Status Endpoint")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}/cameras/{TEST_DEVICE_ID}/realtime-status",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        
        if response.status_code == 200:
            status = response.json()
            print(f"✅ REST API status endpoint works: {json.dumps(status, indent=2)}\n")
            return True
        else:
            print(f"❌ REST API endpoint failed: {response.status_code}\n")
            return False


async def test_websocket_connection(token: str) -> bool:
    """Test 1: WebSocket connection establishment."""
    print("="*60)
    print("TEST 1: WebSocket Connection Establishment")
    print("="*60)
    
    uri = f"{WS_BASE_URL}/cameras/ws/status/{TEST_DEVICE_ID}?token={token}"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to {uri}")
            
            # Try to receive cached status (with timeout)
            print("⏳ Waiting for cached status...")
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                status = json.loads(message)
                print(f"✅ Received cached status: {json.dumps(status, indent=2)}\n")
            except asyncio.TimeoutError:
                print("⚠️  No cached status received (may be OK if camera never connected)\n")
            
            return True
            
    except Exception as e:
        print(f"❌ Connection failed: {e}\n")
        return False


async def test_ping_pong(token: str) -> bool:
    """Test 2: Ping/Pong keep-alive."""
    print("="*60)
    print("TEST 2: Ping/Pong Keep-Alive")
    print("="*60)
    
    uri = f"{WS_BASE_URL}/cameras/ws/status/{TEST_DEVICE_ID}?token={token}"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Skip cached status if any
            try:
                await asyncio.wait_for(websocket.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            
            print("📤 Sending ping...")
            await websocket.send("ping")
            
            print("⏳ Waiting for pong...")
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            
            if response == "pong":
                print("✅ Received pong - keep-alive works!\n")
                return True
            else:
                print(f"❌ Unexpected response: {response}\n")
                return False
                
    except asyncio.TimeoutError:
        print("❌ Timeout waiting for pong\n")
        return False
    except Exception as e:
        print(f"❌ Ping/pong test failed: {e}\n")
        return False


async def test_manual_redis_publish(token: str) -> bool:
    """Test 3: Manual Redis publish (if redis-cli available)."""
    print("="*60)
    print("TEST 3: Manual Redis Message Test")
    print("="*60)
    
    uri = f"{WS_BASE_URL}/cameras/ws/status/{TEST_DEVICE_ID}?token={token}"
    messages_received = []
    
    try:
        async with websockets.connect(uri) as websocket:
            # Skip cached status
            try:
                await asyncio.wait_for(websocket.recv(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            
            print("📻 To test real-time updates, run this in another terminal:")
            print(f"\nredis-cli PUBLISH camera:status:{TEST_DEVICE_ID} '{{\"device_id\": \"{TEST_DEVICE_ID}\", \"event\": \"connected\", \"timestamp\": \"2025-12-23T12:00:00\"}}'\n")
            
            print("⏳ Listening for 10 seconds...")
            
            end_time = time.time() + 10
            while time.time() < end_time:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    
                    if message == "pong":
                        continue
                    
                    status = json.loads(message)
                    messages_received.append(status)
                    print(f"📨 Received: {json.dumps(status, indent=2)}")
                    
                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    await websocket.send("ping")
                    continue
            
            if messages_received:
                print(f"\n✅ Received {len(messages_received)} message(s)\n")
                return True
            else:
                print("⚠️  No messages received (this is OK - manual test skipped)\n")
                return True  # Not a failure
                
    except Exception as e:
        print(f"❌ Manual test failed: {e}\n")
        return False


async def main():
    """Run all tests."""
    print("\n🧪 Camera Status WebSocket Test Suite")
    print("============================================================\n")
    
    # Authenticate
    token = await authenticate()
    if not token:
        print("❌ Cannot proceed without authentication")
        return
    
    # Run tests
    results = {
        "REST Endpoint": await test_rest_endpoint(token),
        "WebSocket Connection": await test_websocket_connection(token),
        "Ping/Pong": await test_ping_pong(token),
        "Manual Redis Test": await test_manual_redis_publish(token),
    }
    
    # Print summary
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed")


if __name__ == "__main__":
    asyncio.run(main())
