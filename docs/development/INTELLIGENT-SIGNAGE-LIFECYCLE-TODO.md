# Intelligent Signage Lifecycle - End-to-End Integration TODO

**Status**: Backend integration complete, Frontend & Signage API integration pending  
**Created**: December 13, 2025  
**Owner**: System Integration

---

## 🎯 Overview

This document outlines the remaining work needed to complete the end-to-end intelligent signage lifecycle integration with the existing triggers system at `http://localhost:3000/#/triggers`.

### What's Already Complete ✅

**Backend Integration:**
- ✅ Database migration with 8 demographic fields added to `triggers` table
- ✅ Trigger model updated with demographic columns
- ✅ Trigger schemas updated with Pydantic validation
- ✅ Webhook endpoint: `POST /api/v1/triggers/instant-detection`
- ✅ Camera webhook configuration working
- ✅ Demographic condition evaluation with AND logic
- ✅ Cooldown mechanism to prevent spam
- ✅ Database persistence of trigger state

**Files Modified:**
- `ppl-meta-media/migrations/versions/321a0601fef9_add_demographic_fields.py` (new)
- `ppl-meta-media/src/models/trigger.py` (updated)
- `ppl-meta-media/src/schemas/trigger.py` (updated)
- `ppl-meta-media/src/routes/triggers.py` (updated)
- `ppl-meta-cameras/src/services/instant_detection.py` (updated)
- `ppl-meta-cameras/src/api/v1/endpoints/instant_detection.py` (updated)

---

## 📋 Remaining Work

### 1. Signage API Integration (HIGH PRIORITY) ✅ EXISTING SERVICE AVAILABLE

**Good News**: PPL Meta already has a comprehensive signage service in `ppl-meta-media`!

**Existing Signage Infrastructure:**

- **Service**: `ppl-meta-media/src/services/signage_service.py`
  - `SignageService` - Video list management
  - `SignagePlaybackService` - Playback control
  - `SignageSyncService` - Device synchronization
  
- **API Routes**: `ppl-meta-media/src/api/v1/signage.py`
  - `/api/v1/signage/video-lists` - CRUD for video lists (playlists)
  - `/api/v1/signage/devices` - Device registration & management
  - `/api/v1/signage/playback/control` - **Playback control endpoint** ✅
  
- **Models**: `ppl-meta-media/src/models/signage.py`
  - `VideoList` (playlist)
  - `SignageDevice`
  - `SyncHistory`

**Current Trigger Code** (`ppl-meta-media/src/routes/triggers.py`, line ~440):
```python
# NEEDS UPDATE - Currently calls non-existent endpoint
signage_api_url = "http://localhost:8080/api/v1/signage"
response = await client.post(f"{signage_api_url}/play", ...)
```

**Required Actions:**

#### Use Existing Playback Control Endpoint

**Existing Endpoint**: `POST /api/v1/signage/playback/control`

**Request Schema** (from `PlaybackControlRequest`):
```python
{
    "device_ids": ["device-uuid-1", "device-uuid-2"],  # List of device UUIDs
    "command": "start",  # start|pause|resume|stop|next|previous
    "video_list_id": "playlist-uuid",  # UUID (not int!)
    "parameters": {
        "volume": 80,
        "start_index": 0,
        "transition_mode": "immediate"  # Custom parameter
    }
}
```

**Response Schema** (from `PlaybackControlResponse`):
```python
{
    "command_id": "uuid",
    "status": "executed|failed",
    "affected_devices": 2,
    "executed_at": "2025-12-13T18:00:00Z",
    "message": "Command sent to 2/2 devices"
}
```

#### UPDATE NEEDED IN triggers.py:

Replace the `_execute_signage_action()` function (line ~422) to use existing endpoint:

#### UPDATE NEEDED IN triggers.py:

Replace the `_execute_signage_action()` function (line ~422) to use existing endpoint:

