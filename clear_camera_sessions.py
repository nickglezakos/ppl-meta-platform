#!/usr/bin/env python3
"""
Script to clear all active camera streaming sessions
"""
import json

import requests

# Configuration
BASE_URL = "http://localhost:8005"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3IiwiZXhwIjoxNzU3Mjc0MzUwfQ.m_hPHk0fx2i1hk5WcjIevgS5OkP68M5TWG3Qh-kMD9U"

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def get_active_sessions():
    """Get all active streaming sessions"""
    response = requests.get(
        f"{BASE_URL}/api/v1/auth/streaming-sessions", headers=headers
    )
    if response.status_code == 200:
        return response.json()["sessions"]["sessions"]
    return []


def revoke_session(session_id):
    """Revoke a specific streaming session"""
    response = requests.delete(
        f"{BASE_URL}/api/v1/auth/streaming-session/{session_id}", headers=headers
    )
    return response.status_code == 200


def main():
    print("🧹 Clearing all active streaming sessions...")

    # Get all active sessions
    sessions = get_active_sessions()
    print(f"Found {len(sessions)} active sessions")

    # Revoke each session
    revoked = 0
    for session in sessions:
        session_id = session["session_id"]
        device_id = session["device_id"]

        if revoke_session(session_id):
            print(f"✅ Revoked session {session_id[:8]}... for device {device_id}")
            revoked += 1
        else:
            print(
                f"❌ Failed to revoke session {session_id[:8]}... for device {device_id}"
            )

    print(f"\n🎯 Successfully revoked {revoked}/{len(sessions)} sessions")

    # Check final state
    remaining = get_active_sessions()
    print(f"📊 Remaining active sessions: {len(remaining)}")


if __name__ == "__main__":
    main()
