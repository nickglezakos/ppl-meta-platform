# Proposal: Archived Media Filter & Restore Flow

**Status:** Implemented   
**Date:** 2026-04-07  
**Scope:** Media service backend, gateway, Flutter frontend

---

## Problem

When media is deleted, the platform soft-deletes it (sets `is_archived = True`). The data and files remain intact, but there is no way for users to view or recover these items. Archived media is silently excluded at multiple layers:

1. **Backend** — `MediaSearchRequest` defines `is_archived: Optional[bool]` but `search_media()` never applies it as a filter. Archived items leak into raw query results but are hidden client-side.
2. **Frontend API client** — `searchMedia()` hardcodes `.where((item) => !item.isArchived)`, dropping archived items from every response.
3. **Frontend filter model** — `MediaSearchFilters` has no `isArchived` field.
4. **Frontend API client** — No `restoreMedia()` or `bulkRestoreMedia()` methods exist.
5. **Backend** — A single-item `POST /{media_id}/restore` endpoint exists and works, but there is no bulk restore endpoint.

The multi-select pattern and selection action bar already exist in `ResponsiveMediaGallery` and can be extended.

---

## Proposed Solution

### Overview

Add an "Archived" filter toggle to the gallery search. When active, the gallery shows only archived items. The user can then select items and restore them via a new action in the selection bar.

```
┌─────────────────────────────────────────────────┐
│  Search bar   [Filters ▼]   [📦 Show Archived] │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐           │
│  │ ☑   │  │     │  │ ☑   │  │     │           │
│  │     │  │     │  │     │  │     │           │
│  └─────┘  └─────┘  └─────┘  └─────┘           │
│                                                 │
├─────────────────────────────────────────────────┤
│  2 selected          [Restore]  [Select All]    │
└─────────────────────────────────────────────────┘
```

---

## Changes Required

### 1. Backend — Wire `is_archived` filter in `search_media()`

**File:** `ppl-meta-media/src/services/media_service.py` — `search_media()` method

The `is_archived` field already exists on `MediaSearchRequest` but is never read. Add the filter:

```python
# After existing filters, before sort/pagination:
if search_request.is_archived is not None:
    query = query.filter(Media.is_archived == search_request.is_archived)
else:
    # Default behavior: exclude archived items
    query = query.filter(Media.is_archived.is_(False))
```

**Behavior:**

| `is_archived` param | Result |
|---|---|
| omitted / `None` | Exclude archived (preserves current default) |
| `true` | Return **only** archived items |
| `false` | Return **only** non-archived items (explicit) |

No schema changes needed — the field is already defined.

### 2. Backend — Add bulk restore endpoint

**File:** `ppl-meta-media/src/api/v1/media.py`

```python
@router.post("/bulk-restore")
async def bulk_restore_media(
    media_ids: List[str] = Form(...),
    user_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Restore multiple archived media items."""
```

**File:** `ppl-meta-media/src/services/media_service.py`

```python
async def bulk_restore_media(self, media_ids: List[str], user_id: UUID) -> dict:
    """Restore multiple archived media items. Returns success/failure counts."""
    restored_ids = []
    failed_ids = []
    for media_id in media_ids:
        result = await self.restore_archived_media(media_id, user_id)
        if result:
            restored_ids.append(media_id)
        else:
            failed_ids.append(media_id)
    return {
        "restored_count": len(restored_ids),
        "failed_count": len(failed_ids),
        "restored_ids": restored_ids,
        "failed_ids": failed_ids,
    }
```

This mirrors the existing `bulk-delete` endpoint pattern.

### 3. Backend — Pass `is_archived` from route to search request

**File:** `ppl-meta-media/src/api/v1/media.py` — search route

Add the query parameter to the search endpoint if not already forwarded:

```python
@router.get("/search")
async def search_media(
    ...
    is_archived: Optional[bool] = Query(None),
    ...
):
```

Ensure it is passed into `MediaSearchRequest(is_archived=is_archived, ...)`.

### 4. Frontend — Add `isArchived` to `MediaSearchFilters`

**File:** `ppl-meta-frontend/lib/models/media_models.dart`

```dart
class MediaSearchFilters {
  // ... existing fields ...

  @JsonKey(name: 'is_archived')
  final bool? isArchived;

  // Update constructor, copyWith, hasFilters, ==, hashCode
}
```

Update `hasFilters` to include:
```dart
bool get hasFilters =>
    query != null ||
    mediaType != null ||
    // ... existing checks ...
    isArchived != null;
```

### 5. Frontend — Remove hardcoded archive filter from API client

**File:** `ppl-meta-frontend/lib/services/media_api_client.dart` — `searchMedia()`

Current code:
```dart
final items = (response.data as List)
    .map((json) => MediaItem.fromJson(json))
    .where((item) => !item.isArchived)  // ← remove this
    .toList();
```

Change to:
```dart
final items = (response.data as List)
    .map((json) => MediaItem.fromJson(json))
    .toList();
```

The backend will now handle archive filtering via the `is_archived` query parameter. The client no longer needs to drop items post-fetch.

Pass the filter to the API call:
```dart
if (filters?.isArchived != null) {
  queryParams['is_archived'] = filters!.isArchived.toString();
}
```

### 6. Frontend — Add `restoreMedia()` and `bulkRestoreMedia()` to API client

**File:** `ppl-meta-frontend/lib/services/media_api_client.dart`