```python
async def _execute_signage_action(
    trigger: Trigger,
    camera_id: str
):
    """Execute signage action using EXISTING playback control API."""
    if not trigger.signage_device_ids or not trigger.signage_playlist_id:
        logger.warning(f"Trigger '{trigger.name}' missing signage configuration")
        return
    
    # Parse device IDs from JSON
    try:
        device_ids = json.loads(trigger.signage_device_ids)
        if not isinstance(device_ids, list):
            device_ids = [device_ids]
    except (json.JSONDecodeError, TypeError):
        device_ids = [trigger.signage_device_ids]
    
    # Call existing playback control API
    signage_api_url = "http://localhost:8000/api/v1/signage/playback/control"
    
    payload = {
        "device_ids": device_ids,
        "command": "start",
        "video_list_id": trigger.signage_playlist_id,  # Should be UUID string
        "parameters": {
            "transition_mode": trigger.signage_transition_mode or "immediate",
            "fade_duration_ms": trigger.signage_fade_duration_ms or 2000,
            "volume": 80,
            "start_index": 0,
            "triggered_by": {
                "trigger_uuid": str(trigger.uuid),
                "trigger_name": trigger.name,
                "camera_id": camera_id
            }
        }
    }
    
    logger.info(f"📺 Calling existing signage API: {signage_api_url}")
    logger.info(f"   Devices: {device_ids}")
    logger.info(f"   Video List: {trigger.signage_playlist_id}")
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.post(signage_api_url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(
                    f"✅ Signage action executed: "
                    f"affected {result.get('affected_devices')}/{len(device_ids)} devices"
                )
            else:
                logger.warning(
                    f"⚠️ Signage API returned {response.status_code}: {response.text}"
                )
        except Exception as e:
            logger.error(f"❌ Error calling signage API: {e}")
```

**Important Notes:**
- `video_list_id` must be a **UUID string**, not integer ID
- `device_ids` are **UUIDs** from SignageDevice table
- No auth header needed (internal service call)
- Transition modes: `immediate`, `after_current`, `fade`

#### Option B: Use Existing Signage System

If you already have a signage system:

#### Option B: No Action Needed - Use Existing Infrastructure

The existing signage API already provides all needed functionality!

---

### 2. Frontend UI Modifications (HIGH PRIORITY) ✅ CAN USE EXISTING ROUTES

**Good News**: The existing signage API provides device & playlist endpoints!

**Available APIs for Frontend:**
- `GET /api/v1/signage/devices` - List registered devices
- `GET /api/v1/signage/video-lists` - List video lists (playlists)

**Location**: `ppl-meta-frontend/lib/widgets/triggers_tab.dart` (or create new trigger dialog)

#### 2.1 Update Trigger Model

**File**: `ppl-meta-frontend/lib/models/trigger.dart`

Add new fields to the Trigger model:
```dart
class Trigger {
  // Existing fields...
  final String uuid;
  final String name;
  final String personCountOperator;
  final String personCountValue;
  // ... other existing fields
  
  // NEW: Demographic fields
  final bool enableDemographicConditions;
  final String? demographicConditions; // JSON string
  final String? signageDeviceIds; // JSON string
  final String? signagePlaylistId;
  final String? signageTransitionMode;
  final int? signageFadeDurationMs;
  final int? cooldownSeconds;
  final DateTime? lastFiredAt;
  
  Trigger({
    required this.uuid,
    required this.name,
    // ... existing parameters
    this.enableDemographicConditions = false,
    this.demographicConditions,
    this.signageDeviceIds,
    this.signagePlaylistId,
    this.signageTransitionMode = 'immediate',
    this.signageFadeDurationMs = 2000,
    this.cooldownSeconds = 60,
    this.lastFiredAt,
  });
  
  factory Trigger.fromJson(Map<String, dynamic> json) {
    return Trigger(
      // ... existing fields
      enableDemographicConditions: json['enable_demographic_conditions'] ?? false,
      demographicConditions: json['demographic_conditions'],
      signageDeviceIds: json['signage_device_ids'],
      signagePlaylistId: json['signage_playlist_id'],
      signageTransitionMode: json['signage_transition_mode'] ?? 'immediate',
      signageFadeDurationMs: json['signage_fade_duration_ms'] ?? 2000,
      cooldownSeconds: json['cooldown_seconds'] ?? 60,
      lastFiredAt: json['last_fired_at'] != null 
          ? DateTime.parse(json['last_fired_at']) 
          : null,
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      // ... existing fields
      'enable_demographic_conditions': enableDemographicConditions,
      'demographic_conditions': demographicConditions,
      'signage_device_ids': signageDeviceIds,
      'signage_playlist_id': signagePlaylistId,
      'signage_transition_mode': signageTransitionMode,
      'signage_fade_duration_ms': signageFadeDurationMs,
      'cooldown_seconds': cooldownSeconds,
    };
  }
}
```

