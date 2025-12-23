# Redis Status Notification Setup Guide

## Overview

This guide will help you set up and test the new robust camera status notification system using Redis Pub/Sub + WebSocket.

## Prerequisites

- macOS (or Linux)
- Python 3.8+
- Camera service (`ppl-meta-cameras`)
- Auth service (port 8001) running

## Step 1: Install Redis

```bash
# Install Redis via Homebrew
brew install redis

# Verify installation
redis-server --version
```

## Step 2: Start Redis Server

### Option A: Foreground (for testing)
```bash
redis-server
```

### Option B: Background (for development)
```bash
# Start as background service
brew services start redis

# Check status
brew services list | grep redis

# Stop later with:
# brew services stop redis
```

### Verify Redis is Running
```bash
# Should return "PONG"
redis-cli ping
```

## Step 3: Install Python Dependencies

```bash
cd ppl-meta-cameras

# Install Redis and WebSocket packages
pip install redis>=5.0.0 websockets==12.0 httpx

# Or install from requirements.txt
pip install -r requirements.txt
```

## Step 4: Start Camera Service

The camera service will automatically initialize the Redis status notification service on startup.

```bash
cd ppl-meta-cameras
source venv/bin/activate

# Start service
cd src
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

**Look for this in logs:**
```
✅ Redis status notification service initialized
```

**If Redis is not available:**
```
⚠️ Redis status service not available: Connection refused
Status updates will work locally but not across instances
```
This is OK - the service will work without Redis, just won't have real-time WebSocket updates.

## Step 5: Run Tests

```bash
cd ppl-meta-cameras

# Run comprehensive WebSocket test suite
python tests/test_status_websocket.py
```

**Expected output:**
```
🧪 Camera Status WebSocket Test Suite
============================================================
🔐 Authenticating...
✅ Authenticated successfully

============================================================
TEST 1: WebSocket Connection Establishment
============================================================
✅ Connected to ws://localhost:8005/api/v1/cameras/ws/status/usb_camera_0?token=...
⏳ Waiting for cached status...
✅ Received cached status: {
  "device_id": "usb_camera_0",
  "status": "disconnected",
  "timestamp": "2025-12-23T08:00:00"
}

============================================================
TEST 2: Ping/Pong Keep-Alive
============================================================
📤 Sending ping...
⏳ Waiting for pong...
✅ Received pong - keep-alive works!

============================================================
TEST 3: Real-Time Status Updates
============================================================
🔄 Testing DISCONNECT → CONNECT cycle...
✅ DISCONNECT triggered successfully
✅ CONNECT triggered successfully
📨 Received: disconnected at 2025-12-23T08:00:01
📨 Received: connected at 2025-12-23T08:00:03
   Latency: ~50ms

✅ Received 2 status updates

============================================================
TEST SUMMARY
============================================================

Tests Passed: 5/5

Detailed Results:
  ✅ PASS  Connection
  ✅ PASS  Ping Pong
  ✅ PASS  Real Time Updates
  ✅ PASS  Connection Stability
  ✅ PASS  All Cameras

🎉 ALL TESTS PASSED! Status WebSocket system is working perfectly.
```

## Step 6: Manual Testing with Redis CLI

Monitor status changes in real-time:

```bash
# Subscribe to all camera status changes
redis-cli SUBSCRIBE camera:status:all

# Or subscribe to specific camera
redis-cli SUBSCRIBE camera:status:usb_camera_0
```

Now trigger status changes via API:
```bash
# Get token first
TOKEN="your-jwt-token"

# Connect camera
curl -X POST http://localhost:8005/api/v1/cameras/usb_camera_0/connect \
  -H "Authorization: Bearer $TOKEN"

# Disconnect camera
curl -X POST http://localhost:8005/api/v1/cameras/usb_camera_0/disconnect \
  -H "Authorization: Bearer $TOKEN"
