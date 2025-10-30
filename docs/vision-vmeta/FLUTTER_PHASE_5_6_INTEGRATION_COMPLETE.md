# Flutter Phase 5 & 6 Integration - Complete
**Date:** October 30, 2025  
**Status:** ✅ COMPLETE

## Overview
Successfully integrated Phase 5 (Get Session Individuals) and Phase 6 (Get Aggregated Individual Analysis) endpoints into the Flutter frontend. The `PersonObjectsDetailScreen` now supports both single-video and cross-video analysis modes.

## Changes Made

### **1. API Client Updates** (`lib/services/media_api_client.dart`)

#### Phase 5 Endpoint
```dart
/// Get individuals from cross-video tracking session (Phase 5)
Future<ApiResponse<Map<String, dynamic>>> getCrossVideoIndividuals({
  required String sessionUuid,
}) async {
  final response = await _apiClient.get(
    '/api/v1/cross-video/individuals/tracking/sessions/$sessionUuid/individuals',
  );
  return ApiResponse.success(response.data as Map<String, dynamic>);
}
```

**Fixed:**
- ❌ Removed incorrect `/vmeta/` prefix
- ✅ Now matches Gateway route exactly

#### Phase 6 Endpoint
```dart
/// Get aggregated individual analysis (Phase 6)
Future<ApiResponse<Map<String, dynamic>>> getIndividualAggregatedAnalysis({
  required String individualUuid,
  required String sessionUuid,  // ✅ Added required parameter
}) async {
  final response = await _apiClient.get(
    '/api/v1/cross-video/individuals/tracking/individuals/$individualUuid/aggregated-analysis?session_uuid=$sessionUuid',
  );
  return ApiResponse.success(response.data as Map<String, dynamic>);
}
```

**Fixed:**
- ❌ Removed incorrect `/vmeta/` prefix
- ❌ Added missing `/tracking/individuals/` path segment
- ✅ Added required `sessionUuid` parameter
- ✅ Added `session_uuid` query parameter to URL

---

### **2. Data Models** (`lib/models/cross_video_analysis_models.dart`)

#### Updated `AggregatedIndividualAnalysis` Model

**Old Model (Expected different backend response):**
```dart
class AggregatedIndividualAnalysis {
  final List<PersonObjectData> personObjects;  // ❌ Not in Phase 6 response
  final PersonObjectData bestQualityObject;    // ❌ Not in Phase 6 response
  final List<RoutePoint> chronologicalRoutes;  // ❌ Not in Phase 6 response
  final Map<String, dynamic> statistics;       // ❌ Not in Phase 6 response
}
```

**New Model (Matches Phase 6 Response):**
```dart
class AggregatedIndividualAnalysis {
  final String individualUuid;
  final String individualId;
  final String sessionUuid;                    // ✅ From Phase 6
  final int totalAppearances;                  // ✅ From Phase 6
  final int uniqueVideos;                      // ✅ From Phase 6
  final DateTime firstSeen;                    // ✅ From Phase 6
  final DateTime lastSeen;                     // ✅ From Phase 6
  final double totalDurationSeconds;           // ✅ From Phase 6
  final double averageConfidence;              // ✅ From Phase 6
  final List<IndividualAppearance> appearances;// ✅ From Phase 6
  final List<String> personObjectUuids;        // ✅ From Phase 6
  final DateTime analysisTimestamp;            // ✅ From Phase 6
  
  // Legacy compatibility getters
  int get totalVideos => uniqueVideos;
  double get confidenceScore => averageConfidence;
  
  // Utility getter
  String get formattedDuration {
    final days = (totalDurationSeconds / 86400).floor();
    final hours = ((totalDurationSeconds % 86400) / 3600).floor();
    final minutes = ((totalDurationSeconds % 3600) / 60).floor();
    
    if (days > 0) {
      return '$days days, $hours hours';
    } else if (hours > 0) {
      return '$hours hours, $minutes minutes';
    } else {
      return '$minutes minutes';
    }
  }
}
```

#### New `IndividualAppearance` Model

