# Merge Individuals Rules Setting

## Overview
This document describes the "Merge Individuals Rules" setting that has been added to the PPL Meta Platform to control how the system handles duplicate individuals in cross-video tracking.

## Location
The setting is located in the Settings screen under the "General" tab, in a new section called "Cross-Video Tracking".

**URL:** `http://localhost:3000/#/settings` (General Settings Tab)

## Options

The setting provides three levels of merge automation:

### 1. No Automatic Merging (Default)
- **Value:** `'none'`
- **Behavior:** Only manual merging is allowed
- **User Action Required:** Users must manually select individuals using checkboxes on the Person Objects Detail screen and click "Merge" button
- **Use Case:** Maximum control, suitable for scenarios where precision is critical

### 2. Semi-Automatic Merging
- **Value:** `'semi'`
- **Behavior:** System suggests merges, but requires user confirmation
- **User Action Required:** After a tracking session completes, system analyzes individuals and presents merge suggestions in a dialog
- **Use Case:** Balanced approach - system assists but user has final say
- **Status:** UI complete, backend logic pending implementation

### 3. Automatic Merging
- **Value:** `'auto'`
- **Behavior:** System automatically merges similar individuals during session processing
- **User Action Required:** None - merges happen automatically based on similarity threshold
- **Use Case:** High-volume scenarios where speed is prioritized over precision
- **Status:** UI complete, backend logic pending implementation

## Implementation Details

### Frontend Components

#### 1. Settings Model
**File:** `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend/lib/models/settings_models.dart`

Added to `GeneralSettings` class:
```dart
final String mergeIndividualsRule; // 'none', 'semi', or 'auto'
```

Default value: `'none'`

#### 2. Settings Provider
**File:** `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend/lib/providers/settings_providers.dart`

Added to `GeneralSettingsNotifier`:
```dart
Future<void> updateMergeIndividualsRule(String rule) async {
  final currentSettings = state.valueOrNull;
  if (currentSettings != null) {
    await _saveSettings(currentSettings.copyWith(mergeIndividualsRule: rule));
  }
}
```

#### 3. Settings Screen UI
**File:** `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend/lib/screens/settings_screen.dart`

Added new section in `GeneralSettingsTab` (lines 161-207):
```dart
_buildSectionHeader('Cross-Video Tracking'),
Card(
  child: Padding(
    padding: const EdgeInsets.all(16),
    child: Column(
      children: [
        ListTile(
          title: const Text('Merge Individuals Rules'),
          subtitle: const Text('Control how duplicate individuals are handled'),
        ),
        RadioListTile<String>(
          title: const Text('No automatic merging'),
          subtitle: const Text('Manual selection only'),
          value: 'none',
          groupValue: data.mergeIndividualsRule,
          onChanged: (value) => notifier.updateMergeIndividualsRule(value!),
        ),
        RadioListTile<String>(
          title: const Text('Semi-automatic merging'),
          subtitle: const Text('Suggest merges, require confirmation'),
          value: 'semi',
          groupValue: data.mergeIndividualsRule,
          onChanged: (value) => notifier.updateMergeIndividualsRule(value!),
        ),
        RadioListTile<String>(
          title: const Text('Automatic merging'),
          subtitle: const Text('Automatically merge similar individuals'),
          value: 'auto',
          groupValue: data.mergeIndividualsRule,
          onChanged: (value) => notifier.updateMergeIndividualsRule(value!),
        ),
      ],
    ),
  ),
),
```

#### 4. JSON Serialization
**File:** `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend/lib/models/settings_models.g.dart`

Auto-generated code includes:
- `mergeIndividualsRule` in `fromJson` method
- `mergeIndividualsRule` in `toJson` method

### Backend Integration (Pending)

The following backend changes are needed to fully implement semi-automatic and automatic merging:

#### Semi-Automatic Mode
1. After a tracking session completes, check the user's `mergeIndividualsRule` setting
2. If set to `'semi'`, run similarity analysis on all individuals in the session
3. Find pairs with similarity > threshold (e.g., 0.6)
4. Send notification or store suggestions in database
5. Frontend displays dialog with merge suggestions
6. User can accept/reject each suggestion

