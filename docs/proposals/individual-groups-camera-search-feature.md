# Individual Groups Camera Search Feature

**Version:** 1.0  
**Date:** December 17, 2025  
**Status:** Proposal  
**Author:** System Design

---

## Overview

This feature adds targeted camera-based search functionality to Individual Groups, enabling users to search for group members' appearances within specific camera collections and time ranges. This bridges the MVR People Search functionality with Individual Groups, providing a powerful tool for security, retail analytics, and investigative workflows.

---

## Business Case

### Problem Statement
Currently, Individual Groups allow users to organize and analyze known individuals, but there's no way to:
- Search for group members in a specific camera location
- Filter group member appearances by time and location
- Quickly identify which group members appeared at a specific camera during a time window

### Use Cases

1. **Security & Investigation**
   - "Show me which VIP guests were at the north entrance between 2-4 PM"
   - "Did any persons of interest appear at camera 3 during the incident window?"
   
2. **Retail Analytics**
   - "Which loyalty program members visited Store 5 today?"
   - "Track high-value customer appearances across store locations"

3. **Access Control Verification**
   - "Verify authorized personnel present at secure area cameras"
   - "Cross-reference employee group with facility access logs"

---

## Feature Specification

### User Interface

#### 1. Individual Group Card Enhancement
**Location:** `http://localhost:3000/#/individual-groups`

Add a **search icon button** to each Individual Group card:
- Icon: Magnifying glass with camera overlay
- Position: Top-right corner of group card (alongside existing actions)
- Tooltip: "Search for group members in camera"
- Color: Primary action color when hover

#### 2. Camera Search Dialog
**Triggered by:** Clicking search icon on group card

**Dialog Title:** "Search for [Group Name] Members"

**Dialog Content:**

```
┌─────────────────────────────────────────────────┐
│  Search for VIP Members                      ×  │
├─────────────────────────────────────────────────┤
│                                                 │
│  📷 Select Camera Collection                    │
│  ┌───────────────────────────────────────────┐ │
│  │ [Dropdown: Camera Collections]            │ │
│  │ • North Entrance                          │ │
│  │ • South Entrance                          │ │
│  │ • Main Floor Camera 1                     │ │
│  │ • Loading Dock                            │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  📅 Time Range                                  │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ Start Time   │  │ End Time     │            │
│  │ [DateTime]   │  │ [DateTime]   │            │
│  └──────────────┘  └──────────────┘            │
│                                                 │
│  Quick Ranges:                                  │
│  [Last Hour] [Today] [Last 24h] [Last Week]    │
│                                                 │
│  ℹ️ Searching 12 group members                  │
│                                                 │
│  [Cancel]                      [Search]         │
└─────────────────────────────────────────────────┘
```

**Dialog Components:**
- **Camera Collection Dropdown:** Lists all available cameras from the system
- **Time Range Pickers:** Start and end datetime selectors (identical to MVR People Search)
- **Quick Range Buttons:** Preset time ranges for convenience
- **Member Count:** Shows how many members will be searched
- **Action Buttons:** Cancel and Search (Search is primary action)

#### 3. Search Execution & Loading State

**Loading Dialog:**
```
┌─────────────────────────────────────────┐
│  Searching for Group Members...        │
├─────────────────────────────────────────┤
│                                         │
│         🔍 [Progress Spinner]           │
│                                         │
│  Step 1: Running MVR search... ✓        │
│  Step 2: Comparing with group... ⏳     │
│  Step 3: Loading analysis...            │
│                                         │
│  Found 3 of 12 members                  │
│                                         │
└─────────────────────────────────────────┘
```

#### 4. Results Display
**Destination:** Cross Video Individual Screen (Person Objects Detail Screen)

**Navigation:** Automatic redirect to `http://localhost:3000/#/person-objects-detail`

**Context Data:**
```json
{
  "source": "individual_group_camera_search",
  "group_id": "uuid-of-group",
  "group_name": "VIP Members",
  "camera_collection": "North Entrance",
  "camera_id": "camera-uuid",
  "search_parameters": {
    "start_time": "2025-12-17T14:00:00Z",
    "end_time": "2025-12-17T16:00:00Z"
  },
  "total_group_members": 12,
  "members_found": 3,
  "member_matches": [
    {
      "individual_uuid": "uuid1",
      "mvr_person_uuid": "mvr-uuid1",
      "match_confidence": 0.95
    }
  ]
}
```