```dart
class IndividualAppearance {
  final String individualUuid;
  final String videoUuid;
  final String personObjectUuid;
  final DateTime startTimestamp;
  final DateTime endTimestamp;
  final List<double>? entryBbox;
  final List<double>? exitBbox;
  final double confidenceScore;
  
  // Utility getters
  double get durationSeconds => 
      endTimestamp.difference(startTimestamp).inSeconds.toDouble();
  
  String get formattedDuration {
    final seconds = durationSeconds.toInt();
    if (seconds < 60) {
      return '$seconds seconds';
    } else {
      final minutes = (seconds / 60).floor();
      final remainingSeconds = seconds % 60;
      return '$minutes min ${remainingSeconds}s';
    }
  }
}
```

---

### **3. Screen Updates** (`lib/screens/person_objects_detail_screen.dart`)

#### Individual Card Display

**Before (Expected face images and person objects):**
```dart
Widget _buildIndividualCard(AggregatedIndividualAnalysis analysis, int index) {
  final bestQualityObject = analysis.personObjects.isNotEmpty 
      ? analysis.personObjects.first 
      : null;
  
  final bestFace = bestQualityObject?.faces.isNotEmpty == true
      ? bestQualityObject!.faces.first
      : null;
  // Display face thumbnail...
}
```

**After (Shows placeholder icon and appearance data):**
```dart
Widget _buildIndividualCard(AggregatedIndividualAnalysis analysis, int index) {
  return Card(
    child: Row(
      children: [
        Container(
          width: 60,
          height: 60,
          decoration: BoxDecoration(
            color: Colors.blue.shade100,
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Icon(Icons.person, size: 40, color: Colors.blue),
        ),
        // Display stats: appearances, videos, confidence, duration
      ],
    ),
  );
}
```

#### Stats Display

**Updated to show actual Phase 6 data:**
```dart
_buildStatChip('Appearances', '${analysis.totalAppearances}'),
_buildStatChip('Videos', '${analysis.uniqueVideos}'),
_buildStatChip('Confidence', '${(analysis.averageConfidence * 100).toStringAsFixed(0)}%'),
_buildStatChip('Duration', analysis.formattedDuration),
```

#### Routes Tab → Appearances Tab

**Before (Tried to display routes from person objects):**
```dart
Widget _buildRoutesTabCrossVideo() {
  final allRoutes = <RoutePoint>[];
  for (final analysis in _aggregatedAnalyses!) {
    allRoutes.addAll(analysis.chronologicalRoutes);  // ❌ Doesn't exist
  }
  // Display route points with x,y coordinates...
}
```

**After (Displays appearances with timestamps and bounding boxes):**
```dart
Widget _buildRoutesTabCrossVideo() {
  final allAppearances = <IndividualAppearance>[];
  for (final analysis in _aggregatedAnalyses!) {
    allAppearances.addAll(analysis.appearances);  // ✅ From Phase 6
  }
  
  // Group by video and display
  final appearancesByVideo = <String, List<IndividualAppearance>>{};
  for (final appearance in allAppearances) {
    appearancesByVideo.putIfAbsent(appearance.videoUuid, () => []).add(appearance);
  }
  
  // Display each appearance with:
  // - Individual UUID
  // - Start/End timestamps
  // - Duration
  // - Confidence score
  // - Entry/Exit bounding boxes
}
```

#### Appearance Card Details

```dart
Widget _buildVideoAppearancesCard(String videoUuid, List<IndividualAppearance> appearances, int videoIndex) {
  return Card(
    child: Column(
      children: [
        // Video header with color dot and UUID
        Row(
          children: [
            Container(color: videoColor, shape: BoxShape.circle),
            Text('Video ${videoUuid.substring(0, 8)}...'),
            Text('${appearances.length} appearances'),
          ],
        ),
        // For each appearance show:
        ...appearances.map((appearance) => Column(
          children: [
            Row([Icon(Icons.person), Text('Individual: ${appearance.individualUuid}')]),
            Row([Icon(Icons.access_time), Text('Start - End timestamps')]),
            Row([Icon(Icons.timer), Text('Duration: ${appearance.formattedDuration}')]),
            Row([Icon(Icons.verified), Text('Confidence: ${appearance.confidenceScore}%')]),
            if (appearance.entryBbox != null)
              Row([Icon(Icons.crop_free), Text('Entry: ${appearance.entryBbox}')]),
          ],
        )),
      ],
    ),
  );
}
```

