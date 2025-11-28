# Cross-Video Analysis Information Bar Implementation

**Date**: November 28, 2025  
**Version**: v2.19.38  
**Feature**: Responsive information bar above tabs in Cross Video Individual Analysis screen

## Overview

This document describes the implementation of a responsive information bar that displays timeframe details (from/to dates) and collection name in the Cross Video Individual Analysis screen at `http://localhost:3000/#/collections`.

## Requirements

- **Location**: Above the tabs in `PersonObjectsDetailScreen` (cross-video mode)
- **Display**: Timeframe (from date, to date) and collection name
- **Layout**: Single row on larger screens, responsive to smaller screens
- **Data Source**: `sessionData['search_parameters']` from collections screen

## Implementation Details

### File Modified

- **Path**: `ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`
- **Method Added**: `_buildCrossVideoInfoBar()`
- **Method Replaced**: Old `_buildCrossVideoHeader()` (vertical column layout)
- **Lines Changed**: ~168 lines modified

### Code Structure

```dart
Widget _buildCrossVideoView() {
  // ... loading and error states ...
  
  return Column(
    children: [
      _buildCrossVideoInfoBar(),  // NEW: Responsive info bar
      TabBar(...),                 // Existing tabs
      Expanded(child: TabBarView(...)),
    ],
  );
}
```

### Information Bar Features

#### 1. Data Extraction

The bar extracts data from `CrossVideoAnalysisContext.sessionData`:

```dart
// From search_parameters in sessionData
if (context.sessionData['search_parameters'] != null) {
  final searchParams = context.sessionData['search_parameters'] as Map<String, dynamic>;
  
  // Parse dates
  startTime = DateTime.tryParse(searchParams['start_time'].toString());
  endTime = DateTime.tryParse(searchParams['end_time'].toString());
  
  // Get collection name
  if (searchParams['collections'] is List) {
    collectionName = searchParams['collections'][0].toString();
  }
}

// Fallback to context.collections if not in search parameters
if (collectionName.isEmpty && context.collections.isNotEmpty) {
  collectionName = context.collections.first;
}
```

#### 2. Date Formatting

Human-friendly date format: `Nov 28, 2025 14:30`

```dart
String formatDate(DateTime? date) {
  if (date == null) return 'N/A';
  final monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  final month = monthNames[date.month - 1];
  final day = date.day;
  final year = date.year;
  final hour = date.hour.toString().padLeft(2, '0');
  final minute = date.minute.toString().padLeft(2, '0');
  return '$month $day, $year $hour:$minute';
}
```

#### 3. Responsive Layout

The bar uses `LayoutBuilder` to adapt to screen size:

**Large Screens (≥ 500px width):**
- Single row using `Wrap` widget
- Horizontal layout with dividers
- Format: `[📅 From: date] | [📅 To: date] | [📹 Collection: name]`
- Automatic wrapping if content exceeds width
- 20px spacing between items

**Small Screens (< 500px width):**
- Vertical column layout
- Each item on its own row with icon
- Format:
  ```
  📅 From: date
  📅 To: date
  📹 Collection: name
  ```
- 4px vertical spacing between rows
- Text truncates with ellipsis if too long

#### 4. Styling

```dart
Container(
  padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
  decoration: BoxDecoration(
    color: Colors.blue.shade50,
    border: Border(
      bottom: BorderSide(
        color: Colors.blue.shade200,
        width: 1,
      ),
    ),
  ),
  child: LayoutBuilder(...),
)
```

**Design Elements:**
- **Background**: `Colors.blue.shade50` (light blue)
- **Border**: Bottom border with `Colors.blue.shade200`
- **Icons**: 16px size, `Colors.blue.shade700`
- **Text**: 13px font size
  - Dates: `fontWeight: FontWeight.w500` (medium)
  - Collection: `fontWeight: FontWeight.w600` (semi-bold)
- **Colors**: `Colors.blue.shade900` for text
- **Dividers**: 1px width, 16px height, `Colors.blue.shade300`

#### 5. Icons Used

- **From date**: `Icons.calendar_today` (calendar icon)
- **To date**: `Icons.event` (event/date icon)
- **Collection**: `Icons.video_collection` (video collection icon)

## Data Flow

### From Collections Screen to Analysis Screen

1. **Collections Screen** (`collections_screen.dart` line 1003-1008):
   ```dart
   _trackingSessionData = {
     'search_results': mvrPeople,
     'total_mvr_people': totalResults,
     'total_appearances': totalAppearances,
     'search_parameters': searchResponse.data!['search_parameters'],
   };
   ```

2. **Navigation** (`collections_screen.dart` line 865):
   ```dart
   _navigateToCrossVideoAnalysis(
     individualUuids: mvrPersonUuids,
     sessionUuid: 'mvr_search_${DateTime.now().millisecondsSinceEpoch}',
     sessionData: _trackingSessionData!,
   );
   ```

