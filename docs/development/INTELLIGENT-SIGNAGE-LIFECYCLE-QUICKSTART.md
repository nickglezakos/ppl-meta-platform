# Intelligent Signage Lifecycle - Quick Start Guide

## 🚀 Implementation Complete!

The intelligent signage lifecycle system has been fully implemented and integrated into your existing PPL Meta platform. This guide will help you get started.

## 📋 What Was Implemented

### 1. Camera Service (ppl-meta-cameras)
- ✅ Webhook push functionality in instant detection service
- ✅ Webhook configuration endpoints
- ✅ Automatic demographic data pushing every 5 seconds
- ✅ Non-blocking async webhook calls

**Files Modified:**
- `src/services/instant_detection.py` - Added webhook push
- `src/api/v1/endpoints/instant_detection.py` - Added webhook configuration endpoints

### 2. Media Service (ppl-meta-media)
- ✅ New demographic triggers system (separate from existing triggers)
- ✅ Webhook endpoint to receive demographics
- ✅ Trigger evaluation with AND logic
- ✅ Cooldown prevention system
- ✅ Complete CRUD API for trigger management
- ✅ Integration with existing signage API

**Files Created:**
- `src/routes/demographic_triggers.py` - Complete webhook-based trigger system

**Files Modified:**
- `src/main.py` - Registered new demographic triggers router

### 3. Test Suite
- ✅ Complete integration test script

**Files Created:**
- `test_intelligent_signage_lifecycle.py` - End-to-end test script

---

## 🎯 Quick Start

### Step 1: Start Services

Make sure both services are running:

```bash
# Terminal 1: Start Camera Service
cd ppl-meta-cameras
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8005 --reload

# Terminal 2: Start Media Service  
cd ppl-meta-media
source venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Configure Webhook

Tell the camera service where to send demographics:

```bash
curl -X POST 'http://localhost:8005/api/v1/instant-detection/webhook/configure' \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "http://localhost:8000/api/v1/triggers/instant-detection",
    "enabled": true
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Webhook configured successfully",
  "webhook_url": "http://localhost:8000/api/v1/triggers/instant-detection",
  "enabled": true
}
```

### Step 3: Get Device and Playlist IDs

Before creating triggers, you need actual UUIDs:

**Get Device IDs (from Discovery Service):**
```bash
curl http://localhost:8006/api/v1/services?service_type=edge
```

Copy the `service_id` of your signage device.

**Get Playlist IDs (from Media Service):**
```bash
curl http://localhost:8000/api/v1/signage/video-lists
```

Copy the `uuid` of the playlists you want to trigger.

### Step 4: Create a Trigger

Replace the placeholder UUIDs with your actual values:

```bash
curl -X POST 'http://localhost:8000/api/v1/triggers/demographic' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "male_dominant_audience",
    "description": "Switch to men products playlist",
    "camera_ids": ["usb_camera_0"],
    "conditions": [
      {"field": "percent_male", "operator": "gte", "value": 60},
      {"field": "people_count", "operator": "gte", "value": 2}
    ],
    "actions": [{
      "type": "signage_playback",
      "device_ids": ["YOUR-DEVICE-UUID"],
      "video_list_id": "YOUR-PLAYLIST-UUID",
      "start_index": 0,
      "volume": 80,
      "transition_mode": "after_current",
      "fade_duration_ms": 2000
    }],
    "enabled": true,
    "cooldown_seconds": 60
  }'
```

### Step 5: Start Recording with Instant Detection

```bash
curl -X POST 'http://localhost:8005/api/v1/streaming/usb_camera_0/record/start?enable_instant_detection=true'
```

---

## 🔍 Monitoring & Debugging

### Check Webhook Status

```bash
curl http://localhost:8005/api/v1/instant-detection/webhook/status
```

### List All Triggers

```bash
curl http://localhost:8000/api/v1/triggers/demographic
```

This shows:
- All configured triggers
- Last fired timestamp per camera
- Cooldown remaining time
- Whether trigger can fire now

### Check Camera Service Logs

```bash
tail -f logs/ppl-meta-cameras.log | grep "webhook"
```

Look for:
- `✅ Webhook configured`
- `✅ Pushed instant detection to webhook`
- `⚠️ Webhook timeout` (if media service slow)

### Check Media Service Logs

```bash
tail -f logs/ppl-meta-media.log | grep "trigger"
```

Look for:
- `📥 Received instant detection webhook`
- `🎯 Trigger fired`
- `✅ Signage action executed`

---

## 🧪 Run Integration Tests

The test script validates the complete flow:

```bash
# Make executable
chmod +x test_intelligent_signage_lifecycle.py

