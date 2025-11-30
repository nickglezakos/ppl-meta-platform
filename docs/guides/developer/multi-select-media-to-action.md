# Multi-Select Media to Action - Developer Guide

**Document Version**: 1.0  
**Date**: November 29, 2025  
**Feature**: Multi-Select Media Management  
**Location**: `http://localhost:3000/#/collections`  
**Service**: Media Service (port 8000)

---

## Table of Contents

1. [Overview](#overview)
2. [User Interface Flow](#user-interface-flow)
3. [Frontend Architecture](#frontend-architecture)
4. [State Management](#state-management)
5. [Media Selection](#media-selection)
6. [Bulk Actions](#bulk-actions)
7. [Backend API Endpoints](#backend-api-endpoints)
8. [Implementation Details](#implementation-details)
9. [Error Handling](#error-handling)
10. [Performance Considerations](#performance-considerations)
11. [Future Enhancements](#future-enhancements)

---

## Overview

The **Multi-Select Media to Action** feature provides users with a powerful interface for performing bulk operations on media files within collections. This functionality is built into the collections view and enables efficient management of multiple media items simultaneously.

### Key Features

- **Multi-Select Mode**: Toggle-able selection mode for media items
- **Visual Feedback**: Selected media items are visually highlighted
- **Bulk Operations**: Perform actions on multiple media simultaneously
- **Action Menu**: Bottom-right floating action button with available operations
- **Collection Management**: Move media between collections in bulk
- **Delete Operations**: Remove multiple media items at once
- **Metadata Updates**: Update metadata for multiple media items
- **Download**: Batch download selected media

### User Experience Goals

1. **Efficiency**: Reduce time to manage multiple media items
2. **Clarity**: Clear visual indication of selection state
3. **Safety**: Confirmation dialogs for destructive operations
4. **Feedback**: Progress indicators for long-running operations
5. **Flexibility**: Support various bulk operations

---

## User Interface Flow

### Step 1: Navigate to Collections

**URL**: `http://localhost:3000/#/collections`

**Initial State**:
- Grid/list view of media items in collection
- Multi-select icon visible in top-right navigation
- No media selected
- Action button hidden

```
┌─────────────────────────────────────────────────────────┐
│  Collections                              [⬚] Multi-Select │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │
│   │ Media  │  │ Media  │  │ Media  │  │ Media  │      │
│   │   1    │  │   2    │  │   3    │  │   4    │      │
│   └────────┘  └────────┘  └────────┘  └────────┘      │
│                                                          │
│   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │
│   │ Media  │  │ Media  │  │ Media  │  │ Media  │      │
│   │   5    │  │   6    │  │   7    │  │   8    │      │
│   └────────┘  └────────┘  └────────┘  └────────┘      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

### Step 2: Enable Multi-Select Mode

**Action**: User taps the multi-select icon (top-right)

**UI Changes**:
1. Multi-select icon changes to "selected/active" state (highlighted)
2. Selection checkboxes appear on each media card
3. Bottom-right action button becomes visible (disabled until selection)
4. Visual overlay/border indicates "selection mode active"

```
┌─────────────────────────────────────────────────────────┐
│  Collections                              [☑] Multi-Select │
├─────────────────────────────────────────────────────────┤
│  Selection Mode Active - Tap media to select            │
│                                                          │
│   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │
│   │☐ Media │  │☐ Media │  │☐ Media │  │☐ Media │      │
│   │   1    │  │   2    │  │   3    │  │   4    │      │
│   └────────┘  └────────┘  └────────┘  └────────┘      │
│                                                          │
│   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │
│   │☐ Media │  │☐ Media │  │☐ Media │  │☐ Media │      │
│   │   5    │  │   6    │  │   7    │  │   8    │      │
│   └────────┘  └────────┘  └────────┘  └────────┘      │
│                                                          │
│                                              [⚫] Actions │
│                                              (disabled)  │
└─────────────────────────────────────────────────────────┘
```

**Frontend State**:
```javascript
{
  multiSelectMode: true,
  selectedMediaIds: [],
  isActionButtonVisible: true,
  isActionButtonEnabled: false
}
```

---

### Step 3: Select Media Items

**Action**: User taps on media cards to select/deselect

**UI Changes**:
1. Selected media cards show checked checkbox (☑)
2. Selected media cards have visual highlight (border, background color)
3. Selection counter appears (e.g., "3 items selected")
4. Action button becomes enabled when at least one item selected
5. Tapping again deselects the media

```
┌─────────────────────────────────────────────────────────┐
│  Collections                              [☑] Multi-Select │
├─────────────────────────────────────────────────────────┤
│  3 items selected                                        │
│                                                          │
│   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │
│   │☑ Media │  │☐ Media │  │☑ Media │  │☐ Media │      │
│   │   1    │  │   2    │  │   3    │  │   4    │      │
│   └────────┘  └────────┘  └────────┘  └────────┘      │
│   [selected]              [selected]                    │
│                                                          │
│   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │
│   │☐ Media │  │☑ Media │  │☐ Media │  │☐ Media │      │
│   │   5    │  │   6    │  │   7    │  │   8    │      │
│   └────────┘  └────────┘  └────────┘  └────────┘      │
│              [selected]                                 │
│                                                          │
│                                              [●] Actions │
│                                              (enabled)   │
└─────────────────────────────────────────────────────────┘
```

**Frontend State**:
```javascript
{
  multiSelectMode: true,
  selectedMediaIds: [
    'media-uuid-1',
    'media-uuid-3',
    'media-uuid-6'
  ],
  isActionButtonVisible: true,
  isActionButtonEnabled: true
}
```

---

### Step 4: Open Actions Menu

**Action**: User taps the floating action button (bottom-right)

**UI Changes**:
1. Action menu opens (modal, dropdown, or bottom sheet)
2. Available actions listed based on context
3. Some actions may be disabled based on selection

```
┌─────────────────────────────────────────────────────────┐
│  Collections                              [☑] Multi-Select │
├─────────────────────────────────────────────────────────┤
│  3 items selected                                        │
│                                                          │
│   ┌────────┐  ┌────────┐  ┌────────┐                   │
│   │☑ Media │  │☐ Media │  │☑ Media │  ┌──────────────┐ │
│   │   1    │  │   2    │  │   3    │  │ Actions Menu │ │
│   └────────┘  └────────┘  └────────┘  ├──────────────┤ │
│                                         │ 📁 Move to   │ │
│   ┌────────┐  ┌────────┐  ┌────────┐  │ 📋 Copy to   │ │
│   │☐ Media │  │☑ Media │  │☐ Media │  │ 🏷️  Tag      │ │
│   │   5    │  │   6    │  │   7    │  │ ⬇️  Download │ │
│   └────────┘  └────────┘  └────────┘  │ 🗑️  Delete   │ │
│                                         │ ℹ️  Details  │ │
│                                         └──────────────┘ │
│                                              [●] Actions │
└─────────────────────────────────────────────────────────┘
```

**Available Actions**:
1. **Move to Collection** - Transfer media to different collection
2. **Copy to Collection** - Duplicate media to another collection
3. **Add Tags** - Bulk tag assignment
4. **Download** - Batch download selected media
5. **Delete** - Remove selected media (with confirmation)
6. **View Details** - Show aggregated metadata
7. **Export** - Export media with metadata
8. **Share** - Generate sharing links

---

### Step 5: Execute Action - Move to Collection

**Action**: User selects "Move to Collection"

**UI Flow**:

1. **Collection Picker Dialog**:
```
┌─────────────────────────────────────────────┐
│  Move 3 Items to Collection                 │
├─────────────────────────────────────────────┤
│                                             │
│  Select destination collection:             │
│                                             │
│  ○ Camera Feed - Kitchen                    │
│  ○ Camera Feed - Living Room                │
│  ● Camera Feed - Garage  ← Selected         │
│  ○ Archive - November 2025                  │
│  ○ Important Events                         │
│                                             │
│  [ Create New Collection ]                  │
│                                             │
├─────────────────────────────────────────────┤
│              [Cancel]    [Move Items]       │
└─────────────────────────────────────────────┘
```

2. **Confirmation Dialog** (optional, for large operations):
```
┌─────────────────────────────────────────────┐
│  Confirm Move                                │
├─────────────────────────────────────────────┤
│                                             │
│  Move 3 media items from:                   │
│    "Camera Feed - Kitchen"                  │
│  to:                                        │
│    "Camera Feed - Garage"                   │
│                                             │
│  This action cannot be undone.              │
│                                             │
├─────────────────────────────────────────────┤
│              [Cancel]    [Confirm Move]     │
└─────────────────────────────────────────────┘
```

3. **Progress Indicator**:
```
┌─────────────────────────────────────────────┐
│  Moving Media...                             │
├─────────────────────────────────────────────┤
│                                             │
│  [████████████░░░░░░░] 66% (2/3)           │
│                                             │
│  Moving: media-file-3.mp4                   │
│                                             │
└─────────────────────────────────────────────┘
```

4. **Success Notification**:
```
┌─────────────────────────────────────────────┐
│  ✓ Successfully moved 3 items               │
│                                             │
│  Items moved to "Camera Feed - Garage"      │
│                                             │
│  [Undo]  [Dismiss]                          │
└─────────────────────────────────────────────┘
```

---

### Step 6: Exit Multi-Select Mode

**Action**: User taps multi-select icon again (or completes action)

**UI Changes**:
1. Multi-select icon returns to inactive state
2. Selection checkboxes disappear
3. Selected highlights removed
4. Action button hidden
5. UI returns to normal browsing mode

```
┌─────────────────────────────────────────────────────────┐
│  Collections                              [⬚] Multi-Select │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │
│   │ Media  │  │ Media  │  │ Media  │  │ Media  │      │
│   │   1    │  │   2    │  │   3    │  │   4    │      │
│   └────────┘  └────────┘  └────────┘  └────────┘      │
│                                                          │
│   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐      │
│   │ Media  │  │ Media  │  │ Media  │  │ Media  │      │
│   │   5    │  │   6    │  │   7    │  │   8    │      │
│   └────────┘  └────────┘  └────────┘  └────────┘      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

### Component Hierarchy

```
CollectionsPage
├── NavigationBar
│   ├── CollectionSelector
│   ├── ViewModeToggle (Grid/List)
│   └── MultiSelectToggle ← Triggers multi-select mode
├── MediaGrid / MediaList
│   └── MediaCard (multiple)
│       ├── MediaThumbnail
│       ├── MediaMetadata
│       └── SelectionCheckbox (conditional: visible in multi-select mode)
├── SelectionToolbar (conditional: visible when items selected)
│   ├── SelectionCounter ("X items selected")
│   ├── SelectAllButton
│   └── DeselectAllButton
└── FloatingActionButton (conditional: visible in multi-select mode)
    └── ActionsMenu
        ├── MoveToCollectionAction
        ├── CopyToCollectionAction
        ├── AddTagsAction
        ├── DownloadAction
        ├── DeleteAction
        └── ViewDetailsAction
```

### Technology Stack

**Frontend Framework**: Flutter (Dart)
- **State Management**: Provider / Riverpod / Bloc
- **UI Components**: Material Design / Custom widgets
- **Routing**: Flutter Navigator 2.0
- **HTTP Client**: Dio / http package

**Backend Service**: Media Service (Python FastAPI)
- **Port**: 8000
- **Database**: PostgreSQL
- **File Storage**: Local filesystem / S3
- **API Style**: RESTful

---

## State Management

### Multi-Select State

**State Container** (e.g., Provider/Riverpod):

```dart
class MultiSelectState extends ChangeNotifier {
  // Core state
  bool _isMultiSelectMode = false;
  Set<String> _selectedMediaIds = {};
  
  // Getters
  bool get isMultiSelectMode => _isMultiSelectMode;
  Set<String> get selectedMediaIds => _selectedMediaIds;
  int get selectedCount => _selectedMediaIds.length;
  bool get hasSelection => _selectedMediaIds.isNotEmpty;
  
  // Actions
  void enableMultiSelectMode() {
    _isMultiSelectMode = true;
    notifyListeners();
  }
  
  void disableMultiSelectMode() {
    _isMultiSelectMode = false;
    _selectedMediaIds.clear();
    notifyListeners();
  }
  
  void toggleMediaSelection(String mediaId) {
    if (_selectedMediaIds.contains(mediaId)) {
      _selectedMediaIds.remove(mediaId);
    } else {
      _selectedMediaIds.add(mediaId);
    }
    notifyListeners();
  }
  
  void selectAll(List<String> mediaIds) {
    _selectedMediaIds.addAll(mediaIds);
    notifyListeners();
  }
  
  void deselectAll() {
    _selectedMediaIds.clear();
    notifyListeners();
  }
  
  void selectRange(String startId, String endId, List<String> mediaIds) {
    final startIndex = mediaIds.indexOf(startId);
    final endIndex = mediaIds.indexOf(endId);
    
    if (startIndex != -1 && endIndex != -1) {
      final range = mediaIds.sublist(
        min(startIndex, endIndex),
        max(startIndex, endIndex) + 1
      );
      _selectedMediaIds.addAll(range);
      notifyListeners();
    }
  }
}
```

### UI State Integration

**CollectionsPage Widget**:

```dart
class CollectionsPage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Consumer<MultiSelectState>(
      builder: (context, multiSelectState, child) {
        return Scaffold(
          appBar: AppBar(
            title: Text('Collections'),
            actions: [
              // Multi-select toggle button
              IconButton(
                icon: Icon(
                  multiSelectState.isMultiSelectMode
                      ? Icons.check_box
                      : Icons.check_box_outline_blank,
                  color: multiSelectState.isMultiSelectMode
                      ? Theme.of(context).primaryColor
                      : null,
                ),
                onPressed: () {
                  if (multiSelectState.isMultiSelectMode) {
                    multiSelectState.disableMultiSelectMode();
                  } else {
                    multiSelectState.enableMultiSelectMode();
                  }
                },
                tooltip: 'Multi-select mode',
              ),
            ],
          ),
          body: Column(
            children: [
              // Selection toolbar (conditional)
              if (multiSelectState.hasSelection)
                SelectionToolbar(
                  selectedCount: multiSelectState.selectedCount,
                  onSelectAll: () => multiSelectState.selectAll(allMediaIds),
                  onDeselectAll: () => multiSelectState.deselectAll(),
                ),
              
              // Media grid
              Expanded(
                child: MediaGrid(
                  isMultiSelectMode: multiSelectState.isMultiSelectMode,
                  selectedMediaIds: multiSelectState.selectedMediaIds,
                  onMediaTap: (mediaId) {
                    if (multiSelectState.isMultiSelectMode) {
                      multiSelectState.toggleMediaSelection(mediaId);
                    } else {
                      // Normal navigation to media detail
                      Navigator.push(...);
                    }
                  },
                ),
              ),
            ],
          ),
          
          // Floating action button (conditional)
          floatingActionButton: multiSelectState.isMultiSelectMode
              ? FloatingActionButton(
                  onPressed: multiSelectState.hasSelection
                      ? () => _showActionsMenu(context, multiSelectState)
                      : null,
                  child: Icon(Icons.more_vert),
                  backgroundColor: multiSelectState.hasSelection
                      ? Theme.of(context).primaryColor
                      : Colors.grey,
                )
              : null,
        );
      },
    );
  }
  
  void _showActionsMenu(BuildContext context, MultiSelectState state) {
    showModalBottomSheet(
      context: context,
      builder: (context) => ActionsMenu(
        selectedMediaIds: state.selectedMediaIds.toList(),
        onActionComplete: () {
          state.disableMultiSelectMode();
          Navigator.pop(context);
        },
      ),
    );
  }
}
```

---

## Media Selection

### MediaCard Widget with Selection

```dart
class MediaCard extends StatelessWidget {
  final Media media;
  final bool isMultiSelectMode;
  final bool isSelected;
  final VoidCallback onTap;
  
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Card(
        elevation: isSelected ? 4 : 1,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: isSelected
              ? BorderSide(color: Theme.of(context).primaryColor, width: 3)
              : BorderSide.none,
        ),
        child: Stack(
          children: [
            // Media content
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Thumbnail
                AspectRatio(
                  aspectRatio: 16 / 9,
                  child: ClipRRect(
                    borderRadius: BorderRadius.vertical(top: Radius.circular(8)),
                    child: Image.network(
                      media.thumbnailUrl,
                      fit: BoxFit.cover,
                    ),
                  ),
                ),
                
                // Metadata
                Padding(
                  padding: EdgeInsets.all(8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        media.filename,
                        style: TextStyle(fontWeight: FontWeight.bold),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      SizedBox(height: 4),
                      Text(
                        _formatDate(media.createdAt),
                        style: TextStyle(fontSize: 12, color: Colors.grey),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            
            // Selection checkbox (conditional)
            if (isMultiSelectMode)
              Positioned(
                top: 8,
                left: 8,
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black26,
                        blurRadius: 4,
                        offset: Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Checkbox(
                    value: isSelected,
                    onChanged: (value) => onTap(),
                    activeColor: Theme.of(context).primaryColor,
                  ),
                ),
              ),
            
            // Selection overlay (conditional)
            if (isSelected)
              Positioned.fill(
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(8),
                    color: Theme.of(context).primaryColor.withOpacity(0.1),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
```

### Selection Gestures

**Single Selection**: Tap on media card
```dart
onTap: () {
  multiSelectState.toggleMediaSelection(media.id);
}
```

**Select All**: Toolbar button
```dart
onSelectAll: () {
  final allIds = mediaList.map((m) => m.id).toList();
  multiSelectState.selectAll(allIds);
}
```

**Range Selection** (Shift+Click on web, long-press on mobile):
```dart
onLongPress: (mediaId) {
  if (lastSelectedId != null) {
    multiSelectState.selectRange(lastSelectedId, mediaId, allMediaIds);
  }
}
```

---

## Bulk Actions

### Actions Menu Component

```dart
class ActionsMenu extends StatelessWidget {
  final List<String> selectedMediaIds;
  final VoidCallback onActionComplete;
  
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Actions',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              IconButton(
                icon: Icon(Icons.close),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          
          Divider(),
          
          // Action items
          ListTile(
            leading: Icon(Icons.drive_file_move),
            title: Text('Move to Collection'),
            onTap: () => _handleMoveToCollection(context),
          ),
          
          ListTile(
            leading: Icon(Icons.content_copy),
            title: Text('Copy to Collection'),
            onTap: () => _handleCopyToCollection(context),
          ),
          
          ListTile(
            leading: Icon(Icons.label),
            title: Text('Add Tags'),
            onTap: () => _handleAddTags(context),
          ),
          
          ListTile(
            leading: Icon(Icons.download),
            title: Text('Download'),
            onTap: () => _handleDownload(context),
          ),
          
          ListTile(
            leading: Icon(Icons.info),
            title: Text('View Details'),
            onTap: () => _handleViewDetails(context),
          ),
          
          Divider(),
          
          ListTile(
            leading: Icon(Icons.delete, color: Colors.red),
            title: Text('Delete', style: TextStyle(color: Colors.red)),
            onTap: () => _handleDelete(context),
          ),
        ],
      ),
    );
  }
  
  Future<void> _handleMoveToCollection(BuildContext context) async {
    // Show collection picker dialog
    final targetCollectionId = await showDialog<String>(
      context: context,
      builder: (context) => CollectionPickerDialog(),
    );
    
    if (targetCollectionId != null) {
      // Execute move operation
      await _executeMoveOperation(targetCollectionId);
      onActionComplete();
    }
  }
}
```

### Move to Collection Implementation

```dart
class MediaBulkOperations {
  final MediaService _mediaService;
  
  Future<BulkOperationResult> moveMediaToCollection({
    required List<String> mediaIds,
    required String sourceCollectionId,
    required String targetCollectionId,
    Function(int current, int total)? onProgress,
  }) async {
    final result = BulkOperationResult();
    
    try {
      // Call backend API
      final response = await _mediaService.bulkMoveMedia(
        mediaIds: mediaIds,
        sourceCollectionId: sourceCollectionId,
        targetCollectionId: targetCollectionId,
      );
      
      if (response.success) {
        result.successCount = response.movedCount;
        result.isSuccess = true;
      } else {
        result.errorMessage = response.message;
        result.failedItems = response.failedMediaIds;
      }
      
    } catch (e) {
      result.isSuccess = false;
      result.errorMessage = e.toString();
    }
    
    return result;
  }
  
  Future<BulkOperationResult> deleteMedia({
    required List<String> mediaIds,
    Function(int current, int total)? onProgress,
  }) async {
    final result = BulkOperationResult();
    
    try {
      // Call backend API
      final response = await _mediaService.bulkDeleteMedia(
        mediaIds: mediaIds,
      );
      
      if (response.success) {
        result.successCount = response.deletedCount;
        result.isSuccess = true;
      } else {
        result.errorMessage = response.message;
        result.failedItems = response.failedMediaIds;
      }
      
    } catch (e) {
      result.isSuccess = false;
      result.errorMessage = e.toString();
    }
    
    return result;
  }
}

class BulkOperationResult {
  bool isSuccess = false;
  int successCount = 0;
  int failedCount = 0;
  String? errorMessage;
  List<String> failedItems = [];
}
```

---

## Backend API Endpoints

### 1. Bulk Move Media

**Endpoint**: `POST /api/v1/media/bulk/move`

**Request**:
```json
{
  "media_ids": [
    "media-uuid-1",
    "media-uuid-2",
    "media-uuid-3"
  ],
  "source_collection_id": "collection-uuid-source",
  "target_collection_id": "collection-uuid-target"
}
```

**Response**:
```json
{
  "success": true,
  "moved_count": 3,
  "failed_count": 0,
  "failed_media_ids": [],
  "message": "Successfully moved 3 media items"
}
```

**Backend Implementation** (FastAPI):
```python
@router.post("/bulk/move")
async def bulk_move_media(
    request: BulkMoveMediaRequest,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    """Move multiple media items to a different collection"""
    
    moved_count = 0
    failed_media_ids = []
    
    for media_id in request.media_ids:
        try:
            # Update media collection
            media = db.query(Media).filter(Media.media_uuid == media_id).first()
            
            if media:
                # Remove from source collection
                if request.source_collection_id:
                    db.execute(
                        """DELETE FROM collection_media 
                           WHERE collection_id = :source_id 
                           AND media_id = :media_id""",
                        {
                            "source_id": request.source_collection_id,
                            "media_id": media_id
                        }
                    )
                
                # Add to target collection
                db.execute(
                    """INSERT INTO collection_media (collection_id, media_id)
                       VALUES (:target_id, :media_id)
                       ON CONFLICT DO NOTHING""",
                    {
                        "target_id": request.target_collection_id,
                        "media_id": media_id
                    }
                )
                
                moved_count += 1
            else:
                failed_media_ids.append(media_id)
                
        except Exception as e:
            logger.error(f"Failed to move media {media_id}: {e}")
            failed_media_ids.append(media_id)
    
    db.commit()
    
    return {
        "success": moved_count > 0,
        "moved_count": moved_count,
        "failed_count": len(failed_media_ids),
        "failed_media_ids": failed_media_ids,
        "message": f"Successfully moved {moved_count} media items"
    }
```

---

### 2. Bulk Copy Media

**Endpoint**: `POST /api/v1/media/bulk/copy`

**Request**:
```json
{
  "media_ids": ["media-uuid-1", "media-uuid-2"],
  "target_collection_id": "collection-uuid-target"
}
```

**Response**:
```json
{
  "success": true,
  "copied_count": 2,
  "failed_count": 0,
  "message": "Successfully copied 2 media items"
}
```

---

### 3. Bulk Delete Media

**Endpoint**: `DELETE /api/v1/media/bulk/delete`

**Request**:
```json
{
  "media_ids": ["media-uuid-1", "media-uuid-2", "media-uuid-3"]
}
```

**Response**:
```json
{
  "success": true,
  "deleted_count": 3,
  "failed_count": 0,
  "message": "Successfully deleted 3 media items"
}
```

---

### 4. Bulk Add Tags

**Endpoint**: `POST /api/v1/media/bulk/tags`

**Request**:
```json
{
  "media_ids": ["media-uuid-1", "media-uuid-2"],
  "tags": ["important", "review", "backup"]
}
```

**Response**:
```json
{
  "success": true,
  "tagged_count": 2,
  "failed_count": 0,
  "message": "Successfully added tags to 2 media items"
}
```

---

### 5. Bulk Download

**Endpoint**: `POST /api/v1/media/bulk/download`

**Request**:
```json
{
  "media_ids": ["media-uuid-1", "media-uuid-2", "media-uuid-3"]
}
```

**Response**: ZIP file stream with all media files

**Backend Implementation**:
```python
@router.post("/bulk/download")
async def bulk_download_media(
    request: BulkDownloadRequest,
    current_user=Depends(get_current_active_user),
    db=Depends(get_db)
):
    """Download multiple media items as a ZIP file"""
    
    import zipfile
    from io import BytesIO
    
    # Create ZIP in memory
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for media_id in request.media_ids:
            media = db.query(Media).filter(Media.media_uuid == media_id).first()
            
            if media and os.path.exists(media.file_path):
                # Add file to ZIP
                zip_file.write(media.file_path, media.filename)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=media_download_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        }
    )
```

---

## Implementation Details

### Collection Picker Dialog

```dart
class CollectionPickerDialog extends StatefulWidget {
  @override
  _CollectionPickerDialogState createState() => _CollectionPickerDialogState();
}

class _CollectionPickerDialogState extends State<CollectionPickerDialog> {
  String? _selectedCollectionId;
  List<Collection> _collections = [];
  bool _isLoading = true;
  
  @override
  void initState() {
    super.initState();
    _loadCollections();
  }
  
  Future<void> _loadCollections() async {
    try {
      final collections = await MediaService().getCollections();
      setState(() {
        _collections = collections;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      // Show error
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Select Destination Collection'),
      content: Container(
        width: double.maxFinite,
        child: _isLoading
            ? Center(child: CircularProgressIndicator())
            : ListView.builder(
                shrinkWrap: true,
                itemCount: _collections.length,
                itemBuilder: (context, index) {
                  final collection = _collections[index];
                  return RadioListTile<String>(
                    title: Text(collection.name),
                    subtitle: Text('${collection.mediaCount} items'),
                    value: collection.id,
                    groupValue: _selectedCollectionId,
                    onChanged: (value) {
                      setState(() => _selectedCollectionId = value);
                    },
                  );
                },
              ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _selectedCollectionId != null
              ? () => Navigator.pop(context, _selectedCollectionId)
              : null,
          child: Text('Move'),
        ),
      ],
    );
  }
}
```

### Progress Dialog

```dart
class ProgressDialog extends StatelessWidget {
  final String title;
  final String? currentItem;
  final int currentProgress;
  final int totalItems;
  
  double get progressPercent => currentProgress / totalItems;
  
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(title),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          LinearProgressIndicator(value: progressPercent),
          SizedBox(height: 16),
          Text('$currentProgress / $totalItems'),
          if (currentItem != null) ...[
            SizedBox(height: 8),
            Text(
              currentItem!,
              style: TextStyle(fontSize: 12, color: Colors.grey),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }
}
```

---

## Error Handling

### User-Facing Error Messages

**Network Errors**:
```dart
"Unable to connect to server. Please check your internet connection."
```

**Permission Errors**:
```dart
"You don't have permission to move media to this collection."
```

**Partial Success**:
```dart
"Moved 5 out of 8 items. 3 items failed (see details)."
```

**Validation Errors**:
```dart
"Cannot move media to the same collection."
```

### Error Handling Strategy

```dart
try {
  final result = await MediaBulkOperations().moveMediaToCollection(
    mediaIds: selectedIds,
    sourceCollectionId: currentCollection.id,
    targetCollectionId: targetCollection.id,
  );
  
  if (result.isSuccess) {
    // Show success notification
    _showSuccessNotification(
      'Successfully moved ${result.successCount} items',
    );
  } else {
    // Show error with details
    _showErrorDialog(
      title: 'Move Failed',
      message: result.errorMessage ?? 'Unknown error occurred',
      failedItems: result.failedItems,
    );
  }
  
} on NetworkException catch (e) {
  _showErrorSnackbar('Network error: ${e.message}');
} on PermissionException catch (e) {
  _showErrorSnackbar('Permission denied: ${e.message}');
} catch (e) {
  _showErrorSnackbar('Unexpected error: ${e.toString()}');
}
```

### Retry Logic

```dart
Future<T> _retryOperation<T>(
  Future<T> Function() operation,
  {int maxRetries = 3}
) async {
  int attempt = 0;
  
  while (attempt < maxRetries) {
    try {
      return await operation();
    } catch (e) {
      attempt++;
      if (attempt >= maxRetries) rethrow;
      
      // Exponential backoff
      await Future.delayed(Duration(seconds: pow(2, attempt).toInt()));
    }
  }
  
  throw Exception('Max retries exceeded');
}
```

---

## Performance Considerations

### Optimization Strategies

**1. Virtual Scrolling**:
- Render only visible media cards
- Lazy load thumbnails
- Recycle card widgets

```dart
ListView.builder(
  itemCount: mediaList.length,
  itemBuilder: (context, index) {
    return MediaCard(media: mediaList[index]);
  },
)
```

**2. Thumbnail Caching**:
- Cache decoded images in memory
- Use cached_network_image package
- Progressive loading (placeholder → low-res → high-res)

```dart
CachedNetworkImage(
  imageUrl: media.thumbnailUrl,
  placeholder: (context, url) => ShimmerLoading(),
  errorWidget: (context, url, error) => Icon(Icons.error),
  memCacheHeight: 200,
  memCacheWidth: 200,
)
```

**3. Batch API Requests**:
- Process media in batches of 50-100 items
- Parallel processing with rate limiting

```python
async def bulk_move_media_batched(media_ids, target_collection_id):
    batch_size = 100
    batches = [media_ids[i:i+batch_size] for i in range(0, len(media_ids), batch_size)]
    
    results = []
    for batch in batches:
        result = await move_media_batch(batch, target_collection_id)
        results.append(result)
    
    return aggregate_results(results)
```

**4. Optimistic UI Updates**:
- Update UI immediately
- Rollback on error

```dart
// Optimistically update UI
setState(() {
  mediaList.removeWhere((m) => selectedIds.contains(m.id));
});

try {
  await MediaService().bulkDeleteMedia(selectedIds);
} catch (e) {
  // Rollback on error
  setState(() {
    mediaList.addAll(deletedMedia);
  });
  _showError('Failed to delete media');
}
```

### Performance Metrics

| Operation | Target Time | Acceptable Time |
|-----------|-------------|-----------------|
| Enable multi-select mode | < 100ms | < 300ms |
| Select single media | < 50ms | < 100ms |
| Select all (100 items) | < 200ms | < 500ms |
| Open actions menu | < 100ms | < 200ms |
| Move 10 items | < 2s | < 5s |
| Move 100 items | < 10s | < 20s |
| Delete 10 items | < 2s | < 5s |

---

## Future Enhancements

### 1. Advanced Selection Features

**Select by Criteria**:
- Select all media from specific date range
- Select by file type (images, videos)
- Select by tag
- Select by face detection results

```dart
void selectByDateRange(DateTime start, DateTime end) {
  final mediaInRange = mediaList.where(
    (m) => m.createdAt.isAfter(start) && m.createdAt.isBefore(end)
  );
  multiSelectState.selectAll(mediaInRange.map((m) => m.id).toList());
}
```

### 2. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl/Cmd + A | Select all |
| Ctrl/Cmd + D | Deselect all |
| Ctrl/Cmd + I | Invert selection |
| Shift + Click | Range select |
| Escape | Exit multi-select mode |

### 3. Drag and Drop

- Drag selected media to collection in sidebar
- Visual feedback during drag
- Drop zones for collections

### 4. Smart Batching

- Automatically batch large operations
- Show estimated time
- Allow pause/resume

### 5. Undo/Redo

- Undo move operations
- Undo delete (with time limit)
- Redo queue

```dart
class UndoManager {
  final List<UndoableAction> _undoStack = [];
  final List<UndoableAction> _redoStack = [];
  
  Future<void> executeAction(UndoableAction action) async {
    await action.execute();
    _undoStack.add(action);
    _redoStack.clear();
  }
  
  Future<void> undo() async {
    if (_undoStack.isEmpty) return;
    
    final action = _undoStack.removeLast();
    await action.undo();
    _redoStack.add(action);
  }
  
  Future<void> redo() async {
    if (_redoStack.isEmpty) return;
    
    final action = _redoStack.removeLast();
    await action.execute();
    _undoStack.add(action);
  }
}
```

### 6. Multi-Select Across Pages

- Persist selection across page navigation
- Show selection count in navigation bar
- Clear selection on collection change

---

## Document Status

**Status**: Complete  
**Last Updated**: November 29, 2025  
**Author**: PPL Meta Development Team  
**Related Documents**:
- Media Service API Documentation
- Collections Management Guide
- Flutter UI Component Library

---

## Summary

The **Multi-Select Media to Action** feature provides a comprehensive solution for bulk media management:

✅ **Intuitive UI**: Toggle-based multi-select mode with clear visual feedback  
✅ **Flexible Selection**: Single tap, select all, range selection support  
✅ **Bulk Operations**: Move, copy, tag, download, delete multiple media items  
✅ **Progress Tracking**: Real-time progress indicators for long operations  
✅ **Error Handling**: Partial success support with detailed error reporting  
✅ **Performance**: Optimized for large collections with virtual scrolling and caching  

**Use this feature for**:
- Organizing media across collections
- Bulk tagging and metadata updates
- Batch downloads for offline access
- Mass cleanup and deletion operations
- Efficient media management workflows
