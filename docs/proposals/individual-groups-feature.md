# Individual Groups Feature Proposal

**Version:** 1.0.0  
**Date:** December 16, 2025  
**Status:** Proposal  
**Author:** System Architecture Team

---

## Executive Summary

This proposal outlines the design and implementation of an **Individual Groups** feature that allows users to organize and manage detected individuals across multiple videos through a collection-based system. The feature mirrors the existing media collections UX pattern while introducing enhanced individual management capabilities.

---

## Table of Contents

1. [Overview](#overview)
2. [User Stories](#user-stories)
3. [Architecture](#architecture)
4. [Data Models](#data-models)
5. [API Design](#api-design)
6. [UI/UX Design](#uiux-design)
7. [Implementation Phases](#implementation-phases)
8. [Technical Considerations](#technical-considerations)
9. [Testing Strategy](#testing-strategy)
10. [Migration & Rollout](#migration--rollout)

---

## 1. Overview

### 1.1 Problem Statement

Currently, users can view and analyze individuals detected across videos, but there's no way to:
- Organize individuals into meaningful groups (e.g., "VIP Customers", "Staff", "Regulars")
- Bulk manage multiple individuals
- Quick-access frequently analyzed individuals
- Share individual analysis with team members

### 1.2 Proposed Solution

Implement a **vmeta-based Individual Groups service** that provides:
- Full CRUD operations for individual groups
- Thumbnail-based grid view matching media collections UX
- Bulk selection and group assignment
- Preview dialogs with detailed individual information
- Seamless navigation to existing cross-video individual analysis

### 1.3 Key Requirements

✅ **Service Location:** vmeta service  
✅ **UX Pattern:** Match media collections interface  
✅ **Thumbnail System:** Individual photos with fallback placeholders  
✅ **Bulk Operations:** Multi-select and batch actions  
✅ **Integration:** Navigate to existing cross-video analysis screen  
✅ **CRUD Screen:** Dedicated individual groups management interface

---

## 2. User Stories

### 2.1 Core User Stories

**US-1: Create Individual Group**
```
AS A user
I WANT TO create a new individual group with a name and description
SO THAT I can organize detected individuals into meaningful categories
```

**US-2: Browse Individual Groups**
```
AS A user
I WANT TO see all my individual groups in a grid/list view
SO THAT I can quickly access organized collections of individuals
```

**US-3: View Group Members**
```
AS A user
I WANT TO see all individuals within a group as thumbnails
SO THAT I can visually identify and select specific individuals
```

**US-4: Add Individuals to Group**
```
AS A user
I WANT TO add selected individuals to a group from the analysis screen
SO THAT I can organize individuals without leaving my workflow
```

**US-5: Preview Individual Details**
```
AS A user
I WANT TO click an individual thumbnail and see a preview dialog
SO THAT I can view details, collections, and actions without full navigation
```

**US-6: Bulk Select and Navigate**
```
AS A user
I WANT TO select multiple individual thumbnails and view them together
SO THAT I can analyze multiple individuals in the cross-video screen
```

### 2.2 Advanced User Stories

**US-7: Remove from Group**
```
AS A user
I WANT TO remove individuals from a group
SO THAT I can keep groups relevant and up-to-date
```

**US-8: Delete Group**
```
AS A user
I WANT TO delete an individual group
SO THAT I can remove obsolete organizational structures
```

**US-9: Search Within Group**
```
AS A user
I WANT TO search/filter individuals within a group
SO THAT I can quickly find specific people
```

**US-10: Group Metadata**
```
AS A user
I WANT TO see group statistics (member count, last updated, etc.)
SO THAT I can understand group relevance at a glance
```

---

## 3. Architecture

### 3.1 Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Flutter)                    │
│  ┌────────────────┐  ┌──────────────────┐  ┌─────────────┐ │
│  │ Individual     │  │ Cross-Video      │  │ Media       │ │
│  │ Groups Screen  │  │ Analysis Screen  │  │ Collections │ │
│  └────────┬───────┘  └────────┬─────────┘  └──────┬──────┘ │
└───────────┼──────────────────┼────────────────────┼─────────┘
            │                  │                    │
            ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway (8080)                       │
│                   Route: /api/v1/individual-groups/*         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    vmeta Service (8008)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Individual Groups Manager                   │  │
│  │  • CRUD Operations                                    │  │
│  │  • Member Management                                  │  │
│  │  • Thumbnail Generation                               │  │
│  │  • Search & Filtering                                 │  │
│  └────────────────────┬─────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────┴─────────────────────────────────┐  │
│  │           Existing vmeta Components                   │  │
│  │  • Individual Tracking                                │  │
│  │  • Person Repository                                  │  │
│  │  • Cross-Video Linking                                │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Qdrant Vector DB                          │
│  • Individual Embeddings                                     │
│  • Individual Groups Collection                              │
│  • Group Membership Index                                    │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Component Responsibilities

#### 3.2.1 Frontend Components

**`IndividualGroupsScreen`** (New)
- Grid/list view of all individual groups
- Group CRUD operations UI
- Navigation to group details
- Search and filter groups

**`IndividualGroupDetailScreen`** (New)
- Display group members as thumbnails
- Bulk selection interface
- Add/remove members
- Navigate to cross-video analysis

**`IndividualThumbnailCard`** (New)
- Display individual thumbnail or placeholder
- Selection checkbox
- Quick actions menu
- Click → Preview dialog

**`IndividualPreviewDialog`** (New)
- Tabs: Details, Collections, Actions
- Similar to media preview dialog
- Navigate to full analysis button

**`CrossVideoIndividualAnalysisScreen`** (Existing - Enhanced)
- Accept group-based navigation
- Display selected individuals from group
- Enhanced "Add to Group" action

#### 3.2.2 Backend Services

**`IndividualGroupsManager`** (New - vmeta)
```python
# Location: ppl-meta-vmeta/src/services/individual_groups_manager.py

class IndividualGroupsManager:
    """
    Manages individual groups, their members, and related operations.
    """
    
    async def create_group(self, name: str, description: str, 
                          created_by: str) -> IndividualGroup
    
    async def get_group(self, group_id: str) -> IndividualGroup
    
    async def list_groups(self, user_id: str = None, 
                         skip: int = 0, limit: int = 50) -> List[IndividualGroup]
    
    async def update_group(self, group_id: str, 
                          updates: IndividualGroupUpdate) -> IndividualGroup
    
    async def delete_group(self, group_id: str) -> bool
    
    async def add_members(self, group_id: str, 
                         individual_ids: List[str]) -> IndividualGroup
    
    async def remove_members(self, group_id: str, 
                            individual_ids: List[str]) -> IndividualGroup
    
    async def get_group_members(self, group_id: str, 
                               skip: int = 0, limit: int = 50) -> List[Individual]
    
    async def get_individual_groups(self, individual_id: str) -> List[IndividualGroup]
```

**`IndividualThumbnailService`** (New - vmeta)
```python
# Location: ppl-meta-vmeta/src/services/individual_thumbnail_service.py

class IndividualThumbnailService:
    """
    Generates and manages thumbnails for individuals.
    """
    
    async def generate_thumbnail(self, individual_id: str) -> str
    
    async def get_thumbnail_url(self, individual_id: str) -> Optional[str]
    
    async def get_best_quality_frame(self, individual_id: str) -> bytes
    
    async def update_thumbnail(self, individual_id: str, 
                              image_data: bytes) -> str
```

---

## 4. Data Models

### 4.1 Database Schema

#### 4.1.1 Individual Group

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class GroupVisibility(str, Enum):
    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"

class IndividualGroup(BaseModel):
    """
    Represents a collection of individuals organized by the user.
    """
    id: str = Field(..., description="Unique group identifier (UUID)")
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    
    created_by: str = Field(..., description="User ID who created the group")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    member_count: int = Field(default=0, ge=0)
    member_ids: List[str] = Field(default_factory=list, 
                                   description="Individual IDs in this group")
    
    visibility: GroupVisibility = Field(default=GroupVisibility.PRIVATE)
    tags: List[str] = Field(default_factory=list)
    
    # Thumbnail settings
    cover_individual_id: Optional[str] = Field(None, 
                                               description="Individual ID for group thumbnail")
    
    # Metadata
    metadata: dict = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "grp_abc123xyz",
                "name": "VIP Customers",
                "description": "High-value customers identified across stores",
                "created_by": "user_456",
                "member_count": 15,
                "visibility": "private",
                "tags": ["vip", "loyalty", "store-a"]
            }
        }
```

#### 4.1.2 Group Membership

```python
class GroupMembership(BaseModel):
    """
    Junction table for many-to-many relationship between groups and individuals.
    """
    id: str = Field(..., description="Membership record ID")
    group_id: str
    individual_id: str
    
    added_by: str = Field(..., description="User ID who added this member")
    added_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Optional member-specific notes
    notes: Optional[str] = None
    
    class Config:
        indexes = [
            ("group_id", "individual_id"),  # Composite unique index
            "individual_id",                 # For reverse lookups
        ]
```

#### 4.1.3 Individual (Enhanced)

```python
class Individual(BaseModel):
    """
    Enhanced individual model with group support.
    """
    id: str = Field(..., description="Unique individual identifier")
    
    # Existing fields...
    first_seen: datetime
    last_seen: datetime
    total_appearances: int
    confidence_score: float
    
    # NEW: Group relationships
    group_ids: List[str] = Field(default_factory=list, 
                                  description="Groups this individual belongs to")
    
    # NEW: Thumbnail data
    thumbnail_url: Optional[str] = None
    best_frame_video_id: Optional[str] = None
    best_frame_timestamp: Optional[float] = None
    
    # Existing demographics, embeddings, etc...
```

### 4.2 API Request/Response Models

#### 4.2.1 Create Group Request

```python
class CreateIndividualGroupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    visibility: GroupVisibility = Field(default=GroupVisibility.PRIVATE)
    tags: List[str] = Field(default_factory=list)
    initial_member_ids: List[str] = Field(default_factory=list)
```

#### 4.2.2 Update Group Request

```python
class UpdateIndividualGroupRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    visibility: Optional[GroupVisibility] = None
    tags: Optional[List[str]] = None
    cover_individual_id: Optional[str] = None
```

#### 4.2.3 Add Members Request

```python
class AddGroupMembersRequest(BaseModel):
    individual_ids: List[str] = Field(..., min_items=1)
    notes: Optional[str] = None
```

#### 4.2.4 Group Response

```python
class IndividualGroupResponse(BaseModel):
    group: IndividualGroup
    members_preview: List[IndividualSummary] = Field(
        default_factory=list,
        description="First 5 members for preview"
    )
    
class IndividualSummary(BaseModel):
    """Lightweight individual data for list views"""
    id: str
    thumbnail_url: Optional[str]
    total_appearances: int
    last_seen: datetime
    group_count: int
```

---

## 5. API Design

### 5.1 RESTful Endpoints

**Base Path:** `/api/v1/individual-groups`  
**Service:** vmeta (port 8008)  
**Gateway Route:** Proxied through API Gateway (8080)

#### 5.1.1 Group Management

```http
# List all groups
GET /api/v1/individual-groups
Query Params:
  - user_id: string (optional, filter by creator)
  - visibility: enum (optional, filter by visibility)
  - tags: string[] (optional, filter by tags)
  - search: string (optional, search in name/description)
  - skip: int (default: 0)
  - limit: int (default: 50, max: 200)
Response: 200 OK
{
  "groups": [IndividualGroup],
  "total": int,
  "skip": int,
  "limit": int
}

# Create new group
POST /api/v1/individual-groups
Body: CreateIndividualGroupRequest
Response: 201 Created
{
  "group": IndividualGroup
}

# Get single group
GET /api/v1/individual-groups/{group_id}
Response: 200 OK
{
  "group": IndividualGroup,
  "members": [IndividualSummary]
}

# Update group
PATCH /api/v1/individual-groups/{group_id}
Body: UpdateIndividualGroupRequest
Response: 200 OK
{
  "group": IndividualGroup
}

# Delete group
DELETE /api/v1/individual-groups/{group_id}
Query Params:
  - remove_members: bool (default: false, if true removes members too)
Response: 204 No Content
```

#### 5.1.2 Member Management

```http
# Get group members
GET /api/v1/individual-groups/{group_id}/members
Query Params:
  - skip: int (default: 0)
  - limit: int (default: 50)
  - sort: enum (added_date, appearances, last_seen)
Response: 200 OK
{
  "members": [Individual],
  "total": int,
  "skip": int,
  "limit": int
}

# Add members to group
POST /api/v1/individual-groups/{group_id}/members
Body: AddGroupMembersRequest
Response: 200 OK
{
  "group": IndividualGroup,
  "added_count": int,
  "skipped_count": int  # Already members
}

# Remove members from group
DELETE /api/v1/individual-groups/{group_id}/members
Body: {
  "individual_ids": [string]
}
Response: 200 OK
{
  "group": IndividualGroup,
  "removed_count": int
}

# Get groups an individual belongs to
GET /api/v1/individuals/{individual_id}/groups
Response: 200 OK
{
  "groups": [IndividualGroup],
  "total": int
}
```

#### 5.1.3 Thumbnail Management

```http
# Get individual thumbnail
GET /api/v1/individuals/{individual_id}/thumbnail
Query Params:
  - size: enum (small=128, medium=256, large=512)
Response: 200 OK (image/jpeg)

# Generate/regenerate thumbnail
POST /api/v1/individuals/{individual_id}/thumbnail/generate
Response: 200 OK
{
  "thumbnail_url": string,
  "generated_at": datetime
}

# Upload custom thumbnail
POST /api/v1/individuals/{individual_id}/thumbnail/upload
Body: multipart/form-data (image file)
Response: 200 OK
{
  "thumbnail_url": string
}
```

#### 5.1.4 Bulk Operations

```http
# Bulk add individuals to group
POST /api/v1/individual-groups/bulk/add-members
Body: {
  "group_id": string,
  "individual_ids": [string]
}
Response: 200 OK
{
  "success_count": int,
  "error_count": int,
  "errors": [{"individual_id": string, "reason": string}]
}

# Bulk assign individuals to multiple groups
POST /api/v1/individuals/bulk/assign-groups
Body: {
  "individual_ids": [string],
  "group_ids": [string]
}
Response: 200 OK
{
  "assignments_created": int,
  "individuals_updated": int
}
```

### 5.2 Error Responses

```python
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime

# Common error codes
400 Bad Request - Invalid input
404 Not Found - Group or individual not found
409 Conflict - Duplicate name, already a member, etc.
422 Unprocessable Entity - Validation failed
500 Internal Server Error
```

---

## 6. UI/UX Design

### 6.1 Screen Hierarchy

```
App Navigation
└── Collections Menu
    ├── Media Collections (Existing)
    └── Individual Groups (NEW)
        ├── Groups List Screen
        │   └── Group Detail Screen
        │       ├── Members Grid View
        │       ├── Individual Preview Dialog
        │       └── Bulk Actions Menu
        └── Create/Edit Group Screen
```

### 6.2 Individual Groups List Screen

#### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back     Individual Groups                    [+ New]    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  🔍 Search groups...                    [Grid] [List] [⚙️]   │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  [Cover]    │  │  [Cover]    │  │  [Cover]    │         │
│  │             │  │             │  │             │         │
│  │             │  │             │  │             │         │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤         │
│  │ VIP Cust... │  │ Store Staff │  │ Regulars    │         │
│  │ 15 members  │  │ 8 members   │  │ 42 members  │         │
│  │ 2d ago      │  │ 5d ago      │  │ 1h ago      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐                           │
│  │  [Cover]    │  │  [+ Create] │                           │
│  │             │  │     New     │                           │
│  │             │  │    Group    │                           │
│  ├─────────────┤  └─────────────┘                           │
│  │ Blacklist   │                                             │
│  │ 3 members   │                                             │
│  │ 1w ago      │                                             │
│  └─────────────┘                                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### UI Components

**Group Card:**
- Cover image (from `cover_individual_id` or first member)
- Group name (bold, truncated)
- Member count with icon
- Last updated timestamp
- Hover: Shows quick actions (View, Edit, Delete)
- Tap: Navigate to Group Detail Screen

**Header Actions:**
- Search bar (filters groups by name/description/tags)
- View toggle (Grid/List)
- Settings (sorting, filtering options)
- "+ New" button → Create Group Dialog

### 6.3 Group Detail Screen

#### Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  ← Groups     VIP Customers                      [Edit] [⋮] │
├─────────────────────────────────────────────────────────────┤
│  High-value customers identified across stores               │
│  📊 15 members  •  Last updated 2 days ago                  │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ [☑️ Select All]  [+ Add Members]  [Actions ▼]         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐           │
│  │☐ [Img] │  │☐ [Img] │  │☐ [Img] │  │☐ [Img] │           │
│  │        │  │        │  │        │  │        │           │
│  │ 12 app │  │ 8 app  │  │ 25 app │  │ 5 app  │           │
│  │ 1h ago │  │ 3h ago │  │ 2d ago │  │ 5d ago │           │
│  └────────┘  └────────┘  └────────┘  └────────┘           │
│                                                               │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐           │
│  │☐ [Img] │  │☐ [👤]  │  │☐ [Img] │  │☐ [Img] │           │
│  │        │  │Fallback│  │        │  │        │           │
│  │ 7 app  │  │ 15 app │  │ 3 app  │  │ 9 app  │           │
│  │ 1w ago │  │ 2w ago │  │ 3w ago │  │ 4w ago │           │
│  └────────┘  └────────┘  └────────┘  └────────┘           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### Individual Thumbnail Card

**Components:**
- Checkbox (top-left) for multi-select
- Thumbnail image (or 👤 placeholder icon)
- Appearance count badge
- Last seen timestamp
- Hover: Highlight border, show quick action icons
- Tap: Open Individual Preview Dialog
- Long press: Toggle selection mode

**Fallback Placeholder:**
```dart
// When no thumbnail available
Container(
  decoration: BoxDecoration(
    gradient: LinearGradient(
      colors: [Colors.blue.shade300, Colors.blue.shade500],
    ),
  ),
  child: Icon(Icons.person, size: 64, color: Colors.white.withOpacity(0.7)),
)
```

#### Bulk Actions Menu

When 1+ individuals selected:
```
┌────────────────────────────────┐
│ [👁️] View in Analysis (3)      │
│ [➕] Add to Another Group       │
│ [➖] Remove from This Group     │
│ [🗑️] Delete from System        │
└────────────────────────────────┘
```

### 6.4 Individual Preview Dialog

**Similar to Media Preview Dialog Pattern**

```
┌───────────────────────────────────────────────────────────┐
│                 Individual Preview               [×]      │
├───────────────────────────────────────────────────────────┤
│                                                             │
│                    ┌─────────────┐                         │
│                    │             │                         │
│                    │  [Thumbnail]│                         │
│                    │             │                         │
│                    └─────────────┘                         │
│                                                             │
│  ┌────────┐ ┌────────────┐ ┌─────────┐                   │
│  │Details │ │ Collections│ │ Actions │                   │
│  └────────┘ └────────────┘ └─────────┘                   │
│  ════════════════════════════════════════                 │
│                                                             │
│  [Details Tab Content]                                     │
│  • Total Appearances: 12                                   │
│  • First Seen: Jan 15, 2025 10:30 AM                      │
│  • Last Seen: Jan 16, 2025 3:45 PM                        │
│  • Confidence: 95.3%                                       │
│  • Demographics: Male, 25-35, Caucasian                   │
│                                                             │
│  Videos Appeared In (5):                                   │
│  └─ Store_A_Jan15_Morning.mp4                             │
│  └─ Store_B_Jan15_Afternoon.mp4                           │
│  └─ ...                                                    │
│                                                             │
│  ┌──────────────────────────────────────────────┐         │
│  │      [View Full Analysis →]                  │         │
│  └──────────────────────────────────────────────┘         │
└───────────────────────────────────────────────────────────┘
```

#### Tab Contents

**Details Tab:**
- Large thumbnail
- Key statistics (appearances, first/last seen, confidence)
- Demographics (if available)
- List of videos with appearances
- Timeline visualization (optional)

**Collections Tab:**
- List of groups this individual belongs to
- Quick actions: Add to group, Remove from group
- Group membership history

**Actions Tab:**
- View Full Analysis
- Add to Group
- Remove from Group(s)
- Merge with Another Individual
- Delete Individual
- Export Data

### 6.5 Navigation Flow: Add to Group

**Scenario:** User is on Cross-Video Individual Analysis Screen

```
Step 1: Select Individuals
┌─────────────────────────────────┐
│ Cross-Video Analysis            │
│                                 │
│ ☑️ Individual A (12 appearances)│
│ ☑️ Individual B (8 appearances) │
│ ☐ Individual C (5 appearances) │
└─────────────────────────────────┘
         ↓
Step 2: Open Actions Menu
┌─────────────────────────────────┐
│ [Actions ▼]                     │
│  ├─ Add to Group (2 selected)  │ ← Click this
│  └─ Merge                       │
└─────────────────────────────────┘
         ↓
Step 3: Select/Create Group Dialog
┌─────────────────────────────────┐
│ Add 2 individuals to group:     │
│                                 │
│ ◉ Existing Group                │
│   [🔍 Search groups...]         │
│   ◯ VIP Customers (15)          │
│   ◯ Store Staff (8)             │
│   ◯ Regulars (42)               │
│                                 │
│ ◉ Create New Group              │
│   Name: [________________]      │
│   Description: [________]       │
│                                 │
│ [Cancel]        [Add →]         │
└─────────────────────────────────┘
         ↓
Step 4: Success Confirmation
┌─────────────────────────────────┐
│ ✅ Added 2 individuals to       │
│    "VIP Customers"              │
│                                 │
│ [View Group]  [Dismiss]         │
└─────────────────────────────────┘
```

### 6.6 Create/Edit Group Dialog

```
┌───────────────────────────────────────────────────────────┐
│  Create Individual Group                         [×]      │
├───────────────────────────────────────────────────────────┤
│                                                             │
│  Group Name *                                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ VIP Customers                                        │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  Description                                               │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ High-value customers identified across all stores   │  │
│  │                                                      │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  Tags (comma-separated)                                    │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ vip, loyalty, high-value                             │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  Visibility                                                │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ ◉ Private  ◯ Shared with Team  ◯ Public             │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  Add Initial Members (optional)                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ [Select from existing individuals...]  [Browse]     │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│                                    [Cancel]  [Create]      │
└───────────────────────────────────────────────────────────┘
```

---

## 7. Implementation Phases

### Phase 1: Backend Foundation (Week 1-2)

**Objectives:**
- Implement core data models in vmeta
- Create database schema and migrations
- Build CRUD API endpoints
- Unit tests for all services

**Deliverables:**
- ✅ `IndividualGroup` model
- ✅ `GroupMembership` model
- ✅ `IndividualGroupsManager` service
- ✅ RESTful API endpoints (list, create, get, update, delete)
- ✅ Member management endpoints (add, remove, list)
- ✅ Unit tests (80%+ coverage)

**Technical Tasks:**
```python
# 1. Create data models
ppl-meta-vmeta/src/models/individual_group.py
ppl-meta-vmeta/src/models/group_membership.py

# 2. Create manager service
ppl-meta-vmeta/src/services/individual_groups_manager.py

# 3. Create API routes
ppl-meta-vmeta/src/api/routes/individual_groups.py

# 4. Update main.py to register routes
ppl-meta-vmeta/src/main.py

# 5. Tests
ppl-meta-vmeta/tests/test_individual_groups_manager.py
ppl-meta-vmeta/tests/test_individual_groups_api.py
```

### Phase 2: Thumbnail System (Week 2-3)

**Objectives:**
- Implement thumbnail generation service
- Create thumbnail storage strategy
- Build thumbnail API endpoints
- Fallback placeholder system

**Deliverables:**
- ✅ `IndividualThumbnailService`
- ✅ Best frame selection algorithm
- ✅ Image resizing and optimization
- ✅ Thumbnail storage (S3 or local)
- ✅ Fallback placeholder generation
- ✅ Thumbnail API endpoints

**Technical Tasks:**
```python
# 1. Create thumbnail service
ppl-meta-vmeta/src/services/individual_thumbnail_service.py

# 2. Create thumbnail routes
ppl-meta-vmeta/src/api/routes/individual_thumbnails.py

# 3. Integrate with media service for frame extraction
# Coordinate with ppl-meta-media team

# 4. Storage configuration
ppl-meta-vmeta/src/config/thumbnail_storage_config.py
```

### Phase 3: Frontend UI Components (Week 3-4)

**Objectives:**
- Build reusable individual thumbnail card
- Create individual preview dialog
- Implement group list/grid views
- Build group detail screen

**Deliverables:**
- ✅ `IndividualThumbnailCard` widget
- ✅ `IndividualPreviewDialog` widget
- ✅ `IndividualGroupsListScreen`
- ✅ `IndividualGroupDetailScreen`
- ✅ State management integration

**Technical Tasks:**
```dart
// 1. Core widgets
ppl-meta-frontend/lib/widgets/individuals/individual_thumbnail_card.dart
ppl-meta-frontend/lib/widgets/individuals/individual_preview_dialog.dart
ppl-meta-frontend/lib/widgets/individuals/individual_fallback_placeholder.dart

// 2. Screens
ppl-meta-frontend/lib/screens/individual_groups/individual_groups_list_screen.dart
ppl-meta-frontend/lib/screens/individual_groups/individual_group_detail_screen.dart
ppl-meta-frontend/lib/screens/individual_groups/create_edit_group_screen.dart

// 3. State management
ppl-meta-frontend/lib/providers/individual_groups_provider.dart

// 4. Services
ppl-meta-frontend/lib/services/individual_groups_service.dart
```

### Phase 4: Integration & Navigation (Week 4-5)

**Objectives:**
- Integrate with existing cross-video analysis screen
- Implement "Add to Group" functionality
- Build bulk selection and actions
- Cross-screen navigation flows

**Deliverables:**
- ✅ Enhanced cross-video analysis screen
- ✅ Add to Group action (from analysis screen)
- ✅ Bulk selection UI
- ✅ Navigation from groups to analysis
- ✅ Deep linking support

**Technical Tasks:**
```dart
// 1. Update existing cross-video analysis screen
ppl-meta-frontend/lib/screens/collections/cross_video_analysis_screen.dart

// 2. Add group integration
ppl-meta-frontend/lib/screens/collections/widgets/add_to_group_dialog.dart

// 3. Update routing
ppl-meta-frontend/lib/routes/app_routes.dart

// 4. Update navigation service
ppl-meta-frontend/lib/services/navigation_service.dart
```

### Phase 5: Polish & Testing (Week 5-6)

**Objectives:**
- End-to-end testing
- Performance optimization
- UX refinements
- Documentation

**Deliverables:**
- ✅ Integration tests (full workflows)
- ✅ Performance benchmarks
- ✅ User documentation
- ✅ API documentation
- ✅ Bug fixes and polish

**Testing Checklist:**
- [ ] Create group with 0 members
- [ ] Create group with 100+ members
- [ ] Add individuals to group from analysis screen
- [ ] Remove individuals from group
- [ ] Delete group with members
- [ ] Navigate from group to analysis with selected individuals
- [ ] Bulk select and add to group
- [ ] Search and filter groups
- [ ] Thumbnail loading and fallbacks
- [ ] Permission/visibility controls

---

## 8. Technical Considerations

### 8.1 Performance

**Thumbnail Loading:**
- Lazy load thumbnails in grid view
- Use progressive image loading (blur-up)
- Cache thumbnails client-side
- CDN for thumbnail delivery (future)

**Large Groups:**
- Pagination for groups with 100+ members
- Virtual scrolling for grid views
- Debounced search
- Batch API requests

**Database Queries:**
```python
# Index strategy for optimal performance
CREATE INDEX idx_group_membership_group ON group_membership(group_id);
CREATE INDEX idx_group_membership_individual ON group_membership(individual_id);
CREATE INDEX idx_groups_created_by ON individual_groups(created_by);
CREATE INDEX idx_groups_updated_at ON individual_groups(updated_at DESC);

# Optimize member count queries
# Use denormalized member_count field instead of COUNT(*) queries
```

### 8.2 Scalability

**Horizontal Scaling:**
- vmeta service is stateless → can scale horizontally
- Use distributed caching (Redis) for thumbnail URLs
- Separate thumbnail storage from service

**Data Growth:**
- Archive old groups (soft delete)
- Compress thumbnail storage
- Implement data retention policies

### 8.3 Security

**Authorization:**
```python
# Group access control
async def check_group_access(user_id: str, group_id: str, 
                             required_permission: Permission) -> bool:
    group = await get_group(group_id)
    
    # Owner has full access
    if group.created_by == user_id:
        return True
    
    # Check visibility
    if group.visibility == GroupVisibility.PUBLIC:
        return required_permission == Permission.READ
    
    if group.visibility == GroupVisibility.SHARED:
        # Check team membership
        return await is_team_member(user_id, group.created_by)
    
    # Private - only owner
    return False
```

**Data Privacy:**
- PII handling for individual thumbnails
- GDPR compliance (right to be forgotten)
- Audit logging for group operations
- Encrypted thumbnail storage

### 8.4 Data Consistency

**Race Conditions:**
```python
# Use optimistic locking for member count updates
class IndividualGroup(BaseModel):
    member_count: int
    version: int  # Incremented on each update
    
# In update operations
async def add_members(group_id: str, individual_ids: List[str]):
    async with db.transaction():
        group = await db.get_group_for_update(group_id)  # Row lock
        
        # Check version
        if group.version != expected_version:
            raise ConcurrentModificationError()
        
        # Perform updates
        await db.add_memberships(group_id, individual_ids)
        group.member_count += len(individual_ids)
        group.version += 1
        await db.save_group(group)
```

### 8.5 Migration Strategy

**Existing Data:**
- No migration needed (new feature)
- Optionally: Pre-create default groups ("All Individuals", "Recently Seen")

**Backwards Compatibility:**
- Individual model extended, not changed
- Existing APIs unaffected
- New endpoints under `/individual-groups`

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Backend (Python/pytest):**
```python
# test_individual_groups_manager.py

@pytest.mark.asyncio
async def test_create_group():
    manager = IndividualGroupsManager()
    group = await manager.create_group(
        name="Test Group",
        description="Test description",
        created_by="user_123"
    )
    assert group.id is not None
    assert group.name == "Test Group"
    assert group.member_count == 0

@pytest.mark.asyncio
async def test_add_members_updates_count():
    manager = IndividualGroupsManager()
    group = await manager.create_group(...)
    
    await manager.add_members(group.id, ["ind_1", "ind_2", "ind_3"])
    
    updated_group = await manager.get_group(group.id)
    assert updated_group.member_count == 3
    assert len(updated_group.member_ids) == 3

@pytest.mark.asyncio
async def test_cannot_add_duplicate_members():
    manager = IndividualGroupsManager()
    group = await manager.create_group(...)
    
    await manager.add_members(group.id, ["ind_1"])
    
    # Should not increase count
    await manager.add_members(group.id, ["ind_1"])
    
    updated_group = await manager.get_group(group.id)
    assert updated_group.member_count == 1
```

**Frontend (Dart/Flutter Test):**
```dart
// individual_groups_provider_test.dart

testWidgets('Should load groups on screen init', (WidgetTester tester) async {
  final provider = IndividualGroupsProvider();
  
  await tester.pumpWidget(
    ChangeNotifierProvider.value(
      value: provider,
      child: IndividualGroupsListScreen(),
    ),
  );
  
  await tester.pumpAndSettle();
  
  expect(find.byType(GroupCard), findsWidgets);
});

testWidgets('Should show add to group dialog', (WidgetTester tester) async {
  // ... test implementation
});
```

### 9.2 Integration Tests

**API Tests:**
```python
# test_individual_groups_api_integration.py

@pytest.mark.integration
async def test_full_group_lifecycle(api_client):
    # Create group
    response = await api_client.post("/api/v1/individual-groups", json={
        "name": "Integration Test Group",
        "description": "Testing full lifecycle"
    })
    assert response.status_code == 201
    group_id = response.json()["group"]["id"]
    
    # Add members
    response = await api_client.post(
        f"/api/v1/individual-groups/{group_id}/members",
        json={"individual_ids": ["ind_1", "ind_2"]}
    )
    assert response.status_code == 200
    assert response.json()["added_count"] == 2
    
    # Get members
    response = await api_client.get(f"/api/v1/individual-groups/{group_id}/members")
    assert response.status_code == 200
    assert len(response.json()["members"]) == 2
    
    # Delete group
    response = await api_client.delete(f"/api/v1/individual-groups/{group_id}")
    assert response.status_code == 204
```

### 9.3 E2E Tests

**User Workflows (Selenium/Playwright):**
```javascript
// e2e/individual_groups.spec.js

describe('Individual Groups Feature', () => {
  it('should create group and add members from analysis screen', async () => {
    // Navigate to collections
    await page.goto('http://localhost:3000/#/collections');
    
    // Go to cross-video analysis
    await page.click('[data-testid="cross-video-analysis"]');
    
    // Select individuals
    await page.click('[data-testid="individual-checkbox-1"]');
    await page.click('[data-testid="individual-checkbox-2"]');
    
    // Open actions menu
    await page.click('[data-testid="actions-button"]');
    
    // Click "Add to Group"
    await page.click('[data-testid="add-to-group-action"]');
    
    // Create new group
    await page.click('[data-testid="create-new-group-radio"]');
    await page.fill('[data-testid="group-name-input"]', 'E2E Test Group');
    await page.click('[data-testid="add-button"]');
    
    // Verify success
    await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();
  });
});
```

### 9.4 Performance Tests

**Load Testing (Locust):**
```python
# locust_individual_groups.py

from locust import HttpUser, task, between

class IndividualGroupsUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def list_groups(self):
        self.client.get("/api/v1/individual-groups")
    
    @task(2)
    def get_group_members(self):
        self.client.get(f"/api/v1/individual-groups/{self.group_id}/members")
    
    @task(1)
    def create_group(self):
        self.client.post("/api/v1/individual-groups", json={
            "name": f"Load Test Group {uuid.uuid4()}",
            "description": "Performance testing"
        })

# Run: locust -f locust_individual_groups.py --host http://localhost:8008
```

---

## 10. Migration & Rollout

### 10.1 Deployment Strategy

**Phase A: Backend Deployment (Day 1)**
1. Deploy vmeta service updates to staging
2. Run database migrations
3. Verify API endpoints
4. Deploy to production (off-hours)
5. Monitor for errors

**Phase B: Frontend Deployment (Day 2-3)**
1. Deploy frontend with feature flag disabled
2. Enable for internal team (beta testing)
3. Gather feedback and fix critical issues
4. Enable for 10% of users (canary)
5. Monitor metrics (load times, error rates)
6. Roll out to 50%, then 100%

**Feature Flag Configuration:**
```dart
// lib/config/feature_flags.dart

class FeatureFlags {
  static bool get individualGroupsEnabled {
    return RemoteConfig.instance.getBool('individual_groups_enabled');
  }
}

// Use in UI
if (FeatureFlags.individualGroupsEnabled) {
  NavigationMenuItem(
    title: 'Individual Groups',
    route: '/individual-groups',
  ),
}
```

### 10.2 Rollback Plan

**If critical issues occur:**
1. Disable feature flag immediately (0% rollout)
2. Revert frontend deployment if needed
3. Keep backend deployed (doesn't affect existing features)
4. Investigate issues in staging environment
5. Fix and redeploy

**Database Rollback:**
```sql
-- If needed to rollback database changes
BEGIN;

-- Drop new tables
DROP TABLE IF EXISTS group_membership;
DROP TABLE IF EXISTS individual_groups;

-- Remove new columns from individuals table
ALTER TABLE individuals DROP COLUMN IF EXISTS group_ids;
ALTER TABLE individuals DROP COLUMN IF EXISTS thumbnail_url;

COMMIT;
```

### 10.3 Monitoring & Metrics

**Key Metrics to Track:**
```yaml
Business Metrics:
  - Groups created per day
  - Average group size
  - Members added per day
  - Groups accessed per user
  - Time spent in groups screens

Technical Metrics:
  - API response times (p50, p95, p99)
  - Error rates per endpoint
  - Thumbnail load times
  - Database query performance
  - Memory usage (thumbnail caching)

User Experience:
  - Page load times
  - Time to first interaction
  - User flows completed
  - Feature adoption rate
```

**Dashboards:**
- Grafana dashboard for backend metrics
- Firebase Analytics for frontend usage
- Error tracking (Sentry)

**Alerts:**
```yaml
Critical:
  - API error rate > 5%
  - Database connection failures
  - Service downtime

Warning:
  - API p95 latency > 2s
  - Thumbnail generation failures > 10%
  - Database query time > 500ms
```

### 10.4 Documentation & Training

**User Documentation:**
- Help article: "Organizing Individuals into Groups"
- Video tutorial: "Getting Started with Individual Groups"
- FAQ section
- In-app tooltips and onboarding

**Developer Documentation:**
- API reference (Swagger/OpenAPI)
- Architecture diagrams
- Code examples
- Troubleshooting guide

**Training Materials:**
- Demo video for support team
- Knowledge base articles
- Internal workshop (optional)

---

## 11. Future Enhancements

### 11.1 Phase 2 Features (Post-Launch)

**Smart Groups (AI-Powered):**
- Auto-group by demographics
- Auto-group by behavior patterns
- Suggest similar individuals
- Anomaly detection

**Advanced Filtering:**
- Filter groups by date range
- Filter by appearance locations
- Filter by demographics
- Saved filter presets

**Collaboration:**
- Share groups with team members
- Comments on group/individuals
- Activity feed
- Permission management

**Analytics:**
- Group insights dashboard
- Trend analysis
- Heatmaps of appearances
- Export reports

### 11.2 Integration Opportunities

**With Signage System:**
- Trigger signage based on group presence
- Group-specific content
- VIP recognition workflows

**With Triggers:**
- Create triggers for group members
- Bulk trigger assignment
- Group-based automation rules

**With Reporting:**
- Group appearance reports
- Demographic breakdowns
- Time-series analysis
- Custom report builder

---

## 12. Appendix

### 12.1 API Reference (Quick Guide)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/individual-groups` | GET | List all groups |
| `/api/v1/individual-groups` | POST | Create new group |
| `/api/v1/individual-groups/{id}` | GET | Get group details |
| `/api/v1/individual-groups/{id}` | PATCH | Update group |
| `/api/v1/individual-groups/{id}` | DELETE | Delete group |
| `/api/v1/individual-groups/{id}/members` | GET | List group members |
| `/api/v1/individual-groups/{id}/members` | POST | Add members |
| `/api/v1/individual-groups/{id}/members` | DELETE | Remove members |
| `/api/v1/individuals/{id}/groups` | GET | Get individual's groups |
| `/api/v1/individuals/{id}/thumbnail` | GET | Get thumbnail image |

### 12.2 Database Schema Diagram

```
┌─────────────────────┐
│ individual_groups   │
├─────────────────────┤
│ id (PK)             │
│ name                │
│ description         │
│ created_by          │
│ created_at          │
│ updated_at          │
│ member_count        │
│ member_ids (array)  │
│ visibility          │
│ tags (array)        │
│ cover_individual_id │
│ metadata (jsonb)    │
└──────────┬──────────┘
           │
           │ 1:N
           │
┌──────────┴──────────┐
│ group_membership    │
├─────────────────────┤
│ id (PK)             │
│ group_id (FK)       │
│ individual_id (FK)  │
│ added_by            │
│ added_at            │
│ notes               │
└──────────┬──────────┘
           │
           │ N:1
           │
┌──────────┴──────────┐
│ individuals         │
├─────────────────────┤
│ id (PK)             │
│ ...existing fields  │
│ group_ids (array)   │ ← NEW
│ thumbnail_url       │ ← NEW
│ best_frame_video_id │ ← NEW
└─────────────────────┘
```

### 12.3 Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend Service | Python 3.11+ |
| Web Framework | FastAPI |
| Database | Qdrant (vectors) + PostgreSQL (metadata) |
| Thumbnail Storage | S3-compatible (MinIO/AWS S3) |
| Image Processing | Pillow / OpenCV |
| Frontend Framework | Flutter (Web/Desktop/Mobile) |
| State Management | Provider / Riverpod |
| HTTP Client | Dio |
| Caching | Redis (optional) |

### 12.4 Dependencies

**Python (vmeta):**
```txt
fastapi>=0.104.0
pydantic>=2.0.0
pillow>=10.0.0
qdrant-client>=1.6.0
asyncpg>=0.28.0
httpx>=0.25.0
```

**Flutter (frontend):**
```yaml
dependencies:
  flutter:
    sdk: flutter
  provider: ^6.0.0
  dio: ^5.0.0
  cached_network_image: ^3.2.0
  flutter_staggered_grid_view: ^0.6.0
  get_it: ^7.6.0
```

### 12.5 Glossary

| Term | Definition |
|------|------------|
| **Individual** | A unique person detected and tracked across videos |
| **Individual Group** | A user-created collection of individuals |
| **Thumbnail** | Small preview image representing an individual |
| **Fallback Placeholder** | Default icon shown when thumbnail unavailable |
| **Cross-Video Analysis** | View showing individual appearances across multiple videos |
| **Bulk Selection** | Selecting multiple items for batch operations |
| **Member** | An individual within a group |
| **vmeta** | Video metadata service (tracking, individuals, embeddings) |

---

## 13. Conclusion

This proposal provides a comprehensive blueprint for implementing the **Individual Groups** feature in the PPL Meta platform. The design prioritizes:

✅ **User Experience** - Familiar patterns matching media collections  
✅ **Scalability** - Architecture supports growth to thousands of groups  
✅ **Flexibility** - Extensible for future AI-powered features  
✅ **Integration** - Seamless connection with existing workflows  

**Next Steps:**
1. Review and approve this proposal
2. Assign development resources
3. Create detailed tickets for each phase
4. Begin Phase 1 implementation

**Questions or feedback?** Contact the architecture team or open a discussion in the project repository.

---

**Document Version:** 1.0.0  
**Last Updated:** December 16, 2025  
**Status:** Awaiting Approval