3. **CrossVideoAnalysisContext** (`cross_video_analysis_models.dart`):
   ```dart
   class CrossVideoAnalysisContext {
     final List<String> individualUuids;
     final String sessionUuid;
     final Map<String, dynamic> sessionData;
   }
   ```

4. **Information Bar** (`person_objects_detail_screen.dart`):
   - Extracts `search_parameters` from `sessionData`
   - Parses `start_time` and `end_time`
   - Gets `collections` array
   - Displays formatted information

## sessionData Structure

```json
{
  "search_results": [...],
  "total_mvr_people": 11,
  "total_appearances": 72,
  "search_parameters": {
    "start_time": "2025-11-01T10:00:00.000Z",
    "end_time": "2025-11-01T12:00:00.000Z",
    "collections": ["usb_camera_0"],
    "video_uuids": [...]
  }
}
```

## Visual Examples

### Desktop View (Large Screen)
```
┌────────────────────────────────────────────────────────────────┐
│ 📅 From: Nov 1, 2025 10:00  |  📅 To: Nov 1, 2025 12:00  |     │
│ 📹 Collection: usb_camera_0                                     │
└────────────────────────────────────────────────────────────────┘
```

### Mobile View (Small Screen)
```
┌──────────────────────┐
│ 📅 From: Nov 1...    │
│ 📅 To: Nov 1...      │
│ 📹 Collection: us... │
└──────────────────────┘
```

## Testing Recommendations

1. **Large Screen (Desktop)**:
   - Verify single-row layout
   - Check spacing between elements (20px)
   - Confirm vertical dividers appear
   - Test wrap behavior when window narrows

2. **Medium Screen (Tablet)**:
   - Verify Wrap widget wraps gracefully
   - Check 8px run spacing when wrapped
   - Confirm text remains readable

3. **Small Screen (Mobile < 500px)**:
   - Verify vertical column layout
   - Check 4px vertical spacing
   - Confirm text truncates with ellipsis
   - Test very long collection names

4. **Data Validation**:
   - Test with valid date range
   - Test with null dates (should show 'N/A')
   - Test with empty collection name
   - Test with multiple collections (should show first)

5. **Theme Compatibility**:
   - Verify colors work in light theme
   - Check if dark theme support needed (currently uses blue shades)

## Future Enhancements

1. **Dark Theme Support**: Add theme-aware colors
2. **Multiple Collections**: Show all collections or count
3. **Click to Edit**: Make bar interactive to modify search parameters
4. **Duration Display**: Add "Duration: X days" or "X hours"
5. **Video Count**: Display number of videos in timeframe
6. **Expand/Collapse**: Allow hiding bar to maximize screen space
7. **Copy to Clipboard**: Add button to copy date range and collection info
8. **Localization**: Support different date formats based on locale

## Related Files

### Modified
- `ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`

### Referenced
- `ppl-meta-frontend/lib/models/cross_video_analysis_models.dart`
- `ppl-meta-frontend/lib/screens/collections_screen.dart`
- `ppl-meta-frontend/lib/services/media_api_client.dart`

### Documentation
- `docs/guides/developer/camera-card-mvr-counter.md` (related MVR feature)
- `docs/vision-vmeta/review/CROSS_VIDEO_INDIVIDUAL_ANALYSIS_IMPLEMENTATION.md`

## Troubleshooting

### Issue: Bar not showing dates
**Cause**: `sessionData['search_parameters']` is null or missing  
**Solution**: Check that `_trackingSessionData` is populated correctly in `collections_screen.dart` before navigation

### Issue: Collection name empty
**Cause**: `search_parameters['collections']` is empty or null  
**Solution**: Verify collection data is passed correctly from collections screen, or check `context.collections` fallback

### Issue: Dates showing 'N/A'
**Cause**: Date parsing failed or dates are null  
**Solution**: Verify date format in `search_parameters` matches ISO 8601 format (YYYY-MM-DDTHH:mm:ss.sssZ)

### Issue: Layout not responsive
**Cause**: LayoutBuilder not detecting screen size changes  
**Solution**: Check that parent widget allows proper constraint propagation

### Issue: Text overflow
**Cause**: Very long collection names or dates  
**Solution**: Verify `overflow: TextOverflow.ellipsis` is applied to Text widgets

## Version History

- **v2.19.38** (Nov 28, 2025): Initial implementation
  - Added responsive information bar
  - Replaced old vertical column header
  - Implemented LayoutBuilder for responsiveness
  - Added date formatting and icon support

## Conclusion

The information bar provides users with immediate context about their cross-video analysis search parameters. The responsive design ensures usability across all device sizes, while the clean visual design maintains consistency with the existing application theme.

The implementation extracts data from the existing `sessionData` structure without requiring backend changes, making it a purely frontend enhancement. The bar is positioned above the tabs for maximum visibility and provides essential context for understanding the analysis results displayed in the tabs below.