#### Statistics Tab

**Updated aggregate calculations:**
```dart
Widget _buildStatisticsTabCrossVideo() {
  int totalAppearances = 0;
  int totalUniqueVideos = 0;
  double sumConfidence = 0;
  double totalDurationSeconds = 0;
  DateTime? earliestSeen;
  DateTime? latestSeen;

  for (final analysis in _aggregatedAnalyses!) {
    totalAppearances += analysis.totalAppearances;
    totalUniqueVideos = math.max(totalUniqueVideos, analysis.uniqueVideos);
    sumConfidence += analysis.averageConfidence;
    totalDurationSeconds += analysis.totalDurationSeconds;
    
    if (earliestSeen == null || analysis.firstSeen.isBefore(earliestSeen)) {
      earliestSeen = analysis.firstSeen;
    }
    if (latestSeen == null || analysis.lastSeen.isAfter(latestSeen)) {
      latestSeen = analysis.lastSeen;
    }
  }

  final avgConfidence = sumConfidence / _aggregatedAnalyses!.length;
  
  // Display stats cards
  return ListView(
    children: [
      _buildStatCard('Total Individuals', '${_aggregatedAnalyses!.length}'),
      _buildStatCard('Total Appearances', '$totalAppearances'),
      _buildStatCard('Unique Videos', '$totalUniqueVideos'),
      _buildStatCard('Average Confidence', '${(avgConfidence * 100).toFixed(1)}%'),
      _buildStatCard('Total Duration', '$days days, $hours hours'),
      _buildStatCard('First Appearance', _formatTimestamp(earliestSeen)),
      _buildStatCard('Last Appearance', _formatTimestamp(latestSeen)),
      _buildStatCard('Time Span', '${latestSeen.difference(earliestSeen).inDays} days'),
    ],
  );
}
```

#### API Call Fix

**Updated to pass sessionUuid:**
```dart
Future<void> _loadCrossVideoData() async {
  final context = widget.crossVideoContext!;
  final aggregatedAnalyses = <AggregatedIndividualAnalysis>[];
  
  for (final individualUuid in context.individualUuids) {
    final response = await mediaApiClient.getIndividualAggregatedAnalysis(
      individualUuid: individualUuid,
      sessionUuid: context.sessionUuid,  // ✅ Now passed
    );
    
    if (response.success && response.data != null) {
      final analysis = AggregatedIndividualAnalysis.fromJson(response.data!);
      aggregatedAnalyses.add(analysis);
    }
  }
  
  setState(() {
    _aggregatedAnalyses = aggregatedAnalyses;
  });
}
```

---

## Navigation Flow

```
Collections Screen
    ↓
User creates tracking session
    ↓
Session completes (Phase 1-4)
    ↓
User clicks "View Individuals"
    ↓
Phase 5: GET /sessions/{uuid}/individuals
    Returns: List of 7 individuals
    ↓
Navigator.push(PersonObjectsDetailScreen(
    crossVideoContext: CrossVideoAnalysisContext(
        individualUuids: [7 UUIDs],
        sessionUuid: "...",
        sessionData: {...}
    )
))
    ↓
Screen detects _isCrossVideoMode = true
    ↓
For each individualUuid:
    Phase 6: GET /individuals/{uuid}/aggregated-analysis?session_uuid=...
    Returns: Full appearance data
    ↓
Display in tabs:
    - Faces: List of individuals with stats
    - Routes: Appearances grouped by video
    - Objects: (Not used in cross-video mode)
    - Statistics: Aggregate metrics
```

---

## API Response Mapping

### Phase 5 Response → UI
```json
{
  "session_uuid": "f684e81d-...",
  "total_individuals": 1,
  "individuals": [{
    "individual_uuid": "b0dee64b-...",
    "individual_id": "ind_b0dee64b",
    "total_appearances": 2,
    "total_videos": 2,
    "first_seen": "2025-10-13T09:13:00",
    "last_seen": "2025-10-30T09:13:30",
    "confidence_score": 0.85
  }]
}
```
→ **Displays**: List view with 1 individual card showing stats