# Run tests (requires both services running)
python test_intelligent_signage_lifecycle.py
```

**What it tests:**
1. ✅ Webhook configuration
2. ✅ Trigger creation
3. ✅ Matching demographics (should fire)
4. ✅ Non-matching demographics (should skip)
5. ✅ Cooldown prevention
6. ✅ Trigger status listing
7. ✅ Cleanup

---

## 📊 Available Demographic Fields

You can create conditions using these fields:

```javascript
{
  // Counts
  "people_count": 3,
  "total_male": 2,
  "total_female": 1,
  "total_young": 0,
  "total_adult": 3,
  
  // Percentages (0-100)
  "percent_male": 67,
  "percent_female": 33,
  "percent_young": 0,
  "percent_adult": 100
}
```

### Supported Operators

- `gt` - Greater than (>)
- `gte` - Greater than or equal (≥)
- `lt` - Less than (<)
- `lte` - Less than or equal (≤)
- `eq` - Equal (=)

---

## 🎨 Transition Modes

Configure how the Android player switches playlists:

### 1. `"immediate"` - Fast Response
```json
{
  "transition_mode": "immediate"
}
```
- Stops current video instantly
- Starts new playlist immediately
- Use for: Urgent content, breaking news, short cooldowns (10-30s)

### 2. `"after_current"` - Smooth & Professional
```json
{
  "transition_mode": "after_current",
  "fade_duration_ms": 2000
}
```
- Lets current video finish
- Queues new playlist
- Switches smoothly when video ends
- Use for: Professional installations, long cooldowns (60s+)

### 3. `"fade"` - Professional Crossfade
```json
{
  "transition_mode": "fade",
  "fade_duration_ms": 3000
}
```
- Crossfades between playlists
- Configurable fade duration (1-5 seconds recommended)
- Use for: High-end retail, museums, corporate lobbies

---

## 🔧 API Endpoints Reference

### Camera Service (Port 8005)

#### Configure Webhook
```
POST /api/v1/instant-detection/webhook/configure
```

#### Get Webhook Status
```
GET /api/v1/instant-detection/webhook/status
```

#### Enable/Disable Webhook
```
POST /api/v1/instant-detection/webhook/enable
POST /api/v1/instant-detection/webhook/disable
```

### Media Service (Port 8000)

#### Webhook Endpoint (Receives from Camera)
```
POST /api/v1/triggers/instant-detection
```

#### Create Trigger
```
POST /api/v1/triggers/demographic
```

#### List Triggers
```
GET /api/v1/triggers/demographic
```

#### Get Specific Trigger
```
GET /api/v1/triggers/demographic/{trigger_name}
```

#### Update Trigger
```
PUT /api/v1/triggers/demographic/{trigger_name}
```

#### Delete Trigger
```
DELETE /api/v1/triggers/demographic/{trigger_name}
```

#### Enable/Disable Trigger
```
POST /api/v1/triggers/demographic/{trigger_name}/enable
POST /api/v1/triggers/demographic/{trigger_name}/disable
```

#### Reset Cooldown
```
POST /api/v1/triggers/demographic/{trigger_name}/reset-cooldown?camera_id=usb_camera_0
```

---

## 💡 Example Trigger Configurations

### Young Audience Trigger
```json
{
  "name": "young_audience",
  "description": "Show youth content",
  "camera_ids": ["usb_camera_0"],
  "conditions": [
    {"field": "percent_young", "operator": "gt", "value": 50},
    {"field": "people_count", "operator": "gte", "value": 3}
  ],
  "actions": [{
    "type": "signage_playback",
    "device_ids": ["device-uuid"],
    "video_list_id": "youth-playlist-uuid",
    "transition_mode": "fade",
    "fade_duration_ms": 3000
  }],
  "cooldown_seconds": 60
}
```

### Female Audience Trigger
```json
{
  "name": "female_dominant_audience",
  "description": "Show women's products",
  "camera_ids": ["usb_camera_0"],
  "conditions": [
    {"field": "percent_female", "operator": "gte", "value": 70}
  ],
  "actions": [{
    "type": "signage_playback",
    "device_ids": ["device-uuid"],
    "video_list_id": "womens-products-uuid",
    "transition_mode": "immediate"
  }],
  "cooldown_seconds": 45
}
```

### Multi-Condition Trigger
```json
{
  "name": "target_demographic",
  "description": "Young male audience",
  "camera_ids": ["usb_camera_0"],
  "conditions": [
    {"field": "percent_male", "operator": "gte", "value": 60},
    {"field": "percent_young", "operator": "gte", "value": 40},
    {"field": "people_count", "operator": "gte", "value": 2}
  ],
  "actions": [{
    "type": "signage_playback",
    "device_ids": ["device-uuid"],
    "video_list_id": "target-playlist-uuid",
    "transition_mode": "after_current"
  }],
  "cooldown_seconds": 120
}
```

---

## ⚠️ Important Notes

### 1. Cooldown Strategy
- **Short cooldown (10-30s)**: Use with `"immediate"` transition for responsive switching
- **Medium cooldown (60-90s)**: Use with `"after_current"` for professional experience
- **Long cooldown (120s+)**: Use with multi-condition triggers to let playlists complete

### 2. Webhook Frequency
- Webhooks arrive **every 5 seconds** (constant)
- Actions only execute when **cooldown expired**
- This prevents playlist switching every 5 seconds

### 3. In-Memory Storage
- Current implementation uses in-memory storage (`TRIGGERS`, `LAST_TRIGGERED`)
- ⚠️ Triggers reset when media service restarts
- For production: Migrate to database (PostgreSQL)

### 4. Android Player Implementation
- Your Android signage player must implement `transition_mode` handling
- See `INTELLIGENT-SIGNAGE-LIFECYCLE.md` Feature 4 for Kotlin implementation

---

## 🎉 You're Ready!

The intelligent signage lifecycle is now fully operational. The system will:

1. ✅ Detect demographics every 5 seconds
2. ✅ Push data to media service automatically
3. ✅ Evaluate your triggers in real-time
4. ✅ Switch signage playlists based on demographics
5. ✅ Respect cooldown to prevent spam
6. ✅ Support smooth transitions

**Next Steps:**
1. Configure webhook (Step 2)
2. Get your actual device/playlist IDs (Step 3)
3. Create your first trigger (Step 4)
4. Start recording with instant detection (Step 5)
5. Watch the magic happen! 🎬

For detailed architecture and implementation details, see:
- `docs/development/INTELLIGENT-SIGNAGE-LIFECYCLE.md`

For questions or issues, check the service logs or run the integration test script.
