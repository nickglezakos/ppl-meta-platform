import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.v1.endpoints.cameras import list_active_connections


class _FakeWorker:
    def __init__(self, device_id: str, status: str, frames_read: int, uptime_seconds: int) -> None:
        self.device_id = device_id
        self.status = SimpleNamespace(value=status)
        self._stats = {
            "frames_read": frames_read,
            "uptime_seconds": uptime_seconds,
        }

    def get_stats(self) -> dict:
        return self._stats


class _FakeWorkerManager:
    def __init__(self, workers: list[_FakeWorker]) -> None:
        self._workers = workers

    def get_connected_workers(self) -> list[_FakeWorker]:
        return self._workers


@pytest.mark.asyncio
async def test_list_active_connections_returns_connected_workers(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_workers = [
        _FakeWorker("camera-a", "connected", 42, 7),
        _FakeWorker("camera-b", "connected", 105, 12),
    ]

    monkeypatch.setattr(
        "src.services.worker_manager.get_worker_manager",
        lambda: _FakeWorkerManager(fake_workers),
    )

    response = await list_active_connections(current_user={"sub": "presence-service"})

    assert response == {
        "active_count": 2,
        "active_cameras": [
            {
                "device_id": "camera-a",
                "status": "connected",
                "frames_read": 42,
                "uptime": 7,
            },
            {
                "device_id": "camera-b",
                "status": "connected",
                "frames_read": 105,
                "uptime": 12,
            },
        ],
    }


@pytest.mark.asyncio
async def test_list_active_connections_handles_empty_worker_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.services.worker_manager.get_worker_manager",
        lambda: _FakeWorkerManager([]),
    )

    response = await list_active_connections(current_user={"sub": "presence-service"})

    assert response == {"active_count": 0, "active_cameras": []}