**Results Layout:**
- Display matched individuals in aggregated analysis cards
- Show "3 of 12 members found" banner at top
- Each card shows member's appearances during the search window
- Timeline view shows when each member appeared
- Ability to filter/sort by appearance time, duration, confidence

---

## Technical Implementation

### Frontend Changes

#### 1. Individual Groups Screen (`individual_groups_screen.dart`)
**Changes:**
- Add search icon button to `_GroupCard` widget
- Implement `_showCameraSearchDialog()` method
- Handle navigation to results with proper context

#### 2. New Widget: Camera Search Dialog (`camera_search_dialog.dart`)
**File:** `lib/widgets/individual_groups/camera_search_dialog.dart`

**Components:**
- Camera collection dropdown (fetches from CameraApiClient)
- DateTime range pickers (reuse from MVR search)
- Quick range buttons
- Validation logic
- Search submission handler

**Key Methods:**
```dart
class CameraSearchDialog extends StatefulWidget {
  final String groupId;
  final String groupName;
  final int memberCount;
  
  Future<void> _loadCameras();
  void _selectCamera(String cameraId);
  void _selectTimeRange(DateTime start, DateTime end);
  void _executeSearch();
}
```

#### 3. Cross Video Analysis Screen Enhancement
**File:** `lib/screens/person_objects_detail_screen.dart`

**Changes:**
- Add handling for `source: 'individual_group_camera_search'`
- Display search context banner (camera name, time range)
- Show "X of Y members found" statistics
- Support filtering by group membership

**New Method:**
```dart
Future<void> _loadGroupCameraSearchData() async {
  // 1. Extract search parameters from context
  // 2. Call backend camera search endpoint
  // 3. Filter results by group membership
  // 4. Display matched individuals with appearances
}
```

### Backend Changes

#### 1. New API Endpoint: Group Camera Search
**Service:** `ppl-meta-vmeta`  
**File:** `src/api/routes/individual_groups.py`

**Endpoint:**
```python
@router.post(
    "/{group_id}/camera-search",
    summary="Search for Group Members in Camera"
)
async def search_group_in_camera(
    group_id: str,
    request: GroupCameraSearchRequest,
    manager: IndividualGroupsManager = Depends(get_groups_manager),
):
    """
    Search for individual group members within a specific camera's 
    video data during a time range.
    
    Process:
    1. Get group member individual UUIDs
    2. Execute MVR search on specified camera/time range
    3. Compare MVR results with group members
    4. Return matched individuals with appearance data
    """
```

**Request Model:**
```python
class GroupCameraSearchRequest(BaseModel):
    camera_id: str
    start_time: datetime
    end_time: datetime
    confidence_threshold: float = 0.7
```

**Response Model:**
```python
class GroupCameraSearchResponse(BaseModel):
    group_id: str
    group_name: str
    camera_id: str
    camera_name: str
    search_window: dict
    total_group_members: int
    members_found: int
    matched_individuals: List[MatchedIndividual]
    search_session_uuid: str  # For further analysis
    
class MatchedIndividual(BaseModel):
    individual_uuid: str
    mvr_person_uuid: str
    total_appearances: int
    first_seen: datetime
    last_seen: datetime
    confidence_score: float
    demographics: Optional[dict]
```

#### 2. IndividualGroupsManager Enhancement
**File:** `src/services/individual_groups_manager.py`