#### 2.2 Update Trigger Creation Dialog

**File**: `ppl-meta-frontend/lib/widgets/trigger_dialog.dart` (or similar)

Add new UI sections:

**Section 1: Evaluation Mode Selector**
```dart
SwitchListTile(
  title: Text('Enable Demographic Conditions'),
  subtitle: Text('Use real-time demographic data from camera'),
  value: _enableDemographicConditions,
  onChanged: (bool value) {
    setState(() {
      _enableDemographicConditions = value;
    });
  },
)
```

**Section 2: Demographic Conditions Builder** (shown when enabled)
```dart
if (_enableDemographicConditions) ...[
  Card(
    child: Padding(
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Demographic Conditions', 
            style: Theme.of(context).textTheme.titleMedium),
          Text('All conditions must be met (AND logic)',
            style: Theme.of(context).textTheme.bodySmall),
          SizedBox(height: 16),
          
          // List of conditions
          ..._demographicConditions.asMap().entries.map((entry) {
            int index = entry.key;
            var condition = entry.value;
            
            return Row(
              children: [
                // Field dropdown
                Expanded(
                  flex: 2,
                  child: DropdownButton<String>(
                    value: condition['field'],
                    items: [
                      DropdownMenuItem(value: 'people_count', child: Text('People Count')),
                      DropdownMenuItem(value: 'percent_male', child: Text('% Male')),
                      DropdownMenuItem(value: 'percent_female', child: Text('% Female')),
                      DropdownMenuItem(value: 'percent_young', child: Text('% Young')),
                      DropdownMenuItem(value: 'percent_adult', child: Text('% Adult')),
                      DropdownMenuItem(value: 'percent_senior', child: Text('% Senior')),
                    ],
                    onChanged: (value) {
                      setState(() {
                        _demographicConditions[index]['field'] = value;
                      });
                    },
                  ),
                ),
                
                // Operator dropdown
                Expanded(
                  flex: 1,
                  child: DropdownButton<String>(
                    value: condition['operator'],
                    items: [
                      DropdownMenuItem(value: 'gt', child: Text('>')),
                      DropdownMenuItem(value: 'gte', child: Text('≥')),
                      DropdownMenuItem(value: 'lt', child: Text('<')),
                      DropdownMenuItem(value: 'lte', child: Text('≤')),
                      DropdownMenuItem(value: 'eq', child: Text('=')),
                    ],
                    onChanged: (value) {
                      setState(() {
                        _demographicConditions[index]['operator'] = value;
                      });
                    },
                  ),
                ),
                
                // Value input
                Expanded(
                  flex: 1,
                  child: TextField(
                    decoration: InputDecoration(labelText: 'Value'),
                    keyboardType: TextInputType.number,
                    controller: TextEditingController(
                      text: condition['value'].toString()
                    ),
                    onChanged: (value) {
                      _demographicConditions[index]['value'] = 
                        double.tryParse(value) ?? 0;
                    },
                  ),
                ),
                
                // Remove button
                IconButton(
                  icon: Icon(Icons.remove_circle),
                  onPressed: () {
                    setState(() {
                      _demographicConditions.removeAt(index);
                    });
                  },
                ),
              ],
            );
          }).toList(),
          
          // Add condition button
          TextButton.icon(
            icon: Icon(Icons.add),
            label: Text('Add Condition'),
            onPressed: () {
              setState(() {
                _demographicConditions.add({
                  'field': 'people_count',
                  'operator': 'gte',
                  'value': 0,
                });
              });
            },
          ),
        ],
      ),
    ),
  ),
]
```

