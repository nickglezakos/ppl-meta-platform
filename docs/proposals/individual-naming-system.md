# Individual Naming System - Feature Proposal

**Version:** 1.0  
**Date:** 2025-12-19  
**Status:** Proposed  
**Author:** System Architecture Team

---

## Executive Summary

This proposal introduces a **naming system for MVR people** (individuals) who are members of Individual Groups. Users can assign human-readable names (e.g., "John Doe", "VIP Customer #5") to MVR people for easier identification and management. The system handles complex merge scenarios where multiple named or unnamed MVR people are consolidated, ensuring name preservation and inheritance.

---

## Problem Statement

### Current Limitations

1. **UUID-Only Identification**: MVR people are identified solely by UUIDs (e.g., `b24ad688-26f0-4e1e-9484-4fecec18df9c`), making it difficult for users to recognize individuals
2. **Group Member Management**: Users cannot easily distinguish between group members in the Individual Groups detail screen
3. **No Persistent Labels**: There's no way to assign permanent, human-readable labels to frequently appearing individuals
4. **Merge Confusion**: When MVR people merge, there's no mechanism to preserve user-assigned identities

### User Impact

- **Retail managers** want to label VIP customers: "Sarah - Regular Shopper", "Mike - Loyalty Member"
- **Security teams** need to tag individuals: "Authorized Personnel", "Contractor #42"
- **Analytics users** want meaningful reports instead of UUID lists

---

## Feature Overview

### Core Functionality

1. **Name Assignment**: Users can assign/edit a string name to any MVR person who is a member of an Individual Group
2. **Name Display**: Names appear in:
   - Individual Groups detail screen (member cards)
   - Cross-Video Analysis screen (individual cards)
   - Search results
   - Reports and exports
3. **Merge Handling**: Automatic name consolidation when MVR people merge
4. **Name Propagation**: Name changes propagate to all merged MVR people in the hierarchy

---

## Use Cases

### UC-1: Assign Name to Group Member

**Actor**: Store Manager  
**Preconditions**: MVR person is a member of "VIP Customers" group  
**Flow**:
1. User opens "VIP Customers" group detail screen
2. User clicks "Edit Name" icon on member card
3. User enters "Sarah Thompson"
4. System saves name to MVR person record
5. Name appears on all screens showing this MVR person

**Postconditions**: MVR person displays "Sarah Thompson" instead of UUID

---

### UC-2: Edit Existing Name

**Actor**: Security Manager  
**Preconditions**: MVR person already has name "Contractor"  
**Flow**:
1. User opens Individual Groups screen
2. User clicks "Edit Name" on member card showing "Contractor"
3. User changes name to "John - Authorized Contractor"
4. System updates name and propagates to all merged MVR records
5. All super-individuals and merged records inherit new name

**Postconditions**: All related MVR people display updated name

---

### UC-3: Merge Unnamed MVR People

**Scenario**: Multiple unnamed MVR people merge into one  
**Actor**: System (automatic)  
**Flow**:
1. Vision system identifies 3 unnamed MVR people as same person
2. System merges them into super-individual
3. User assigns name "Alex" to super-individual
4. System propagates name to all 3 constituent MVR records

**Result**: All 3 original MVR people now display "Alex"

---

### UC-4: Merge One Named + Multiple Unnamed

**Scenario**: Named MVR person merges with unnamed ones  
**Actor**: System (automatic)  
**Flow**:
1. MVR person "Jennifer" merges with 2 unnamed MVR people
2. System creates super-individual
3. System automatically assigns "Jennifer" to super-individual
4. All constituent MVR records inherit "Jennifer"

**Result**: Unified identity with preserved name

---

### UC-5: Merge Multiple Named MVR People

**Scenario**: Multiple named MVR people merge (name conflict)  
**Actor**: System (automatic)  
**Flow**:
1. "Sarah" merges with "Sarah Thompson" and "Regular Customer"
2. System creates super-individual with consolidated name
3. System combines names: "Sarah, Sarah Thompson, Regular Customer"
4. User can edit to clean up: "Sarah Thompson (Regular Customer)"

**Result**: All original names preserved, user can refine

---

## Technical Architecture

### Database Schema Changes

#### 1. Add Name Column to `mvr_people` Table

```sql
-- Migration: 01X_add_mvr_people_names.sql

ALTER TABLE mvr_people 
ADD COLUMN name VARCHAR(255) DEFAULT NULL,
ADD COLUMN name_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL,
ADD COLUMN name_updated_by VARCHAR(255) DEFAULT NULL;

-- Index for name searches
CREATE INDEX idx_mvr_people_name ON mvr_people(name) WHERE name IS NOT NULL;

-- Index for group member name lookups
CREATE INDEX idx_mvr_people_name_search ON mvr_people(name text_pattern_ops) WHERE name IS NOT NULL;

COMMENT ON COLUMN mvr_people.name IS 'User-assigned human-readable name for this MVR person';
COMMENT ON COLUMN mvr_people.name_updated_at IS 'Timestamp when name was last updated';
COMMENT ON COLUMN mvr_people.name_updated_by IS 'User email who last updated the name';
```

#### 2. Name History Table (Optional - for audit trail)