**New Method:**
```python
async def search_members_in_camera(
    self,
    group_id: str,
    camera_id: str,
    start_time: datetime,
    end_time: datetime,
    confidence_threshold: float = 0.7
) -> GroupCameraSearchResponse:
    """
    Search for group members in camera footage.
    
    Steps:
    1. Fetch all member individual_uuids for the group
    2. Execute MVR search on camera collection
    3. Get MVR mappings for returned MVR people
    4. Filter MVR people that map to group members
    5. Fetch appearance details for matched individuals
    6. Return structured results
    """
    
    # Get group members
    members = await self.get_group_members(group_id)
    member_uuids = {m.id for m in members}
    
    # Execute MVR search
    mvr_results = await self._execute_mvr_camera_search(
        camera_id, start_time, end_time, confidence_threshold
    )
    
    # Compare and match
    matched = []
    for mvr_person in mvr_results:
        individual_uuid = await self._get_individual_from_mvr(
            mvr_person.uuid
        )
        if individual_uuid in member_uuids:
            matched.append({
                'individual_uuid': individual_uuid,
                'mvr_person_uuid': mvr_person.uuid,
                'appearances': mvr_person.appearances,
                # ... more details
            })
    
    return GroupCameraSearchResponse(...)
```

#### 3. Integration with Existing MVR Search
**Reuse existing logic from:**
- `src/api/v1/cross_video_tracking_simple.py` (MVR search endpoint)
- MVR people matching algorithms
- Individual-MVR mapping queries

**Database Queries Required:**
```sql
-- 1. Get group members
SELECT individual_id FROM group_memberships 
WHERE group_id = $1

-- 2. Get MVR mappings for individuals
SELECT mvr_people_uuid, individual_uuid 
FROM individual_mvr_mapping 
WHERE individual_uuid = ANY($1)

-- 3. Filter MVR search results by group membership
SELECT DISTINCT mvr.* 
FROM mvr_search_results mvr
JOIN individual_mvr_mapping imm ON mvr.mvr_people_uuid = imm.mvr_people_uuid
WHERE imm.individual_uuid = ANY($1)
  AND mvr.camera_id = $2
  AND mvr.timestamp BETWEEN $3 AND $4
```

### Gateway Changes
**File:** `ppl-meta-gateway/src/api/v1/router.py`

**Add proxy endpoint:**
```python
@api_router.post("/individual-groups/{group_id}/camera-search")
async def proxy_group_camera_search(request: Request):
    """Proxy group camera search to vmeta service."""
    return await _proxy_to_vmeta_service(request)
```

---

## Data Flow

```
┌──────────────────────────────────────────────────────────┐
│                     User Journey                          │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  1. User clicks search icon on Individual Group card     │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  2. Camera Search Dialog opens                           │
│     - Loads available cameras                            │
│     - Shows group context (name, member count)           │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  3. User selects camera and time range                   │
│     - Camera: "North Entrance"                           │
│     - Time: "Today, 2 PM - 4 PM"                         │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  4. Frontend POSTs to:                                   │
│     /api/v1/individual-groups/{group_id}/camera-search   │
│     {                                                    │
│       camera_id: "cam-123",                              │
│       start_time: "2025-12-17T14:00:00Z",               │
│       end_time: "2025-12-17T16:00:00Z"                  │
│     }                                                    │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  5. Backend Process:                                     │
│     a. Fetch group members (12 individuals)              │
│     b. Execute MVR search on camera/time range           │
│        - Returns 45 MVR people                           │
│     c. Get individual_uuids for MVR people               │
│     d. Filter MVR people by group membership             │
│        - 3 matched individuals found                     │
│     e. Fetch appearance details for matches              │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  6. Backend Returns:                                     │
│     {                                                    │
│       total_group_members: 12,                           │
│       members_found: 3,                                  │
│       matched_individuals: [...]                         │
│     }                                                    │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│  7. Frontend navigates to Cross Video Individual Screen  │
│     - Shows "3 of 12 VIP Members found"                  │
│     - Displays appearance timeline for matched members   │
│     - Context: North Entrance, 2-4 PM                    │
└──────────────────────────────────────────────────────────┘
```

---

## Edge Cases & Error Handling

### 1. No Members Found
**Scenario:** Search completes but no group members appeared in camera
**Handling:**
- Show dialog: "No group members found in North Entrance during this time"
- Offer to adjust time range or try different camera
- Don't navigate to results screen

### 2. All Members Found
**Scenario:** Every group member appeared in the search window
**Handling:**
- Highlight this in results: "All 12 members found! 🎉"
- Useful for verifying attendance/presence

