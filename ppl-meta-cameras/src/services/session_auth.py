"""
Session-based authentication service for camera streaming.
Provides browser-compatible authentication for MJPEG streams.
"""

import logging
import secrets
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class StreamingSessionManager:
    """Manages streaming sessions for browser-compatible authentication."""

    def __init__(self):
        self._sessions: Dict[str, Dict] = {}
        self._cleanup_interval = 300  # 5 minutes
        self._session_duration = 3600  # 1 hour

    def create_session(self, user_id: str, device_id: str, permissions: list) -> str:
        """Create a new streaming session."""
        session_id = secrets.token_urlsafe(32)
        expires_at = time.time() + self._session_duration

        session_data = {
            "user_id": user_id,
            "device_id": device_id,
            "permissions": permissions,
            "created_at": time.time(),
            "expires_at": expires_at,
            "last_accessed": time.time(),
        }

        self._sessions[session_id] = session_data

        logger.info(
            f"Created streaming session {session_id} for user {user_id} on device {device_id}"
        )
        return session_id

    def validate_session(self, session_id: str, device_id: str) -> Optional[Dict]:
        """Validate a streaming session."""
        if not session_id or session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        # Check if session is expired
        if time.time() > session["expires_at"]:
            logger.warning(f"Session {session_id} has expired")
            del self._sessions[session_id]
            return None

        # Check if session is for the correct device
        if session["device_id"] != device_id:
            logger.warning(
                f"Session {session_id} device mismatch: expected {device_id}, got {session['device_id']}"
            )
            return None

        # Update last accessed time
        session["last_accessed"] = time.time()

        return session

    def revoke_session(self, session_id: str) -> bool:
        """Revoke a streaming session."""
        if session_id in self._sessions:
            logger.info(f"Revoked streaming session {session_id}")
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        current_time = time.time()
        expired_sessions = [
            session_id
            for session_id, session in self._sessions.items()
            if current_time > session["expires_at"]
        ]

        for session_id in expired_sessions:
            logger.info(f"Cleaning up expired session {session_id}")
            del self._sessions[session_id]

    def get_active_sessions(self) -> Dict:
        """Get information about active sessions."""
        self.cleanup_expired_sessions()

        return {
            "total_sessions": len(self._sessions),
            "sessions": [
                {
                    "session_id": session_id[:16] + "...",  # Truncate for security
                    "user_id": session["user_id"],
                    "device_id": session["device_id"],
                    "created_at": session["created_at"],
                    "last_accessed": session["last_accessed"],
                }
                for session_id, session in self._sessions.items()
            ],
        }


# Global session manager instance
session_manager = StreamingSessionManager()
