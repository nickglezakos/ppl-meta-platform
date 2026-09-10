"""Unit tests for vehicle_plate worker STABLE fire + plate metadata."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.services.vehicle_plate_worker import (
    VehiclePlateWorker,
    get_vehicle_plate_metrics,
)


def _trigger(**overrides):
    base = dict(
        uuid=uuid4(),
        camera_device_ids='["cam1"]',
        camera_device_id="vehicle_plate",
        vehicle_class_allowlist='["car"]',
        vehicle_roi=None,
        vehicle_t_stable_seconds=10,
        vehicle_min_box_area_px=100,
        vehicle_plate_ocr_enabled=True,
        vehicle_plate_ocr_every_n_cycles=2,
        vehicle_iou_threshold=0.3,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_vehicle_stable_fires_with_plate():
    worker = VehiclePlateWorker()
    trigger = _trigger()
    await worker.activate_trigger(trigger)

    t0 = datetime.now(timezone.utc)
    bbox = [100.0, 100.0, 300.0, 250.0]

    # Warm-up + dwell
    for i in range(6):
        ts = t0 + timedelta(seconds=i * 3)
        met, reason, info = await worker.evaluate(
            trigger,
            {
                "camera_id": "cam1",
                "timestamp": ts.isoformat(),
                "vehicles": [
                    {
                        "class_label": "car",
                        "bbox": bbox,
                        "confidence": 0.9,
                        "plate_text": "ABC1234" if i > 1 else None,
                        "plate_confidence": 0.85 if i > 1 else None,
                    }
                ],
            },
        )
        if i < 4:
            assert not met
        else:
            assert met
            assert info["class_label"] == "car"
            assert info["plate_text"] == "ABC1234"
            assert "vehicle_plate MET" in reason
            break
    else:
        pytest.fail("expected STABLE fire")


@pytest.mark.asyncio
async def test_metrics_keys_present():
    before = get_vehicle_plate_metrics()
    assert "vehicle_tracks" in before
    assert "vehicle_fired" in before
    assert "plate_ocr_ok" in before
