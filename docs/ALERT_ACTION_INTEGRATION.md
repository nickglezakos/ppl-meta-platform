Again# Alert Action Integration Documentation

**Version:** 2.23.7  
**Date:** January 21, 2026  
**Status:** ✅ Complete (with On-Screen Display)

---

## Overview

The Alert (On-Screen) action type allows triggers to display visual alert notifications when conditions are met. This action type provides **complete end-to-end functionality** including:

- ✅ Alert configuration UI in frontend
- ✅ Backend execution and logging
- ✅ **Real-time on-screen display** with animated overlays
- ✅ Automatic polling and notification delivery
- ✅ Works across all screens and navigation states

When a trigger fires with an alert action, the alert is immediately logged and will appear as an animated notification overlay on the screen within 5 seconds.

---

## Features

### Alert Configuration

- **Message**: Custom alert message to display
- **Severity**: Alert severity level (info, warning, error, critical)
- **Duration**: How long the alert should be displayed (in seconds)

### Alert Execution & Display

When a trigger fires with an alert action:
1. Alert details are extracted from action configuration
2. Alert is logged via Communications Service as an audit event
3. **Frontend polling service automatically detects new alerts**
4. **Animated alert overlay appears on screen** (regardless of current page)
5. **Alert auto-dismisses** after configured duration
6. Alert remains in audit logs for historical review

---

## Frontend Implementation

### Alert Action Form

**File:** `ppl-meta-frontend/lib/widgets/actions_tab.dart`

The alert configuration form includes:
- **Alert Message** field (required, multiline)
- **Severity** dropdown (info, warning, error, critical)
- **Duration** field (in seconds, must be positive integer)

```dart
Widget _buildAlertConfig() {
  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      TextFormField(
        controller: _alertMessageController,
        decoration: const InputDecoration(
          labelText: 'Alert Message *',
          hintText: 'High traffic detected!',
          helperText: 'Message displayed in the on-screen alert',
          prefixIcon: Icon(Icons.notifications_active),
        ),
        maxLines: 3,
        validator: (value) => value?.isEmpty ?? true ? 'Required' : null,
      ),
      // ... severity and duration fields
    ],
  );
}
```

### Action Configuration JSON

Alert actions are stored with the following configuration:

```json
{
  "message": "High traffic detected!",
  "severity": "warning",
  "duration_seconds": 30
}
```

---

## Backend Implementation

### Alert Action Execution

**File:** `ppl-meta-media/src/services/redis_subscriber.py`

When a trigger fires with an alert action, the `_execute_alert_action` method:

```python
async def _execute_alert_action(self, action, trigger: Trigger, db: Session):
    """Execute alert action via Communications Service."""
    logger.info(f"  🔔 Executing alert action...")
    
    try:
        # Parse action_config
        config = json.loads(action.action_config)
        
        # Extract alert settings
        message = config.get("message", "Alert triggered")
        severity = config.get("severity", "warning")
        duration_seconds = config.get("duration_seconds", 30)
        
        # Build alert data
        alert_data = {
            "trigger_id": str(trigger.uuid),
            "trigger_name": trigger.name,
            "action_name": action.name,
            "message": message,
            "severity": severity,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Log via Communications Service
        comms_client = get_communications_client()
        result = await comms_client.log_audit_event(
            event_type="alert",
            event_source="media_service",
            event_data=alert_data,
            severity=severity,
        )
```

### Integration with Trigger System

Alerts are routed through the trigger action execution system:

```python
async def _execute_trigger_action(self, trigger: Trigger, db: Session):
    # ...
    if action.action_type == "alert":
        await self._execute_alert_action(action, trigger, db)
```

---

## Usage Guide

### Creating an Alert Action

1. **Navigate to Actions Tab**
   - Open the PPL Meta Platform frontend
   - Go to the Actions tab
   - Click "Create Action"

