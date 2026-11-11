# Fix plan: vmeta stall → analytics / video-preview failures + post-recovery UI lag

| Field | Value |
|--------|--------|
| **Date** | 2026-10-21 |
| **VERSION** | 2.25.103 |
| **Lab** | `eyenet-demo` (`lab-work-dual-64g`) @ Tailscale `100.101.128.40` |
| **Status** | Open — mitigated by manual vmeta restart; durable fixes not shipped |
| **Severity** | 🔴 High for demo (preview details / analytics 503); 🟡 Medium residual UX lag over Tailscale |
| **Known-issue id** | KI-004 (see [`known issues.md`](./known%20issues.md)) |

---

## Summary

On 2026-10-21, EyeNet demo analytics and video-preview detail fetches failed with gateway **503** after ~60 s. Investigation showed **vmeta wedged** (alive, listening, not OOM-killed) under memory pressure with concurrent materialization retries. A forced `docker restart` of `ppl-meta-vmeta` restored health.

After restart, analytics **API latency is fine (~50–130 ms)**; perceived lag is mostly a **frontend sequential waterfall** amplified by Tailscale RTT.

This document separates the two problems and gives a phased fix plan.

---

## Observed symptoms

1. **Hard failure (pre-restart)**
   - UI: analytics not loading; video preview details empty / spinning
   - Gateway: `503` after ~`60.0s` on:
     - `POST /api/v1/mvr-people/count-by-videos`
     - `GET /api/v1/media/{id}/faces/enhanced-v2`
     - `GET /api/v1/orchestrator/person-objects/{id}`
   - Orchestrator: `VMeta materialization call failed … Read timed out. (read timeout=60)`
   - vmeta: requests authenticated and fetched media metadata, then **stalled**; `/health` hung (10 s timeout)

2. **Residual lag (post-restart)**
   - Same analytics endpoints return **200 in &lt;150 ms**
   - Browser (Mac Chrome over Tailscale `100.102.56.67`) spaces calls ~**2–6 s** apart (OPTIONS→GET and endpoint→endpoint)
   - Wall clock ~1–2 min for a full analytics page load despite fast APIs

---

## Root causes

### A. vmeta worker stall (primary outage)

| Factor | Evidence |
|--------|----------|
| Not a hard OOM kill | `OOMKilled=false`; mem ~**3.9 GiB / 5 GiB** (~78%) |
| Event loop / worker unresponsive | `/health` timeout; materialization never completes |
| Retry pile-on | Clients retry every ~60 s; more concurrent hangs |
| Concurrent ML load | Face processing (~10 s/face), age/gender, identify, persist-batch while UI hammers materialize |
| Chronic watchfiles noise | ~**338 “change detected” / 2 min** since 2026-10-19 — uvicorn reload watching `/app/logs` (log write → change → more log) |

**Immediate mitigation that worked:** `docker restart pplmeta-ppl-meta-vmeta-1` → health 200 in ~10 s; mem ~606 MiB.

### B. Analytics UX lag after recovery (secondary)

| Factor | Evidence |
|--------|----------|
| Sequential gateway fan-out (when many cameras) | `_get_instant_detection_approx_dataset` awaits approx **per camera in a `for` loop** (`ppl-meta-gateway/src/api/v1/analytics.py`) |
| Sequential UI loads | summary → quality → time-series → demographics → behavioral, not parallel |
| Tailscale RTT | Client on mesh; multi-second OPTIONS→GET gaps |
| Empty datasets still pay full waterfall | Selected cameras returned `raw=0` for the week |

---

## Goals

1. **Reliability:** vmeta must not silently wedge; analytics / preview must fail fast or recover without manual restart.
2. **Observability:** detect wedged vmeta before a demo (health + mem + request latency).
3. **Performance:** analytics page usable over Tailscale without multi-minute waterfalls.
4. **Ops:** documented lab recovery until durable fixes ship.

---

## Fix plan (phased)

### Phase 0 — Ops runbook (same day / any demo)

**Owner:** lab ops  
**Effort:** low  
**Ship:** doc + optional script (no product release required)

1. **Detect**
   - `docker exec … curl -m 5 http://127.0.0.1:8008/health` → must be 200 quickly
   - `docker stats` → vmeta mem approaching limit (e.g. &gt;80% of 5 GiB)
   - Gateway logs: repeated `503` / `process_time≈60s` on analytics or `faces/enhanced-v2`
2. **Recover**
   - Prefer: `docker restart pplmeta-ppl-meta-vmeta-1` (compose project restart may no-op if wrong project dir/name — confirm container recycle via `StartedAt`)
   - Verify: health 200; mem drop; one analytics + one preview detail call succeeds
3. **Document** in day-to-day lab guide (link from this issue)

**Done when:** anyone on the team can recover a wedged demo in &lt;2 minutes without this chat.

---

### Phase 1 — Stop the watchfiles / reload feedback loop

**Owner:** platform / vmeta  
**Effort:** small  
**Affects:** `ppl-meta-vmeta` image / entrypoint / logging config