**Section 3: Signage Configuration** (shown when demographic enabled)
```dart
if (_enableDemographicConditions) ...[
  Card(
    child: Padding(
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Signage Control', 
            style: Theme.of(context).textTheme.titleMedium),
          SizedBox(height: 16),
          
          // Device selector (multi-select)
          FutureBuilder<List<SignageDevice>>(
            future: _fetchSignageDevices(),
            builder: (context, snapshot) {
              if (!snapshot.hasData) return CircularProgressIndicator();
              
              return Wrap(
                spacing: 8,
                children: snapshot.data!.map((device) {
                  bool isSelected = _selectedDeviceIds.contains(device.id);
                  return FilterChip(
                    label: Text(device.name),
                    selected: isSelected,
                    onSelected: (selected) {
                      setState(() {
                        if (selected) {
                          _selectedDeviceIds.add(device.id);
                        } else {
                          _selectedDeviceIds.remove(device.id);
                        }
                      });
                    },
                  );
                }).toList(),
              );
            },
          ),
          
          SizedBox(height: 16),
          
          // Playlist selector
          FutureBuilder<List<Playlist>>(
            future: _fetchPlaylists(),
            builder: (context, snapshot) {
              if (!snapshot.hasData) return CircularProgressIndicator();
              
              return DropdownButton<String>(
                value: _selectedPlaylistId,
                hint: Text('Select Playlist'),
                isExpanded: true,
                items: snapshot.data!.map((playlist) {
                  return DropdownMenuItem(
                    value: playlist.id,
                    child: Text('${playlist.name} (${playlist.videoCount} videos)'),
                  );
                }).toList(),
                onChanged: (value) {
                  setState(() {
                    _selectedPlaylistId = value;
                  });
                },
              );
            },
          ),
          
          SizedBox(height: 16),
          
          // Transition mode
          DropdownButton<String>(
            value: _transitionMode,
            isExpanded: true,
            items: [
              DropdownMenuItem(
                value: 'immediate',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Immediate'),
                    Text('Switch now', style: TextStyle(fontSize: 12, color: Colors.grey)),
                  ],
                ),
              ),
              DropdownMenuItem(
                value: 'after_current',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('After Current'),
                    Text('Wait for video to finish', style: TextStyle(fontSize: 12, color: Colors.grey)),
                  ],
                ),
              ),
              DropdownMenuItem(
                value: 'fade',
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Fade'),
                    Text('Crossfade transition', style: TextStyle(fontSize: 12, color: Colors.grey)),
                  ],
                ),
              ),
            ],
            onChanged: (value) {
              setState(() {
                _transitionMode = value!;
              });
            },
          ),
          
          // Fade duration (if fade mode)
          if (_transitionMode == 'fade') ...[
            SizedBox(height: 16),
            TextField(
              decoration: InputDecoration(
                labelText: 'Fade Duration (ms)',
                helperText: 'Crossfade duration in milliseconds',
              ),
              keyboardType: TextInputType.number,
              controller: TextEditingController(
                text: _fadeDurationMs.toString()
              ),
              onChanged: (value) {
                _fadeDurationMs = int.tryParse(value) ?? 2000;
              },
            ),
          ],
          
          SizedBox(height: 16),
          
          // Cooldown
          TextField(
            decoration: InputDecoration(
              labelText: 'Cooldown (seconds)',
              helperText: 'Minimum time between trigger firings',
            ),
            keyboardType: TextInputType.number,
            controller: TextEditingController(
              text: _cooldownSeconds.toString()
            ),
            onChanged: (value) {
              _cooldownSeconds = int.tryParse(value) ?? 60;
            },
          ),
        ],
      ),
    ),
  ),
]
```

**Section 4: Serialize to JSON on Save**
```dart
Future<void> _saveTrigger() async {
  // Convert demographic conditions to JSON string
  String? demographicConditionsJson;
  if (_enableDemographicConditions && _demographicConditions.isNotEmpty) {
    demographicConditionsJson = jsonEncode(_demographicConditions);
  }
  
  // Convert device IDs to JSON string
  String? signageDeviceIdsJson;
  if (_selectedDeviceIds.isNotEmpty) {
    signageDeviceIdsJson = jsonEncode(_selectedDeviceIds);
  }
  
  final trigger = Trigger(
    // ... existing fields
    enableDemographicConditions: _enableDemographicConditions,
    demographicConditions: demographicConditionsJson,
    signageDeviceIds: signageDeviceIdsJson,
    signagePlaylistId: _selectedPlaylistId,
    signageTransitionMode: _transitionMode,
    signageFadeDurationMs: _fadeDurationMs,
    cooldownSeconds: _cooldownSeconds,
  );
  
  // POST to /api/v1/triggers
  await apiService.createTrigger(trigger);
}
```

