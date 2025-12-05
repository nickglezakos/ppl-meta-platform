# Triggers Feature - Backend to Frontend Integration

## Overview
Successfully implemented a complete triggers management system with REST API backend and Flutter frontend integration.

## Backend Implementation (ppl-meta-media service)

### 1. Database Model
**File**: `/ppl-meta-media/src/models/trigger.py`

**Enums:**
- `PersonCountOperator`: less_than, more_than, equals, between
- `AgeRange`: underage (<18), adults (18-64), seniors (65+), all
- `TriggerAction`: alert, email, webhook, log

**Fields:**
- `id` (int): Primary key
- `uuid` (UUID): Public identifier (unique, indexed)
- `person_count_operator` (Enum): Comparison operator
- `person_count_value` (String 50): Value/range (e.g., "10" or "10-20")
- `age_range` (Enum): Age filter
- `gender_filter` (String 50, nullable): Gender criteria
- `time_span` (String 100): Time conditions (e.g., "Mon-Fri 09:00-17:00")
- `media_source_uuid` (UUID, indexed): Reference to camera/collection
- `media_source_name` (String 255, nullable): Friendly name
- `action` (Enum): Trigger action type
- `action_config` (String 500, nullable): JSON configuration for action
- `is_active` (Boolean, indexed): Enable/disable trigger
- `name` (String 255, nullable): Trigger name
- `description` (String 500, nullable): Trigger description
- `created_at` (DateTime): Creation timestamp
- `updated_at` (DateTime, nullable): Last update timestamp

### 2. API Schemas
**File**: `/ppl-meta-media/src/schemas/trigger.py`

**Schemas:**
- `TriggerBase`: Base schema with all fields and validators
- `TriggerCreate`: For POST requests (creates new trigger)
- `TriggerUpdate`: For PUT requests (all fields optional)
- `TriggerResponse`: Response model with ID and timestamps
- `TriggerListResponse`: Paginated list with metadata

### 3. REST API Endpoints
**File**: `/ppl-meta-media/src/routes/triggers.py`

**Endpoints:**
```
POST   /api/v1/triggers              - Create new trigger
GET    /api/v1/triggers              - List triggers (paginated, filterable)
GET    /api/v1/triggers/{uuid}       - Get single trigger
PUT    /api/v1/triggers/{uuid}       - Update trigger
PATCH  /api/v1/triggers/{uuid}/toggle - Toggle active status
DELETE /api/v1/triggers/{uuid}       - Delete trigger
GET    /api/v1/triggers/stats/summary - Get statistics
```

**Query Parameters (List endpoint):**
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 50)
- `is_active` (bool): Filter by active status
- `action` (string): Filter by action type

### 4. Database Migration
**File**: `/ppl-meta-media/src/alembic/versions/add_triggers_table.py`

**Migration includes:**
- Creates `triggers` table with all columns
- Creates PostgreSQL enums: personcountoperator, agerange, triggeraction
- Creates indexes on: uuid (unique), is_active, media_source_uuid
- Provides downgrade to remove table and enums

**⚠️ ACTION REQUIRED**: Before running migration, update `down_revision` in the migration file to point to the latest migration in the database.

### 5. Router Registration
**File**: `/ppl-meta-media/src/main.py`

**Changes:**
- Line 21: Added `from src.routes.triggers import router as triggers_router`
- Line 43: Added `from src.models.trigger import Trigger` (for table creation)
- Line 300: Added `app.include_router(triggers_router)`

## Frontend Implementation (ppl-meta-frontend)

### 1. Data Model
**File**: `/ppl-meta-frontend/lib/models/trigger_model.dart`

**Classes:**
- `TriggerModel`: Main trigger entity with all fields
- `TriggerCreateRequest`: Request model for creating triggers
- `TriggerListResponse`: Paginated list response

**Helper Properties:**
- `personCountDisplay`: Formats operator + value for display
- `ageRangeDisplay`: Human-readable age range labels

### 2. API Service
**File**: `/ppl-meta-frontend/lib/services/trigger_service.dart`

**Methods:**
```dart
fetchTriggers({page, pageSize, isActive, action})  // GET list
fetchTrigger(uuid)                                  // GET single
createTrigger(request)                              // POST
updateTrigger(uuid, request)                        // PUT
toggleTrigger(uuid)                                 // PATCH
deleteTrigger(uuid)                                 // DELETE
fetchStats()                                        // GET stats
```

### 3. Configuration
**File**: `/ppl-meta-frontend/lib/core/config.dart`

Defines service URLs:
- `mediaServiceUrl`: http://localhost:8000
- Other service URLs for future use

### 4. UI Widget
**File**: `/ppl-meta-frontend/lib/widgets/triggers_tab.dart`

**Features:**
- Stateful widget with lifecycle management
- Automatic data loading on init
- Responsive layout (DataTable for desktop, Cards for mobile)
- Filter by active/inactive status
- Pagination support
- Toggle active status (clickable badge)
- Delete with confirmation dialog
- Loading states
- Error handling with retry
- Empty state message

**Actions:**
- ✅ List triggers (with pagination)
- ✅ Toggle active/inactive status
- ✅ Delete trigger (with confirmation)
- 🔄 Create trigger (placeholder - dialog to be implemented)
- 🔄 Edit trigger (placeholder - dialog to be implemented)

### 5. Screen Integration
**File**: `/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`

**Changes:**
- Added import: `import '../widgets/triggers_tab.dart';`
- Replaced `_buildTriggersTab()` method to return `TriggersTab()` widget
- Removed old hardcoded trigger data and helper methods

## Deployment Steps

### Backend Deployment

