# Hierarchical MVR People Merging - Implementation Progress

**Date**: December 15, 2025  
**Version**: 2.19.84  
**Status**: Backend Complete, Frontend In Progress

---

## ✅ Completed Components

### 1. Backend Service Layer

**File**: `ppl-meta-vmeta/src/services/hierarchical_mvr_merger.py`

✅ **HierarchicalMVRMerger Class**
- Similarity matrix calculation with O(N²) optimization
- Union-Find algorithm for connected components
- Quality-based winner selection
- Bulk orphaning and merge tracking
- Super-individual hierarchy retrieval

✅ **UnionFind Class**
- Path compression optimization
- Union by rank
- Get connected components as groups

**Key Methods**:
- `merge_hierarchical()`: Main merge orchestration
- `_calculate_similarity_matrix()`: Cosine similarity with early termination
- `_find_merge_groups()`: Union-Find based grouping
- `_merge_group()`: Execute merge within group
- `get_super_individual_hierarchy()`: Retrieve full 3-tier hierarchy

### 2. Backend API Endpoints

**File**: `ppl-meta-vmeta/src/api/routes/mvr_people.py`

✅ **Endpoint 15**: `POST /api/v1/mvr-people/merge/hierarchical`
- Accepts list of MVR UUIDs
- Configurable similarity threshold (0.60-0.90)
- Returns super-individuals and merge metadata
- Maximum 1000 MVR per request

✅ **Endpoint 16**: `GET /api/v1/mvr-people/super-individual/{uuid}/hierarchy`
- Retrieves full 3-tier hierarchy
- Returns merged MVR people with similarities
- Includes all individuals and person objects
- Provides aggregate statistics

### 3. Database Repository Methods

**File**: `ppl-meta-vmeta/src/database/mvr_repository.py`

✅ **bulk_orphan_mvr_people()**
- Marks multiple MVR as orphaned in single transaction
- Updates merged_into_mvr_uuid field
- Returns count of orphaned records

✅ **get_merged_mvr_people()**
- Retrieves all MVR merged into a super-individual
- Returns sorted by quality score

✅ **get_individuals_for_mvr()**
- Gets all individuals linked to an MVR
- Includes person object counts
- Sorted by first appearance

---

## 🚧 Remaining Work

### 4. Frontend Data Models

**Files to Update**:
- `ppl-meta-frontend/lib/models/person_objects_models.dart`
- `ppl-meta-frontend/lib/models/cross_video_analysis_models.dart`

**Required Changes**:
```dart
class AggregatedIndividualAnalysis {
  final String individualUuid;
  final bool isSuperIndividual; // NEW: Distinguish merged vs standalone
  final int mergedMVRCount;     // NEW: Number of merged MVR people
  final List<String> mergedMVRPeople; // NEW: List of merged MVR UUIDs
  final Map<String, double> similarities; // NEW: Similarities to featured
  final String bestFaceThumbnail;
  final Demographics? demographics;
  final int totalAppearances;
  final int uniqueVideos;
  // ... existing fields
  
  // Factory method for merged super-individuals
  factory AggregatedIndividualAnalysis.fromSuperIndividual(
    Map<String, dynamic> json
  );
  
  // Factory method for standalone individuals
  factory AggregatedIndividualAnalysis.fromJson(
    Map<String, dynamic> json
  );
}
```

### 5. Frontend UI Components

**File**: `ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart`

**Required Changes**:

1. **Hierarchical Card Widget** (lines ~1080-1140)
   ```dart
   Widget _buildHierarchicalIndividualCard(
     AggregatedIndividualAnalysis analysis,
     bool isSuperIndividual,
   ) {
     return Card(
       elevation: 4, // Same for all Level 1
       child: Column(
         children: [
           // Level 1: Super-individual/Standalone header
           ListTile(
             leading: Stack(
               children: [
                 CircleAvatar(...),
                 // Badge: Blue for merged, Grey for standalone
                 Positioned(
                   child: Container(
                     decoration: BoxDecoration(
                       color: isSuperIndividual ? Colors.blue : Colors.grey[600],
                     ),
                     child: Icon(
                       isSuperIndividual ? Icons.merge_type : Icons.person,
                     ),
                   ),
                 ),
               ],
             ),
             title: Row(
               children: [
                 Text(analysis.demographics?.gender ?? 'Unknown'),
                 Chip(
                   label: Text(
                     isSuperIndividual 
                       ? '${analysis.mergedMVRCount} batches merged'
                       : 'Standalone individual',
                   ),
                   backgroundColor: isSuperIndividual 
                     ? Colors.blue.withOpacity(0.2)
                     : Colors.grey.withOpacity(0.2),
                 ),
               ],
             ),
             // ... rest of Level 1 UI
           ),
           
           // Level 2: Merged MVR people (only if isSuperIndividual)
           if (isSuperIndividual && _expandedIndividuals.contains(analysis.individualUuid))
             ..._buildMergedMVRList(analysis),
           
           // Level 2/3: Person objects
           if (_expandedIndividuals.contains(analysis.individualUuid))
             ..._buildPersonObjectsList(analysis),
         ],
       ),
     );
   }
   ```