#### 2.3 Update Triggers List Display

**File**: `ppl-meta-frontend/lib/widgets/triggers_tab.dart`

Add visual indicators for demographic-enabled triggers:

```dart
ListTile(
  leading: trigger.enableDemographicConditions
      ? Icon(Icons.psychology, color: Colors.purple) // Brain icon for AI/demographic
      : Icon(Icons.people, color: Colors.blue),
  title: Text(trigger.name),
  subtitle: Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(trigger.description ?? ''),
      if (trigger.enableDemographicConditions) ...[
        SizedBox(height: 4),
        Row(
          children: [
            Icon(Icons.analytics, size: 16, color: Colors.grey),
            SizedBox(width: 4),
            Text('Demographic Mode', style: TextStyle(fontSize: 12, color: Colors.grey)),
            if (trigger.lastFiredAt != null) ...[
              SizedBox(width: 8),
              Icon(Icons.access_time, size: 16, color: Colors.grey),
              SizedBox(width: 4),
              Text(
                'Last fired: ${_formatTimestamp(trigger.lastFiredAt!)}',
                style: TextStyle(fontSize: 12, color: Colors.grey),
              ),
            ],
          ],
        ),
      ],
    ],
  ),
  trailing: Switch(
    value: trigger.isActive,
    onChanged: (value) => _toggleTrigger(trigger.uuid, value),
  ),
  onTap: () => _editTrigger(trigger),
)
```

#### 2.4 Add API Service Methods

**File**: `ppl-meta-frontend/lib/services/api_service.dart`

Add methods to fetch signage data:

```dart
class ApiService {
  // Existing methods...
  
  Future<List<SignageDevice>> fetchSignageDevices() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/signage/devices'),
    );
    
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body)['devices'];
      return data.map((json) => SignageDevice.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load signage devices');
    }
  }
  
  Future<List<Playlist>> fetchPlaylists() async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/signage/playlists'),
    );
    
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body)['playlists'];
      return data.map((json) => Playlist.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load playlists');
    }
  }
}
```

---

### 3. Device Communication Layer (MEDIUM PRIORITY)

The signage player app (Android/Flutter) needs to receive and execute playlist commands.

#### 3.1 Signage Player App Updates

**Location**: `ppl-meta-signage-player` (new app or existing)

**Required Components:**

1. **WebSocket/SSE Connection** to signage service
2. **Command Handler** to process playlist switch commands
3. **Playlist Manager** to handle transitions
4. **Device Registration** on app startup

**Example WebSocket Handler:**
```dart
class SignagePlayerService {
  WebSocketChannel? _channel;
  String? _deviceId;
  
  Future<void> connect() async {
    _deviceId = await _getDeviceId();
    
    _channel = WebSocketChannel.connect(
      Uri.parse('ws://localhost:8080/api/v1/signage/ws/$_deviceId'),
    );
    
    _channel!.stream.listen((message) {
      final command = jsonDecode(message);
      _handleCommand(command);
    });
  }
  
  void _handleCommand(Map<String, dynamic> command) {
    switch (command['type']) {
      case 'play_playlist':
        _playPlaylist(
          playlistId: command['playlist_id'],
          transitionMode: command['transition_mode'],
          fadeDurationMs: command['fade_duration_ms'],
        );
        break;
      case 'pause':
        _pausePlayback();
        break;
      case 'resume':
        _resumePlayback();
        break;
    }
  }
  
  Future<void> _playPlaylist({
    required String playlistId,
    required String transitionMode,
    required int fadeDurationMs,
  }) async {
    // Fetch playlist videos
    final playlist = await _fetchPlaylist(playlistId);
    
    // Handle transition
    switch (transitionMode) {
      case 'immediate':
        await _videoPlayer.stop();
        await _videoPlayer.loadPlaylist(playlist);
        await _videoPlayer.play();
        break;
      case 'after_current':
        _videoPlayer.onCurrentVideoComplete(() async {
          await _videoPlayer.loadPlaylist(playlist);
          await _videoPlayer.play();
        });
        break;
      case 'fade':
        await _videoPlayer.fadeOut(fadeDurationMs);
        await _videoPlayer.loadPlaylist(playlist);
        await _videoPlayer.fadeIn(fadeDurationMs);
        break;
    }
  }
}
```