2. **Configure Alert**
   - **Name**: Give your alert a descriptive name (e.g., "High Traffic Alert")
   - **Description**: Optional description
   - **Action Type**: Select "Alert (On-Screen)"
   - **Alert Message**: Enter the message to display (e.g., "High traffic detected in Camera 1!")
   - **Severity**: Choose severity level:
     - `info` - Informational alerts (blue)
     - `warning` - Warning alerts (orange)  
     - `error` - Error alerts (red)
     - `critical` - Critical alerts (red, high priority)
   - **Duration**: Set how long the alert should be visible (default: 30 seconds)
   - **Active**: Ensure the action is active

3. **Save Action**
   - Click "Create" to save the alert action

### Attaching Alert to Trigger

1. **Create/Edit Trigger**
   - Go to Triggers tab
   - Create a new trigger or edit existing one
   - Configure trigger conditions (e.g., people_count > 10)

2. **Select Alert Action**
   - In the trigger configuration, select your alert action from the dropdown
   - Save the trigger

3. **Test Alert**
   - Activate the trigger by meeting its conditions
   - Check Communication Logs for alert entries

---

## Alert Display

### Viewing Alerts

Alerts are logged in the Communications Service and can be viewed in:

**Communication Logs Screen:**
- Filter by type: "audit"
- Look for events with `event_type="alert"`
- Each log entry contains:
  - Alert message
  - Severity level
  - Duration
  - Trigger information
  - Timestamp

### Real-Time Alert Display (✅ IMPLEMENTED)

**Alert Notification System** is now fully implemented with automatic on-screen display!

#### How It Works

1. **Alert Polling Service** (`alert_notification_service.dart`)
   - Automatically polls Communications Service every 5 seconds
   - Fetches audit logs with `type=audit_log`
   - Processes new alerts and emits them via Stream

2. **Alert Overlay Widget** (`alert_overlay.dart`)
   - Wraps entire application at root level
   - Displays alerts as animated cards in top-right corner
   - Shows alerts on top of ANY screen
   - Auto-dismisses after configured duration
   - Supports manual dismissal via close button

3. **Global Integration** (`main.dart`)
   - Alert overlay integrated at app root level
   - Alerts visible regardless of navigation state
   - No screen-specific code required

#### Alert Display Features

- **Animated Entry**: Smooth slide-in animation from right
- **Severity Colors**:
  - 🔵 Info: Blue
  - 🟠 Warning: Orange  
  - 🔴 Error: Red
  - 🟣 Critical: Purple
- **Rich Information**:
  - Severity badge
  - Trigger name
  - Alert message
  - Action name
  - Relative timestamp
- **Auto-Dismiss**: Respects configured duration
- **Manual Dismiss**: Close button for immediate removal
- **Multiple Alerts**: Stacks multiple simultaneous alerts
- **Responsive**: Constrains max width for readability

#### Implementation Details

```dart
// Service automatically starts polling when app launches
final alertNotificationServiceProvider = Provider<AlertNotificationService>((ref) {
  final client = ref.watch(communicationsApiClientProvider);
  final service = AlertNotificationService(client);
  service.startPolling(); // Starts automatic polling
  return service;
});

// Overlay integrated in main.dart builder
builder: (context, child) {
  return AlertOverlay(
    child: GlobalScreenshotOverlay(
      child: child ?? const SizedBox.shrink(),
    ),
  );
}
```

#### Files Added

- `lib/services/alert_notification_service.dart` - Polling service and alert model
- `lib/widgets/alert_overlay.dart` - UI overlay widget with animations

---

## Configuration Examples

### Basic Alert

```json
{
  "message": "Motion detected",
  "severity": "info",
  "duration_seconds": 15
}
```

### Warning Alert

```json
{
  "message": "High customer traffic - consider opening additional registers",
  "severity": "warning",
  "duration_seconds": 60
}
```

### Critical Alert

```json
{
  "message": "SECURITY ALERT: Unauthorized access detected in restricted area",
  "severity": "critical",
  "duration_seconds": 120
}
```

---

## API Integration

### Alert Logs Endpoint

**GET** `/api/v1/audit/logs`

Query parameters:
- `type=audit` - Filter for audit logs
- `page=1` - Page number
- `page_size=50` - Results per page

