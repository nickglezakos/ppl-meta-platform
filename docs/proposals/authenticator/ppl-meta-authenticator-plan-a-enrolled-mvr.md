# EyeNet Authenticator — Plan A + enrolled MVR Presence

**Status:** Implemented (v1 skeleton)  
**Date:** 2026-10-18  
**App:** `ppl-meta-authenticator/`  
**Backend:** `ppl-meta-presence` authenticator APIs + gateway proxy

---

## Product decisions

1. **Auth = Plan A** — LAN Discovery (`:8006`) or Authority VPN enrollment token + Tailscale, then **local** gateway login. No Authority user-directory lookup.
2. **Not a camera** — never calls `POST /api/v1/cameras/mobile`. Presence `device_uuid` is a soft app install UUID.
3. **MVR once via vmeta (email/PPP scoped)** — registration captures a face still. Presence resolves the signed-in user → PPP (by email/guid), then:
   - If the live face matches an MVR already **linked to that PPP** (console or prior enroll), bind that MVR as `authenticator_mvr_people_uuid` (no gallery search).
   - Else `identify-face` with `force_create=true` + `detect_face=true`, bind the new MVR, and link it to the active Presence group.
   App stores only the MVR UUID locally. Users who already have PPP↔MVR links may skip a redundant enroll (enrollment GET reports enrolled).
4. **Live verify at check-in** — each video grant path captures again and calls `verify-face` with `create_if_missing=false`, scoring **1:N** against the authenticator binding **plus** all MVR `individual_id`s linked to that PPP (active group first). Never gallery nearest-neighbor; never grant from a cached UUID alone.
5. **Phone-side Presence actions** — Owner QR, Scan station QR, Video match, QR + Video.

---

## API contract (gateway → Presence)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/presence/authenticator/enrollment` | Enrollment status for current user |
| POST | `/api/v1/presence/authenticator/enroll-face` | Multipart face image → durable MVR + PPP bind |
| POST | `/api/v1/presence/authenticator/verify-face?session_uuid=` | Live face vs enrolled MVR; advances session |
| POST | `/api/v1/presence/mobile/sessions` | Create session with `client_origin: "authenticator"` |

Authenticator sessions skip installation camera/trigger video readiness. Video modes are satisfied by successful `verify-face`.

---

## Validation

```bash
# Smoke (no ML):
PRESENCE_VALIDATION_SKIP_ML=1 \
PRESENCE_VALIDATION_USERNAME=... PRESENCE_VALIDATION_PASSWORD=... \
python ppl-meta-presence/validate_authenticator_flow.py

# Full enroll→verify→grant:
PRESENCE_VALIDATION_FACE_IMAGE=/path/to/face.jpg \
PRESENCE_VALIDATION_USERNAME=... PRESENCE_VALIDATION_PASSWORD=... \
python ppl-meta-presence/validate_authenticator_flow.py
```

Unit tests: `PYTHONPATH=src pytest ppl-meta-presence/tests/test_authenticator_enroll_verify.py`

---

## Out of scope (v1)

- Authority email → VPN directory (Plan B)
- On-device FaceNet
- iOS release
- Console Actions parity (Render station QR / Scan Owner QR against USB webcam)
- Replacing EyeNet Mobile Camera streaming