```dart
/// Restore a single archived media item
Future<ApiResponse<MediaItem>> restoreMedia(String mediaId) async {
  final userId = await _getCurrentUserId();
  final response = await _apiClient.post(
    '/api/v1/media/$mediaId/restore',
    data: FormData.fromMap({'user_id': userId}),
  );
  return ApiResponse.success(MediaItem.fromJson(response.data));
}

/// Restore multiple archived media items
Future<ApiResponse<BulkOperationResult>> bulkRestoreMedia(
  List<String> mediaIds,
) async {
  final userId = await _getCurrentUserId();
  final response = await _apiClient.post(
    '/api/v1/media/bulk-restore',
    data: FormData.fromMap({
      'media_ids': mediaIds,
      'user_id': userId,
    }),
  );
  return ApiResponse.success(BulkOperationResult.fromJson(response.data));
}
```

### 7. Frontend — Add archive toggle to search UI

**File:** `ppl-meta-frontend/lib/widgets/advanced_search_interface.dart`

Add a toggle/chip labeled **"Show Archived"** alongside the existing filter controls. When toggled on, set `isArchived: true` in the filters and rebuild the gallery. When toggled off, set `isArchived: null` (back to default behavior that excludes archived).

```dart
FilterChip(
  label: const Text('Show Archived'),
  selected: _showArchived,
  onSelected: (value) {
    setState(() => _showArchived = value);
    _applyFilters();  // rebuilds with isArchived: value ? true : null
  },
  avatar: const Icon(Icons.archive_outlined, size: 18),
)
```

Visual cue: when the archive filter is active, tint the gallery background or show a banner:

```
┌─────────────────────────────────────────┐
│  📦 Viewing archived items              │
└─────────────────────────────────────────┘
```

### 8. Frontend — Add "Restore" action to selection bar

**File:** `ppl-meta-frontend/lib/widgets/responsive_media_gallery.dart`

Extend `_buildSelectionBar()` to show a **Restore** button when `isArchived` filter is active:

```dart
Widget _buildSelectionBar() {
  final isArchiveView = widget.filters?.isArchived == true;

  return Container(
    // ... existing layout ...
    child: Row(
      children: [
        Text('${_selectedItems.length} selected'),
        const Spacer(),
        if (isArchiveView)
          TextButton.icon(
            icon: const Icon(Icons.restore),
            label: const Text('Restore'),
            onPressed: _selectedItems.isNotEmpty ? _restoreSelected : null,
          ),
        if (!isArchiveView)
          TextButton.icon(
            icon: const Icon(Icons.delete_outline),
            label: const Text('Delete'),
            onPressed: _selectedItems.isNotEmpty ? _deleteSelected : null,
          ),
        TextButton(onPressed: _selectAll, child: const Text('Select All')),
        TextButton(onPressed: _clearSelection, child: const Text('Clear')),
      ],
    ),
  );
}
```

The restore handler:

```dart
Future<void> _restoreSelected() async {
  final confirm = await showDialog<bool>(
    context: context,
    builder: (_) => AlertDialog(
      title: const Text('Restore Media'),
      content: Text('Restore ${_selectedItems.length} item(s) from archive?'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
        ElevatedButton(onPressed: () => Navigator.pop(context, true), child: const Text('Restore')),
      ],
    ),
  );
  if (confirm != true) return;

  final result = await _mediaApiClient.bulkRestoreMedia(_selectedItems.toList());
  if (result.isSuccess) {
    _clearSelection();
    _refreshItems();  // re-fetch — restored items will no longer appear in archive view
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${result.data!.restoredCount} item(s) restored')),
    );
  }
}
```

---

## User Flow

```
1.  User opens media gallery
2.  User taps "Show Archived" filter chip
3.  Gallery reloads with is_archived=true → shows only soft-deleted items
4.  A banner "Viewing archived items" appears above the grid
5.  User long-presses to enter selection mode
6.  User selects one or more items
7.  Selection bar shows: "3 selected   [Restore]  [Select All]  [Clear]"
8.  User taps "Restore"
9.  Confirmation dialog: "Restore 3 item(s) from archive?"
10. On confirm → POST /api/v1/media/bulk-restore
11. Success snackbar: "3 item(s) restored"
12. Gallery refreshes — restored items disappear from archive view
13. User toggles off "Show Archived" → sees restored items in normal gallery
```

---

## Data Flow

```
Frontend                          Gateway                     Media Service
────────                          ───────                     ─────────────
GET /search?is_archived=true  →   proxy pass-through      →   search_media()
                                                               ├─ filter: is_archived == True
                                                               ├─ filter: uploaded_by == user
                                                               └─ return archived items only
                              ←   List[MediaResponse]      ←

POST /bulk-restore            →   proxy pass-through      →   bulk_restore_media()
  { media_ids, user_id }                                       ├─ for each id:
                                                               │   ├─ is_archived = False
                                                               │   ├─ processing_status = COMPLETED
                                                               │   ├─ clear archive_* fields
                                                               │   └─ commit
                                                               └─ return counts
                              ←   { restored_count, ... }  ←
```

---

## Edge Cases

| Scenario | Handling |
|---|---|
| Restore item that is not archived | `restore_archived_media()` already handles this — returns the item unchanged |
| Restore item owned by another user | Ownership check (`uploaded_by != user_id`) returns `None` → counted as failed |
| Bulk restore with mixed valid/invalid IDs | Returns per-item success/failure counts and ID lists |
| Archive filter + other filters combined | All filters apply together — e.g., show only archived videos from January |
| No archived items exist | Gallery shows empty state — same as any empty search result |
| Concurrent restore by same user | Idempotent — restoring an already-restored item succeeds silently |

---

## Migration Risk

**None.** All changes are additive:

- The `is_archived` field already exists on the backend schema — only the query logic needs wiring
- The restore endpoint already exists — only bulk restore and frontend calls are new
- The default search behavior (exclude archived) is preserved when `is_archived` is omitted
- The frontend hardcoded filter removal is safe because the backend default now handles it
- No database migrations required
