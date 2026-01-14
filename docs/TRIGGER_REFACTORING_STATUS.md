# Trigger Refactoring Status - 2026-01-14

## ✅ Completed Backend Changes

### 1. Database Model ([trigger.py](../ppl-meta-media/src/models/trigger.py))
- ✅ Removed: `person_count_operator`, `person_count_value`, `age_range_operator`, `age_range_value`, `gender_filter`
- ✅ Removed: `action`, `action_config` (deprecated fields)
- ✅ Removed: `enable_demographic_conditions`, `signage_device_ids`, `signage_playlist_id`, `signage_transition_mode`, `signage_fade_duration_ms`
- ✅ Kept: `demographic_conditions` (now required), `cooldown_seconds`, `last_fired_at`, `action_uuid`, `tracking_duration`
- ✅ Updated docstrings and repr method

### 2. Schemas ([trigger.py](../ppl-meta-media/src/schemas/trigger.py))
- ✅ Created `DemographicCondition` schema with validation
- ✅ Updated `TriggerBase` to use List[DemographicCondition]
- ✅ Removed all old field references
- ✅ Updated `TriggerResponse` schema
- ✅ Simplified `TriggerUpdate` schema

### 3. User Actions ([user_trigger_action.py](../ppl-meta-media/src/schemas/user_trigger_action.py))
- ✅ Added `digital_signage` to allowed action types
- ✅ Updated documentation for action_config format:
  ```json
  {
    "device_ids": ["device-uuid-1", "device-uuid-2"],
    "playlist_id": "playlist-uuid",
    "transition_mode": "immediate|after_current|fade",
    "fade_duration_ms": 2000
  }
  ```

### 4. Trigger Evaluation Service ([trigger_evaluation.py](../ppl-meta-media/src/services/trigger_evaluation.py))
- ✅ Renamed `CounterData` → `DemographicData`
- ✅ Complete rewrite to evaluate demographic_conditions array
- ✅ All conditions must pass (AND logic)
- ✅ Supports all operators: gt, gte, lt, lte, eq
- ✅ Handles all demographic fields (people_count, percent_male, percent_female, percent_age_*)
- ✅ Improved time_span handling (including overnight spans)

### 5. Database Migration ([refactor_triggers_to_demographic_only.py](../ppl-meta-media/migrations/versions/refactor_triggers_to_demographic_only.py))
- ✅ Created Alembic migration script
- ✅ Migrates old triggers to new format (person_count → demographic_conditions)
- ✅ Drops obsolete columns
- ✅ Includes downgrade path (with warnings about data loss)

### 6. Frontend Model ([trigger_model.dart](../ppl-meta-frontend/lib/models/trigger_model.dart))
- ✅ Created `DemographicCondition` class
- ✅ Updated `TriggerModel` to use List<DemographicCondition>
- ✅ Removed all old fields
- ✅ Updated `TriggerCreateRequest`
- ✅ Simplified model structure

## 🚧 Remaining Frontend Changes

### 7. Frontend Trigger Forms and UI (triggers_tab.dart)
**File:** `ppl-meta-frontend/lib/widgets/triggers_tab.dart`

**Required Changes:**
- [ ] Remove old form fields (person count operator/value, age range, gender)
- [ ] Add demographic conditions builder UI
- [ ] Update data table columns to show conditions count instead of individual fields
- [ ] Update dialog to use `DemographicTriggerConfig` widget for all triggers
- [ ] Remove "Enable Demographic" toggle (always enabled now)
- [ ] Remove signage device/playlist selectors from trigger dialog
- [ ] Ensure action dropdown only shows action names (signage config in actions)

**Suggested Approach:**
```dart
// Data table columns should show:
- Name
- Conditions (count + summary)
- Camera  
- Time Span
- Tracking Duration
- Action (from user actions list)
- Status
- Actions (Edit/Delete buttons)

// Dialog should have:
- Name/Description fields
- Demographic Conditions builder (reuse DemographicTriggerConfig widget logic)
- Camera selector
- Time span input
- Tracking duration selector
- Action dropdown (links to user action)
- Cooldown seconds
- Active toggle
```

### 8. Frontend Action Configuration
**File:** Need to create/update action management UI

**Required Changes:**
- [ ] Add "Digital Signage" action type to action creation form
- [ ] Create UI for configuring digital signage action:
  - Device selector (multi-select)
  - Playlist selector
  - Transition mode dropdown
  - Fade duration input
- [ ] Update actions list to show action type badge
- [ ] Add action preview/details view

**Suggested Location:**
Create new file: `ppl-meta-frontend/lib/widgets/digital_signage_action_config.dart`

Or extend existing user actions UI to handle digital_signage type.

## 📋 Migration Steps

### Before Running Migration:
1. **Backup database!**
2. Ensure all services are stopped
3. Review existing triggers (especially those with signage config)
4. Note down any digital signage configurations to recreate as actions

### Running Migration:
```bash
cd ppl-meta-media
source venv/bin/activate
alembic upgrade head
```

### After Migration:
1. Verify triggers migrated correctly
2. Create digital_signage user actions for old signage triggers
3. Link triggers to new digital_signage actions
4. Regenerate frontend code generation:
   ```bash
   cd ppl-meta-frontend
   flutter pub run build_runner build --delete-conflicting-outputs
   ```
5. Test trigger creation/editing
6. Test trigger evaluation

## 🎯 Architecture Benefits

### Clean Separation of Concerns:
- **Triggers** = WHAT to detect (conditions)
- **Actions** = WHAT to do (execution)

### Flexibility:
- Any trigger can use any action type
- Actions are reusable across triggers
- Easy to add new action types

### Consistency:
- All conditions use same format (demographic_conditions)
- No redundant fields
- Clear data model

## 📝 Example Usage

### Creating a Trigger (API):
```json
{
  "name": "High Traffic Alert",
  "demographic_conditions": [
    {"field": "people_count", "operator": "gte", "value": 10},
    {"field": "percent_age_18_24", "operator": "gte", "value": 50}
  ],
  "time_span": "Mon-Fri 09:00-17:00",
  "camera_device_id": "usb_camera_0",
  "action_uuid": "action-uuid-here",
  "tracking_duration": "5 minutes",
  "cooldown_seconds": 60
}
```

### Creating a Digital Signage Action (API):
```json
{
  "name": "Show Youth Content",
  "action_type": "digital_signage",
  "action_config": "{\"device_ids\": [\"device-1\", \"device-2\"], \"playlist_id\": \"youth-playlist-uuid\", \"transition_mode\": \"fade\", \"fade_duration_ms\": 2000}"
}
```

## ⚠️ Breaking Changes

1. **API Changes:**
   - Old trigger fields no longer accepted
   - Must provide demographic_conditions array
   - Signage config moved to user actions

2. **Database Schema:**
   - Multiple columns dropped
   - demographic_conditions now required

3. **Frontend:**
   - Models completely refactored
   - UI needs significant updates
   - Code generation required

## 🔄 Next Steps Priority

1. **HIGH**: Update frontend trigger forms (task #7)
2. **HIGH**: Add digital signage action configuration UI (task #8)
3. **MEDIUM**: Update any API routes that reference old fields
4. **MEDIUM**: Update tests
5. **LOW**: Update documentation
6. **LOW**: Create migration guide for existing users