Response includes alert logs with:

```json
{
  "logs": [
    {
      "id": "uuid",
      "type": "audit",
      "event_type": "alert",
      "event_source": "media_service",
      "event_data": {
        "trigger_id": "trigger-uuid",
        "trigger_name": "High Traffic Trigger",
        "action_name": "Traffic Alert",
        "message": "High traffic detected!",
        "severity": "warning",
        "duration_seconds": 30,
        "timestamp": "2026-01-21T13:00:00Z"
      },
      "severity": "warning",
      "created_at": "2026-01-21T13:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "total_pages": 1
}
```

---

## Testing

### Manual Testing

1. **Create Test Alert Action:**
   - Name: "Test Alert"
   - Message: "This is a test alert"
   - Severity: warning
   - Duration: 10 seconds

2. **Create Test Trigger:**
   - Condition: people_count >= 1
   - Action: Test Alert
   - Cooldown: 60 seconds

3. **Trigger the Alert:**
   - Ensure camera is active
   - Stand in front of camera to trigger detection
   - Check Media Service logs for alert execution
   - Check Communication Logs for alert entry

### Expected Log Output

**Media Service logs:**
```
🔔 Executing alert action...
   Message: This is a test alert
   Severity: warning
   Duration: 10s
✅ Alert logged successfully. Log UUID: xxx-xxx-xxx
```

**Communications Service logs:**
```
📋 Audit event logged: alert
   Source: media_service
   Severity: warning
```

---

## Troubleshooting

### Alert Not Firing

**Issue:** Alert action not executing when trigger fires

**Solutions:**
1. Check trigger is active and conditions are met
2. Verify alert action is active
3. Check trigger cooldown hasn't blocked execution
4. Review Media Service logs for execution messages

### Alert Not Visible

**Issue:** Alert logs not appearing in Communication Logs

**Solutions:**
1. Check Communications Service is running
2. Verify audit logs endpoint is accessible
3. Filter logs by type "audit" in frontend
4. Check for error messages in backend logs

### Invalid Configuration

**Issue:** Alert action fails with config error

**Solutions:**
1. Verify alert message is not empty
2. Check duration is a positive integer
3. Ensure severity is one of: info, warning, error, critical
4. Review action_config JSON syntax

### Alerts Not Displaying On Screen

**Issue:** Alerts are logged but not showing on screen

**Solutions:**
1. Verify alert polling service is running
2. Check browser console for errors
3. Ensure Communications Service is accessible
4. Check that alert_overlay is integrated in main.dart
5. Try triggering alert again and watch for animation

---

## Future Enhancements

### Planned Features

1. **✅ Real-Time Alert Display** - IMPLEMENTED
   - ✅ Polling-based notification system
   - ✅ Animated overlay UI components
   - ✅ Auto-dismiss with configurable duration
   - ✅ Manual dismissal
   - 🔄 WebSocket push notifications (future)
   - 🔄 Sound notifications (future)
   - 🔄 Desktop notifications (future)

2. **Alert Templates**
   - Pre-configured alert messages
   - Variable substitution (camera name, time, etc.)
   - Multi-language support

3. **Alert Acknowledgment**
   - Mark alerts as seen/acknowledged
   - Alert history tracking
   - User-specific alert preferences

4. **Advanced Severity Handling**
   - Color-coded severity levels
   - Priority-based alert ordering
   - Escalation rules

---

## Version History

### v2.23.6 (January 21, 2026)
- ✅ Initial alert action implementation
- ✅ Frontend alert configuration form
- ✅ Backend alert execution via Communications Service
- ✅ Alert logging in audit system
- ✅ Integration with trigger system

---

## See Also

- [Webhook Action Integration](WEBHOOK_INTEGRATION_STATUS_REPORT.md)
- [Communications Service Integration](COMMUNICATIONS_SERVICE_INTEGRATION.md)
- [Trigger System Architecture](TRIGGER_ARCHITECTURE_DIAGRAM.txt)

---

**Last Updated:** January 21, 2026  
**Status:** Production Ready