**Suggested Implementation Location:**
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`
- Add function: `suggest_individual_merges(session_uuid: str) -> List[MergeSuggestion]`
- Call after `process_tracking_session` completes

#### Automatic Mode
1. During `process_tracking_session`, after individual consolidation
2. Check user's `mergeIndividualsRule` setting
3. If set to `'auto'`, automatically call merge endpoint for similar individuals
4. Log all automatic merges for audit trail
5. Include merge statistics in session summary

**Suggested Implementation Location:**
- `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta/src/api/v1/cross_video_tracking_simple.py`
- Modify `process_tracking_session` to include auto-merge logic
- Add `auto_merge_individuals(session_uuid: str, threshold: float)` function

## Current Status

### ✅ Completed
- Settings model updated with `mergeIndividualsRule` field
- Settings provider updated with `updateMergeIndividualsRule()` method
- Settings UI added with three radio options
- JSON serialization code generated
- Default value set to `'none'` (manual merging only)
- Setting persists across app restarts via local storage

### 🔄 Partially Complete
- Manual merge workflow (checkbox selection + confirmation dialog)
- Similarity threshold validation on backend
- Debug logging for merge operations

### ⏳ Pending
- Semi-automatic merge suggestions implementation
- Automatic merge during session processing
- Backend setting retrieval and enforcement
- Notification system for merge suggestions
- Merge audit trail/history

## Testing

### Manual Testing Steps
1. Navigate to `http://localhost:3000/#/settings`
2. Click on "General" tab
3. Scroll to "Cross-Video Tracking" section
4. Verify three radio options are displayed
5. Select each option and verify selection persists
6. Close and reopen app, verify selection is remembered
7. Verify default is "No automatic merging"

### Integration Testing
1. Set to "No automatic merging"
   - Verify manual merge still works with checkboxes
2. Set to "Semi-automatic merging"
   - Run tracking session
   - Verify suggestions are displayed (once implemented)
3. Set to "Automatic merging"
   - Run tracking session
   - Verify individuals are automatically merged (once implemented)

## User Stories

### Story 1: Manual Control (Current Implementation)
**As a** precision-focused user  
**I want** to manually review and confirm all merges  
**So that** I maintain complete control over individual consolidation

**Acceptance Criteria:**
- ✅ Can select "No automatic merging" option
- ✅ System only merges when I explicitly select individuals and click Merge
- ✅ No automatic merges occur in the background

### Story 2: Semi-Automatic Workflow (Future)
**As a** power user  
**I want** the system to suggest likely duplicates  
**So that** I can quickly review and approve merges without manual searching

**Acceptance Criteria:**
- ⏳ Can select "Semi-automatic merging" option
- ⏳ After session, system shows dialog with merge suggestions
- ⏳ Can review similarity scores and accept/reject each suggestion
- ⏳ Manual merge option still available for non-suggested pairs

### Story 3: Automatic Processing (Future)
**As a** high-volume user  
**I want** the system to automatically merge duplicates  
**So that** I can process many videos without manual intervention

**Acceptance Criteria:**
- ⏳ Can select "Automatic merging" option
- ⏳ System automatically merges individuals above threshold during session
- ⏳ Can view merge history/audit log
- ⏳ Can adjust global similarity threshold for auto-merging

## Configuration

The setting is stored in local browser storage as part of the `GeneralSettings` object.

**Storage Key:** `'general_settings'`

**JSON Structure:**
```json
{
  "darkTheme": false,
  "autoRefresh": true,
  "refreshInterval": 30,
  "enableNotifications": true,
  "maxLogEntries": 1000,
  "debugMode": false,
  "performanceMonitoring": true,
  "mergeIndividualsRule": "none"
}
```

## Related Documentation
- [Face Embeddings for Individual Merging](../ppl-meta-vmeta/docs/FACE_EMBEDDINGS_FOR_INDIVIDUAL_MERGING.md)
- [Manual Individual Merge Implementation](../ppl-meta-vmeta/docs/MANUAL_INDIVIDUAL_MERGE_IMPLEMENTATION.md)

## Next Steps
1. ✅ Add setting UI (COMPLETE)
2. ✅ Add setting model and provider (COMPLETE)
3. ⏳ Implement backend setting retrieval in merge endpoint
4. ⏳ Implement semi-automatic merge suggestions
5. ⏳ Implement automatic merge during session processing
6. ⏳ Add merge audit trail
7. ⏳ Add notification system for suggestions

## Notes
- The current manual merge implementation (with checkboxes and confirmation dialog) serves as the foundation
- Semi-automatic and automatic modes will leverage the same merge logic
- Consider adding a global similarity threshold setting that applies to auto/semi-auto modes
- Audit logging is important for automatic merges to allow review and rollback if needed