### 3. Camera Offline or No Data
**Scenario:** Selected camera has no video data for time range
**Handling:**
- Error message: "No video data available for North Entrance during selected time"
- Show camera's operational status and last data timestamp

### 4. Large Time Range
**Scenario:** User selects very long time range (e.g., 1 month)
**Handling:**
- Warning: "Large time range may take longer to search. Continue?"
- Consider implementing pagination or limiting to last N results

### 5. Invalid Time Range
**Scenario:** End time before start time, or future dates
**Validation:**
- Client-side validation before search
- Error highlight on invalid fields
- Helpful message: "End time must be after start time"

### 6. Search Timeout
**Scenario:** Backend search takes too long
**Handling:**
- 60-second timeout on frontend
- Option to retry or run as background job
- Consider async search for very large datasets

---

## Performance Considerations

### Expected Query Performance

**Small Search (1 camera, 1 day, 10 members):**
- MVR Search: ~500ms
- Member matching: ~200ms
- Appearance fetching: ~300ms
- **Total: ~1 second**

**Medium Search (1 camera, 1 week, 50 members):**
- MVR Search: ~2 seconds
- Member matching: ~800ms
- Appearance fetching: ~1.5 seconds
- **Total: ~4-5 seconds**

**Large Search (1 camera, 1 month, 200 members):**
- Consider async processing or pagination

### Optimization Strategies

1. **Database Indexes:**
   ```sql
   CREATE INDEX idx_mvr_camera_time ON mvr_people(camera_id, timestamp);
   CREATE INDEX idx_group_members ON group_memberships(group_id, individual_id);
   CREATE INDEX idx_mvr_mapping ON individual_mvr_mapping(mvr_people_uuid, individual_uuid);
   ```

2. **Query Optimization:**
   - Use JOIN instead of multiple queries where possible
   - Limit MVR search results before matching
   - Fetch appearance details in parallel

3. **Caching:**
   - Cache camera list for dropdown
   - Cache group member lists (invalidate on membership changes)
   - Consider caching recent search results (5-minute TTL)

4. **Progressive Loading:**
   - Show matched members as they're found
   - Stream results instead of waiting for complete search

---

## Testing Strategy

### Unit Tests

**Frontend:**
- Camera search dialog component rendering
- Form validation (time ranges, camera selection)
- Search result context creation

**Backend:**
- Group member fetching
- MVR search execution
- Member matching logic
- Response formatting

### Integration Tests

**Test Scenarios:**
1. Search with 5 members, 2 found
2. Search with 0 members found
3. Search with all members found
4. Search with invalid camera ID
5. Search with overlapping time ranges
6. Search with group containing no members

### E2E Tests

**User Flows:**
1. Complete search flow: select group → choose camera → view results
2. Search, modify time range, search again
3. Search from multiple groups, compare results
4. Navigate from search results to appearance details

### Performance Tests

**Load Testing:**
- Concurrent searches from multiple users
- Large groups (100+ members)
- Extended time ranges (30+ days)
- High-traffic cameras with dense footage

---

## UI/UX Considerations

### Visual Design

**Search Icon:**
- Use Material Icons: `search` combined with `videocam`
- Animation: Subtle pulse on hover
- State: Disabled when group has no members

**Dialog Design:**
- Clean, focused layout
- Large, easy-to-tap selection areas
- Clear visual hierarchy
- Responsive to different screen sizes

**Results Banner:**
```
┌────────────────────────────────────────────────┐
│  🎯 Search Results: VIP Members                │
│                                                │
│  📷 North Entrance                             │
│  📅 Dec 17, 2025  2:00 PM - 4:00 PM           │
│  ✅ Found 3 of 12 members                      │
│                                                │
│  [Modify Search]                               │
└────────────────────────────────────────────────┘
```

### Accessibility

- Keyboard navigation support (Tab, Enter, Esc)
- Screen reader announcements for search progress
- ARIA labels for all interactive elements
- Color contrast compliance (WCAG 2.1 AA)
- Focus indicators on all focusable elements

### Mobile Responsiveness