#### 3.2 Device Registration

**On App Startup:**
```dart
Future<void> registerDevice() async {
  final deviceInfo = await _getDeviceInfo();
  
  await http.post(
    Uri.parse('http://localhost:8080/api/v1/signage/devices/register'),
    body: jsonEncode({
      'device_id': deviceInfo.id,
      'name': deviceInfo.name,
      'platform': Platform.operatingSystem,
      'screen_resolution': '${deviceInfo.width}x${deviceInfo.height}',
      'capabilities': ['immediate', 'after_current', 'fade'],
    }),
  );
}
```

---

### 4. Testing Strategy (HIGH PRIORITY)

#### 4.1 Unit Tests

**Backend:**
- Test demographic condition evaluation logic
- Test cooldown mechanism
- Test webhook payload parsing
- Test signage API payload formatting

**Frontend:**
- Test trigger model serialization/deserialization
- Test condition builder logic
- Test device/playlist selection

#### 4.2 Integration Tests

**Current Test** (`test_integrated_demographic_triggers.py`):
- ✅ Tests webhook configuration
- ✅ Tests trigger creation
- ✅ Tests webhook reception
- ✅ Tests condition evaluation
- ✅ Tests cooldown
- ❌ Needs: Mock signage API responses

**Update Test:**
```python
# Add mock signage API
from unittest.mock import patch
import responses

@responses.activate
def test_step_3_with_signage_mock():
    # Mock signage API
    responses.add(
        responses.POST,
        'http://localhost:8080/api/v1/signage/play',
        json={'status': 'success', 'device_id': 'test-device-uuid-1234'},
        status=200
    )
    
    # Run webhook test
    result = test_step_3_simulate_webhook_match(trigger_uuid)
    
    # Verify signage API was called
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url.endswith('/play')
```

#### 4.3 End-to-End Test Flow

**Manual Test Procedure:**

1. **Setup:**
   - Start all services
   - Register signage device
   - Create playlists
   - Configure camera webhook

2. **Create Trigger:**
   - Open `http://localhost:3000/#/triggers`
   - Click "Create Trigger"
   - Enable demographic conditions
   - Add condition: `percent_male >= 60`
   - Select signage device
   - Select playlist
   - Set cooldown to 10 seconds
   - Save

3. **Trigger Camera Detection:**
   - Start camera with instant detection
   - Position camera to detect people
   - Wait for demographics to match (60%+ male)

4. **Verify:**
   - Check trigger fired in logs
   - Verify `last_fired_at` updated in database
   - Verify signage device switched playlist
   - Wait 5 seconds, verify cooldown prevents re-fire
   - Wait 10+ seconds, verify can fire again

---

### 5. Configuration & Deployment (MEDIUM PRIORITY)

#### 5.1 Environment Configuration

**Add to `.env` or config files:**

```bash
# Media Service
SIGNAGE_API_URL=http://localhost:8080/api/v1/signage
SIGNAGE_API_TIMEOUT=5

# Signage Service (if separate)
SIGNAGE_SERVICE_PORT=8009
SIGNAGE_DEVICE_REGISTRY=database  # or redis
SIGNAGE_WEBSOCKET_PORT=8010
```

#### 5.2 Update Service Discovery

Register signage service with discovery:

```python
# ppl-meta-signage/src/main.py
async def register_with_discovery():
    await http.post(
        'http://localhost:8006/api/v1/services/register',
        json={
            'service_type': 'signage',
            'name': 'ppl-meta-signage',
            'host': 'localhost',
            'port': 8009,
            'version': '1.0.0',
        }
    )
```

#### 5.3 Update Nginx Configuration

**Add to `nginx-local-dev.conf`:**