1. **Update Migration File:**
   ```bash
   cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-media
   
   # Find the latest migration
   ls -la src/alembic/versions/
   
   # Edit add_triggers_table.py and update down_revision
   # Set it to the revision ID of the latest migration
   ```

2. **Run Migration:**
   ```bash
   # Activate virtual environment
   source venv/bin/activate
   
   # Run migration
   alembic upgrade head
   
   # Verify table created
   psql -d your_database -c "\d triggers"
   ```

3. **Restart Media Service:**
   ```bash
   # Use VS Code task or manual restart
   # The service should pick up the new routes automatically
   ```

### Frontend Deployment

1. **Generate JSON Code (Already done):**
   ```bash
   cd /Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend
   flutter packages pub run build_runner build --delete-conflicting-outputs
   ```

2. **Run Frontend:**
   ```bash
   # Use VS Code task: "📱 Start Frontend (Web)"
   # Or manually:
   flutter run -d chrome --web-port 3000
   ```

3. **Verify Integration:**
   - Navigate to Collections -> Vision tab -> Triggers
   - Should see loading spinner initially
   - If no triggers exist, should see empty state message
   - Create, toggle, delete operations should work

## Testing Checklist

### Backend Tests
- [ ] Create trigger via POST /api/v1/triggers
- [ ] List triggers via GET /api/v1/triggers
- [ ] Get single trigger via GET /api/v1/triggers/{uuid}
- [ ] Update trigger via PUT /api/v1/triggers/{uuid}
- [ ] Toggle status via PATCH /api/v1/triggers/{uuid}/toggle
- [ ] Delete trigger via DELETE /api/v1/triggers/{uuid}
- [ ] Pagination works (page, page_size parameters)
- [ ] Filtering works (is_active, action parameters)
- [ ] Statistics endpoint returns correct counts

### Frontend Tests
- [ ] Triggers tab loads without errors
- [ ] Loading spinner shows during data fetch
- [ ] Error message displays on API failure with retry button
- [ ] Empty state shows when no triggers exist
- [ ] Triggers list displays correctly (desktop DataTable view)
- [ ] Triggers list displays correctly (mobile Cards view)
- [ ] Active/inactive badges are clickable and toggle status
- [ ] Delete button shows confirmation dialog
- [ ] Delete operation removes trigger from list
- [ ] Filter dropdown changes displayed triggers
- [ ] Pagination controls work (if > 50 triggers)
- [ ] Create button shows placeholder message
- [ ] Edit button shows placeholder message

## Known Limitations & TODOs

### Frontend
1. **Create Dialog**: Not yet implemented
   - Need form with fields for all trigger properties
   - Validation for required fields
   - Dropdown selectors for enums

2. **Edit Dialog**: Not yet implemented
   - Similar to create dialog but pre-populated
   - Should fetch current trigger data

3. **Advanced Filtering**: 
   - Currently only filters by active/inactive
   - Could add filters for action type, media source, etc.

4. **Real-time Updates**:
   - No WebSocket integration yet
   - Manual refresh required to see changes from other users

### Backend
1. **Authentication**: No auth/authorization implemented
2. **Validation**: Could add more complex validation rules
3. **Action Execution**: Trigger actions (alert, email, etc.) not implemented
4. **Webhooks**: No webhook execution logic
5. **Monitoring**: No metrics/logging for trigger execution

## API Examples

### Create Trigger
```bash
curl -X POST http://localhost:8000/api/v1/triggers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Traffic Alert",
    "person_count_operator": "more_than",
    "person_count_value": "10",
    "age_range": "all",
    "gender_filter": "Any",
    "time_span": "Mon-Fri 09:00-17:00",
    "media_source_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "media_source_name": "Camera 01",
    "action": "alert",
    "is_active": true
  }'
```

### List Triggers
```bash
# All triggers
curl http://localhost:8000/api/v1/triggers

# Only active triggers
curl "http://localhost:8000/api/v1/triggers?is_active=true"

# Page 2 with 20 items
curl "http://localhost:8000/api/v1/triggers?page=2&page_size=20"
```

### Toggle Status
```bash
curl -X PATCH http://localhost:8000/api/v1/triggers/550e8400-e29b-41d4-a716-446655440000/toggle
```

### Delete Trigger
```bash
curl -X DELETE http://localhost:8000/api/v1/triggers/550e8400-e29b-41d4-a716-446655440000
```

## Architecture Notes

### Why Separate Widget?
The `TriggersTab` was implemented as a separate stateful widget instead of inline in the screen for:
1. **State Management**: Easier to manage loading/error states
2. **Reusability**: Can be used in other screens if needed
3. **Testability**: Easier to write unit tests
4. **Code Organization**: Keeps the detail screen clean
5. **Lifecycle**: Independent lifecycle from parent screen

### Why UUID Instead of ID?
- UUIDs used for public API to avoid exposing internal database IDs
- Prevents ID enumeration attacks
- Allows distributed systems to generate IDs without coordination
- More secure for public-facing APIs

### Why String for person_count_value?
- Supports both single values ("10") and ranges ("10-20")
- More flexible than separate min/max integer fields
- Easier to display in UI
- Validation happens at API level

## Version Information
- **Backend Version**: Python 3.8+, FastAPI, SQLAlchemy, Alembic
- **Frontend Version**: Flutter 3.x, Dart 3.x
- **Database**: PostgreSQL with UUID extension
- **Status**: ✅ Backend Complete, ✅ Frontend Complete, ⏸️ Migration Pending

## Next Steps
1. ✅ Update migration `down_revision`
2. ✅ Run Alembic migration
3. ✅ Test API endpoints
4. ✅ Test frontend integration
5. 🔄 Implement Create Trigger dialog
6. 🔄 Implement Edit Trigger dialog
7. 🔄 Add trigger action execution logic