```sql
-- Track name changes over time
CREATE TABLE mvr_people_name_history (
    id SERIAL PRIMARY KEY,
    mvr_people_uuid UUID NOT NULL REFERENCES mvr_people(mvr_people_uuid) ON DELETE CASCADE,
    old_name VARCHAR(255),
    new_name VARCHAR(255),
    changed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    changed_by VARCHAR(255),
    reason VARCHAR(50) CHECK (reason IN ('user_edit', 'merge_inherit', 'merge_consolidate'))
);

CREATE INDEX idx_name_history_mvr ON mvr_people_name_history(mvr_people_uuid);
CREATE INDEX idx_name_history_timestamp ON mvr_people_name_history(changed_at DESC);
```

---

## API Endpoints

### Backend Service: `ppl-meta-vmeta`

#### 1. Update MVR Person Name

```python
# File: ppl-meta-vmeta/src/api/routes/mvr_people.py

@router.patch("/mvr-person/{mvr_person_uuid}/name")
async def update_mvr_person_name(
    mvr_person_uuid: str,
    request: UpdateNameRequest,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Update the name of an MVR person and propagate to merged hierarchy.
    
    Request Body:
    {
        "name": "Sarah Thompson",
        "propagate": true  // Apply to all merged MVR people
    }
    
    Returns:
    {
        "success": true,
        "mvr_person_uuid": "uuid",
        "name": "Sarah Thompson",
        "updated_at": "2025-12-19T10:30:00Z",
        "propagated_to": ["uuid1", "uuid2", "uuid3"],  // List of affected MVR UUIDs
        "affected_super_individuals": ["super_uuid1"]
    }
    """
    pass
```

**Logic:**
1. Validate MVR person exists
2. Update `mvr_people.name` field
3. Set `name_updated_at` and `name_updated_by`
4. If `propagate=true`:
   - Find all merged MVR people via `individual_super_mapping`
   - Update their names to match
   - Find super-individuals and update their display names
5. Record in `mvr_people_name_history` table
6. Return affected UUIDs

---

#### 2. Get MVR Person with Name

```python
@router.get("/mvr-person/{mvr_person_uuid}")
async def get_mvr_person_details(
    mvr_person_uuid: str,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Get MVR person details including name.
    
    Returns:
    {
        "mvr_person_uuid": "uuid",
        "name": "Sarah Thompson",  // NEW FIELD
        "name_updated_at": "2025-12-19T10:30:00Z",
        "name_updated_by": "manager@store.com",
        "confidence_score": 0.95,
        "quality_score": 0.87,
        "is_super_individual": false,
        "merged_count": 3,
        "total_appearances": 45,
        // ... existing fields
    }
    """
    pass
```

---

#### 3. Bulk Name Update (for group members)

```python
@router.post("/individual-groups/{group_id}/members/update-names")
async def bulk_update_member_names(
    group_id: str,
    request: BulkNameUpdateRequest,
    mvr_repository: MVRRepository = Depends(get_mvr_repository),
    current_user: dict = Depends(get_current_user),
):
    """
    Update names for multiple group members at once.
    
    Request Body:
    {
        "updates": [
            {"mvr_person_uuid": "uuid1", "name": "Sarah"},
            {"mvr_person_uuid": "uuid2", "name": "John"},
            {"mvr_person_uuid": "uuid3", "name": "Mike"}
        ],
        "propagate": true
    }
    
    Returns:
    {
        "success": true,
        "updated_count": 3,
        "total_propagated": 8,  // Including merged records
        "errors": []
    }
    """
    pass
```

---

### Gateway Routing

```python
# File: ppl-meta-gateway/src/api/v1/router.py

# Add routes to proxy to vmeta
@api_router.patch("/mvr-people/{mvr_person_uuid}/name")
async def update_mvr_person_name(request: Request):
    """Proxy MVR person name update to vmeta service."""
    return await proxy_to_vmeta(request, f"/api/v1/mvr-people/{mvr_person_uuid}/name")
```

---

## Merge Scenarios & Name Inheritance Rules

### Scenario 1: Unnamed MVR People Merge

**Before Merge:**
- MVR Person A: `name = NULL`
- MVR Person B: `name = NULL`
- MVR Person C: `name = NULL`

**After Merge:**
- Super-Individual: `name = NULL`
- Constituent MVR A, B, C: `name = NULL`

**User Assigns Name "Alex":**
- Super-Individual: `name = "Alex"`
- Constituent MVR A: `name = "Alex"` (inherited)
- Constituent MVR B: `name = "Alex"` (inherited)
- Constituent MVR C: `name = "Alex"` (inherited)

---

### Scenario 2: One Named + Multiple Unnamed

**Before Merge:**
- MVR Person A: `name = "Jennifer"`
- MVR Person B: `name = NULL`
- MVR Person C: `name = NULL`

**After Merge (Automatic):**
- Super-Individual: `name = "Jennifer"` (inherited from named constituent)
- Constituent MVR A: `name = "Jennifer"` (original)
- Constituent MVR B: `name = "Jennifer"` (inherited)
- Constituent MVR C: `name = "Jennifer"` (inherited)

**Rule**: Named MVR person's name propagates to all unnamed ones

---

### Scenario 3: Multiple Named MVR People (Conflict)

