# Service Startup Issue - November 19, 2025

## Problem

Flutter frontend shows "Unable to connect to server" errors because backend services (Node, Gateway, Discovery, etc.) are not starting properly.

## Root Cause

**Start script issue:**
```bash
set -e  # Exit on error - THIS CAUSES THE PROBLEM
```

When `set -e` is enabled:
- Script exits on FIRST service that fails to start
- Subsequent services never get started
- Only Media (8000) and Bootcore (8007) running
- Node (8001), Gateway (8080), Discovery (8006) all missing

## Evidence

```bash
# Port check results:
Port 8000: ✅ LISTEN (Media)
Port 8001: ❌ not listening (Node) - NEEDED FOR AUTH
Port 8002: ❌ not listening (Orchestrator)
Port 8003: ❌ not listening (Vision)
Port 8005: ❌ not listening (Cameras)
Port 8006: ❌ not listening (Discovery) - NEEDED FOR FLUTTER
Port 8007: ✅ LISTEN (Bootcore)
Port 8008: ❌ not listening (VMeta)
Port 8080: ❌ not listening (Gateway) - NEEDED FOR FLUTTER
```

## Flutter Configuration (Correct)

Flutter is properly configured to use:
- Gateway: `http://localhost:8080` (not running!)
- Discovery: `http://localhost:8006` (not running!)
- Node/Auth: via Gateway (Gateway not running!)

File: `ppl-meta-frontend/assets/config/env.development.json`

## Fix Applied

1. **Removed `set -e`** from start script
2. **Added error handling** to `start_service()` function
3. **Added PID verification** - checks if service actually started
4. **Added sleep delays** - gives services time to initialize
5. **Better error messages** - shows which service failed

## Next Steps

1. **Stop all services:**
   ```bash
   ./scripts/stop-all-services.sh
   ```

2. **Start services with fixed script:**
   ```bash
   ./scripts/start-all-services.sh
   ```

3. **Verify services running:**
   ```bash
   for port in 8000 8001 8002 8003 8005 8006 8007 8008 8080; do
       echo -n "Port $port: "
       lsof -i :$port 2>/dev/null | grep LISTEN || echo "not listening"
   done
   ```

4. **Check logs if services fail:**
   ```bash
   tail -f logs/ppl-meta-node.log      # Auth service
   tail -f logs/ppl-meta-gateway.log   # API gateway
   tail -f logs/ppl-meta-discovery.log # Service discovery
   ```

5. **Once services running, Flutter will connect automatically**

## Flutter Error Explained

```
⛔ AuthNotifier: Login error: Unable to connect to server
❌ Failed to discover services: DioException [connection error]
```

These errors are **EXPECTED** when backend is down. They mean:
- Flutter is working correctly
- Backend services (Node, Gateway, Discovery) are not responding
- Not a Flutter configuration issue
- Not a credentials issue

## Quick Verification

```bash
# Check if Node service (auth) is up:
curl http://localhost:8001/api/v1/health

# Check if Gateway is up:
curl http://localhost:8080/health

# Check if Discovery is up:
curl http://localhost:8006/health
```

If all three respond, Flutter will work!

## Related Files

- **Start script:** `scripts/start-all-services.sh` (FIXED)
- **Flutter config:** `ppl-meta-frontend/assets/config/env.development.json` (OK)
- **Service logs:** `logs/*.log`
- **Service PIDs:** `pids/*.pid`