2. **Auto-merge Integration** (in `_loadCrossVideoData()`)
   ```dart
   Future<void> _loadCrossVideoData() async {
     setState(() {
       _isLoadingCrossVideoData = true;
       _crossVideoError = null;
     });
     
     try {
       // 1. Get MVR people from search
       final response = await apiClient.post(
         '/api/v1/mvr-people/search',
         body: {...},
       );
       
       List<String> mvrUuids = response.mvrPeople.map((m) => m.uuid).toList();
       
       // 2. NEW: Auto-merge MVR people
       final mergeResponse = await apiClient.post(
         '/api/v1/mvr-people/merge/hierarchical',
         body: {
           'mvr_uuids': mvrUuids,
           'similarity_threshold': _similarityThreshold,
         },
       );
       
       // 3. Get hierarchy for each super-individual
       List<AggregatedIndividualAnalysis> analyses = [];
       for (String superUuid in mergeResponse.superIndividuals) {
         final hierarchy = await apiClient.get(
           '/api/v1/mvr-people/super-individual/$superUuid/hierarchy',
         );
         
         analyses.add(
           AggregatedIndividualAnalysis.fromSuperIndividual(hierarchy)
         );
       }
       
       setState(() {
         _aggregatedAnalyses = analyses;
         _isLoadingCrossVideoData = false;
       });
       
     } catch (e) {
       setState(() {
         _crossVideoError = e.toString();
         _isLoadingCrossVideoData = false;
       });
     }
   }
   ```

### 6. Frontend Service Client

**File**: `ppl-meta-frontend/lib/services/person_objects_api_client.dart`

**Required Methods**:
```dart
class PersonObjectsApiClient {
  // ... existing methods
  
  /// Perform hierarchical merge of MVR people
  Future<HierarchicalMergeResponse> mergeHierarchical({
    required List<String> mvrUuids,
    double similarityThreshold = 0.70,
  }) async {
    final response = await _apiClient.post(
      '/api/v1/mvr-people/merge/hierarchical',
      body: {
        'mvr_uuids': mvrUuids,
        'similarity_threshold': similarityThreshold,
      },
    );
    
    return HierarchicalMergeResponse.fromJson(response.data);
  }
  
  /// Get super-individual hierarchy
  Future<SuperIndividualHierarchy> getSuperIndividualHierarchy(
    String superIndividualUuid,
  ) async {
    final response = await _apiClient.get(
      '/api/v1/mvr-people/super-individual/$superIndividualUuid/hierarchy',
    );
    
    return SuperIndividualHierarchy.fromJson(response.data);
  }
}
```

### 7. Collections Screen Integration

**File**: `ppl-meta-frontend/lib/screens/collections_screen.dart` (or equivalent)

**Required Changes**:
- Add auto-merge call after search completes
- Display merge statistics ("45 MVR → 15 unique people")
- Show merge badge/indicator
- Pass merged data to PersonObjectsDetailScreen

---

## 📊 Implementation Statistics

### Backend
- **Lines of Code**: ~700 lines
- **New Files**: 1 (hierarchical_mvr_merger.py)
- **Modified Files**: 2 (mvr_people.py, mvr_repository.py)
- **New Endpoints**: 2
- **New Repository Methods**: 3

### Frontend (Estimated)
- **Lines of Code**: ~500 lines (estimated)
- **Modified Files**: 3-4
- **New Models**: 2-3
- **New Widgets**: 2-3

### Total Effort
- **Backend**: ✅ Complete (2-3 hours)
- **Frontend**: 🚧 In Progress (4-6 hours estimated)
- **Testing**: ⏳ Not Started (2-3 hours estimated)
- **Documentation**: ✅ Complete

---

## 🧪 Testing Requirements

### Unit Tests
1. **UnionFind Algorithm**
   - Test path compression
   - Test union by rank
   - Test get_groups with various sizes

2. **Similarity Matrix**
   - Test cosine similarity calculation
   - Test early termination optimization
   - Test sparse matrix storage

3. **Merge Groups**
   - Test quality-based winner selection
   - Test orphaning logic
   - Test standalone handling

### Integration Tests
1. **End-to-End Merge Flow**
   - Search → Merge → Display
   - Verify 3-tier hierarchy
   - Verify standalone handling

2. **API Endpoints**
   - Test with various thresholds
   - Test with large MVR lists
   - Test error handling

### UI Tests
1. **Hierarchical Display**
   - Test badge colors
   - Test expand/collapse
   - Test standalone vs merged

---

## 📝 Next Steps

1. **Complete Frontend Models** (1 hour)
   - Update AggregatedIndividualAnalysis
   - Add factory methods
   - Add response models

2. **Implement UI Components** (2-3 hours)
   - Add hierarchical card widget
   - Add badge logic
   - Add expand/collapse logic

3. **Integrate Collections Screen** (1 hour)
   - Add auto-merge call
   - Add statistics display
   - Wire up navigation

4. **Testing** (2-3 hours)
   - Write unit tests
   - Write integration tests
   - Manual QA

5. **Documentation** (30 minutes)
   - Update API docs
   - Update user guide
   - Add code comments

**Total Estimated Time**: 6-8 hours remaining

---

## 🔗 Related Documents

- [Full Proposal](./HIERARCHICAL_MVR_PEOPLE_MERGING.md)
- [Executive Summary](./HIERARCHICAL_MVR_MERGING_SUMMARY.md)
- [Visual Diagrams](./HIERARCHICAL_MVR_MERGING_DIAGRAMS.md)
- [Proposals Guide](./README.md)

---

**Implementation Status**: 50% Complete (Backend Done, Frontend In Progress)
