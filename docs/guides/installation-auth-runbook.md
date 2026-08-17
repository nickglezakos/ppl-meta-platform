# Runbook & Policy: `INSTALLATION_AUTH_SECRET` / `AUTH_ENFORCE` (Issue #8)

This is the operational runbook for rolling out **token authentication** on the
Signage Player ↔ `ppl-meta-discovery` connection.

## 1. What it is

Discovery accepts **two** credential types on the protected endpoints
(`/api/v1/services/*`, `/api/v1/devices/*`, `/api/v1/discovery/topology`):

**1) HMAC installation token (edge installations — signage player, mobile camera):**
```
api_token = HMAC_SHA256(INSTALLATION_AUTH_SECRET, installation_uuid)
```
- **Authority** (`enroll-installation`) mints it and returns it as `api_token`.
- Client sends `Authorization: Bearer <api_token>` + `X-Installation-Uuid: <uuid>`.
- **Discovery** recomputes it from `X-Installation-Uuid` and returns **401** on mismatch.
- **Local (Option 1):** for fully-local onboarding, Discovery also exposes
  `POST /api/v1/device-enroll` (guarded by `X-Enroll-Key: INSTALLATION_AUTH_SECRET`) which
  mints the token server-side — the signage player and mobile camera use this so they do not
  need the remote Authority to obtain a token.

**2) Internal service token (platform backend services — gateway, cameras, vision,
node, orchestrator, media):**
- Client sends `Authorization: Bearer <INTERNAL_SERVICE_TOKEN>` +
  `X-Service-Name: <name>` where the name is a `KNOWN_SERVICES` member
  (mirrors `shared/auth/service_auth.py`).
- **Discovery** validates it and accepts the request (so service-to-service
  registration/heartbeat keeps working when enforcement is on).

Enforcement is controlled by `AUTH_ENFORCE` (default **off**), so this is a **progressive
rollout** that does not break existing clients until it is switched on.

## 2. Configuration reference

| Setting | Service | Default | Notes |
|---|---|---|---|
| `INSTALLATION_AUTH_SECRET` | Authority + Discovery | `ppl-meta-installation-auth-secret-dev` | **Must be identical on both services.** The dev default is for local-only use. |
| `AUTH_ENFORCE` | Discovery | `false` | When true, protected endpoints reject missing/invalid tokens with 401. |

## 3. Rollout steps

1. **Choose a production secret** and set `INSTALLATION_AUTH_SECRET` identically on
   **both** the Authority and Discovery (env / secrets manager). Do **not** use the dev
   default in production.
2. **Confirm all clients can send tokens.** The Signage Player already does once it has
   enrolled through the Authority (token persisted in `ConfigService.installationApiToken`
   and sent via the Dio auth interceptor). Verify that any *other* clients that call the
   protected endpoints (mobile cameras, edge cameras, other services) also send valid
   tokens — otherwise they will fail once enforcement is on.
3. **Enable enforcement on Discovery:** set `AUTH_ENFORCE=true` and restart/reload the
   Discovery service.
4. **Verify** (see §5) that authenticated players pass and unauthenticated requests get
   401.
5. **Monitor** Discovery logs for a spike in 401s (indicates a non-updated client).

## 4. Local / staging quick check

```bash
# 1. Simulate the token the Authority would issue (same secret as Discovery dev default):
python3 - <<'PY'
import hmac, hashlib
secret = "ppl-meta-installation-auth-secret-dev"
uuid = "my-installation"
print(hmac.new(secret.encode(), uuid.encode(), hashlib.sha256).hexdigest())
PY
```

```bash
# 2. Unauthenticated request (expect 401 once AUTH_ENFORCE=true):
curl -i -X POST http://localhost:8006/api/v1/services/heartbeat \
  -H 'Content-Type: application/json' -d '{"service_id":"x","status":"healthy"}'

# 3. Authenticated request (expect 200):
TOKEN=<token from step 1>
curl -i -X POST http://localhost:8006/api/v1/services/heartbeat \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'X-Installation-Uuid: my-installation' \
  -d '{"service_id":"x","status":"healthy"}'
```

## 5. Policy notes & security guidance

- **Symmetric bearer tokens.** Whoever holds a token is authenticated. Protect HTTP
  transport (Tailscale mesh / TLS) so tokens are not sent in the clear.
- **HMAC token scope is per installation** (edge apps); the **service token is shared
  across all platform services** (backend). Neither is per-device.
- **Two credential paths coexist** — an edge installation uses the HMAC token, a backend
  service uses the service token; both are accepted by Discovery.
- **No built-in expiry in the token.** A leaked token stays valid until the shared secret
  is rotated. The enrollment pre-auth key still expires after 24 h.
- **Rotation:** changing `INSTALLATION_AUTH_SECRET` invalidates all issued tokens; clients
  must re-enroll (they get a fresh token via `/api/v1/vpn/enroll-installation` on the
  next setup). Do this during a maintenance window.
- **Failed auth returns 401**, which the player already handles defensively in
  `register()` (treats 401/403 as "credentials mismatch").
- **Never** ship the dev default secret (`ppl-meta-installation-auth-secret-dev`) to
  production.

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Player logs 401 from discovery | `INSTALLATION_AUTH_SECRET` differs between Authority & Discovery, or token not enrolled | Re-enroll via Authority; match secrets |
| All clients start failing 401 | `AUTH_ENFORCE=true` before non-player clients were updated | Update clients or temporarily set `AUTH_ENFORCE=false` |
| Token empty on player | Enrollment did not complete/persist | Re-run setup; check `installationApiToken` is saved |
| `api_token` missing in Authority response | Older Authority build | Deploy the updated `ppl-meta-authority` |
| Backend services (gateway/cameras/vision/node/…) get 401 | They don't yet send the **service token** | Have them send `Authorization: Bearer <INTERNAL_SERVICE_TOKEN>` + `X-Service-Name` (they currently send none) |
| Mobile camera gets 401 | It sends no HMAC token yet | Add token attachment via its Authority/VPN enrollment flow |