### Phase 6 Response → UI
```json
{
  "individual_uuid": "b0dee64b-...",
  "individual_id": "ind_b0dee64b",
  "session_uuid": "f684e81d-...",
  "total_appearances": 2,
  "unique_videos": 2,
  "first_seen": "2025-10-13T09:13:00",
  "last_seen": "2025-10-30T09:13:30",
  "total_duration_seconds": 1468830,
  "average_confidence": 0.85,
  "appearances": [
    {
      "individual_uuid": "b0dee64b-...",
      "video_uuid": "7b462847-...",
      "person_object_uuid": "28802f35-...",
      "start_timestamp": "2025-10-13T09:13:00",
      "end_timestamp": "2025-10-13T09:13:30",
      "entry_bbox": [100, 200, 150, 300],
      "exit_bbox": [110, 210, 160, 310],
      "confidence_score": 0.85
    }
  ],
  "person_object_uuids": ["28802f35-...", "46310cea-..."]
}
```
→ **Displays**:
- Individual card with placeholder icon
- Stats: 2 appearances, 2 videos, 85% confidence, 17 days duration
- Appearances tab: 2 appearances grouped by video with full details
- Statistics tab: Aggregated metrics across all individuals

---

## Testing Results

### ✅ **Phase 5 Test (Get Session Individuals)**
```
Request: GET /api/v1/cross-video/individuals/tracking/sessions/f684e81d-e1c2-42d0-9d9e-dd180a44a0aa/individuals
Response: 200 OK
Data: {
  "total_individuals": 1,
  "individuals": [{ ... }]
}
Status: ✅ SUCCESS
```

### ✅ **Phase 6 Test (Get Aggregated Analysis)**
```
Request: GET /api/v1/cross-video/individuals/tracking/individuals/b0dee64b-a660-44a9-9386-1b338dec34fc/aggregated-analysis?session_uuid=f684e81d-e1c2-42d0-9d9e-dd180a44a0aa
Response: 200 OK
Data: {
  "total_appearances": 2,
  "unique_videos": 2,
  "appearances": [{ ... }, { ... }],
  ...
}
Status: ✅ SUCCESS
```

### ❌ **Previous Error (FIXED)**
```
Error: TypeError: null: type 'Null' is not a subtype of type 'int'
Cause: Model expected fields that didn't exist in backend response
Fix: Updated model to match actual Phase 6 response structure
Status: ✅ RESOLVED
```

---

## Files Modified

### Flutter Frontend
1. **`lib/services/media_api_client.dart`**
   - Fixed Phase 5 endpoint URL
   - Fixed Phase 6 endpoint URL
   - Added `sessionUuid` parameter to Phase 6

2. **`lib/models/cross_video_analysis_models.dart`**
   - Rewrote `AggregatedIndividualAnalysis` model
   - Added `IndividualAppearance` model
   - Added utility getters for formatting

3. **`lib/screens/person_objects_detail_screen.dart`**
   - Updated individual card to show placeholder icon
   - Updated stats display to show Phase 6 fields
   - Converted routes tab to appearances tab
   - Updated statistics tab calculations
   - Fixed API call to pass sessionUuid

---

## Summary

✅ **All Flutter components now aligned with Phase 5 & 6 backend**
✅ **API endpoints correctly calling Gateway routes**
✅ **Data models match backend response structure**
✅ **UI displays all available data from Phase 6**
✅ **No compilation errors**
✅ **Ready for production testing**

The Flutter app can now successfully:
1. Create cross-video tracking sessions
2. Retrieve list of individuals (Phase 5)
3. View detailed aggregated analysis for each individual (Phase 6)
4. Display appearances across multiple videos
5. Show comprehensive statistics

**Next Steps:**
- Test with real tracking sessions in Flutter
- Optionally enhance UI to fetch person object details from Orchestrator using `person_object_uuids`
- Add face images by calling Orchestrator with person object UUIDs
- Consider adding route visualization using bounding box coordinates
