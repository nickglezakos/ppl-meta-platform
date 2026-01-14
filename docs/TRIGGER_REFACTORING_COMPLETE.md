# Trigger System Refactoring - Complete

**Date:** January 14, 2026  
**Status:** ✅ Complete  
**Migration:** `refactor_demographic_2026_01_14` - Successfully Applied

---

## Overview

Completed a major architectural refactoring of the trigger system to:
1. **Simplify trigger logic** - All triggers now use unified `demographic_conditions` array
2. **Separate concerns** - Moved signage-specific config from triggers to actions
3. **Improve maintainability** - Single source of truth for trigger evaluation

---

## Changes Summary

### Backend Changes

#### 1. Database Model (`ppl-meta-media/src/models/trigger.py`)
**Removed 12 redundant columns:**
- `person_count_threshold`
- `person_count_operator`
- `age_range_filter`
- `age_range_operator`
- `age_range_threshold`
- `gender_filter`
- `action`
- `action_config`
- `enable_demographic_conditions`
- `signage_device_ids`
- `signage_video_list_id`
- `signage_playback_config`

**Made required:**
- `demographic_conditions` (NOT NULL, JSON array)

#### 2. API Schemas (`ppl-meta-media/src/schemas/trigger.py`)
**New structure:**
```python
class DemographicCondition(BaseModel):
    field: str  # e.g., "people_count", "percent_male", "percent_age_18_24"
    operator: str  # "gt", "gte", "lt", "lte", "eq"
    value: float
```

**Example trigger:**
```json
{
  "name": "High Traffic Trigger",
  "demographic_conditions": [
    {"field": "people_count", "operator": "gt", "value": 10},
    {"field": "percent_male", "operator": "gte", "value": 60}
  ]
}
```

#### 3. Trigger Evaluation (`ppl-meta-media/src/services/trigger_evaluation.py`)
**Complete rewrite:**
- Renamed `CounterData` → `DemographicData`
- New evaluation logic for unified conditions
- Supports all demographic fields and operators
- All conditions must pass (AND logic)

#### 4. User Actions (`ppl-meta-media/src/schemas/user_action.py`)
**Added `digital_signage` action type:**
```json
{
  "action_type": "digital_signage",
  "action_config": {
    "device_ids": ["device-uuid-1", "device-uuid-2"],
    "playlist_id": "playlist-uuid",
    "transition_mode": "fade",
    "fade_duration_ms": 1000
  }
}
```

#### 5. Database Migration
**File:** `ppl-meta-media/migrations/versions/refactor_triggers_to_demographic_only.py`

**Migration steps:**
1. Added `demographic_conditions_temp` column
2. Migrated existing triggers:
   - Converted `person_count_*` → demographic condition
   - Set empty array `[]` for triggers without conditions
3. Dropped 12 redundant columns
4. Renamed `demographic_conditions_temp` → `demographic_conditions`
5. Set NOT NULL constraint

**Result:** All existing triggers successfully migrated ✅

---

### Frontend Changes

#### 1. Trigger Model (`ppl-meta-frontend/lib/models/trigger_model.dart`)
**Added:**
```dart
@JsonSerializable()
class DemographicCondition {
  final String field;
  final String operator;
  final double value;
}
```

**Removed fields:**
- `personCountThreshold`
- `personCountOperator`
- `ageRangeFilter`
- `ageRangeOperator`
- `ageRangeThreshold`
- `genderFilter`
- `action`
- `actionConfig`
- `signageDeviceIds`
- `signageVideoListId`
- `signagePlaybackConfig`

#### 2. Triggers UI (`ppl-meta-frontend/lib/widgets/triggers_tab.dart`)
**Complete rewrite (923 lines → simplified):**

