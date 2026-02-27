"""
Test script to verify the complete recording-aware polling flow.
This simulates what should happen during a 4:10 recording.
"""

import asyncio
import httpx
from datetime import datetime

async def test_recording_flow():
    """Test the complete recording lifecycle."""
    
    vmeta_base = "http://localhost:8008"
    collection_id = "test_camera_001"
    session_uuid = "test-session-" + datetime.utcnow().isoformat()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        
        print("\n🔍 Step 1: Check VMeta status before recording")
        response = await client.get(f"{vmeta_base}/api/v1/recording/status")
        print(f"Status: {response.json()}")
        
        print("\n📹 Step 2: Start recording (should activate polling)")
        response = await client.post(
            f"{vmeta_base}/api/v1/recording/started",
            json={
                "collection_id": collection_id,
                "session_uuid": session_uuid,
                "device_id": collection_id,
                "user_id": "test_user",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "metadata": {}
            }
        )
        print(f"Response: {response.json()}")
        
        print("\n🔍 Step 3: Check status during recording")
        response = await client.get(f"{vmeta_base}/api/v1/recording/status")
        status = response.json()
        print(f"Status: {status}")
        print(f"Active recordings: {status['active_recordings']}")
        
        if status['active_recordings'] == 0:
            print("❌ PROBLEM: Recording started but no active recordings!")
        else:
            print("✅ Recording is active")
        
        print("\n⏸️  Step 4: Simulate 4:10 recording (waiting a bit...)")
        await asyncio.sleep(2)
        
        print("\n🛑 Step 5: Stop recording (should trigger final batch)")
        response = await client.post(
            f"{vmeta_base}/api/v1/recording/stopped",
            json={
                "collection_id": collection_id,
                "session_uuid": session_uuid,
                "device_id": collection_id,
                "user_id": "test_user",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "video_count": 8,  # 4:10 = ~8 videos
                "metadata": {}
            }
        )
        result = response.json()
        print(f"Response: {result}")
        
        print("\n🔍 Step 6: Check final status")
        response = await client.get(f"{vmeta_base}/api/v1/recording/status")
        status = response.json()
        print(f"Status: {status}")
        print(f"Active recordings: {status['active_recordings']}")
        print(f"Recordings started: {status['statistics']['recordings_started']}")
        print(f"Recordings stopped: {status['statistics']['recordings_stopped']}")
        
        if status['active_recordings'] == 0:
            print("✅ Recording properly stopped")
        else:
            print("❌ PROBLEM: Recording still active after stop!")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Recording-Aware Polling Flow")
    print("=" * 60)
    print("\nMake sure VMeta service is running on port 8008")
    print("Press Enter to start test...")
    input()
    
    try:
        asyncio.run(test_recording_flow())
        print("\n" + "=" * 60)
        print("✅ Test completed successfully")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