**Before Merge:**
- MVR Person A: `name = "Sarah"`
- MVR Person B: `name = "Sarah Thompson"`
- MVR Person C: `name = "Regular Customer"`

**After Merge (Automatic Consolidation):**
- Super-Individual: `name = "Sarah, Sarah Thompson, Regular Customer"`
- Constituent MVR A: `name = "Sarah"` (original preserved)
- Constituent MVR B: `name = "Sarah Thompson"` (original preserved)
- Constituent MVR C: `name = "Regular Customer"` (original preserved)

**User Edits Super-Individual Name to "Sarah Thompson (VIP)":**
- Super-Individual: `name = "Sarah Thompson (VIP)"`
- Constituent MVR A: `name = "Sarah Thompson (VIP)"` (inherited)
- Constituent MVR B: `name = "Sarah Thompson (VIP)"` (inherited)
- Constituent MVR C: `name = "Sarah Thompson (VIP)"` (inherited)

**Rules**:
1. Concatenate all existing names with comma separator
2. Allow user to edit/clean up consolidated name
3. Edited name propagates to all constituents

---

### Name Propagation Algorithm

```python
# Pseudocode for name propagation

async def propagate_name_to_hierarchy(
    mvr_person_uuid: str,
    new_name: str,
    user_email: str
):
    """
    Propagate name change through MVR merge hierarchy.
    """
    # 1. Update the target MVR person
    await update_mvr_name(mvr_person_uuid, new_name, user_email)
    
    # 2. Find all super-individuals containing this MVR person
    super_individuals = await get_super_individuals_for_mvr(mvr_person_uuid)
    
    for super_uuid in super_individuals:
        # Update super-individual display name
        await update_mvr_name(super_uuid, new_name, user_email, is_super=True)
        
        # 3. Find all constituent MVR people in this super-individual
        constituent_mvrs = await get_constituent_mvr_people(super_uuid)
        
        # 4. Propagate name to all constituents
        for constituent_uuid in constituent_mvrs:
            if constituent_uuid != mvr_person_uuid:  # Skip the one we just updated
                await update_mvr_name(
                    constituent_uuid, 
                    new_name, 
                    user_email,
                    reason='merge_inherit'
                )
    
    # 5. Return list of affected UUIDs
    return {
        'updated': mvr_person_uuid,
        'super_individuals': super_individuals,
        'propagated_to': constituent_mvrs
    }
```

---

### Merge Consolidation Algorithm

```python
# Pseudocode for automatic name consolidation during merge

async def consolidate_names_on_merge(constituent_mvr_uuids: List[str]) -> str:
    """
    Consolidate names when merging multiple MVR people.
    """
    # 1. Get names of all constituent MVR people
    names = []
    for mvr_uuid in constituent_mvr_uuids:
        mvr_record = await get_mvr_person(mvr_uuid)
        if mvr_record.name and mvr_record.name.strip():
            names.append(mvr_record.name.strip())
    
    # 2. Handle cases
    if len(names) == 0:
        # Case 1: No names - return NULL
        return None
    
    elif len(names) == 1:
        # Case 2: One name - use it directly
        return names[0]
    
    else:
        # Case 3: Multiple names - consolidate
        # Remove duplicates while preserving order
        unique_names = []
        for name in names:
            if name not in unique_names:
                unique_names.append(name)
        
        # Join with comma separator
        consolidated = ", ".join(unique_names)
        
        # Truncate if too long (keep within VARCHAR(255))
        if len(consolidated) > 250:
            consolidated = consolidated[:247] + "..."
        
        return consolidated
```

---

## Frontend Implementation

### Data Models

```dart
// File: ppl-meta-frontend/lib/models/mvr_person.dart

class MVRPerson {
  final String mvrPersonUuid;
  final String? name;  // NEW FIELD
  final DateTime? nameUpdatedAt;
  final String? nameUpdatedBy;
  final double confidenceScore;
  final double qualityScore;
  final bool isSuperIndividual;
  final int mergedCount;
  
  // Display name logic
  String get displayName => name ?? mvrPersonUuid.substring(0, 8);
  
  MVRPerson({
    required this.mvrPersonUuid,
    this.name,
    this.nameUpdatedAt,
    this.nameUpdatedBy,
    required this.confidenceScore,
    required this.qualityScore,
    required this.isSuperIndividual,
    required this.mergedCount,
  });
  
  factory MVRPerson.fromJson(Map<String, dynamic> json) {
    return MVRPerson(
      mvrPersonUuid: json['mvr_person_uuid'] as String,
      name: json['name'] as String?,  // NEW
      nameUpdatedAt: json['name_updated_at'] != null 
          ? DateTime.parse(json['name_updated_at'] as String)
          : null,
      nameUpdatedBy: json['name_updated_by'] as String?,
      // ... existing fields
    );
  }
}
```

---

### API Service