1. Confirm production start path enables reload / watchfiles (logs show `watchfiles.main` + `notify-rs` thread).
2. **Disable file reload in production** images (no `--reload`; no watch on `/app` or `/app/logs`).
3. If file logging must remain: exclude log dirs from any watcher; prefer stdout-only in containers.
4. Verify: after deploy, zero sustained `change detected` spam; `/app/logs` no longer drives reload.

**Done when:** lab vmeta logs are free of continuous watchfiles lines under normal load.

**Why first:** cheap, reduces background load that contributed to the wedged state.

---

### Phase 2 — Harden vmeta against wedging

**Owner:** vmeta + gateway/orchestrator callers  
**Effort:** medium  
**Affects:** `ppl-meta-vmeta`, callers in gateway / orchestrator / media paths

1. **Bound concurrency** for materialization / heavy ML endpoints (semaphore or worker queue); reject or queue with clear 429/503 instead of unbounded pile-on.
2. **Request deadlines** inside vmeta (cancel work when client disconnects / soft deadline &lt; caller timeout).
3. **Memory hygiene**
   - Review FaceNet / TF / embedding caches for unbounded growth (mem climbed 0.6 → 3 GiB within ~15 min after restart under live cameras)
   - Consider lower mem limit alert vs raising limit blindly on 15 GiB host
4. **Health that reflects readiness**
   - `/health` (or `/ready`) must fail or degrade when event loop blocked / queue saturated — so compose / gateway can detect without waiting 60 s
5. **Caller behaviour**
   - Orchestrator / gateway: shorter timeout + backoff (avoid sync 60 s retry storms)
   - Surface distinct error to UI (“analytics temporarily unavailable”) vs infinite spinner

**Done when:** under intentional overload (parallel materialize + live cameras), vmeta either sheds load cleanly or recovers without manual restart; no 60 s silent hangs on `/health`.

---

### Phase 3 — Analytics path performance

**Owner:** gateway + frontend  
**Effort:** medium  
**Affects:** `ppl-meta-gateway/src/api/v1/analytics.py`, `ppl-meta-frontend` analytics screen / clients

1. **Gateway:** parallelize `_fetch_instant_detection_approximation` per camera (`asyncio.gather` with limit), not sequential `for`.
2. **Optional:** single bulk approx endpoint on vmeta (one query / many cameras) to cut N round-trips.
3. **Frontend:** fire summary / time-series / demographics / behavioral / quality **in parallel** (or progressive paint: show summary first without waiting for all).
4. **CORS / client gaps:** investigate 2–6 s OPTIONS→GET delays over Tailscale (connection reuse, preflight caching, client serialisation); reduce unnecessary OPTIONS if same-origin or cached.
5. **Empty-state fast path:** if approx returns empty quickly, do not block UI on remaining waterfall unnecessarily.

**Done when:** cold analytics load over Tailscale to `eyenet-demo` completes useful first paint in a few seconds, not ~1–2 minutes, with the same camera selection.

---

### Phase 4 — Lab monitoring / prevention

**Owner:** ops  
**Effort:** small–medium

1. Simple watch: alert if vmeta health fails twice or mem % &gt; threshold for N minutes.
2. Optional: auto-restart policy only after confirmed unhealthy (careful — avoid flapping during long ML jobs).
3. Stage 3 / demo checklist: health + one analytics + one preview smoke before customer session.

**Done when:** wedged vmeta is noticed before the demo audience is.

---

## Suggested implementation order

```
Phase 0 (runbook)     →  now
Phase 1 (watchfiles)  →  next small PR / image
Phase 2 (harden)      →  next reliability sprint
Phase 3 (analytics UX)→  can parallel with Phase 2
Phase 4 (monitoring)  →  after Phase 1–2 land on lab
```

---

## Verification checklist (lab)

After each phase on `eyenet-demo`:

- [ ] `curl -m 5` vmeta `/health` → 200
- [ ] `docker stats` vmeta mem stable under live cameras for ≥30 min (no climb to limit)
- [ ] No continuous `watchfiles` / `change detected` in vmeta logs
- [ ] Analytics page (last week, multi-camera) loads without 503
- [ ] Video preview → faces / person-objects details return without 60 s timeout
- [ ] Over Tailscale: wall-clock analytics load acceptable for demo

---

## Incident reference (2026-10-21)

| Item | Value |
|------|--------|
| Host | `eyenet-demo` / Tailscale `100.101.128.40` |
| Pin | `2.25.103` |
| Container | `pplmeta-ppl-meta-vmeta-1` |
| Pre-fix | mem ~3.9 / 5 GiB; health hang; gateway 503 @ 60 s |
| Action | `docker restart pplmeta-ppl-meta-vmeta-1` |
| Post-fix | health 200 ~10 s; mem ~606 MiB; APIs fast; UI waterfall still slow |

---

## Related code (starting points)

- Gateway sequential approx fan-out: `ppl-meta-gateway/src/api/v1/analytics.py` (`_get_instant_detection_approx_dataset`, `_fetch_instant_detection_approximation`)
- Frontend analytics load: `ppl-meta-frontend/lib/screens/analytics_screen.dart`, `lib/services/media_api_client.dart`
- vmeta instant-detection analytics: `ppl-meta-vmeta/src/api/v1/` (instant detection analytics / storage routers)
- Lab machines: `docs/documentation/deployment/lab-machines.md` (`lab-work-dual-64g`)