```

You should see messages in Redis CLI:
```
1) "message"
2) "camera:status:usb_camera_0"
3) "{\"device_id\":\"usb_camera_0\",\"event\":\"connected\",\"timestamp\":\"2025-12-23T08:00:00\"}"
```

## Step 7: Test with Browser WebSocket

Create a test HTML file:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Camera Status WebSocket Test</title>
</head>
<body>
    <h1>Camera Status Monitor</h1>
    <div id="status"></div>
    <div id="messages"></div>

    <script>
        const token = 'YOUR_JWT_TOKEN'; // Replace with actual token
        const ws = new WebSocket(
            `ws://localhost:8005/api/v1/cameras/ws/status/usb_camera_0?token=${token}`
        );

        ws.onopen = () => {
            document.getElementById('status').innerHTML = '✅ Connected';
        };

        ws.onmessage = (event) => {
            const status = JSON.parse(event.data);
            const msg = document.createElement('div');
            msg.innerHTML = `<strong>${status.event}</strong> at ${status.timestamp}`;
            document.getElementById('messages').prepend(msg);
        };

        ws.onerror = (error) => {
            document.getElementById('status').innerHTML = '❌ Error';
            console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
            document.getElementById('status').innerHTML = '⚠️ Disconnected';
        };

        // Keep connection alive
        setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send('ping');
            }
        }, 30000);
    </script>
</body>
</html>
```

## Troubleshooting

### Redis Connection Errors

**Error**: `Connection refused`
```bash
# Check if Redis is running
redis-cli ping

# If not running, start it
redis-server
```

**Error**: `Could not connect to Redis`
```bash
# Check Redis port
netstat -an | grep 6379

# Check Redis config
cat /usr/local/etc/redis.conf | grep port
```

### WebSocket Connection Errors

**Error**: `401 Unauthorized`
- Token expired or invalid
- Get new token from auth service

**Error**: `Connection closed immediately`
- Check camera service logs
- Verify Redis is running
- Check token is in query parameter: `?token=JWT`

### No Status Updates

**Check Redis pub/sub is working:**
```bash
# Terminal 1: Subscribe
redis-cli SUBSCRIBE camera:status:all

# Terminal 2: Publish test message
redis-cli PUBLISH camera:status:all "test message"

# Should see message in Terminal 1
```

**Check camera status changes:**
```bash
# View service logs
tail -f ppl-meta-cameras.log | grep "status:"

# Should see logs like:
# 📊 Camera usb_camera_0 status: disconnected → connecting
# 📊 Camera usb_camera_0 status: connecting → connected
```

### Service Logs Don't Show Redis Initialization

**Check Python dependencies:**
```bash
pip list | grep redis
# Should show: redis 5.0.0 or higher
```

**Check Redis URL configuration:**
```python
# In Python shell
import redis
client = redis.Redis(host='localhost', port=6379)
client.ping()  # Should return True
```

## Performance Monitoring

### Monitor Redis Performance
```bash
# Real-time stats
redis-cli INFO stats

# Monitor all commands
redis-cli MONITOR

# Check pub/sub channels
redis-cli PUBSUB CHANNELS camera:*

# Count subscribers
redis-cli PUBSUB NUMSUB camera:status:all
```

### Monitor WebSocket Connections
```bash
# Check open connections to port 8005
lsof -i :8005

# Count WebSocket connections
netstat -an | grep 8005 | grep ESTABLISHED | wc -l
```

## Production Deployment

### Redis Configuration

For production, configure Redis for persistence and security:

```bash
# Edit Redis config
vim /usr/local/etc/redis.conf

# Recommended settings:
# - Enable AOF persistence: appendonly yes
# - Set password: requirepass yourpassword
# - Bind to specific IP: bind 127.0.0.1
# - Set maxmemory: maxmemory 256mb
# - Set eviction policy: maxmemory-policy allkeys-lru
```

### Environment Variables

```bash
export REDIS_URL="redis://username:password@redis-host:6379/0"
export REDIS_MAX_CONNECTIONS=50
```

### Monitoring

Consider using:
- **Redis Commander** - Web UI for Redis
- **RedisInsight** - Official Redis GUI
- **Prometheus + Redis Exporter** - Metrics collection

## Next Steps

✅ Redis and WebSocket status system is now running!

**Frontend Integration:**
1. Update camera cards to use WebSocket instead of polling
2. Add connection status indicator (connected/disconnected)
3. Handle reconnection on network issues

**Documentation:**
- See `docs/architecture/CAMERA_STATUS_SOLUTION.md` for detailed architecture
- See `tests/test_status_websocket.py` for code examples

**Performance Testing:**
- Test with multiple concurrent clients
- Measure latency under load
- Test reconnection scenarios

## References

- [Redis Pub/Sub Documentation](https://redis.io/docs/manual/pubsub/)
- [WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