```dart
// File: ppl-meta-frontend/lib/services/mvr_api_client.dart

class MVRApiClient {
  final ApiClient _apiClient;
  
  MVRApiClient(this._apiClient);
  
  /// Update MVR person name with propagation
  Future<ApiResponse<Map<String, dynamic>>> updateMVRPersonName({
    required String mvrPersonUuid,
    required String name,
    bool propagate = true,
  }) async {
    try {
      final response = await _apiClient.patch(
        '/api/v1/mvr-people/$mvrPersonUuid/name',
        data: {
          'name': name,
          'propagate': propagate,
        },
      );
      
      return ApiResponse.success(response.data as Map<String, dynamic>);
    } catch (e) {
      return ApiResponse.error('Failed to update name: $e');
    }
  }
  
  /// Clear MVR person name
  Future<ApiResponse<void>> clearMVRPersonName({
    required String mvrPersonUuid,
  }) async {
    return updateMVRPersonName(
      mvrPersonUuid: mvrPersonUuid,
      name: '',  // Empty string clears the name
      propagate: true,
    );
  }
}
```

---

### UI Components

#### 1. Editable Name Display

```dart
// File: ppl-meta-frontend/lib/widgets/editable_mvr_name.dart

class EditableMVRName extends StatefulWidget {
  final String mvrPersonUuid;
  final String? currentName;
  final Function(String) onNameUpdated;
  
  const EditableMVRName({
    Key? key,
    required this.mvrPersonUuid,
    this.currentName,
    required this.onNameUpdated,
  }) : super(key: key);
  
  @override
  _EditableMVRNameState createState() => _EditableMVRNameState();
}

class _EditableMVRNameState extends State<EditableMVRName> {
  bool _isEditing = false;
  late TextEditingController _controller;
  
  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.currentName ?? '');
  }
  
  Widget build(BuildContext context) {
    if (_isEditing) {
      return Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              decoration: InputDecoration(
                hintText: 'Enter name...',
                isDense: true,
              ),
              autofocus: true,
              onSubmitted: _saveName,
            ),
          ),
          IconButton(
            icon: Icon(Icons.check, color: Colors.green),
            onPressed: _saveName,
          ),
          IconButton(
            icon: Icon(Icons.close, color: Colors.red),
            onPressed: () => setState(() => _isEditing = false),
          ),
        ],
      );
    }
    
    return GestureDetector(
      onTap: () => setState(() => _isEditing = true),
      child: Row(
        children: [
          Expanded(
            child: Text(
              widget.currentName ?? widget.mvrPersonUuid.substring(0, 8),
              style: TextStyle(
                fontWeight: widget.currentName != null 
                    ? FontWeight.bold 
                    : FontWeight.normal,
                color: widget.currentName != null 
                    ? Colors.black 
                    : Colors.grey,
              ),
            ),
          ),
          Icon(Icons.edit, size: 16, color: Colors.blue),
        ],
      ),
    );
  }
  
  void _saveName() async {
    final name = _controller.text.trim();
    
    // Show loading indicator
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => Center(child: CircularProgressIndicator()),
    );
    
    try {
      final apiClient = context.read<ApiClient>();
      final mvrApiClient = MVRApiClient(apiClient);
      
      final response = await mvrApiClient.updateMVRPersonName(
        mvrPersonUuid: widget.mvrPersonUuid,
        name: name,
        propagate: true,
      );
      
      Navigator.of(context).pop(); // Dismiss loading
      
      if (response.success) {
        widget.onNameUpdated(name);
        setState(() => _isEditing = false);
        
        // Show success message
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Name updated successfully'),
            backgroundColor: Colors.green,
          ),
        );
      } else {
        throw Exception(response.error);
      }
    } catch (e) {
      Navigator.of(context).pop(); // Dismiss loading
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to update name: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
}
```

---

#### 2. Individual Groups Member Card with Name

```dart
// File: ppl-meta-frontend/lib/screens/individual_group_detail_screen.dart

Widget _buildMemberCard(GroupMember member) {
  return Card(
    child: ListTile(
      // Face thumbnail
      leading: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: _buildMemberThumbnail(member),
      ),
      
      // Editable name
      title: EditableMVRName(
        mvrPersonUuid: member.mvrPersonUuid,
        currentName: member.name,  // NEW FIELD
        onNameUpdated: (newName) {
          setState(() {
            // Update local state
            final index = _members.indexWhere(
              (m) => m.mvrPersonUuid == member.mvrPersonUuid
            );
            if (index != -1) {
              _members[index] = member.copyWith(name: newName);
            }
          });
        },
      ),
      
      // Member stats
      subtitle: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (member.name != null)
            Text(
              'UUID: ${member.mvrPersonUuid.substring(0, 8)}...',
              style: TextStyle(fontSize: 10, color: Colors.grey),
            ),
          Text('${member.totalAppearances} appearances'),
          Text('Last seen: ${_formatTimestamp(member.lastSeen)}'),
        ],
      ),
      
      // Actions
      trailing: PopupMenuButton(
        itemBuilder: (context) => [
          PopupMenuItem(
            child: Text('Edit Name'),
            onTap: () => _showEditNameDialog(member),
          ),
          PopupMenuItem(
            child: Text('Clear Name'),
            onTap: () => _clearMemberName(member),
          ),
          PopupMenuItem(
            child: Text('Remove from Group'),
            onTap: () => _removeMember(member),
          ),
        ],
      ),
    ),
  );
}
```

---

#### 3. Cross-Video Analysis Card with Name