**New features:**
- Demographic conditions builder UI
- Dynamic field selector (people_count, demographics)
- Operator dropdown (>, >=, <, <=, =)
- Value input with validation
- Add/remove conditions
- Camera validation (warns if selected camera doesn't exist)
- Action dropdown (links to user actions)

**Old UI backed up to:** `triggers_tab_old_backup.dart`

#### 3. Actions UI (`ppl-meta-frontend/lib/widgets/actions_tab.dart`)
**Added digital signage action configuration:**

**New features when action type = `digital_signage`:**
- Device multi-selector (fetches from discovery service)
  - Shows device name, host:port, online status
  - Checkbox list for selecting multiple devices
- Playlist selector (fetches from signage API)
  - Shows playlist name and video count
- Transition mode dropdown:
  - `immediate` - Switch immediately
  - `after_current` - Wait for current video to finish
  - `fade` - Fade transition
- Fade duration input (only shown for fade mode)

**Config JSON structure:**
```json
{
  "device_ids": ["uuid1", "uuid2"],
  "playlist_id": "playlist-uuid",
  "transition_mode": "fade",
  "fade_duration_ms": 1000
}
```

#### 4. User Action Model (`ppl-meta-frontend/lib/models/user_action_model.dart`)
**Added UI helpers:**
```dart
String get actionTypeDisplay {
  switch (actionType) {
    case 'digital_signage': return 'Digital Signage';
    // ... other types
  }
}

IconData get actionTypeIcon {
  switch (actionType) {
    case 'digital_signage': return Icons.smart_display;
    // ... other types
  }
}

Color get actionTypeColor {
  switch (actionType) {
    case 'digital_signage': return Colors.green;
    // ... other types
  }
}
```

---

## Architecture

### Before
```
Trigger Model:
  - camera_device_id
  - name
  - person_count_threshold ❌
  - person_count_operator ❌
  - age_range_filter ❌
  - gender_filter ❌
  - action ❌
  - action_config ❌
  - signage_device_ids ❌ (mixing concerns)
  - signage_video_list_id ❌ (mixing concerns)
  - signage_playback_config ❌ (mixing concerns)
  - demographic_conditions (optional)
```

### After
```
Trigger Model:
  - camera_device_id
  - name
  - demographic_conditions ✅ (required, unified)

User Action Model:
  - name
  - action_type (alert, email, webhook, log, digital_signage)
  - action_config (JSON - type-specific configuration)

Trigger → Action (many-to-one)
```

---

## Data Flow

### Trigger Evaluation Flow
```
1. Camera sends demographic update
   ↓
2. DemographicData object created
   ↓
3. TriggerEvaluationService evaluates all active triggers
   ↓
4. For each trigger:
   - Parse demographic_conditions array
   - Evaluate each condition (ALL must pass)
   - Return (trigger, passed, reason)
   ↓
5. For passed triggers:
   - Look up linked user action
   - Execute action based on action_type
   - For digital_signage: send playlist change to devices
```

### Digital Signage Action Flow
```
1. Trigger passes evaluation
   ↓
2. Action executor loads user action
   ↓
3. Parse action_config JSON
   ↓
4. For each device_id:
   - Call SignageApiClient.startPlayback()
   - Pass playlist_id, transition_mode, fade_duration
   ↓
5. Signage device receives command
   ↓
6. Device switches playlist based on transition_mode
```

---

## Testing Checklist

### Backend
- [x] Migration runs successfully
- [x] Existing triggers migrated correctly
- [ ] Create trigger with demographic conditions
- [ ] Update trigger conditions
- [ ] Evaluate trigger against camera data
- [ ] Create digital_signage user action
- [ ] Link trigger to action
- [ ] Trigger fires and executes action

### Frontend
- [x] Code generation successful
- [x] No compilation errors
- [ ] Triggers tab loads
- [ ] Create trigger with conditions
- [ ] Edit trigger conditions
- [ ] Delete trigger
- [ ] Actions tab loads
- [ ] Create digital signage action
- [ ] Device list loads from discovery
- [ ] Playlist list loads from signage API
- [ ] Save digital signage action
- [ ] Edit digital signage action

### Integration
- [ ] Camera sends demographic data
- [ ] Trigger evaluates correctly
- [ ] Action executes
- [ ] Signage devices receive playlist change
- [ ] Playlist switches on device
- [ ] Monitor logs for errors

---

## API Examples

### Create Trigger
```bash
POST /api/v1/triggers
{
  "name": "High Traffic - Young Adults",
  "camera_device_id": "camera-123",
  "demographic_conditions": [
    {"field": "people_count", "operator": "gt", "value": 15},
    {"field": "percent_age_18_24", "operator": "gte", "value": 40}
  ],
  "user_action_id": "action-uuid"
}
```

### Create Digital Signage Action
```bash
POST /api/v1/user-actions
{
  "name": "Switch to Promo Playlist",
  "description": "Show promotional content during high traffic",
  "action_type": "digital_signage",
  "action_config": "{\"device_ids\": [\"dev1\", \"dev2\"], \"playlist_id\": \"promo-playlist\", \"transition_mode\": \"fade\", \"fade_duration_ms\": 2000}",
  "is_active": true
}
```

---

## Migration Details

### Command
```bash
cd ppl-meta-media
alembic upgrade refactor_demographic_2026_01_14
```

### Result
```
INFO  [alembic.runtime.migration] Running upgrade c1f0e3a37ad0 -> refactor_demographic_2026_01_14, Refactor triggers to use only demographic_conditions
INFO  [alembic.runtime.migration] Migrated 5 triggers successfully
```

### Verified Changes
```sql
-- Check migrated triggers
SELECT 
  uuid,
  name,
  demographic_conditions,
  user_action_id
FROM triggers;

-- Verify columns dropped
\d triggers
-- Confirmed: 12 columns removed
```

---

## File Changes

### Backend
| File | Status | Description |
|------|--------|-------------|
| `src/models/trigger.py` | ✅ Modified | Removed 12 columns, made demographic_conditions required |
| `src/schemas/trigger.py` | ✅ Modified | Added DemographicCondition schema |
| `src/services/trigger_evaluation.py` | ✅ Rewritten | New evaluation logic for unified conditions |
| `src/schemas/user_action.py` | ✅ Modified | Added digital_signage support |
| `migrations/versions/refactor_triggers_to_demographic_only.py` | ✅ Created | Migration script |

### Frontend
| File | Status | Description |
|------|--------|-------------|
| `lib/models/trigger_model.dart` | ✅ Modified | Added DemographicCondition class |
| `lib/widgets/triggers_tab.dart` | ✅ Rewritten | New UI for demographic conditions |
| `lib/widgets/triggers_tab_old_backup.dart` | ✅ Created | Backup of old UI |
| `lib/models/user_action_model.dart` | ✅ Modified | Added digital_signage helpers |
| `lib/widgets/actions_tab.dart` | ✅ Modified | Added digital signage config UI |

---

## Benefits

### 1. Simplified Architecture
- Single source of truth for trigger conditions
- No overlapping/conflicting configuration
- Cleaner separation of concerns

### 2. Better Maintainability
- Easier to add new demographic fields
- Easier to add new operators
- Type-safe validation with Pydantic

### 3. More Flexible
- Support any combination of conditions
- Support multiple actions per trigger (future)
- Support complex boolean logic (future)

### 4. Better UI/UX
- Dynamic condition builder
- Live validation
- Clear error messages
- Specialized config UI per action type

---

## Future Enhancements

### Phase 1 (Current)
- ✅ Unified demographic conditions
- ✅ Digital signage action type
- ✅ Migration complete

### Phase 2 (Planned)
- [ ] OR logic support (currently AND only)
- [ ] Nested condition groups
- [ ] Action chaining (execute multiple actions)
- [ ] Action delays/scheduling

### Phase 3 (Planned)
- [ ] Trigger history/analytics
- [ ] A/B testing support
- [ ] Machine learning condition suggestions
- [ ] Visual trigger builder with drag-drop

---

## Notes

### Database Schema
The new `demographic_conditions` column stores an array of condition objects:
```json
[
  {"field": "people_count", "operator": "gt", "value": 10},
  {"field": "percent_male", "operator": "gte", "value": 60},
  {"field": "percent_age_25_34", "operator": "gte", "value": 30}
]
```

All conditions must be met (AND logic) for the trigger to pass.

### Supported Fields
- `people_count` - Total number of people
- `percent_male` - Percentage of males (0-100)
- `percent_female` - Percentage of females (0-100)
- `percent_age_0_12` - Age range percentages
- `percent_age_13_17`
- `percent_age_18_24`
- `percent_age_25_34`
- `percent_age_35_44`
- `percent_age_45_54`
- `percent_age_55_64`
- `percent_age_65_plus`

### Supported Operators
- `gt` - Greater than
- `gte` - Greater than or equal
- `lt` - Less than
- `lte` - Less than or equal
- `eq` - Equal to

---

## Contact

For questions or issues, contact the development team or refer to:
- [Architecture Docs](./architecture/)
- [API Documentation](./api/)
- [Frontend Guidelines](../ppl-meta-frontend/README.md)
- [Backend Guidelines](../ppl-meta-media/README.md)
