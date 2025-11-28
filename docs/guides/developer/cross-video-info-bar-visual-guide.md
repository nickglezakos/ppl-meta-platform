# Cross-Video Analysis Information Bar - Visual Guide

## Screen Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Person Objects Detail Screen                     │
│                     (Cross-Video Analysis Mode)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                   NEW: Information Bar                        │ │
│  │                   (Responsive Layout)                         │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │  Large Screen (≥ 500px):                                     │ │
│  │  📅 From: Nov 28, 2025 10:00  |  📅 To: Nov 28, 2025 12:00  │ │
│  │  |  📹 Collection: usb_camera_0                              │ │
│  │                                                               │ │
│  │  Small Screen (< 500px):                                     │ │
│  │  📅 From: Nov 28, 2025 10:00                                 │ │
│  │  📅 To: Nov 28, 2025 12:00                                   │ │
│  │  📹 Collection: usb_camera_0                                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ [Individuals] [Routes] [Statistics] [Best Faces] ← Tabs      │ │
│  ├───────────────────────────────────────────────────────────────┤ │
│  │                                                               │ │
│  │                  Tab Content Area                             │ │
│  │                                                               │ │
│  │  (Shows individuals, routes, statistics, or best faces        │ │
│  │   based on selected tab)                                      │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Collections Screen                          │
│                   (http://localhost:3000/#/collections)             │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ User selects date range,
                               │ collection, and clicks
                               │ "Analysis" button
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              _fetchIndividualsCount() Method                        │
│        (collections_screen.dart lines 905-1015)                     │
│                                                                     │
│  1. Search for videos in date range                                │
│  2. Search for MVR people in those videos                          │
│  3. Create _trackingSessionData:                                   │
│     {                                                               │
│       'search_results': [...],                                     │
│       'total_mvr_people': 11,                                      │
│       'total_appearances': 72,                                     │
│       'search_parameters': {                                       │
│         'start_time': "2025-11-01T10:00:00.000Z",                 │
│         'end_time': "2025-11-01T12:00:00.000Z",                   │
│         'collections': ["usb_camera_0"],                          │
│         'video_uuids': [...]                                       │
│       }                                                             │
│     }                                                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ _navigateToCrossVideoAnalysis()
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│          CrossVideoAnalysisContext (Model Object)                   │
│      (cross_video_analysis_models.dart lines 1-26)                  │
│                                                                     │
│  CrossVideoAnalysisContext(                                         │
│    individualUuids: mvrPersonUuids,                                │
│    sessionUuid: 'mvr_search_...',                                  │
│    sessionData: _trackingSessionData  ← Carries search params      │
│  )                                                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ Navigator.push()
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│        PersonObjectsDetailScreen (Cross-Video Mode)                 │
│      (person_objects_detail_screen.dart lines 1-4596)               │
│                                                                     │
│  _buildCrossVideoView() calls:                                      │
│    _buildCrossVideoInfoBar()  ← NEW METHOD                         │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ Extracts data
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              _buildCrossVideoInfoBar() Method                       │
│      (person_objects_detail_screen.dart lines 251-418)              │
│                                                                     │
│  1. Extract search_parameters from sessionData                     │
│  2. Parse start_time and end_time                                  │
│  3. Get collection name                                            │
│  4. Format dates (formatDate function)                             │
│  5. Build responsive layout:                                       │
│     - LayoutBuilder detects screen width                           │
│     - If ≥500px: Single row with Wrap                             │
│     - If <500px: Vertical Column                                  │
│  6. Display information with icons                                 │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               │ Renders
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      User Sees Info Bar                             │
│                                                                     │
│  📅 From: Nov 28, 2025 10:00  |  📅 To: Nov 28, 2025 12:00        │
│  |  📹 Collection: usb_camera_0                                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Responsive Behavior

### Desktop/Tablet (Width ≥ 500px)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Container (padding: 16h, 12v)                                       │
│  ├─ LayoutBuilder (detects width ≥ 500px)                           │
│  └─ Wrap (spacing: 20, runSpacing: 8)                               │
│     ├─ Row [Icon + Text] "From: ..."                                │
│     ├─ Container (divider 1x16)                                     │
│     ├─ Row [Icon + Text] "To: ..."                                  │
│     ├─ Container (divider 1x16)                                     │
│     └─ Row [Icon + Text] "Collection: ..."                          │
└──────────────────────────────────────────────────────────────────────┘

Width Available: 800px
Layout: [From] | [To] | [Collection]  (all in one row)
```

### Tablet Narrow (Width 400-499px)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Container (padding: 16h, 12v)                                       │
│  ├─ LayoutBuilder (detects width ≥ 500px but content wraps)         │
│  └─ Wrap (spacing: 20, runSpacing: 8)                               │
│     ├─ Row [Icon + Text] "From: ..."                                │
│     ├─ Container (divider 1x16)                                     │
│     ├─ Row [Icon + Text] "To: ..."                                  │
│     │  ↓ WRAP TO NEXT LINE (runSpacing: 8px)                        │
│     ├─ Container (divider 1x16)                                     │
│     └─ Row [Icon + Text] "Collection: ..."                          │
└──────────────────────────────────────────────────────────────────────┘

Width Available: 450px
Layout: [From] | [To]
        [Collection]  (wraps to second line)
```

### Mobile (Width < 500px)

```
┌─────────────────────────────────────────┐
│  Container (padding: 16h, 12v)          │
│  ├─ LayoutBuilder (detects width <500)  │
│  └─ Column (spacing via SizedBox: 4)    │
│     ├─ Row [Icon + Text] "From: ..."    │
│     ├─ SizedBox(height: 4)              │
│     ├─ Row [Icon + Text] "To: ..."      │
│     ├─ SizedBox(height: 4)              │
│     └─ Row [Icon + Text] "Collection..."│
└─────────────────────────────────────────┘

Width Available: 375px
Layout: (vertical stack)
  [From]
  [To]
  [Collection]
```

## Widget Tree

```
_buildCrossVideoView()
│
├─ Column
│  │
│  ├─ _buildCrossVideoInfoBar() ← NEW
│  │  │
│  │  └─ Container
│  │     ├─ padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12)
│  │     ├─ decoration: BoxDecoration
│  │     │  ├─ color: Colors.blue.shade50
│  │     │  └─ border: Border(bottom: BorderSide(...))
│  │     │
│  │     └─ child: LayoutBuilder
│  │        │
│  │        └─ builder: (context, constraints)
│  │           │
│  │           ├─ if (width < 500) → Column
│  │           │  ├─ Row [Icon + Text "From"]
│  │           │  ├─ SizedBox(height: 4)
│  │           │  ├─ Row [Icon + Text "To"]
│  │           │  ├─ SizedBox(height: 4)
│  │           │  └─ Row [Icon + Text "Collection"]
│  │           │
│  │           └─ else → Wrap
│  │              ├─ Row [Icon + Text "From"]
│  │              ├─ Container (divider)
│  │              ├─ Row [Icon + Text "To"]
│  │              ├─ Container (divider)
│  │              └─ Row [Icon + Text "Collection"]
│  │
│  ├─ TabBar (Individuals, Routes, Statistics, Best Faces)
│  │
│  └─ Expanded
│     └─ TabBarView
│        ├─ _buildIndividualsTabCrossVideo()
│        ├─ _buildRoutesTabCrossVideo()
│        ├─ _buildStatisticsTabCrossVideo()
│        └─ _buildFacesTabCrossVideo()
```

## Color Scheme

```
Information Bar Colors:
┌──────────────────────────────────────┐
│ Background: Colors.blue.shade50      │
│            #E3F2FD (light blue)      │
├──────────────────────────────────────┤
│ Border: Colors.blue.shade200         │
│        #90CAF9 (medium light blue)   │
├──────────────────────────────────────┤
│ Icons: Colors.blue.shade700          │
│       #1976D2 (medium blue)          │
├──────────────────────────────────────┤
│ Text: Colors.blue.shade900           │
│      #0D47A1 (dark blue)             │
├──────────────────────────────────────┤
│ Dividers: Colors.blue.shade300       │
│          #64B5F6 (medium light blue) │
└──────────────────────────────────────┘
```

## Code Snippet Example

```dart
// Example of how the bar is rendered

// Large screen (≥500px)
Container(
  padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
  decoration: BoxDecoration(
    color: Colors.blue.shade50,
    border: Border(bottom: BorderSide(color: Colors.blue.shade200)),
  ),
  child: Wrap(
    spacing: 20,
    children: [
      Row(children: [
        Icon(Icons.calendar_today, size: 16, color: Colors.blue.shade700),
        SizedBox(width: 6),
        Text('From: Nov 28, 2025 10:00', style: TextStyle(...)),
      ]),
      Container(width: 1, height: 16, color: Colors.blue.shade300),
      Row(children: [
        Icon(Icons.event, size: 16, color: Colors.blue.shade700),
        SizedBox(width: 6),
        Text('To: Nov 28, 2025 12:00', style: TextStyle(...)),
      ]),
      Container(width: 1, height: 16, color: Colors.blue.shade300),
      Row(children: [
        Icon(Icons.video_collection, size: 16, color: Colors.blue.shade700),
        SizedBox(width: 6),
        Text('Collection: usb_camera_0', style: TextStyle(...)),
      ]),
    ],
  ),
)
```

## User Journey

```
Step 1: Collections Screen
├─ User selects date range (Nov 1-28, 2025)
├─ User selects collection (usb_camera_0)
└─ User clicks "Analysis" button

Step 2: Navigation
├─ App creates CrossVideoAnalysisContext
├─ App passes sessionData with search_parameters
└─ App navigates to PersonObjectsDetailScreen

Step 3: Analysis Screen Renders
├─ Screen detects cross-video mode
├─ Calls _buildCrossVideoInfoBar()
└─ Info bar displays above tabs

Step 4: User Views Information
├─ Sees "From: Nov 1, 2025 10:00"
├─ Sees "To: Nov 28, 2025 12:00"
├─ Sees "Collection: usb_camera_0"
└─ Has context for analysis results below

Step 5: User Interacts with Tabs
├─ Clicks between [Individuals] [Routes] [Statistics] [Best Faces]
├─ Info bar remains visible at top
└─ Provides consistent context across all tabs
```

## Key Implementation Points

### 1. Data Extraction
- Source: `widget.crossVideoContext!.sessionData['search_parameters']`
- Dates: `searchParams['start_time']` and `['end_time']`
- Collection: `searchParams['collections'][0]`

### 2. Date Formatting
- Input: `"2025-11-01T10:00:00.000Z"` (ISO 8601)
- Output: `"Nov 1, 2025 10:00"` (Human-readable)

### 3. Responsive Breakpoint
- **500px**: The width threshold that switches layout
- `constraints.maxWidth < 500` → Column (vertical)
- `constraints.maxWidth ≥ 500` → Wrap (horizontal)

### 4. Text Overflow
- All Text widgets use `overflow: TextOverflow.ellipsis`
- Ensures long collection names don't break layout
- Example: "very_long_collection_name..." truncates

### 5. Icon Placement
- Icons positioned before text: `[Icon] Text`
- Consistent 6px spacing: `SizedBox(width: 6)`
- All icons same size: `size: 16`

## Testing Checklist

- [ ] Desktop: Single row layout appears correctly
- [ ] Desktop: Dividers visible between items
- [ ] Desktop: 20px spacing between items
- [ ] Tablet: Wrap behavior works when narrowing
- [ ] Mobile: Vertical layout appears on small screens
- [ ] Mobile: 4px spacing between rows
- [ ] Text: Long collection names truncate with ellipsis
- [ ] Dates: Parse correctly from ISO 8601 format
- [ ] Dates: Display in readable format
- [ ] Fallback: Shows 'N/A' if dates missing
- [ ] Fallback: Uses context.collections if search params missing
- [ ] Colors: Blue theme consistent with app
- [ ] Icons: Calendar and video collection icons display
- [ ] Alignment: Items align properly in both layouts

---

For detailed implementation information, see:
- `docs/guides/developer/cross-video-info-bar-implementation.md`
- `docs/Release Notes/v2.19.38-cross-video-info-bar.md`