```nginx
# Signage API
location /api/v1/signage {
    proxy_pass http://localhost:8009;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}

# Signage WebSocket
location /api/v1/signage/ws {
    proxy_pass http://localhost:8010;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

---

### 6. Cleanup Tasks (LOW PRIORITY)

#### 6.1 Remove Old Demographic Triggers File

**File to Remove:**
- `ppl-meta-media/src/routes/demographic_triggers.py` (no longer needed)

**Update main.py:**
```python
# Remove these lines from ppl-meta-media/src/main.py
# from src.routes.demographic_triggers import router as demographic_triggers_router
# app.include_router(demographic_triggers_router)
```

#### 6.2 Update Documentation

**Files to Update:**
- `TRIGGERS_IMPLEMENTATION_COMPLETE.md` - Add demographic features
- `INTELLIGENT-SIGNAGE-LIFECYCLE.md` - Update with integration details
- `API.md` - Document new endpoints

---

## 📊 Implementation Priority Matrix

| Task | Priority | Estimated Time | Blocking |
|------|----------|----------------|----------|
| Signage API Service | HIGH | 2-3 days | Yes - required for E2E |
| Frontend UI Updates | HIGH | 1-2 days | Yes - required for user config |
| Device Communication | MEDIUM | 2-3 days | No - can mock initially |
| Integration Tests | HIGH | 1 day | No - but critical for validation |
| Environment Config | MEDIUM | 2 hours | No |
| Documentation | LOW | 4 hours | No |
| Cleanup | LOW | 1 hour | No |

**Total Estimated Time**: 7-10 days

---

## 🚀 Recommended Implementation Order

### Phase 1: Minimum Viable Product (MVP) - 3-4 days

1. **Day 1-2**: Create signage API service with mock device registry
2. **Day 2-3**: Update frontend UI with demographic fields
3. **Day 3-4**: Integration testing with mock devices
4. **Result**: Can create demographic triggers in UI, trigger fires on webhook, logs signage action

### Phase 2: Real Device Integration - 2-3 days

5. **Day 5-6**: Implement WebSocket device communication
6. **Day 6-7**: Update signage player app to receive commands
7. **Day 7**: End-to-end testing with real devices
8. **Result**: Full lifecycle working with actual playlist switching

### Phase 3: Polish & Production - 2-3 days

9. **Day 8**: Configuration and deployment updates
10. **Day 9**: Documentation and cleanup
11. **Day 10**: Production testing and monitoring setup
12. **Result**: Production-ready system with documentation

---

## 📝 Success Criteria

The integration is complete when:

- ✅ User can create trigger with demographic conditions via UI
- ✅ Trigger appears in triggers list with demographic indicator
- ✅ Camera sends demographics via webhook every 5 seconds
- ✅ Trigger evaluates conditions correctly (AND logic)
- ✅ Cooldown prevents spam firing
- ✅ Signage API receives playlist switch command
- ✅ Signage device executes transition (immediate/after/fade)
- ✅ All actions logged and auditable
- ✅ System handles errors gracefully
- ✅ Documentation complete and accurate

---

## 🔍 Current Limitations

1. **No Signage API** - Trigger fires but signage action fails silently
2. **No Device Registry** - Cannot select devices in UI (no API endpoint)
3. **No Playlist Management** - Cannot select playlists (no API endpoint)
4. **No Device Communication** - No way to send commands to players
5. **Mock Signage URL** - Hardcoded to localhost:8080 (should be configurable)

---

## 💡 Future Enhancements

- **Analytics Dashboard** - Show trigger firing history and demographics over time
- **A/B Testing** - Compare effectiveness of different demographic triggers
- **Machine Learning** - Auto-optimize conditions based on engagement metrics
- **Multi-camera Aggregation** - Combine demographics from multiple cameras
- **Geofencing** - Location-based trigger conditions
- **Time-based Rules** - Different playlists for different times of day
- **Audience Segmentation** - More sophisticated demographic analysis

---

## 📞 Support & Questions

For implementation questions or issues, refer to:
- Backend integration: `ppl-meta-media/src/routes/triggers.py`
- Database schema: `ppl-meta-media/migrations/versions/321a0601fef9_*`
- Test examples: `test_integrated_demographic_triggers.py`
- Original spec: `INTELLIGENT-SIGNAGE-LIFECYCLE.md`