```dart
// File: ppl-meta-frontend/lib/screens/person_objects_detail_screen.dart

Widget _buildIndividualCard(AggregatedIndividualAnalysis analysis, int index) {
  final isSuperIndividual = analysis.isSuperIndividual ?? false;
  final isExpanded = _expandedIndividuals.contains(analysis.individualUuid);
  final isSelected = _selectedIndividuals.contains(analysis.individualUuid);
  
  return Card(
    child: Column(
      children: [
        InkWell(
          onTap: () => _toggleExpansion(analysis.individualUuid),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Row(
              children: [
                // Checkbox
                Checkbox(
                  value: isSelected,
                  onChanged: (value) => _toggleSelection(analysis.individualUuid),
                ),
                
                // Face thumbnail
                Container(
                  width: 60,
                  height: 60,
                  child: _buildIndividualThumbnail(
                    analysis.individualId,
                    isSuperIndividual,
                  ),
                ),
                
                SizedBox(width: 16),
                
                // Name and stats
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Editable name or UUID
                      EditableMVRName(
                        mvrPersonUuid: analysis.individualId,
                        currentName: analysis.name,  // NEW FIELD
                        onNameUpdated: (newName) {
                          setState(() {
                            // Update local state
                            final index = _aggregatedAnalyses!.indexWhere(
                              (a) => a.individualUuid == analysis.individualUuid
                            );
                            if (index != -1) {
                              _aggregatedAnalyses![index] = analysis.copyWith(name: newName);
                            }
                          });
                        },
                      ),
                      
                      SizedBox(height: 4),
                      
                      // Stats row
                      Wrap(
                        spacing: 8,
                        children: [
                          _buildStatChip(
                            Icons.video_library,
                            '${analysis.uniqueVideos} videos',
                          ),
                          _buildStatChip(
                            Icons.visibility,
                            '${analysis.totalAppearances} appearances',
                          ),
                          if (isSuperIndividual)
                            _buildStatChip(
                              Icons.merge_type,
                              'Merged: ${analysis.mergedMVRCount}',
                              color: Colors.blue,
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
                
                // Expand icon
                Icon(
                  isExpanded ? Icons.expand_less : Icons.expand_more,
                  color: Colors.grey,
                ),
              ],
            ),
          ),
        ),
        
        // Expanded appearances
        if (isExpanded)
          _buildExpandedAppearances(analysis),
      ],
    ),
  );
}
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

**Objectives:**
- Database schema changes
- Basic API endpoints
- Name storage and retrieval

**Deliverables:**
- ✅ Migration script: `01X_add_mvr_people_names.sql`
- ✅ Backend endpoint: `PATCH /api/v1/mvr-people/{uuid}/name`
- ✅ Backend endpoint: `GET /api/v1/mvr-people/{uuid}` (with name field)
- ✅ Updated MVR repository methods
- ✅ Unit tests for name CRUD operations

**Acceptance Criteria:**
- Names can be assigned and retrieved via API
- Names persist correctly in database
- API returns 400 for invalid names (>255 chars)

---

### Phase 2: Name Propagation Logic (Week 2)

**Objectives:**
- Implement merge hierarchy traversal
- Name inheritance algorithms
- Automatic consolidation on merge

**Deliverables:**
- ✅ `propagate_name_to_hierarchy()` function
- ✅ `consolidate_names_on_merge()` function
- ✅ Update merge service to trigger name consolidation
- ✅ Name history tracking (optional)
- ✅ Integration tests for propagation scenarios

**Acceptance Criteria:**
- Editing super-individual name updates all constituents
- Merging named + unnamed MVR people inherits name correctly
- Merging multiple named MVR people consolidates names
- Scenario 1, 2, 3 all work as specified

---

### Phase 3: Frontend Integration (Week 3)

**Objectives:**
- UI components for name editing
- Update Individual Groups screen
- Update Cross-Video Analysis screen

**Deliverables:**
- ✅ `EditableMVRName` widget
- ✅ `MVRApiClient.updateMVRPersonName()` method
- ✅ Update `IndividualGroupDetailScreen` member cards
- ✅ Update `PersonObjectsDetailScreen` individual cards
- ✅ Name display in search results
- ✅ Frontend unit tests

**Acceptance Criteria:**
- Users can click name/UUID to edit inline
- Name updates show loading indicator
- Success/error messages display correctly
- Names appear consistently across all screens

---

### Phase 4: Bulk Operations & UX Polish (Week 4)

**Objectives:**
- Bulk name updates
- Import/export with names
- Advanced search by name
- Performance optimization

**Deliverables:**
- ✅ Bulk name update API endpoint
- ✅ CSV import/export with names
- ✅ Name search in Individual Groups
- ✅ Autocomplete suggestions (recently used names)
- ✅ Name validation and sanitization
- ✅ Performance testing (10,000+ MVR people)

**Acceptance Criteria:**
- Bulk update processes 100+ names in <5 seconds
- CSV export includes name column
- Search finds MVR people by partial name match
- Autocomplete shows last 20 unique names

---

## Data Validation & Constraints

### Name Validation Rules

```python
# Validation logic

