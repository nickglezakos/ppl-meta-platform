# Cybersecurity Remediation — Remaining Actions

**Status**: Tracking Document  
**Date**: June 29, 2026  
**Source**: `docs/proposals/headscale-vpn-architecture.md` §10 — Cybersecurity Hardening Plan

---

## Completed (This Session)

| ID | Severity | Issue | Status |
|---|---|---|---|
| C1 | 🔴 | Hardcoded test passwords in node | ✅ Fixed — env-only dev bootstrap |
| C2 | 🔴 | `INTERNAL_SERVICE_TOKEN` hardcoded in 3 orchestrator files | ✅ Fixed — env-only with startup validation |
| C3/C4 | 🔴 | Default `SECRET_KEY` values in node + communications | ✅ Fixed — known-default detection + warnings |
| C5 | 🔴 | Edge camera token validation bypass | ✅ Fixed — JWT signature validation with dev fallback |
| H1 | 🟠 | Plain-text password in admin reset email | ✅ Fixed — time-limited reset link instead |
| H2 | 🟠 | SMTP password stored as plaintext in communications DB | ✅ Fixed — AES-256-GCM decryption at use time |

---

## Remaining — Prioritized for Follow-Up Sessions

### 🔴 CRITICAL

| ID | Issue | Service | File(s) | Effort | Notes |
|---|---|---|---|---|---|
| **C8** | Symmetric HS256 JWT — single compromised key forges all tokens | All Python services | `config.py` in each service | Large | Generate RSA keypair per deployment. Private key on node, public key distributed to all services for verification via JWKS endpoint. Requires coordinated deployment. |

### 🟠 HIGH

| ID | Issue | Service | File(s) | Effort | Notes |
|---|---|---|---|---|---|
| **H3** | Webhook `auth_token` stored as plaintext | `ppl-meta-communications` | `webhook_service.py`, `webhook_config` model | Medium | Encrypt on write via `shared/security/encryption.py`, decrypt on read. Backward-compatible with existing plaintext values. |
| **H4** | JWT in unencrypted `SharedPreferences` (Flutter) | `ppl_meta_mobile_camera`, `ppl-meta-signage-simple-player` | `token_manager.dart`, `enhanced_authentication_service.dart`, `mobile_camera_heartbeat_service.dart` | Medium | Migrate to `flutter_secure_storage` (Keychain/iOS, EncryptedSharedPreferences/Android). Requires Flutter build. |
| **H6** | No token refresh flow — tokens stored indefinitely | `ppl_meta_mobile_camera`, `ppl-meta-node` | `enhanced_authentication_service.dart`, `users.py` (node) | Medium | Add `POST /api/v1/auth/refresh` on node. Mobile stores refresh token (longer TTL) in secure storage, access token (short TTL) in memory. |
| **H7** | 5 parallel auth implementations in Flutter | `ppl_meta_mobile_camera` | `enhanced_authentication_service.dart` + 4 others | Medium | Consolidate to single `EnhancedAuthenticationService`. Deprecate `AutoAuthenticationService`, `DiscoveryBasedAuthenticationService`, `EnhancedAutoAuthenticationService`, `HybridServiceDiscovery`. |

### 🟡 MEDIUM

| ID | Issue | Service | File(s) | Effort | Notes |
|---|---|---|---|---|---|
| **M1** | Edge camera dev mode in production path | `ppl-meta-edge-camera` | `management_api.py` (already partially fixed in C5) | Small | Verify C5 changes fully address this. |
| **M2** | Orchestrator `get_auth_token()` returns unvalidated user tokens | `ppl-meta-orchestrator` | `face_detection_endpoints.py`, `workflow_settings_endpoints.py` | Small | Add JWT validation step for user tokens (currently only checks presence). |
| **M3** | No rate limiting on email/webhook endpoints | `ppl-meta-communications` | `routes/email.py`, `routes/notification.py` | Medium | 10 emails/min, 100 webhooks/min via in-memory sliding window. Requires `redis` for production. |
| **M4** | `is_trusted_device()` needs ACL tag validation | `ppl-meta-discovery` | `edge_registry.py` (already has `TAILSCALE_CGNAT` constant) | Small | Add ACL tag check alongside CGNAT range check as designed. |
| **M5** | Headscale admin API insecure config | `autonomous/ppl-meta-authority` | `headscale` config | Small | Production MUST set `grpc_allow_insecure: false` and require API key. |
| **M6** | No TLS pinning on Flutter/Python clients | `ppl_meta_mobile_camera`, Python services | Various | Medium | Pin Let's Encrypt intermediate CA for `vpn.eyenet-vision.com`. Requires coordinating cert rotation with app updates. |
| **M7** | Pre-auth key exposure risk | `autonomous/ppl-meta-authority` | `api/vpn.py` (already has 1h TTL) | Small | Audit all key issuance to audit trail. Verify scoping to specific user + tags. |

---

## Recommended Sprint Plan

### Sprint 1: Quick Wins (1-2 hours)
- **M2**: JWT validation in orchestrator auth token (~10 lines)
- **M4**: ACL tag validation in trusted-device check (~5 lines)
- **M5**: Headscale production config hardening (~5 lines)
- **M7**: Pre-auth key audit logging (~5 lines)

### Sprint 2: Encryption + Rate Limiting (2-3 hours)
- **H3**: Webhook token encryption/decryption (~30 lines)
- **M3**: Rate limiting middleware for communications endpoints (~50 lines)

### Sprint 3: Flutter Security (3-4 hours)
- **H4**: `flutter_secure_storage` migration
- **H6**: Token refresh flow
- **H7**: Auth implementation consolidation

### Sprint 4: JWT Algorithm Migration (4-6 hours)
- **C8**: HS256 → RS256 migration across all services
- **M6**: TLS pinning for Python + Flutter clients

---

*Document prepared for security remediation planning*  
*Confidential - Internal Use Only*