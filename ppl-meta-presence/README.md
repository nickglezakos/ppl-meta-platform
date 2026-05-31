# PPL Meta Presence Local Notes

This service runs on `http://localhost:8011` in local development and uses PostgreSQL by default.

## Local Start

VS Code tasks:

- `🫶 Start Presence Service (Local Python 3.11)`
- `♻️ Reset Presence Reservations (Local)`
- `🧪 Validate Presence Flow (Local)`

Direct run:

```zsh
cd ppl-meta-presence/src
PRESENCE_DETECTION_BACKEND_MODE=auto \
DATABASE_URL=postgresql://nickgklezakos@localhost:5432/ppl_meta_presence \
PYTHONPATH=/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-presence/src \
python3.11 -m uvicorn main:app --host 0.0.0.0 --port 8011 --reload
```

## Local Environment Variables

- `DATABASE_URL`: presence PostgreSQL connection string
- `PRESENCE_DETECTION_BACKEND_MODE`: `auto`, `gateway`, or `simulate`
- `PRESENCE_PREFERRED_CAMERA_TYPES`: comma-separated type priority such as `USB,EDGE,RTSP,MOBILE`
- `PRESENCE_PREFERRED_CAMERA_NAMES`: comma-separated preferred camera names or exact `device_id` fragments
- `PRESENCE_ALLOWED_CAMERA_STATUSES`: comma-separated candidate statuses such as `available,disconnected,connected`
- `PRESENCE_RESET_TOKEN`: bearer token used by `reset_presence_reservations.sh`
- `PRESENCE_RESET_BASE_URL`: optional base URL for the reset helper, default `http://localhost`
- `PRESENCE_RESET_INSTALLATION_UUID`: optional installation override for the reset helper, default `local-installation`
- `PRESENCE_VALIDATION_USERNAME`: username for `validate_presence_flow.py`
- `PRESENCE_VALIDATION_PASSWORD`: password for `validate_presence_flow.py`
- `PRESENCE_VALIDATION_GATEWAY_URL`: optional gateway base for asset inspection, default `http://localhost:8080/api/v1`
- `PRESENCE_VALIDATION_FORCE_EMPTY_GROUP`: when `1`, empties the expected presence individual group before validation so the run exercises first-member seeding
- `PRESENCE_VALIDATION_EXPECT_CONFIRMATION`: when `1`, requires the validator to observe a follow-up confirmation attempt before completion

## Reservation Helpers

Inspect installation reservation state:

```zsh
curl -H "Authorization: Bearer <token>" http://localhost/api/presence/installations/current
```

Reset installation reservations:

```zsh
cd ppl-meta-presence
PRESENCE_RESET_TOKEN=<token> ./reset_presence_reservations.sh
```

## Current Selection Behavior

- When no reservation exists, presence auto-selects a real registered platform camera.
- Name preferences are applied before camera type preferences.
- Candidate cameras are filtered by allowed status when possible.
- If status filtering removes every camera, the service falls back to the full camera list rather than leaving the installation unbound.