def validate_mvr_name(name: str) -> Tuple[bool, Optional[str]]:
    """
    Validate MVR person name.
    
    Returns:
        (is_valid, error_message)
    """
    if not name:
        return (True, None)  # Empty name is OK (clears name)
    
    # Length check
    if len(name) > 255:
        return (False, "Name must be 255 characters or less")
    
    # No leading/trailing whitespace
    if name != name.strip():
        return (False, "Name cannot have leading or trailing spaces")
    
    # Optional: No special characters (customize as needed)
    # if not re.match(r'^[a-zA-Z0-9\s\-.,()]+$', name):
    #     return (False, "Name contains invalid characters")
    
    # No control characters
    if any(ord(c) < 32 for c in name):
        return (False, "Name contains invalid control characters")
    
    return (True, None)
```

---

### Database Constraints

```sql
-- Additional constraints

-- Prevent names that are just whitespace
ALTER TABLE mvr_people 
ADD CONSTRAINT mvr_name_not_whitespace 
CHECK (name IS NULL OR LENGTH(TRIM(name)) > 0);

-- Prevent excessively long names
ALTER TABLE mvr_people 
ADD CONSTRAINT mvr_name_length 
CHECK (name IS NULL OR LENGTH(name) <= 255);
```

---

## Security Considerations

### Access Control

1. **Authentication Required**: All name update endpoints require valid JWT token
2. **Authorization**: Users can only update names for MVR people in their organization/workspace
3. **Audit Trail**: All name changes recorded with user email and timestamp
4. **Rate Limiting**: Limit name updates to 100 per minute per user

### Input Sanitization

```python
# Sanitize user input

def sanitize_mvr_name(name: str) -> str:
    """
    Sanitize user-provided name.
    """
    if not name:
        return ""
    
    # Remove leading/trailing whitespace
    name = name.strip()
    
    # Replace multiple spaces with single space
    name = re.sub(r'\s+', ' ', name)
    
    # Remove any null bytes
    name = name.replace('\x00', '')
    
    # Truncate to max length
    if len(name) > 255:
        name = name[:255]
    
    return name
```

---

## Search & Filtering Enhancements

### Search by Name

```python
# Add to MVR repository