- Full-screen dialog on mobile
- Touch-friendly tap targets (minimum 44x44pt)
- Simplified datetime pickers for mobile
- Swipe to dismiss dialog

---

## Security & Privacy

### Access Control

- Only users with "view_individual_groups" permission can use this feature
- Camera access limited to user's authorized cameras
- Group search limited to groups user has access to
- Audit log all camera searches with user ID

### Data Privacy

- Comply with video surveillance regulations
- Respect individual privacy settings if implemented
- Consider GDPR right to erasure
- Log retention policies for search history

### Rate Limiting

- Limit searches per user: 20 per hour
- Prevent abuse/scraping
- Exponential backoff for repeated failures

---

## Future Enhancements

### Phase 2 Features

1. **Multi-Camera Search:**
   - Search across multiple cameras simultaneously
   - Aggregate results by camera
   - Show movement patterns between cameras

2. **Saved Searches:**
   - Save frequently used search configurations
   - One-click re-run of saved searches
   - Schedule recurring searches

3. **Search History:**
   - View past searches for this group
   - Compare results across different time periods
   - Trend analysis

4. **Alert Configuration:**
   - "Notify me when any VIP member appears at Front Door"
   - Real-time alerts based on group membership
   - Integration with notification system

5. **Batch Operations:**
   - Search multiple groups simultaneously
   - Export search results to CSV/PDF
   - Generate attendance reports

6. **Advanced Filters:**
   - Filter by demographics (age range, gender)
   - Minimum appearance duration
   - Confidence score threshold
   - Exclude certain members

---

## Implementation Phases

### Phase 1: MVP (Week 1-2)
- [ ] Add search icon to group cards
- [ ] Implement basic camera search dialog
- [ ] Create backend camera search endpoint
- [ ] Display results in existing Cross Video screen
- [ ] Basic error handling

### Phase 2: Polish (Week 3)
- [ ] Loading states and progress indicators
- [ ] Enhanced error messages
- [ ] Quick time range buttons
- [ ] Results banner with search context
- [ ] Unit tests

### Phase 3: Optimization (Week 4)
- [ ] Performance tuning
- [ ] Database indexes
- [ ] Caching layer
- [ ] Integration tests
- [ ] Documentation

### Phase 4: Advanced Features (Future)
- [ ] Multi-camera search
- [ ] Saved searches
- [ ] Search history
- [ ] Alerts and notifications

---

## Success Metrics

### User Engagement
- Number of camera searches per day
- Average searches per user
- Search-to-result conversion rate

### Performance
- Average search completion time
- Search success rate (results found)
- Error rate

### Business Value
- Time saved vs manual video review
- Accuracy of member identification
- User satisfaction scores

---

## Dependencies

### Frontend
- Existing MVR search dialog code (for reference)
- Camera API client
- DateTime picker components
- Cross Video Individual Screen

### Backend
- MVR People search functionality
- Individual-MVR mapping tables
- Camera metadata and status
- Individual Groups Manager

### Infrastructure
- Database indexes for performance
- Sufficient API capacity for concurrent searches

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Performance degradation with large groups | High | Medium | Implement pagination, caching, async processing |
| Complex UI confuses users | Medium | Low | User testing, tooltips, clear labeling |
| Backend overload from concurrent searches | High | Medium | Rate limiting, queue system, resource monitoring |
| Inaccurate matches due to MVR errors | Medium | Low | Confidence thresholds, manual review option |
| Privacy/compliance concerns | High | Low | Legal review, audit logging, access controls |

---

## Open Questions

1. Should we show non-matched group members in results (greyed out)?
2. Do we need real-time search (as people are detected) or batch only?
3. Should search history be per-user or per-group?
4. How long should we retain search result data?
5. Should we support searching archived/offline cameras?

---

## Approval & Sign-off

- [ ] Product Owner: _______________________ Date: _______
- [ ] Engineering Lead: _______________________ Date: _______
- [ ] Security Review: _______________________ Date: _______
- [ ] Privacy Officer: _______________________ Date: _______

---

## References

- Individual Groups Phase 3 Implementation
- MVR People Search Documentation
- Cross Video Analysis Architecture
- Camera API Specification
