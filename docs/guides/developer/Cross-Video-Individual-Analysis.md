# Cross-Video Individual Analysis - Technical Documentation

## Overview

The **Cross-Video Individual Analysis** screen (accessible at `http://localhost:3000/#/collections`) is a Flutter-based UI component that displays aggregated analysis of individuals (MVR People or raw individuals) tracked across multiple videos. This document analyzes how the screen is organized, what data structure it expects, and the complete data flow from backend to UI.

---

## Table of Contents

1. [Screen Organization](#screen-organization)
2. [MVR People vs Raw Individuals](#mvr-people-vs-raw-individuals)
3. [Data Flow Architecture](#data-flow-architecture)
4. [API Endpoints](#api-endpoints)
5. [Data Structures](#data-structures)
6. [Navigation and Context](#navigation-and-context)
7. [UI Components](#ui-components)
8. [Route Data Integration](#route-data-integration)
9. [Testing Guide](#testing-guide)

---

## Screen Organization

### File Location
**Path:** `/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`

### Screen Modes

The `PersonObjectsDetailScreen` supports **two distinct modes**:

#### 1. Single-Video Mode
- **Trigger:** `mediaItem` parameter provided
- **Purpose:** Displays analysis for one specific video
- **Data Source:** Person objects from a single video file
- **Use Case:** Analyzing detections in a single recording

#### 2. Cross-Video Mode (Our Focus)
- **Trigger:** `crossVideoContext` parameter provided
- **Purpose:** Displays aggregated analysis across multiple videos
- **Data Source:** MVR People or raw individuals from search/tracking session
- **Use Case:** Analyzing the same person appearing in multiple videos

### Tab Structure

The screen is organized into **4 main tabs** (controlled by `TabController`):

1. **Individuals Tab** (Index 0)
   - Lists all detected individuals/MVR people
   - Expandable cards showing appearance details
   - Merge functionality (manual selection)
   - Demographics display (age, gender with confidence)

2. **Routes Tab** (Index 1)
   - Visual map of movement tracking
   - Scatter plot or path visualization
   - Route sampling for performance (100-point threshold)
   - Color-coded individual trajectories

3. **Face Gallery Tab** (Index 2)
   - Grid of face crops for each individual
   - Quality metrics and confidence scores
   - Face embedding visualization

4. **Statistics Tab** (Index 3)
   - **Aggregate Metrics:**
     - Total appearances across all individuals
     - Unique videos count
     - Time span (first seen → last seen)
     - Average confidence score
     - **Average route velocity** (normalized px/s)
   - **Demographics Breakdown:**
     - Gender distribution (Male/Female/Unknown)
     - Average age with confidence
   - **Search Parameters:**
     - Date/time range used for search
     - Total video duration analyzed

---

## MVR People vs Raw Individuals

### Critical Design Decision

The screen **intelligently switches** between two data types based on search results:

#### MVR People (Consolidated Mode)
**Detection Logic:**
```dart
final bool loadingMVRPeople = context.sessionData['search_results'] != null;
```

**When to Use:**
- User performs MVR search from Collections screen
- Search results contain already-merged individuals
- Each UUID represents a **unique person** (consolidated identity)

**Characteristics:**
- UUID = `mvr_people_uuid` (e.g., `8428c9f5-4723-4372-9e4f-1a703eebc52a`)
- Multiple constituent `individual_uuid`s grouped together
- Pre-computed demographics and statistics
- Higher accuracy due to face embedding similarity

#### Raw Individuals (Backwards Compatible Mode)
**Detection Logic:**
```dart
if (!loadingMVRPeople) {
  // Load individual data using session-less endpoint
}
```

**When to Use:**
- Legacy tracking sessions without MVR merge
- Direct individual UUID navigation
- Session-based tracking results

**Characteristics:**
- UUID = `individual_uuid` (unique per video detection)
- No consolidation across videos
- May contain duplicate detections of same person

---

## Data Flow Architecture

### High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Collections Screen                                 │
│  http://localhost:3000/#/collections                                │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           │ User clicks Search 🔍
                           │ Selects: Collection, Date Range
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│              MVR People Search (Backend)                             │
│  Step 1: Get videos from collection (Media Service)                 │
│  Step 2: Search MVR people in videos (VMeta Service)                │
│          POST /api/v1/mvr-people/search/by-videos                   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           │ Returns: MVR people list with appearances
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│           Collections Screen - Display Results                       │
│  • Shows: "X appearances → Y unique people"                          │
│  • Stores: _trackingSessionData with search_results                 │
│  • Enables: "Analysis" button                                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           │ User clicks "Analysis"
                           │ Extracts MVR UUIDs from search_results
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│           Navigate to PersonObjectsDetailScreen                      │
│  • Creates CrossVideoAnalysisContext                                 │
│  • Passes: individualUuids (MVR UUIDs)                              │
│  • Passes: sessionData with search_results                          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           │ Screen initializes → _loadCrossVideoData()
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│        PersonObjectsDetailScreen - Load MVR Data                     │
│  For each MVR UUID:                                                  │
│    GET /api/v1/mvr-people/mvr-person/{uuid}/analysis                │
│    • Fetches consolidated appearances across videos                  │
│    • Aggregates demographics from constituent individuals           │
│    • Calculates route velocity from movement data                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           │ Parse response into AggregatedIndividualAnalysis
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│              Render UI Components                                    │
│  Individuals Tab: Expandable cards with appearance details          │
│  Routes Tab: Movement visualization with sampling                   │
│  Statistics Tab: Aggregated metrics and demographics                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints

### Primary Endpoint: Get MVR Person Analysis

**URL:** `GET /api/v1/mvr-people/mvr-person/{mvr_person_uuid}/analysis`

**Gateway Proxy:** `http://localhost:8080/api/v1/mvr-people/mvr-person/{mvr_person_uuid}/analysis`

**VMeta Service:** `http://localhost:8008/api/v1/mvr-people/mvr-person/{mvr_person_uuid}/analysis`

#### Request Parameters

**Path Parameters:**
- `mvr_person_uuid` (required): UUID of the MVR person

**Query Parameters:**
- `start_time` (optional): ISO 8601 timestamp for filtering appearances
  - Example: `2025-11-29T08:00:00Z`
- `end_time` (optional): ISO 8601 timestamp for filtering appearances
  - Example: `2025-11-29T18:00:00Z`

#### Flutter Implementation

**File:** `ppl-meta-frontend/lib/services/media_api_client.dart`

```dart
Future<ApiResponse<Map<String, dynamic>>> getMVRPersonAnalysis({
  required String mvrPersonUuid,
  DateTime? startTime,
  DateTime? endTime,
}) async {
  // Build query parameters
  final queryParams = <String>[];
  if (startTime != null) {
    queryParams.add('start_time=${startTime.toUtc().toIso8601String()}');
  }
  if (endTime != null) {
    queryParams.add('end_time=${endTime.toUtc().toIso8601String()}');
  }
  
  final queryString = queryParams.isNotEmpty ? '?${queryParams.join('&')}' : '';
  
  final response = await _apiClient.get(
    '/api/v1/mvr-people/mvr-person/$mvrPersonUuid/analysis$queryString',
  );

  return ApiResponse.success(response.data as Map<String, dynamic>);
}
```

#### Response Structure

```json
{
  "mvr_person_uuid": "8428c9f5-4723-4372-9e4f-1a703eebc52a",
  "individual_uuids": [
    "f4c3b2a1-9876-5432-1098-abcdef123456",
    "a1b2c3d4-5678-9012-3456-fedcba987654"
  ],
  "total_appearances": 15,
  "unique_videos": 3,
  "first_seen": "2025-11-29T09:23:15.000000",
  "last_seen": "2025-11-29T14:47:32.000000",
  "average_route_velocity": 0.027428,
  "appearances": [
    {
      "individual_uuid": "f4c3b2a1-9876-5432-1098-abcdef123456",
      "video_uuid": "56ebe3bc-6b40-4850-b57a-5068ed4ebda1",
      "person_object_uuid": "po-12345",
      "start_timestamp": "2025-11-29T09:23:15.000000",
      "end_timestamp": "2025-11-29T09:25:42.000000",
      "confidence": 0.92
    }
  ],
  "demographics": {
    "gender": "Male",
    "gender_confidence": 0.89,
    "age_min": 30,
    "age_max": 40,
    "age_mean": 35.0,
    "age_confidence": 0.85
  }
}
```

### Secondary Endpoint: Get Individual Analysis (No Session)

**URL:** `GET /api/v1/mvr-people/individuals/{individual_uuid}/analysis`

**Purpose:** Fetch raw individual data without MVR consolidation

**Use Case:** Backwards compatibility when `search_results` not present

#### Flutter Implementation

```dart
Future<ApiResponse<Map<String, dynamic>>> getIndividualAnalysisNoSession({
  required String individualUuid,
  DateTime? startTime,
  DateTime? endTime,
}) async {
  // Build query parameters
  final queryParams = <String>[];
  if (startTime != null) {
    queryParams.add('start_time=${startTime.toUtc().toIso8601String()}');
  }
  if (endTime != null) {
    queryParams.add('end_time=${endTime.toUtc().toIso8601String()}');
  }
  
  final queryString = queryParams.isNotEmpty ? '?${queryParams.join('&')}' : '';
  
  final response = await _apiClient.get(
    '/api/v1/mvr-people/individuals/$individualUuid/analysis$queryString',
  );

  return ApiResponse.success(response.data as Map<String, dynamic>);
}
```

### Route Data Endpoint

**URL:** `GET /api/v1/orchestrator/person-objects/{video_uuid}`

**Gateway Proxy:** `http://localhost:8080/api/v1/orchestrator/person-objects/{video_uuid}`

**Purpose:** Fetch route points (movement tracking) for a specific video

**Response Structure:**

```json
{
  "success": true,
  "status": "completed",
  "person_groups": [
    {
      "person_id": "IND-001",
      "movement_tracking": {
        "route_points": [
          {
            "center_x": 640.5,
            "center_y": 480.2,
            "timestamp": 13.333333,
            "frame_number": 400,
            "velocity_x": 0.012,
            "velocity_y": -0.008,
            "confidence": 0.94
          }
        ]
      }
    }
  ]
}
```

**Key Details:**
- `timestamp`: Float representing seconds from video start (not ISO string)
- `center_x`, `center_y`: Absolute pixel coordinates (requires normalization)
- Used for velocity calculation and route visualization

---

## Data Structures

### CrossVideoAnalysisContext

**File:** `ppl-meta-frontend/lib/models/cross_video_analysis_models.dart`

**Purpose:** Navigation context passed from Collections screen to Analysis screen

```dart
class CrossVideoAnalysisContext {
  final List<String> individualUuids;  // MVR person UUIDs or individual UUIDs
  final String sessionUuid;             // Session identifier (can be dummy for MVR search)
  final Map<String, dynamic> sessionData;
  
  CrossVideoAnalysisContext({
    required this.individualUuids,
    required this.sessionUuid,
    required this.sessionData,
  });
  
  /// Get total videos from session data
  int get totalVideos => sessionData['total_videos'] as int? ?? 0;
  
  /// Get individuals count from session data
  int get individualsCount => sessionData['individuals_found'] as int? ?? 0;
  
  /// Get collections from session data
  List<String> get collections => 
      (sessionData['collections'] as List?)?.cast<String>() ?? [];
}
```

#### sessionData Structure (MVR Search Mode)

```dart
Map<String, dynamic> sessionData = {
  'search_results': [  // List of MVR people from search
    {
      'mvr_people_uuid': '8428c9f5-...',
      'individual_uuids': ['f4c3b2a1-...', 'a1b2c3d4-...'],
      'total_appearances': 15,
      'unique_videos': 3,
      'first_seen': '2025-11-29T09:23:15.000000',
      'last_seen': '2025-11-29T14:47:32.000000',
      'confidence_score': 0.92,
      'estimated_age': '30-40',
      'estimated_gender': 'Male',
      'appearances': [...]
    }
  ],
  'total_mvr_people': 12,
  'total_appearances': 145,
  'search_parameters': {
    'start_time': '2025-11-29T00:00:00Z',
    'end_time': '2025-11-29T23:59:59Z',
    'video_uuids': ['56ebe3bc-...', '7f1a2b3c-...'],
    'limit': 500
  },
  'collection_name': 'usb_camera_0',
  'collection_id': 'coll-12345'
}
```

### AggregatedIndividualAnalysis

**Purpose:** Flutter model for storing individual/MVR person analysis data

```dart
class AggregatedIndividualAnalysis {
  final String individualUuid;           // MVR UUID or individual UUID
  final String individualId;             // Display identifier
  final String sessionUuid;              // Session identifier
  final int totalAppearances;            // Total detections across videos
  final int uniqueVideos;                // Number of unique videos
  final DateTime firstSeen;              // Earliest appearance
  final DateTime lastSeen;               // Latest appearance
  final double totalDurationSeconds;     // Sum of all appearance durations
  final double averageConfidence;        // Mean confidence score
  final double? averageRouteVelocity;    // Normalized px/s movement speed
  final Demographics? demographics;      // Age/gender data
  final List<IndividualAppearance> appearances;
  final List<String> personObjectUuids;
  final DateTime analysisTimestamp;
}
```

### Demographics

```dart
class Demographics {
  final String? gender;              // 'Male', 'Female', or null
  final double? genderConfidence;    // 0.0 to 1.0
  final int? ageMin;                 // Minimum age estimate
  final int? ageMax;                 // Maximum age estimate
  final double? ageMean;             // Average age estimate
  final double? ageConfidence;       // 0.0 to 1.0
}
```

### IndividualAppearance

```dart
class IndividualAppearance {
  final String individualUuid;
  final String videoUuid;
  final String personObjectUuid;
  final DateTime startTimestamp;
  final DateTime endTimestamp;
  final List<double>? entryBbox;     // [x, y, width, height]
  final List<double>? exitBbox;
  final double confidenceScore;
  
  /// Get duration of this appearance in seconds
  double get durationSeconds => 
      endTimestamp.difference(startTimestamp).inSeconds.toDouble();
}
```

---

## Navigation and Context

### Step 1: Collections Screen Search

**File:** `ppl-meta-frontend/lib/screens/collections_screen.dart`

**User Flow:**
1. User selects collection (e.g., `usb_camera_0`)
2. User clicks search icon 🔍
3. User selects date/time range
4. User clicks "Apply"

**Code Execution:**

```dart
Future<void> _fetchIndividualsCount() async {
  // Step 1: Get all videos from collection within date range
  final mediaResponse = await mediaApiClient.searchMedia(
    collectionId: collectionIdentifier,
    mediaType: MediaType.video,
    startDate: _startDate,
    endDate: _endDate,
    limit: 500,
  );

  final videoUuids = mediaResponse.data!.items.map((media) => media.uuid).toList();
  
  // Step 2: Search for existing MVR people in these videos
  final searchResponse = await mediaApiClient.searchMVRPeopleByVideos(
    videoUuids: videoUuids,
    startTime: _startDate,
    endTime: _endDate,
    limit: 500,
  );

  final mvrPeople = searchResponse.data!['mvr_people'] as List<dynamic>;
  
  // Count total appearances across all MVR people
  int totalAppearances = 0;
  for (var mvr in mvrPeople) {
    totalAppearances += (mvr['total_appearances'] as int? ?? 0);
  }
  
  setState(() {
    _individualsCount = totalAppearances;      // e.g., 145
    _uniqueMvrCount = searchResponse.data!['total_results']; // e.g., 12
    _trackingSessionData = {
      'search_results': mvrPeople,
      'total_mvr_people': searchResponse.data!['total_results'],
      'total_appearances': totalAppearances,
      'search_parameters': searchResponse.data!['search_parameters'],
      'collection_name': _selectedCollection!.name,
      'collection_id': _selectedCollection!.id,
    };
  });
}
```

### Step 2: Navigate to Analysis Screen

**Triggered by:** User clicks "Analysis" button

```dart
Future<void> _navigateToIndividualAnalysis() async {
  // Extract MVR people from search results
  final mvrPeople = _trackingSessionData!['search_results'] as List<dynamic>;
  
  // Extract MVR person UUIDs (not individual UUIDs)
  final List<String> mvrPersonUuids = mvrPeople
      .map((mvr) => mvr['mvr_people_uuid'].toString())
      .toList();

  print('📊 Navigating to analysis with ${mvrPersonUuids.length} MVR people');

  // Navigate using MaterialPageRoute
  _navigateToCrossVideoAnalysis(
    individualUuids: mvrPersonUuids,  // Actually MVR person UUIDs
    sessionUuid: 'mvr_search_${DateTime.now().millisecondsSinceEpoch}',
    sessionData: _trackingSessionData!,
  );
}

void _navigateToCrossVideoAnalysis({
  required List<String> individualUuids,
  required String sessionUuid,
  required Map<String, dynamic> sessionData,
}) {
  final context = CrossVideoAnalysisContext(
    individualUuids: individualUuids,
    sessionUuid: sessionUuid,
    sessionData: sessionData,
  );
  
  Navigator.of(this.context).push(
    MaterialPageRoute(
      builder: (ctx) => PersonObjectsDetailScreen(
        crossVideoContext: context,
      ),
    ),
  );
}
```

### Step 3: Load Data in Analysis Screen

**File:** `person_objects_detail_screen.dart`

```dart
Future<void> _loadCrossVideoData() async {
  final context = widget.crossVideoContext!;
  final apiClient = ref.read(apiClientProvider);
  final mediaApiClient = MediaApiClient(apiClient);
  
  final aggregatedAnalyses = <AggregatedIndividualAnalysis>[];
  
  // Extract date range from search parameters
  DateTime? startTime;
  DateTime? endTime;
  if (context.sessionData['search_parameters'] != null) {
    final searchParams = context.sessionData['search_parameters'] as Map<String, dynamic>;
    if (searchParams['start_time'] != null) {
      startTime = DateTime.parse(searchParams['start_time'] as String);
    }
    if (searchParams['end_time'] != null) {
      endTime = DateTime.parse(searchParams['end_time'] as String);
    }
  }

  // Check if we're loading MVR people or individuals
  final bool loadingMVRPeople = context.sessionData['search_results'] != null;

  if (loadingMVRPeople) {
    print('📊 Loading MVR person data (consolidated individuals)');
    
    // For each MVR person UUID, call the MVR person endpoint
    for (final mvrPersonUuid in context.individualUuids) {
      try {
        final response = await mediaApiClient.getMVRPersonAnalysis(
          mvrPersonUuid: mvrPersonUuid,
          startTime: startTime,
          endTime: endTime,
        );
        
        if (response.success && response.data != null) {
          final data = response.data!;
          
          // Parse demographics
          Demographics? demographics;
          if (data['demographics'] != null) {
            final demoData = data['demographics'] as Map<String, dynamic>;
            demographics = Demographics(
              gender: demoData['gender'] as String?,
              genderConfidence: (demoData['gender_confidence'] as num?)?.toDouble(),
              ageMin: demoData['age_min'] as int?,
              ageMax: demoData['age_max'] as int?,
              ageMean: (demoData['age_mean'] as num?)?.toDouble(),
              ageConfidence: (demoData['age_confidence'] as num?)?.toDouble(),
            );
          }
          
          final analysis = AggregatedIndividualAnalysis(
            individualUuid: data['mvr_person_uuid'] as String,
            individualId: data['mvr_person_uuid'] as String,
            sessionUuid: context.sessionUuid,
            totalAppearances: data['total_appearances'] as int,
            uniqueVideos: data['unique_videos'] as int,
            firstSeen: DateTime.parse(data['first_seen'] as String),
            lastSeen: DateTime.parse(data['last_seen'] as String),
            totalDurationSeconds: 0.0,
            averageConfidence: 0.0,
            averageRouteVelocity: (data['average_route_velocity'] as num?)?.toDouble(),
            appearances: (data['appearances'] as List)
                .map((app) => IndividualAppearance(
                      individualUuid: app['individual_uuid'] as String,
                      videoUuid: app['video_uuid'] as String,
                      personObjectUuid: app['person_object_uuid'] as String,
                      startTimestamp: DateTime.parse(app['start_timestamp'] as String),
                      endTimestamp: DateTime.parse(app['end_timestamp'] as String),
                      confidenceScore: (app['confidence'] as num).toDouble(),
                      entryBbox: null,
                      exitBbox: null,
                    ))
                .toList(),
            personObjectUuids: (data['appearances'] as List)
                .map((app) => app['person_object_uuid'] as String)
                .toList(),
            analysisTimestamp: DateTime.now(),
            demographics: demographics,
          );

          aggregatedAnalyses.add(analysis);
          print('✅ Loaded MVR person $mvrPersonUuid: ${analysis.totalAppearances} appearances');
        }
      } catch (e) {
        print('❌ Error loading MVR person $mvrPersonUuid: $e');
      }
    }
  }
  
  setState(() {
    _aggregatedAnalyses = aggregatedAnalyses;
    _isLoadingCrossVideoData = false;
  });
}
```

---

## UI Components

### Statistics Tab Implementation

**Key Metrics Displayed:**

1. **Total Appearances**
   - Sum of all detections across all MVR people
   - Icon: `Icons.people`
   - Color: Blue

2. **Unique Videos**
   - Count of distinct videos where MVR people appeared
   - Icon: `Icons.video_library`
   - Color: Green

3. **Time Span**
   - Duration between first and last appearance
   - Formatted as: "X hours Y minutes"
   - Icon: `Icons.access_time`
   - Color: Orange

4. **Average Confidence**
   - Mean confidence score across all appearances
   - Formatted as percentage
   - Icon: `Icons.analytics`
   - Color: Purple

5. **Average Movement Velocity** (NEW in v2.19.42)
   - Normalized pixel velocity (resolution-independent)
   - Only displayed if velocity > 0
   - Formatted with 6 decimal places
   - Subtitle: "Normalized movement speed"
   - Icon: `Icons.trending_up`
   - Color: Deep Purple

#### Statistics Card Widget

```dart
Widget _buildStatCard(
  String title,
  String value,
  IconData icon,
  Color color, {
  String? subtitle,
}) {
  return Card(
    elevation: 2,
    child: Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 24),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            value,
            style: const TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 4),
            Text(
              subtitle,
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[600],
              ),
            ),
          ],
        ],
      ),
    ),
  );
}
```

### Demographics Display

**Gender Breakdown:**
- Extracted from `search_results` array in `sessionData`
- Counts Male/Female/Unknown individuals
- Displayed as pie chart or bar graph

**Age Statistics:**
- Parses age range strings (e.g., "30-40")
- Calculates mean age across all MVR people
- Shows confidence score

**Example Code:**

```dart
// Extract demographics from search results
if (widget.crossVideoContext!.sessionData['search_results'] != null) {
  final searchResults = widget.crossVideoContext!.sessionData['search_results'] as List<dynamic>;
  
  for (final mvrPerson in searchResults) {
    // Parse gender
    final gender = mvrPerson['estimated_gender'] as String?;
    if (gender != null) {
      if (gender.toLowerCase() == 'male') {
        totalMale++;
      } else if (gender.toLowerCase() == 'female') {
        totalFemale++;
      } else {
        totalUnknown++;
      }
    }
    
    // Parse age (format: "33-43")
    final ageStr = mvrPerson['estimated_age'] as String?;
    if (ageStr != null && ageStr.contains('-')) {
      final parts = ageStr.split('-');
      if (parts.length == 2) {
        final minAge = int.tryParse(parts[0]);
        final maxAge = int.tryParse(parts[1]);
        if (minAge != null && maxAge != null) {
          ages.add((minAge + maxAge) / 2.0);
        }
      }
    }
  }
}
```

---

## Route Data Integration

### Route Sampling for Performance

**Problem:** Large route datasets (1000+ points) cause rendering slowdowns

**Solution:** Adaptive sampling with 100-point threshold

**Implementation Location:** `_fetchCrossVideoRoutesData()` method

```dart
// Sample route points if there are too many (threshold: 100 points)
const maxRoutePoints = 100;
List<Map<String, dynamic>> sampledRoutePoints = allRoutePoints;

if (allRoutePoints.length > maxRoutePoints) {
  // Calculate sampling interval
  final interval = (allRoutePoints.length / maxRoutePoints).ceil();
  sampledRoutePoints = [];
  
  // Always include first and last points
  sampledRoutePoints.add(allRoutePoints.first);
  
  // Sample intermediate points
  for (int j = interval; j < allRoutePoints.length - 1; j += interval) {
    sampledRoutePoints.add(allRoutePoints[j]);
  }
  
  // Always include last point
  if (allRoutePoints.length > 1) {
    sampledRoutePoints.add(allRoutePoints.last);
  }
  
  print('📊 Sampled ${allRoutePoints.length} points down to ${sampledRoutePoints.length}');
}

// Create unified person group
personGroups.add({
  'person_id': individualId,
  'total_detections': allRoutePoints.length,      // Original count
  'sampled_points': sampledRoutePoints.length,    // Sampled count
  'movement_tracking': {
    'route_points': sampledRoutePoints,           // Use sampled for rendering
    'total_distance': 0.0,
    'movement_duration': analysis.totalDurationSeconds,
  },
});
```

**Performance Benefits:**
- 500 points → 101 points: ~5x faster rendering
- 1000 points → 101 points: ~10x faster rendering
- 5000 points → 101 points: ~50x faster rendering

**Algorithm Details:**
- **Threshold:** 100 points (configurable via `maxRoutePoints`)
- **Strategy:** Uniform interval sampling
- **Endpoint Preservation:** Always includes first and last points
- **Shape Fidelity:** Maintains route trajectory

**See also:** `/docs/guides/developer/route-sample-rendering.md` for detailed explanation

### Velocity Calculation

**Backend Implementation:**

**File:** `ppl-meta-vmeta/src/api/routes/mvr_people.py`

```python
# Fetch route data from gateway
gateway_url = os.getenv("PPL_GATEWAY_URL", "http://localhost:8080")
auth_header = request.headers.get("Authorization")

response = await client.get(
    f"{gateway_url}/api/v1/orchestrator/person-objects/{video_uuid}",
    headers={"Authorization": auth_header} if auth_header else {}
)

# Extract route points
route_points = response['person_groups'][0]['movement_tracking']['route_points']

all_route_points = []
for route_point in route_points:
    all_route_points.append({
        'x': float(route_point.get('center_x', route_point.get('x', 0))),
        'y': float(route_point.get('center_y', route_point.get('y', 0))),
        'timestamp': float(route_point['timestamp']),  # Float seconds
        'video_uuid': video_uuid,
        'confidence': float(route_point.get('confidence', 1.0))
    })

# Calculate velocity (inline implementation)
width, height = 1920, 1080
velocities = []

for i in range(1, len(all_route_points)):
    prev = all_route_points[i-1]
    curr = all_route_points[i]
    
    # Normalize coordinates
    x1_norm = prev['x'] / width
    y1_norm = prev['y'] / height
    x2_norm = curr['x'] / width
    y2_norm = curr['y'] / height
    
    # Calculate distance
    dx = x2_norm - x1_norm
    dy = y2_norm - y1_norm
    distance_normalized = (dx ** 2 + dy ** 2) ** 0.5
    
    # Time difference (float timestamps)
    time_diff = curr['timestamp'] - prev['timestamp']
    
    if time_diff > 0:
        velocity = distance_normalized / time_diff
        velocities.append(velocity)

if velocities:
    avg_route_velocity = round(sum(velocities) / len(velocities), 6)
```

**Units:** Normalized pixels per second (resolution-independent)

**Frontend Display:**

```dart
if (avgRouteVelocity > 0)
  _buildStatCard(
    'Average Movement Velocity',
    '${avgRouteVelocity.toStringAsFixed(6)} px/s',
    Icons.trending_up,
    Colors.deepPurple,
    subtitle: 'Normalized movement speed',
  ),
```

---

## Testing Guide

### Manual Testing Steps

#### 1. Start Services

```bash
# Start all backend services
cd /Users/nickgklezakos/Documents/ppl-meta-code
🚀 Start All Local Python Services
```

**Verify Services Running:**
```bash
🏥 Local Python Health Check - All Services
```

**Expected Output:**
```
✅ ppl-meta-gateway (8080): OK
✅ ppl-meta-vmeta (8008): OK
✅ ppl-meta-media (8000): OK
✅ ppl-meta-node (8001): OK
```

#### 2. Start Flutter App

```bash
cd ppl-meta-frontend
flutter run -d chrome --web-port 3000
```

#### 3. Navigate to Collections Screen

- Open browser: `http://localhost:3000/#/collections`
- Wait for collections list to load
- Select a collection (e.g., `usb_camera_0`)

#### 4. Perform MVR Search

1. Click search icon (🔍) in top-right corner
2. Select date/time range with existing data:
   - Start: 2025-11-29 00:00:00
   - End: 2025-11-29 23:59:59
3. Click "Apply"

**Expected Result:**
```
Individuals: 145 → 12 unique
```
- 145 = Total appearances across all MVR people
- 12 = Unique MVR people (consolidated identities)

#### 5. Navigate to Analysis Screen

1. Click "Analysis" button
2. Wait for loading (fetches MVR data from backend)
3. Verify screen displays: "Cross-Video Individual Analysis"

#### 6. Verify UI Components

**Individuals Tab:**
- [ ] Shows 12 expandable cards (one per MVR person)
- [ ] Each card displays appearance count
- [ ] Demographics visible (age, gender with confidence)
- [ ] Expand card shows video breakdown

**Routes Tab:**
- [ ] Route points render on map visualization
- [ ] Multiple colors for different individuals
- [ ] Sampling indicator if >100 points: "Sampled X points down to Y"

**Statistics Tab:**
- [ ] Total Appearances: 145
- [ ] Unique Videos: count displays
- [ ] Time Span: formatted duration
- [ ] Average Confidence: percentage
- [ ] Average Movement Velocity: displays if > 0 (e.g., "0.027428 px/s")
- [ ] Gender Breakdown: Male/Female/Unknown counts
- [ ] Average Age: with confidence score
- [ ] Search Time Span: date range used

#### 7. Test Velocity Feature

**Check Backend Logs:**
```bash
# Monitor vmeta service logs
tail -f logs/ppl-meta-vmeta.log
```

**Expected Log Output:**
```
🚀 Starting velocity calculation for MVR person 8428c9f5-...
📊 Found 4 appearances across videos
🎯 Calculated velocity: 0.027428 normalized px/s
```

**Check Flutter Console:**
```dart
✅ Loaded MVR person 8428c9f5-...: 4 appearances
Average velocity: 0.027428
```

### Automated Testing

#### Backend API Test

```bash
# Test MVR person analysis endpoint
curl -X GET \
  'http://localhost:8080/api/v1/mvr-people/mvr-person/8428c9f5-4723-4372-9e4f-1a703eebc52a/analysis' \
  -H 'Authorization: Bearer <token>' \
  | python3 -m json.tool
```

**Expected Response:**
```json
{
  "mvr_person_uuid": "8428c9f5-4723-4372-9e4f-1a703eebc52a",
  "total_appearances": 4,
  "unique_videos": 1,
  "average_route_velocity": 0.027428,
  "demographics": {
    "gender": "Male",
    "age_mean": 35.0
  }
}
```

#### Flutter Widget Test

```dart
testWidgets('Statistics tab displays velocity', (WidgetTester tester) async {
  final analysis = AggregatedIndividualAnalysis(
    individualUuid: 'test-uuid',
    averageRouteVelocity: 0.027428,
    // ... other required fields
  );

  await tester.pumpWidget(
    MaterialApp(
      home: PersonObjectsDetailScreen(
        crossVideoContext: CrossVideoAnalysisContext(
          individualUuids: ['test-uuid'],
          sessionUuid: 'test-session',
          sessionData: {'search_results': [...]},
        ),
      ),
    ),
  );

  // Verify velocity card exists
  expect(find.text('Average Movement Velocity'), findsOneWidget);
  expect(find.text('0.027428 px/s'), findsOneWidget);
});
```

---

## Troubleshooting

### Issue: Velocity Returns None

**Symptoms:**
- Statistics tab shows no velocity field
- Backend logs show: `"average_route_velocity": null`

**Causes:**
1. No route data available for videos
2. Route points have invalid timestamps
3. Gateway endpoint unreachable

**Solutions:**

```bash
# Check if route data exists for video
curl http://localhost:8080/api/v1/orchestrator/person-objects/56ebe3bc-6b40-4850-b57a-5068ed4ebda1

# Expected: person_groups with route_points array
# If empty: Video was not processed for movement tracking
```

**Fix:**
- Ensure video has been processed by vision service
- Check that `movement_tracking` is enabled in video processing
- Verify route points have valid `center_x`, `center_y`, `timestamp` fields

### Issue: Statistics Tab Shows 0 Individuals

**Symptoms:**
- "No statistics available" message displayed
- `_aggregatedAnalyses` is empty or null

**Causes:**
1. MVR person UUIDs not found in database
2. API request failed due to authentication
3. Date range filter excludes all appearances

**Solutions:**

```dart
// Check Flutter console for error logs
print('📊 Loading analysis for ${context.individualUuids.length} individuals');
print('📅 Filtering by start_time: $startTime');
print('📅 Filtering by end_time: $endTime');

// Verify UUIDs are valid
for (final uuid in context.individualUuids) {
  print('UUID: $uuid (length: ${uuid.length})');
}
```

**Expected:**
- UUIDs should be 36 characters (UUID format)
- Start/end times should match search parameters
- Backend should return at least one appearance per UUID

### Issue: Route Sampling Not Applied

**Symptoms:**
- Performance slowdown with large datasets
- Console doesn't show "Sampled X points down to Y" message

**Causes:**
1. Route points array empty
2. All routes have < 100 points
3. Sampling logic not executed

**Solutions:**

```dart
// Verify route points count
print('🚦 Individual $i: Combined ${allRoutePoints.length} route points');

// Check sampling threshold
const maxRoutePoints = 100;
if (allRoutePoints.length > maxRoutePoints) {
  print('📊 Applying sampling...');
}
```

**Adjust Threshold:**
```dart
// Change threshold to trigger sampling earlier
const maxRoutePoints = 50;  // Instead of 100
```

---

## Summary

### Key Takeaways

1. **Data Source Intelligence**
   - Screen automatically detects MVR people vs raw individuals
   - Detection based on `search_results` presence in `sessionData`
   - Ensures backwards compatibility with legacy tracking sessions

2. **MVR People = Consolidated Identities**
   - One MVR person UUID = Multiple constituent individual UUIDs
   - Pre-merged based on face embedding similarity
   - Higher accuracy than raw individual tracking

3. **Primary Data Endpoint**
   - `GET /api/v1/mvr-people/mvr-person/{uuid}/analysis`
   - Returns consolidated appearances across all videos
   - Includes demographics, velocity, and temporal analysis

4. **Navigation Flow**
   - Collections Screen → MVR Search → Analysis Button → PersonObjectsDetailScreen
   - Context passed via `CrossVideoAnalysisContext` object
   - `sessionData` contains search results and parameters

5. **Performance Optimizations**
   - Route sampling (100-point threshold) prevents rendering slowdowns
   - Velocity calculated backend-side (resolution-independent)
   - Demographics extracted from cached search results

6. **Statistics Tab**
   - Aggregates metrics across all MVR people
   - Displays demographics from search results
   - Shows velocity only if movement tracking data available

---

## References

- **Related Documents:**
  - [Route Sample Rendering Guide](/docs/guides/developer/route-sample-rendering.md)
  - [MVR People Search Implementation](/docs/vision-vmeta/MVR_PEOPLE_SEARCH_IMPLEMENTATION.md)
  - [Cross Video Analysis API Data Flow](/docs/vision-vmeta/CROSS_VIDEO_ANALYSIS_API_DATA_FLOW.md)

- **Source Files:**
  - Flutter: `ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`
  - API Client: `ppl-meta-frontend/lib/services/media_api_client.dart`
  - Models: `ppl-meta-frontend/lib/models/cross_video_analysis_models.dart`
  - Backend: `ppl-meta-vmeta/src/api/routes/mvr_people.py`

- **Version:** 2.19.42
- **Last Updated:** November 29, 2025
- **Author:** GitHub Copilot (Claude Sonnet 4.5)