async def search_mvr_people_by_name(
    self,
    query: str,
    limit: int = 50,
    offset: int = 0
) -> List[MVRPerson]:
    """
    Search MVR people by name (case-insensitive partial match).
    """
    query = f"%{query.lower()}%"
    
    async with self.pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM mvr_people
            WHERE name ILIKE $1
            AND is_orphaned = FALSE
            ORDER BY name ASC
            LIMIT $2 OFFSET $3
            """,
            query, limit, offset
        )
        
        return [MVRPerson.from_db_row(row) for row in rows]
```

### Individual Groups Filtering

```dart
// Add name filter to Individual Groups screen

Widget _buildMemberFilters() {
  return Row(
    children: [
      Expanded(
        child: TextField(
          decoration: InputDecoration(
            labelText: 'Search by name',
            prefixIcon: Icon(Icons.search),
            suffixIcon: _nameFilter.isNotEmpty
                ? IconButton(
                    icon: Icon(Icons.clear),
                    onPressed: () => setState(() => _nameFilter = ''),
                  )
                : null,
          ),
          onChanged: (value) {
            setState(() {
              _nameFilter = value;
              _filterMembers();
            });
          },
        ),
      ),
      
      SizedBox(width: 16),
      
      // Show only named / unnamed toggle
      SegmentedButton<String>(
        segments: [
          ButtonSegment(value: 'all', label: Text('All')),
          ButtonSegment(value: 'named', label: Text('Named Only')),
          ButtonSegment(value: 'unnamed', label: Text('Unnamed Only')),
        ],
        selected: {_nameFilterMode},
        onSelectionChanged: (Set<String> newSelection) {
          setState(() {
            _nameFilterMode = newSelection.first;
            _filterMembers();
          });
        },
      ),
    ],
  );
}

void _filterMembers() {
  _filteredMembers = _members.where((member) {
    // Apply name search filter
    if (_nameFilter.isNotEmpty) {
      final name = member.name?.toLowerCase() ?? '';
      final uuid = member.mvrPersonUuid.toLowerCase();
      if (!name.contains(_nameFilter.toLowerCase()) &&
          !uuid.contains(_nameFilter.toLowerCase())) {
        return false;
      }
    }
    
    // Apply named/unnamed filter
    if (_nameFilterMode == 'named' && member.name == null) {
      return false;
    }
    if (_nameFilterMode == 'unnamed' && member.name != null) {
      return false;
    }
    
    return true;
  }).toList();
}
```

---

## Export & Reporting

### CSV Export with Names

```python
# Update CSV export to include names

async def export_group_members_csv(
    group_id: str,
    include_names: bool = True
) -> str:
    """
    Export group members to CSV including names.
    """
    members = await get_group_members(group_id)
    
    csv_rows = []
    headers = [
        'MVR Person UUID',
        'Name',  # NEW COLUMN
        'Total Appearances',
        'First Seen',
        'Last Seen',
        'Confidence Score',
        'Is Super Individual',
        'Merged Count'
    ]
    csv_rows.append(headers)
    
    for member in members:
        csv_rows.append([
            member.mvr_person_uuid,
            member.name or '',  # Include name or empty string
            member.total_appearances,
            member.first_seen.isoformat(),
            member.last_seen.isoformat(),
            f"{member.confidence_score:.3f}",
            'Yes' if member.is_super_individual else 'No',
            member.merged_count
        ])
    
    # Convert to CSV string
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerows(csv_rows)
    
    return output.getvalue()
```

---

## Testing Strategy

### Unit Tests

```python
# Test name CRUD operations

async def test_update_mvr_name():
    """Test updating MVR person name."""
    # Create test MVR person
    mvr_uuid = await create_test_mvr_person()
    
    # Update name
    result = await update_mvr_person_name(
        mvr_uuid,
        "Test Name",
        user_email="test@example.com"
    )
    
    assert result['success'] == True
    assert result['name'] == "Test Name"
    
    # Verify in database
    mvr = await get_mvr_person(mvr_uuid)
    assert mvr.name == "Test Name"
    assert mvr.name_updated_by == "test@example.com"

async def test_name_propagation():
    """Test name propagates to merged MVR people."""
    # Create 3 MVR people and merge them
    mvr1 = await create_test_mvr_person()
    mvr2 = await create_test_mvr_person()
    mvr3 = await create_test_mvr_person()
    
    super_uuid = await merge_mvr_people([mvr1, mvr2, mvr3])
    
    # Update super-individual name
    await update_mvr_person_name(
        super_uuid,
        "Merged Person",
        user_email="test@example.com",
        propagate=True
    )
    
    # Verify all constituents have the name
    for mvr_uuid in [mvr1, mvr2, mvr3]:
        mvr = await get_mvr_person(mvr_uuid)
        assert mvr.name == "Merged Person"

async def test_name_consolidation():
    """Test name consolidation on merge."""
    # Create 3 MVR people with different names
    mvr1 = await create_test_mvr_person(name="Alice")
    mvr2 = await create_test_mvr_person(name="Alice Smith")
    mvr3 = await create_test_mvr_person(name=None)
    
    # Merge them
    super_uuid = await merge_mvr_people([mvr1, mvr2, mvr3])
    
    # Verify consolidated name
    super_mvr = await get_mvr_person(super_uuid)
    assert super_mvr.name == "Alice, Alice Smith"
```

### Integration Tests

```python
# Test API endpoints

async def test_update_name_api(client: TestClient):
    """Test name update API endpoint."""
    mvr_uuid = await create_test_mvr_person()
    
    response = await client.patch(
        f"/api/v1/mvr-people/{mvr_uuid}/name",
        json={"name": "John Doe", "propagate": True},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data['success'] == True
    assert data['name'] == "John Doe"
```

### Frontend Tests

```dart
// Widget test for editable name

testWidgets('EditableMVRName allows editing', (WidgetTester tester) async {
  String? updatedName;
  
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: EditableMVRName(
          mvrPersonUuid: 'test-uuid',
          currentName: 'Original Name',
          onNameUpdated: (name) => updatedName = name,
        ),
      ),
    ),
  );
  
  // Tap to enter edit mode
  await tester.tap(find.byType(GestureDetector));
  await tester.pumpAndSettle();
  
  // Verify text field appears
  expect(find.byType(TextField), findsOneWidget);
  
  // Enter new name
  await tester.enterText(find.byType(TextField), 'New Name');
  await tester.tap(find.byIcon(Icons.check));
  await tester.pumpAndSettle();
  
  // Verify callback was called
  expect(updatedName, 'New Name');
});
```

---

## Performance Considerations

### Database Indexing

```sql
-- Optimize name lookups
CREATE INDEX idx_mvr_people_name_trgm ON mvr_people 
USING gin (name gin_trgm_ops) 
WHERE name IS NOT NULL;

-- Enable trigram extension for fuzzy search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### Caching Strategy

```python
# Cache frequently accessed MVR names

from functools import lru_cache
import asyncio

class MVRNameCache:
    def __init__(self, max_size=1000, ttl_seconds=300):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl_seconds
    
    async def get(self, mvr_uuid: str) -> Optional[str]:
        if mvr_uuid in self.cache:
            name, timestamp = self.cache[mvr_uuid]
            if time.time() - timestamp < self.ttl:
                return name
        
        # Cache miss - fetch from database
        mvr = await get_mvr_person(mvr_uuid)
        self.cache[mvr_uuid] = (mvr.name, time.time())
        
        # Evict old entries if cache too large
        if len(self.cache) > self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        return mvr.name
    
    def invalidate(self, mvr_uuid: str):
        """Invalidate cache entry when name changes."""
        if mvr_uuid in self.cache:
            del self.cache[mvr_uuid]
```

---

## Migration & Rollout Plan

### Database Migration

```sql
-- Migration script (can be run on production with minimal downtime)

BEGIN;

-- 1. Add columns (fast, no table lock)
ALTER TABLE mvr_people 
ADD COLUMN IF NOT EXISTS name VARCHAR(255) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS name_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL,
ADD COLUMN IF NOT EXISTS name_updated_by VARCHAR(255) DEFAULT NULL;

-- 2. Create indexes (can run concurrently)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_mvr_people_name 
ON mvr_people(name) WHERE name IS NOT NULL;

-- 3. Add constraints
ALTER TABLE mvr_people 
ADD CONSTRAINT mvr_name_not_whitespace 
CHECK (name IS NULL OR LENGTH(TRIM(name)) > 0);

COMMIT;
```

### Feature Flag

```python
# Gradual rollout with feature flag

from config import Settings

settings = Settings()

def is_naming_feature_enabled(user: dict) -> bool:
    """
    Check if naming feature is enabled for user.
    """
    # Enable for all users after testing
    if settings.NAMING_FEATURE_ENABLED:
        return True
    
    # Or enable for specific organizations during beta
    if user.get('organization_id') in settings.NAMING_BETA_ORGS:
        return True
    
    return False
```

---

## Success Metrics

### Key Performance Indicators (KPIs)

1. **Adoption Rate**:
   - Target: 60% of group members have names within 30 days
   - Measure: `COUNT(DISTINCT mvr_people_uuid WHERE name IS NOT NULL) / COUNT(DISTINCT mvr_people_uuid)`

2. **Name Edit Frequency**:
   - Target: Average 2-3 edits per named MVR person
   - Measure: Track via `mvr_people_name_history` table

3. **Search Usage**:
   - Target: 40% of Individual Groups searches use name filter
   - Measure: Track search queries with name parameter

4. **User Satisfaction**:
   - Target: 80% positive feedback on naming feature
   - Measure: In-app survey after using feature

5. **Performance**:
   - Target: Name update completes in <500ms
   - Measure: API response time monitoring

---

## Future Enhancements

### Phase 5+: Advanced Features

1. **Auto-Naming from Integrations**:
   - Import names from CRM systems
   - Sync with employee directories
   - Badge/ID card recognition

2. **Smart Name Suggestions**:
   - ML-based name recommendations
   - Detect common patterns (e.g., "Customer #123")
   - Suggest names based on demographics/appearance

3. **Name Aliases**:
   - Multiple names per MVR person
   - Primary name + aliases
   - Useful for multilingual environments

4. **Name Templates**:
   - Predefined naming schemes
   - Auto-increment counters (e.g., "VIP-001", "VIP-002")
   - Template variables (e.g., "{gender}-{age_group}-{date}")

5. **Advanced Merge Conflict Resolution**:
   - UI to review name conflicts before merge
   - User can choose which name to keep
   - Merge history shows original names

---

## Conclusion

The Individual Naming System provides a robust, user-friendly solution for assigning human-readable names to MVR people in Individual Groups. The design handles complex merge scenarios intelligently while maintaining data integrity and user expectations.

**Key Benefits**:
- ✅ Improved user experience with recognizable names
- ✅ Simplified group member management
- ✅ Automatic name inheritance on merge
- ✅ Flexible editing with full propagation
- ✅ Backward compatible (names optional)

**Next Steps**:
1. Review and approve proposal
2. Create implementation tickets in project management system
3. Begin Phase 1 development
4. Schedule demo for stakeholders after Phase 3

---

## Appendix

### Example API Requests

#### Update Name

```bash
curl -X PATCH http://localhost:8080/api/v1/mvr-people/b24ad688-26f0-4e1e-9484-4fecec18df9c/name \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sarah Thompson",
    "propagate": true
  }'
```

Response:
```json
{
  "success": true,
  "mvr_person_uuid": "b24ad688-26f0-4e1e-9484-4fecec18df9c",
  "name": "Sarah Thompson",
  "updated_at": "2025-12-19T10:30:00Z",
  "propagated_to": [
    "uuid1",
    "uuid2", 
    "uuid3"
  ],
  "affected_super_individuals": [
    "super_uuid1"
  ]
}
```

#### Clear Name

```bash
curl -X PATCH http://localhost:8080/api/v1/mvr-people/b24ad688-26f0-4e1e-9484-4fecec18df9c/name \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "",
    "propagate": true
  }'
```

---

### Database Schema Reference

```sql
-- Final schema with all enhancements

CREATE TABLE mvr_people (
    mvr_people_uuid UUID PRIMARY KEY,
    name VARCHAR(255) DEFAULT NULL,
    name_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL,
    name_updated_by VARCHAR(255) DEFAULT NULL,
    confidence_score DOUBLE PRECISION,
    quality_score DOUBLE PRECISION,
    is_orphaned BOOLEAN DEFAULT FALSE,
    is_super_individual BOOLEAN DEFAULT FALSE,
    merged_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT mvr_name_not_whitespace 
        CHECK (name IS NULL OR LENGTH(TRIM(name)) > 0),
    CONSTRAINT mvr_name_length 
        CHECK (name IS NULL OR LENGTH(name) <= 255)
);

CREATE INDEX idx_mvr_people_name ON mvr_people(name) WHERE name IS NOT NULL;
CREATE INDEX idx_mvr_people_name_search ON mvr_people(name text_pattern_ops) WHERE name IS NOT NULL;

CREATE TABLE mvr_people_name_history (
    id SERIAL PRIMARY KEY,
    mvr_people_uuid UUID NOT NULL REFERENCES mvr_people(mvr_people_uuid) ON DELETE CASCADE,
    old_name VARCHAR(255),
    new_name VARCHAR(255),
    changed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    changed_by VARCHAR(255),
    reason VARCHAR(50) CHECK (reason IN ('user_edit', 'merge_inherit', 'merge_consolidate'))
);

CREATE INDEX idx_name_history_mvr ON mvr_people_name_history(mvr_people_uuid);
CREATE INDEX idx_name_history_timestamp ON mvr_people_name_history(changed_at DESC);
```

---

**End of Proposal**
