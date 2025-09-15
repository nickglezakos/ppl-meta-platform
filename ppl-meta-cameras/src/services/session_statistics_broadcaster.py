"""
PPL Meta Cameras Service - Real-time Session Statistics Broadcasting
Provides WebSocket broadcasting of live session statistics and monitoring data

This module provides real-time statistics broadcasting:
- Live session statistics via WebSocket
- Performance monitoring and health metrics
- Real-time face detection counts and rates
- Session status and health monitoring
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Set

from fastapi import WebSocket, WebSocketDisconnect
from src.services.session_aware_face_detector import session_aware_face_detector
from src.services.streaming_session_manager import streaming_session_manager

logger = logging.getLogger(__name__)


class SessionStatisticsBroadcaster:
    """Manages real-time broadcasting of session statistics via WebSocket."""

    def __init__(self):
        """Initialize the statistics broadcaster."""
        self.active_websockets: Set[WebSocket] = set()
        self.broadcast_task: asyncio.Task = None
        self.broadcast_interval = 5.0  # seconds
        self.is_broadcasting = False

        logger.info("SessionStatisticsBroadcaster initialized")

    async def add_websocket(self, websocket: WebSocket) -> None:
        """Add a WebSocket connection for statistics broadcasting."""
        self.active_websockets.add(websocket)
        logger.info(
            f"Added WebSocket for statistics broadcasting. Active connections: {len(self.active_websockets)}"
        )

        # Start broadcasting if this is the first connection
        if len(self.active_websockets) == 1 and not self.is_broadcasting:
            await self.start_broadcasting()

    async def remove_websocket(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from broadcasting."""
        self.active_websockets.discard(websocket)
        logger.info(
            f"Removed WebSocket from statistics broadcasting. Active connections: {len(self.active_websockets)}"
        )

        # Stop broadcasting if no more connections
        if len(self.active_websockets) == 0 and self.is_broadcasting:
            await self.stop_broadcasting()

    async def start_broadcasting(self) -> None:
        """Start the periodic statistics broadcasting."""
        if self.is_broadcasting:
            return

        self.is_broadcasting = True
        self.broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info(
            f"Started statistics broadcasting with {self.broadcast_interval}s interval"
        )

    async def stop_broadcasting(self) -> None:
        """Stop the periodic statistics broadcasting."""
        if not self.is_broadcasting:
            return

        self.is_broadcasting = False
        if self.broadcast_task:
            self.broadcast_task.cancel()
            try:
                await self.broadcast_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped statistics broadcasting")

    async def _broadcast_loop(self) -> None:
        """Main broadcasting loop that sends statistics periodically."""
        try:
            while self.is_broadcasting and self.active_websockets:
                try:
                    # Collect statistics
                    statistics = await self._collect_statistics()

                    # Broadcast to all active WebSocket connections
                    await self._broadcast_statistics(statistics)

                    # Wait for next broadcast interval
                    await asyncio.sleep(self.broadcast_interval)

                except Exception as e:
                    logger.error(f"Error in statistics broadcasting loop: {e}")
                    await asyncio.sleep(1)  # Short delay before retry

        except asyncio.CancelledError:
            logger.info("Statistics broadcasting loop cancelled")
        except Exception as e:
            logger.error(f"Fatal error in statistics broadcasting loop: {e}")
        finally:
            self.is_broadcasting = False

    async def _collect_statistics(self) -> Dict:
        """Collect current session and performance statistics."""
        try:
            # Get streaming session statistics
            streaming_sessions = streaming_session_manager.get_all_active_sessions()

            # Get face detection session statistics
            detection_performance = (
                session_aware_face_detector.get_performance_summary()
            )
            detection_sessions = (
                session_aware_face_detector.get_all_session_statistics()
            )

            # Calculate aggregate statistics
            total_active_sessions = len(streaming_sessions)
            total_faces_detected = sum(
                session.get("face_count", 0) for session in streaming_sessions.values()
            )
            total_frames_processed = sum(
                session.get("frames_processed", 0)
                for session in streaming_sessions.values()
            )

            # Calculate average processing rate across all sessions
            avg_processing_rate = 0.0
            if streaming_sessions:
                rates = []
                for session in streaming_sessions.values():
                    if session.get("started_at"):
                        duration = (
                            datetime.now(timezone.utc) - session["started_at"]
                        ).total_seconds()
                        if duration > 0:
                            rate = session.get("frames_processed", 0) / duration
                            rates.append(rate)

                avg_processing_rate = sum(rates) / len(rates) if rates else 0.0

            # Prepare comprehensive statistics
            statistics = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "session_statistics",
                "summary": {
                    "active_streaming_sessions": total_active_sessions,
                    "total_faces_detected": total_faces_detected,
                    "total_frames_processed": total_frames_processed,
                    "average_processing_rate_fps": round(avg_processing_rate, 2),
                    "detection_performance": detection_performance,
                },
                "streaming_sessions": {
                    device_id: {
                        "session_uuid": session.get("session_uuid"),
                        "face_count": session.get("face_count", 0),
                        "frames_processed": session.get("frames_processed", 0),
                        "started_at": (
                            session.get("started_at").isoformat()
                            if session.get("started_at")
                            else None
                        ),
                        "last_detection_time": (
                            session.get("last_detection_time").isoformat()
                            if session.get("last_detection_time")
                            else None
                        ),
                        "session_metadata": session.get("session_metadata", {}),
                    }
                    for device_id, session in streaming_sessions.items()
                },
                "detection_sessions": detection_sessions,
                "system_health": {
                    "active_websocket_connections": len(self.active_websockets),
                    "broadcasting_enabled": self.is_broadcasting,
                    "broadcast_interval_seconds": self.broadcast_interval,
                },
            }

            return statistics

        except Exception as e:
            logger.error(f"Error collecting statistics: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": "statistics_error",
                "error": str(e),
                "system_health": {
                    "active_websocket_connections": len(self.active_websockets),
                    "broadcasting_enabled": self.is_broadcasting,
                },
            }

    async def _broadcast_statistics(self, statistics: Dict) -> None:
        """Broadcast statistics to all active WebSocket connections."""
        if not self.active_websockets:
            return

        message = json.dumps(statistics)
        disconnected_websockets = set()

        # Send to all active WebSocket connections
        for websocket in self.active_websockets.copy():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send statistics to WebSocket: {e}")
                disconnected_websockets.add(websocket)

        # Clean up disconnected WebSockets
        for websocket in disconnected_websockets:
            await self.remove_websocket(websocket)

    async def broadcast_immediate(self, statistics: Dict) -> None:
        """Broadcast statistics immediately (outside of periodic loop)."""
        if not self.active_websockets:
            return

        message = json.dumps(statistics)
        disconnected_websockets = set()

        for websocket in self.active_websockets.copy():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send immediate statistics to WebSocket: {e}")
                disconnected_websockets.add(websocket)

        # Clean up disconnected WebSockets
        for websocket in disconnected_websockets:
            await self.remove_websocket(websocket)

    async def handle_statistics_websocket(self, websocket: WebSocket) -> None:
        """Handle a statistics WebSocket connection."""
        await websocket.accept()
        await self.add_websocket(websocket)

        try:
            # Send initial statistics immediately
            initial_stats = await self._collect_statistics()
            await websocket.send_text(json.dumps(initial_stats))

            # Keep connection alive and handle any incoming messages
            while True:
                try:
                    # Wait for messages (ping/pong or commands)
                    data = await websocket.receive_text()
                    message = json.loads(data)

                    if message.get("type") == "ping":
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "pong",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                            )
                        )
                    elif message.get("type") == "get_statistics":
                        # Send current statistics on demand
                        stats = await self._collect_statistics()
                        await websocket.send_text(json.dumps(stats))
                    elif message.get("type") == "set_interval":
                        # Allow changing broadcast interval
                        new_interval = message.get("interval", self.broadcast_interval)
                        if (
                            1.0 <= new_interval <= 60.0
                        ):  # Limit interval to reasonable range
                            self.broadcast_interval = new_interval
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "interval_updated",
                                        "new_interval": self.broadcast_interval,
                                        "timestamp": datetime.now(
                                            timezone.utc
                                        ).isoformat(),
                                    }
                                )
                            )

                except json.JSONDecodeError:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "message": "Invalid JSON format",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                    )

        except WebSocketDisconnect:
            logger.info("Statistics WebSocket disconnected")
        except Exception as e:
            logger.error(f"Error in statistics WebSocket handler: {e}")
        finally:
            await self.remove_websocket(websocket)


# Global statistics broadcaster instance
statistics_broadcaster = SessionStatisticsBroadcaster()
