"""
Test Recording-Aware Polling System
Simulates camera recording events and verifies polling behavior.
"""

import asyncio
import httpx
from datetime import datetime

# Service URLs
VMETA_URL = "http://localhost:8008"
NODE_URL = "http://localhost:8001"

# Auth credentials
USERNAME = "fresh.user@example.com"
PASSWORD = "NewPassword234!"


async def get_auth_token():
    """Get JWT authentication token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{NODE_URL}/api/v1/users/login",
            data={"username": USERNAME, "password": PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            raise Exception(f"Auth failed: {response.status_code}")


async def send_recording_started(token: str, collection_id: str, session_uuid: str):
    """Send recording started event to vmeta service."""
    print(f"\n📹 Sending recording_started event...")
    print(f"   Collection: {collection_id}")
    print(f"   Session: {session_uuid}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{VMETA_URL}/api/v1/recording/started",
            json={
                "collection_id": collection_id,
                "session_uuid": session_uuid,
                "device_id": "usb_camera_0",
                "user_id": "test_user",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        print(f"   Response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ {result['message']}")
            return result
        else:
            print(f"   ❌ Error: {response.text}")
            return None


async def send_recording_stopped(token: str, collection_id: str, session_uuid: str):
    """Send recording stopped event to vmeta service."""
    print(f"\n🛑 Sending recording_stopped event...")
    print(f"   Collection: {collection_id}")
    print(f"   Session: {session_uuid}")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{VMETA_URL}/api/v1/recording/stopped",
            json={
                "collection_id": collection_id,
                "session_uuid": session_uuid,
                "device_id": "usb_camera_0",
                "user_id": "test_user",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "video_count": 8,
                "metadata": {}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        print(f"   Response: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ {result['message']}")
            print(f"   Videos processed: {result.get('videos_processed', 0)}")
            print(f"   Total batches: {result.get('total_batches', 0)}")
            return result
        else:
            print(f"   ❌ Error: {response.text}")
            return None


async def get_polling_status(token: str):
    """Get current polling status."""
    print(f"\n📊 Getting polling status...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{VMETA_URL}/api/v1/recording/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            result = response.json()
            manager = result['polling_manager']
            print(f"   Enabled: {manager['enabled']}")
            print(f"   Running: {manager['running']}")
            print(f"   Active recordings: {manager['active_recordings']}")
            print(f"   Pending videos: {manager['pending_videos']}")
            print(f"   Statistics:")
            stats = manager['statistics']
            print(f"     - Polls performed: {stats['polls_performed']}")
            print(f"     - Videos discovered: {stats['videos_discovered']}")
            print(f"     - Batches triggered: {stats['batches_triggered']}")
            print(f"     - Recordings started: {stats['recordings_started']}")
            print(f"     - Recordings stopped: {stats['recordings_stopped']}")
            return result
        else:
            print(f"   ❌ Error: {response.status_code}")
            return None


async def test_recording_lifecycle():
    """Test complete recording lifecycle."""
    print("=" * 60)
    print("Testing Recording-Aware Polling System")
    print("=" * 60)
    
    try:
        # 1. Get auth token
        print("\n1️⃣ Authenticating...")
        token = await get_auth_token()
        print("   ✅ Authenticated")
        
        # 2. Check initial status
        print("\n2️⃣ Checking initial status...")
        await get_polling_status(token)
        
        # 3. Start recording
        print("\n3️⃣ Starting recording...")
        collection_id = "usb_camera_0"
        session_uuid = "test-session-12345"
        await send_recording_started(token, collection_id, session_uuid)
        
        # 4. Wait for polling to detect videos
        print("\n4️⃣ Waiting for polling to detect videos (30 seconds)...")
        print("   (During actual recording, videos will appear progressively)")
        await asyncio.sleep(30)
        
        # 5. Check status during recording
        print("\n5️⃣ Checking status during recording...")
        await get_polling_status(token)
        
        # 6. Wait for more polling cycles
        print("\n6️⃣ Waiting for more polling cycles (30 seconds)...")
        await asyncio.sleep(30)
        
        # 7. Stop recording
        print("\n7️⃣ Stopping recording...")
        await send_recording_stopped(token, collection_id, session_uuid)
        
        # 8. Check final status
        print("\n8️⃣ Checking final status...")
        await get_polling_status(token)
        
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_recording_lifecycle())
