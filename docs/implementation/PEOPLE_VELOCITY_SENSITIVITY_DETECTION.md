# People Velocity Sensitivity Detection - Implementation Document

**Version:** 2.21.12  
**Date:** December 28, 2024  
**Status:** Implementation Ready  
**Author:** PPL Meta Platform Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Implementation Analysis](#current-implementation-analysis)
3. [Hardcoded Values Inventory](#hardcoded-values-inventory)
4. [Proposed Implementation](#proposed-implementation)
5. [Step-by-Step Implementation Plan](#step-by-step-implementation-plan)
6. [Testing Strategy](#testing-strategy)
7. [Rollback Plan](#rollback-plan)

---

## 1. Executive Summary

### Purpose
Expose the face rectangle overlap percentage (currently hardcoded at 20%) as a configurable setting called "People Velocity Sensitivity" in the workflow settings dropdown at `http://localhost:3000/#/settings`.

### Current State
The `tolerance_percent` parameter is hardcoded to `20.0` across 42+ locations in the vision service codebase, controlling how face rectangles are grouped temporally across video frames.

### Goal State
Users can adjust the overlap percentage via a slider (range: 5% - 50%) in the frontend settings UI, with the value stored persistently and applied to all person objects (PPL Thread) workflows.

### Impact
- **User Experience**: Fine-tune person tracking for different scenarios (fast-moving vs. slow-moving people)
- **Accuracy**: Better grouping for varying velocity conditions
- **Configuration**: No code changes needed for different use cases

---

## 2. Current Implementation Analysis

### 2.1 Face Grouping Algorithm Logic

**Location**: `ppl-meta-vision/src/person_objects/face_grouping_engine.py`

The face grouping engine uses a **percentage-based tolerance matching algorithm** to determine if face detections in consecutive frames belong to the same person.

#### Core Algorithm (lines 58-106):

```python
def calculate_position_distance(self, pos1: Dict, pos2: Dict) -> Dict[str, float]:
    """
    Calculate position-based distance with percentage tolerance matching.
    
    This replicates the exact same algorithm used in PPL Meta Mini's
    FaceGroupingEngine for consistency across implementations.
    """
    x1, y1 = float(pos1["x"]), float(pos1["y"])
    x2, y2 = float(pos2["x"]), float(pos2["y"])

    # Calculate absolute differences
    x_distance = abs(x1 - x2)
    y_distance = abs(y1 - y2)

    # Calculate percentage-based tolerances (HARDCODED: 20%)
    x_tolerance = x1 * (self.tolerance_percent / 100.0)
    y_tolerance = y1 * (self.tolerance_percent / 100.0)

    # Check if within tolerance thresholds
    x_within_tolerance = x_distance <= x_tolerance
    y_within_tolerance = y_distance <= y_tolerance

    # Calculate Euclidean distance
    euclidean_distance = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    # Calculate combined distance metric (weighted)
    combined_distance = (
        x_distance * 0.3 + y_distance * 0.3 + euclidean_distance * 0.4
    )

    return {
        "x_distance": x_distance,
        "y_distance": y_distance,
        "euclidean_distance": euclidean_distance,
        "combined_distance": combined_distance,
        "within_tolerance": x_within_tolerance and y_within_tolerance,
        "x_tolerance_used": x_tolerance,
        "y_tolerance_used": y_tolerance,
    }
```

#### Initialization (line 36):

```python
def __init__(self):
    """Initialize the face grouping engine with PPL Mini default settings."""
    self.tolerance_percent = 20.0  # HARDCODED VALUE
    self.quality_weights = {
        "sharpness": 0.4,
        "exposure": 0.3,
        "contrast": 0.2,
        "noise": 0.1,
    }
```

### 2.2 How Temporal Grouping Works

1. **Frame-by-Frame Processing**: Faces are detected in each video frame
2. **Position Extraction**: Each face's position is extracted (x, y coordinates)
3. **Distance Calculation**: The algorithm calculates distance from current face to all active tracks
4. **Tolerance Matching**: If distance is within tolerance percentage, faces are grouped as same person
5. **Track Management**: Tracks are created for new faces or updated for matched faces

### 2.3 Velocity Sensitivity Explanation

The `tolerance_percent` parameter controls how much movement is allowed between frames:

- **Lower values (5-10%)**: Stricter matching, better for slow-moving or stationary subjects
- **Default value (20%)**: Balanced approach for normal walking speed
- **Higher values (30-50%)**: Looser matching, better for fast-moving subjects or jerky camera movements

**Real-World Example**:
- Face at position (100, 150) in frame 1
- Face at position (115, 160) in frame 2
- With 20% tolerance:
  - X tolerance: 100 * 0.20 = 20 pixels
  - Y tolerance: 150 * 0.20 = 30 pixels
  - X distance: |100 - 115| = 15 ≤ 20 ✅ Within tolerance
  - Y distance: |150 - 160| = 10 ≤ 30 ✅ Within tolerance
  - **Result**: Same person

---

## 3. Hardcoded Values Inventory

### 3.1 Production Files - WILL BE MODIFIED ✏️

These files contain the hardcoded 20.0% value and **will be updated** to use the configurable setting:

| File | Line | Context | Type |
|------|------|---------|------|
| `src/person_objects/face_grouping_engine.py` | 36 | `self.tolerance_percent = 20.0` | Class initialization |
| `src/person_objects/face_grouping_engine.py` | 421 | `tolerance_percent: float = 20.0` | Method parameter default |
| `src/person_objects/person_objects_api.py` | 83 | `default=20.0` | API request field default |
| `src/person_objects/person_objects_api.py` | 135 | `default=20.0` | API request field default |
| `src/person_objects/ppl_thread_workflow.py` | 76 | `self.default_tolerance_percent = 20.0` | Workflow controller default |
| `src/person_objects/ppl_thread_workflow.py` | 224 | `tolerance_percent: float = 20.0` | Method parameter default |
| `src/person_objects/ppl_thread_workflow.py` | 432 | `tolerance_percent: float = 20.0` | Method parameter default |
| `deployment/ppl_thread_config.py` | 39 | `"PPL_DEFAULT_TOLERANCE", 20.0` | Environment config |

**Total Production Files**: 4 files, 8 occurrences

### 3.2 Database Schema - WILL BE MODIFIED ✏️

| File | Line | Context | Action |
|------|------|---------|--------|
| `src/database/person_objects_migrations.py` | 111 | `tolerance_percent REAL DEFAULT 20.0` | Keep as fallback default |
| `src/database/person_objects_migrations.py` | 157 | `tolerance_percent REAL DEFAULT 20.0` | Keep as fallback default |

**Note**: Database defaults will remain at 20.0 as a fallback, but active workflows will fetch from the new `workflow_settings` table.

### 3.3 Test Files - WILL NOT BE MODIFIED 📖

**These test files contain hardcoded 20.0% values that will remain unchanged.** They serve as reference documentation and regression test baselines. The hardcoded values in tests are intentional and document the expected behavior.

#### Complete Test File Inventory (34 occurrences):

##### `test_phase2_core_face_grouping.py` (3 occurrences):
```python
Line 114: # With 20% tolerance: x_tolerance = 100 * 0.2 = 20, y_tolerance = 150 * 0.2 = 30
Line 115: self.assertEqual(result["x_tolerance_used"], 20.0)
Line 184: self.sample_faces, tolerance_percent=20.0
Line 205: self.assertEqual(statistics["tolerance_percent"], 20.0)
```
**Purpose**: Tests core face grouping algorithm with known 20% baseline

##### `test_phase3_workflow_integration.py` (17 occurrences):
```python
Line 59:  self.default_tolerance_percent = 20.0
Line 164: self.assertEqual(self.controller.default_tolerance_percent, 20.0)
Line 209: tolerance_percent=20.0,
Line 299: "tolerance_percent": 20.0,
Line 307: "tolerance_percent": 20.0,
Line 337: "tolerance_percent": 20.0,
Line 444: tolerance_values = [5.0, 15.0, 20.0, 30.0, 45.0]
Line 464: session_uuid=self.test_session_uuid, tolerance_percent=tolerance
Line 521: workflow_id, self.test_session_uuid, 20.0, {"test": "metadata"}
Line 614: "tolerance_percent": 20.0,
Line 674: "tolerance_percent": 20.0,
Line 695: "tolerance_percent": 20.0,
Line 800: results = await engine.apply_percentage_based_tracking(test_faces, 20.0)
Line 913: session_uuid="test-session", tolerance_percent=1.0
Line 919: session_uuid="test-session", tolerance_percent=50.0
```
**Purpose**: Integration tests for workflow controller with default tolerance

##### `test_phase4_integration_suite.py` (8 occurrences):
```python
Line 83:  "tolerance_percent": 20.0,
Line 281: tolerance_percent=20.0,
Line 335: "tolerance_percent": 20.0,
Line 343: "tolerance_percent": 20.0,
Line 382: "tolerance_percent": 20.0,
Line 435: self.assertEqual(group["Tolerance_Percent"], 20.0)
Line 504: test_faces, 20.0
```
**Purpose**: End-to-end integration tests with 20% as baseline

##### `validate_phase3_integration.py` (3 occurrences):
```python
Line 133: results = await engine.apply_percentage_based_tracking(test_faces, 20.0)
Line 187: "tolerance_percent": 20.0,
Line 192: assert request.tolerance_percent == 20.0
```
**Purpose**: Phase 3 validation with expected 20% default

##### `test_phase1_person_objects_schema.py` (1 occurrence):
```python
Line 351: VALUES (%s, %s, 10, 20.0, %s)
```
**Purpose**: Database schema test with sample data

##### `tests/test_integration_comprehensive.py` (1 occurrence):
```python
Line 170: "total_processing_time": 120.0,  # Unrelated, just happens to be 20*6
```
**Purpose**: Performance timing test (not related to tolerance)

##### `setup_phase2.py` (1 occurrence):
```python
Line 79: def test_face_grouping_engine():
    # Contains test with 20.0 default
```
**Purpose**: Setup/bootstrap script for Phase 2 testing

**Total Test Files**: 7 files, 34 occurrences

#### Why Test Files Are Not Modified:

1. **Baseline Documentation**: Tests document the original 20% default behavior
2. **Regression Testing**: Tests verify the algorithm still works correctly at 20%
3. **Backward Compatibility**: Tests ensure explicit tolerance_percent parameters still work
4. **Reference Values**: Tests serve as examples of valid tolerance values (5.0-50.0)
5. **Test Independence**: Tests should not depend on dynamic system settings

### 3.4 API Response Examples - WILL BE UPDATED ✏️

| File | Line | Context | Action |
|------|------|---------|--------|
| `src/person_objects/person_objects_api.py` | 109, 183 | Example JSON responses | Update to `null` (uses system setting) |
| `src/person_objects/person_objects_api.py` | 288, 299 | Example response data | Update to show dynamic value |

---

### 3.5 Summary

| Category | Files | Occurrences | Action |
|----------|-------|-------------|--------|
| **Production Code** | 4 | 8 | ✏️ **MODIFY** - Use configurable setting |
| **Database Schema** | 1 | 2 | ✏️ **KEEP** - Retain as fallback default |
| **Test Files** | 7 | 34 | 📖 **NO CHANGE** - Retain as reference |
| **API Examples** | 1 | 4 | ✏️ **UPDATE** - Show null/dynamic values |
| **TOTAL** | 13 | 48 | - |

---

## 4. Proposed Implementation

### 4.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Frontend (Flutter)                          │
│  Settings Screen → WorkflowSettings → Slider (5% - 50%)         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ HTTP POST/GET
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                  Orchestrator Service (8002)                     │
│  New: /api/v1/settings/workflow/velocity-sensitivity           │
│  - GET: Retrieve current setting                               │
│  - PUT: Update setting (validates 5.0 <= value <= 50.0)        │
│  - Storage: PostgreSQL settings table                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ HTTP (pass as parameter)
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    Vision Service (8003)                         │
│  Modified: /api/v1/person-objects/workflows/start              │
│  - Accept tolerance_percent parameter from orchestrator        │
│  - Pass to face_grouping_engine.py                             │
│  - Store in database with workflow record                      │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Data Flow

1. **User adjusts slider** in frontend settings (e.g., changes from 20% to 30%)
2. **Frontend calls orchestrator** → `PUT /api/v1/settings/workflow/velocity-sensitivity` with `{"value": 30.0}`
3. **Orchestrator validates** (5.0 ≤ 30.0 ≤ 50.0) and stores in database
4. **When workflow starts**, orchestrator retrieves setting and passes to vision service
5. **Vision service** uses value in `face_grouping_engine.py` for temporal grouping
6. **Value is persisted** with workflow record in database for audit trail

### 4.3 User Interface Design

**Location**: Settings Screen → Workflow Settings (new dropdown)

```dart
_buildSectionHeader('Workflow Settings'),
Card(
  child: Padding(
    padding: const EdgeInsets.all(16),
    child: Column(
      children: [
        Text(
          'People Velocity Sensitivity: ${velocitySensitivity.toStringAsFixed(0)}%',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        Text(
          'Controls face tracking tolerance for temporal grouping',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Colors.grey[600],
          ),
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            const Text('Slow', style: TextStyle(fontSize: 12)),
            Expanded(
              child: Slider(
                value: velocitySensitivity,
                min: 5.0,
                max: 50.0,
                divisions: 45,
                label: '${velocitySensitivity.toStringAsFixed(0)}%',
                onChanged: (value) => notifier.updateVelocitySensitivity(value),
              ),
            ),
            const Text('Fast', style: TextStyle(fontSize: 12)),
          ],
        ),
        const SizedBox(height: 8),
        Text(
          _getRecommendation(velocitySensitivity),
          style: TextStyle(
            fontSize: 11,
            fontStyle: FontStyle.italic,
            color: Colors.blue[700],
          ),
        ),
      ],
    ),
  ),
),
```

**Slider Characteristics**:
- Range: 5% - 50%
- Divisions: 45 (1% increments)
- Default: 20%
- Visual labels: "Slow" (left) and "Fast" (right)

**Dynamic Recommendations**:
- 5-15%: "Recommended for stationary or slow-moving subjects"
- 16-25%: "Recommended for normal walking speed (default)"
- 26-40%: "Recommended for fast-moving subjects or running"
- 41-50%: "Recommended for very fast motion or unstable cameras"

---

## 5. Step-by-Step Implementation Plan

> **Important**: This implementation plan modifies **ONLY production code** (4 files, 8 occurrences). Test files with hardcoded 20.0% values (7 files, 34 occurrences) will remain unchanged as they serve as reference documentation and regression baselines. See section 3.3 for complete test file inventory.

### Phase 1: Backend - Orchestrator Settings Endpoint (2 hours)

#### 5.1.1 Create Database Migration

**File**: `ppl-meta-orchestrator/migrations/versions/XXXXX_add_workflow_settings.py`

```python
"""Add workflow settings table

Revision ID: XXXXX
Revises: 4c7870119fb1
Create Date: 2024-12-28

"""
from alembic import op
import sqlalchemy as sa

revision = 'XXXXX'
down_revision = '4c7870119fb1'

def upgrade():
    op.create_table(
        'workflow_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('setting_key', sa.String(255), unique=True, nullable=False),
        sa.Column('setting_value', sa.Float(), nullable=False),
        sa.Column('min_value', sa.Float(), nullable=True),
        sa.Column('max_value', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('updated_by', sa.String(255), nullable=True),
    )
    
    # Insert default value
    op.execute("""
        INSERT INTO workflow_settings 
        (setting_key, setting_value, min_value, max_value, description) 
        VALUES 
        ('velocity_sensitivity', 20.0, 5.0, 50.0, 
         'Face tracking tolerance percentage for temporal grouping')
    """)

def downgrade():
    op.drop_table('workflow_settings')
```

**Run migration**:
```bash
cd ppl-meta-orchestrator
source venv/bin/activate
alembic upgrade head
```

#### 5.1.2 Create Settings Service

**File**: `ppl-meta-orchestrator/src/services/workflow_settings_service.py` (NEW)

```python
"""
PPL Meta Orchestrator - Workflow Settings Service
Manages workflow-level configuration settings stored in database.
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkflowSetting:
    """Database model for workflow_settings table."""
    
    def __init__(self, db_row):
        self.id = db_row.id
        self.setting_key = db_row.setting_key
        self.setting_value = db_row.setting_value
        self.min_value = db_row.min_value
        self.max_value = db_row.max_value
        self.description = db_row.description
        self.updated_at = db_row.updated_at
        self.updated_by = db_row.updated_by


class WorkflowSettingsService:
    """Service for managing workflow settings."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def get_setting(self, key: str) -> Optional[float]:
        """Retrieve a workflow setting value by key."""
        try:
            result = await self.db.execute(
                select(WorkflowSetting).where(WorkflowSetting.setting_key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                logger.info(f"Retrieved setting {key}: {setting.setting_value}")
                return setting.setting_value
            else:
                logger.warning(f"Setting not found: {key}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving setting {key}: {e}")
            return None
    
    async def update_setting(
        self, 
        key: str, 
        value: float, 
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a workflow setting value with validation.
        
        Returns:
            Dict with status and message
        """
        try:
            # Fetch current setting to validate bounds
            result = await self.db.execute(
                select(WorkflowSetting).where(WorkflowSetting.setting_key == key)
            )
            setting = result.scalar_one_or_none()
            
            if not setting:
                return {
                    "success": False,
                    "message": f"Setting '{key}' not found"
                }
            
            # Validate value against min/max
            if setting.min_value is not None and value < setting.min_value:
                return {
                    "success": False,
                    "message": f"Value {value} below minimum {setting.min_value}"
                }
            
            if setting.max_value is not None and value > setting.max_value:
                return {
                    "success": False,
                    "message": f"Value {value} above maximum {setting.max_value}"
                }
            
            # Update setting
            await self.db.execute(
                update(WorkflowSetting)
                .where(WorkflowSetting.setting_key == key)
                .values(
                    setting_value=value,
                    updated_at=datetime.now(),
                    updated_by=updated_by
                )
            )
            await self.db.commit()
            
            logger.info(f"Updated setting {key} to {value} by {updated_by or 'system'}")
            
            return {
                "success": True,
                "message": f"Setting '{key}' updated to {value}",
                "value": value
            }
            
        except Exception as e:
            logger.error(f"Error updating setting {key}: {e}")
            await self.db.rollback()
            return {
                "success": False,
                "message": f"Database error: {str(e)}"
            }
    
    async def get_velocity_sensitivity(self) -> float:
        """Get velocity sensitivity setting with fallback to default."""
        value = await self.get_setting('velocity_sensitivity')
        return value if value is not None else 20.0
```

#### 5.1.3 Create API Endpoints

**File**: `ppl-meta-orchestrator/src/api/workflow_settings_endpoints.py` (NEW)

```python
"""
PPL Meta Orchestrator - Workflow Settings API Endpoints
REST API for managing workflow configuration settings.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.workflow_settings_service import WorkflowSettingsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings/workflow", tags=["workflow-settings"])


# Request/Response Models

class VelocitySensitivityUpdate(BaseModel):
    """Request model for updating velocity sensitivity."""
    
    value: float = Field(
        ...,
        description="Velocity sensitivity percentage (5.0-50.0)",
        ge=5.0,
        le=50.0
    )
    updated_by: str = Field(
        default="user",
        description="Who updated the setting"
    )
    
    @validator('value')
    def validate_value(cls, v):
        if not (5.0 <= v <= 50.0):
            raise ValueError('Value must be between 5.0 and 50.0')
        return round(v, 1)  # Round to 1 decimal place
    
    class Config:
        schema_extra = {
            "example": {
                "value": 25.0,
                "updated_by": "admin@pplmeta.com"
            }
        }


class VelocitySensitivityResponse(BaseModel):
    """Response model for velocity sensitivity."""
    
    value: float
    min_value: float
    max_value: float
    description: str
    recommendation: str


# Endpoints

@router.get(
    "/velocity-sensitivity",
    response_model=VelocitySensitivityResponse,
    summary="Get velocity sensitivity setting"
)
async def get_velocity_sensitivity(db: Session = Depends(get_db)):
    """
    Retrieve the current velocity sensitivity setting for face tracking.
    
    Returns the percentage tolerance used for temporal grouping of faces
    across video frames.
    """
    try:
        service = WorkflowSettingsService(db)
        value = await service.get_velocity_sensitivity()
        
        recommendation = _get_recommendation(value)
        
        return VelocitySensitivityResponse(
            value=value,
            min_value=5.0,
            max_value=50.0,
            description="Face tracking tolerance percentage for temporal grouping",
            recommendation=recommendation
        )
        
    except Exception as e:
        logger.error(f"Error retrieving velocity sensitivity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve setting: {str(e)}"
        )


@router.put(
    "/velocity-sensitivity",
    response_model=Dict[str, Any],
    summary="Update velocity sensitivity setting"
)
async def update_velocity_sensitivity(
    request: VelocitySensitivityUpdate,
    db: Session = Depends(get_db)
):
    """
    Update the velocity sensitivity setting for face tracking.
    
    - **value**: New percentage (5.0-50.0)
    - **updated_by**: Optional identifier of who made the change
    
    The setting is validated and stored immediately, affecting all future
    person objects workflows.
    """
    try:
        service = WorkflowSettingsService(db)
        result = await service.update_setting(
            key='velocity_sensitivity',
            value=request.value,
            updated_by=request.updated_by
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return {
            "success": True,
            "message": result["message"],
            "value": result["value"],
            "recommendation": _get_recommendation(result["value"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating velocity sensitivity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update setting: {str(e)}"
        )


# Helper Functions

def _get_recommendation(value: float) -> str:
    """Generate recommendation text based on sensitivity value."""
    if value <= 15:
        return "Recommended for stationary or slow-moving subjects"
    elif value <= 25:
        return "Recommended for normal walking speed (default)"
    elif value <= 40:
        return "Recommended for fast-moving subjects or running"
    else:
        return "Recommended for very fast motion or unstable cameras"
```

#### 5.1.4 Register Endpoints in Main

**File**: `ppl-meta-orchestrator/src/main.py` (MODIFY)

```python
# Add import
from .api import workflow_settings_endpoints

# Register router (add after monitoring endpoints)
app.include_router(workflow_settings_endpoints.router)
```

#### 5.1.5 Test Orchestrator Endpoints

```bash
# Get current setting
curl -X GET http://localhost:8002/api/v1/settings/workflow/velocity-sensitivity

# Update setting
curl -X PUT http://localhost:8002/api/v1/settings/workflow/velocity-sensitivity \
  -H "Content-Type: application/json" \
  -d '{"value": 30.0, "updated_by": "test_user"}'
```

---

### Phase 2: Backend - Vision Service Integration (1.5 hours)

> **Note**: This phase modifies 3 production files in the vision service. Test files remain unchanged.

#### 5.2.1 Modify Workflow Controller

**File**: `ppl-meta-vision/src/person_objects/ppl_thread_workflow.py`

**Changes**:

1. Remove hardcoded default (line 76):
```python
# OLD:
self.default_tolerance_percent = 20.0

# NEW:
self.default_tolerance_percent = None  # Will be fetched from orchestrator
```

2. Add method to fetch from orchestrator:
```python
async def _fetch_velocity_sensitivity_from_orchestrator(self) -> float:
    """
    Fetch velocity sensitivity setting from orchestrator service.
    Falls back to 20.0 if orchestrator is unreachable.
    """
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'http://localhost:8002/api/v1/settings/workflow/velocity-sensitivity',
                timeout=aiohttp.ClientTimeout(total=3)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    value = data.get('value', 20.0)
                    logger.info(f"Retrieved velocity sensitivity from orchestrator: {value}%")
                    return value
                else:
                    logger.warning(f"Orchestrator returned status {response.status}, using default")
                    return 20.0
    except Exception as e:
        logger.warning(f"Failed to fetch velocity sensitivity from orchestrator: {e}, using default 20.0")
        return 20.0
```

3. Update method signatures to accept None and fetch (lines 224, 432):
```python
async def start_workflow_from_session(
    self,
    session_uuid: str,
    tolerance_percent: Optional[float] = None,  # Changed from 20.0
    workflow_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Start person objects workflow from existing face detection session."""
    
    # Fetch from orchestrator if not provided
    if tolerance_percent is None:
        tolerance_percent = await self._fetch_velocity_sensitivity_from_orchestrator()
    
    # ... rest of method
```

#### 5.2.2 Update API Request Models

**File**: `ppl-meta-vision/src/person_objects/person_objects_api.py`

**Changes** (lines 83, 135):

```python
# OLD:
tolerance_percent: float = Field(
    default=20.0,
    description="Position matching tolerance percentage (5.0-50.0)",
    ge=5.0,
    le=50.0,
)

# NEW:
tolerance_percent: Optional[float] = Field(
    default=None,  # Will use orchestrator setting if None
    description="Position matching tolerance percentage (5.0-50.0), fetched from settings if not provided",
    ge=5.0,
    le=50.0,
)
```

Update example JSON (lines 109, 183):
```python
"tolerance_percent": None,  # Uses system setting (default: 20.0)
```

#### 5.2.3 Test Vision Service

```bash
# Start workflow without tolerance_percent (should fetch from orchestrator)
curl -X POST http://localhost:8003/api/v1/person-objects/workflows/start \
  -H "Content-Type: application/json" \
  -d '{"session_uuid": "test-uuid-123"}'

# Start workflow with explicit tolerance_percent (should use provided value)
curl -X POST http://localhost:8003/api/v1/person-objects/workflows/start \
  -H "Content-Type: application/json" \
  -d '{"session_uuid": "test-uuid-123", "tolerance_percent": 35.0}'
```

---

### Phase 3: Frontend - Settings UI (2 hours)

#### 5.3.1 Add Workflow Settings Model

**File**: `ppl-meta-frontend/lib/models/settings_models.dart` (MODIFY)

Add new model before `ConfigurationBundle`:

```dart
// ====================
// Workflow Settings
// ====================

@JsonSerializable()
class WorkflowSettings {
  final double velocitySensitivity;

  WorkflowSettings({
    required this.velocitySensitivity,
  });

  factory WorkflowSettings.fromJson(Map<String, dynamic> json) =>
      _$WorkflowSettingsFromJson(json);

  Map<String, dynamic> toJson() => _$WorkflowSettingsToJson(this);

  factory WorkflowSettings.defaultSettings() {
    return WorkflowSettings(
      velocitySensitivity: 20.0,
    );
  }

  WorkflowSettings copyWith({
    double? velocitySensitivity,
  }) {
    return WorkflowSettings(
      velocitySensitivity: velocitySensitivity ?? this.velocitySensitivity,
    );
  }
}
```

Update `ConfigurationBundle` to include workflow settings:

```dart
@JsonSerializable()
class ConfigurationBundle {
  final GeneralSettings general;
  final DetectionSettings detection;
  final CameraSettings camera;
  final AutomationSettings automation;
  final WorkflowSettings workflow;  // NEW
  final String version;
  final DateTime exportDate;
  final Map<String, dynamic>? metadata;

  ConfigurationBundle({
    required this.general,
    required this.detection,
    required this.camera,
    required this.automation,
    required this.workflow,  // NEW
    required this.version,
    required this.exportDate,
    this.metadata,
  });
  
  // Update fromJson, toJson, and fromSettings accordingly
}
```

Run code generation:
```bash
cd ppl-meta-frontend
flutter packages pub run build_runner build --delete-conflicting-outputs
```

#### 5.3.2 Create Workflow Settings Provider

**File**: `ppl-meta-frontend/lib/providers/settings_providers.dart` (MODIFY)

Add provider:

```dart
import 'package:dio/dio.dart';
import '../models/settings_models.dart';

// Workflow Settings Provider
final workflowSettingsProvider =
    StateNotifierProvider<WorkflowSettingsNotifier, AsyncValue<WorkflowSettings>>(
  (ref) => WorkflowSettingsNotifier(),
);

class WorkflowSettingsNotifier extends StateNotifier<AsyncValue<WorkflowSettings>> {
  WorkflowSettingsNotifier() : super(const AsyncValue.loading()) {
    _loadSettings();
  }

  final Dio _dio = Dio(BaseOptions(baseUrl: 'http://localhost:8002'));

  Future<void> _loadSettings() async {
    try {
      final response = await _dio.get('/api/v1/settings/workflow/velocity-sensitivity');
      
      if (response.statusCode == 200) {
        final value = response.data['value'] as double;
        state = AsyncValue.data(
          WorkflowSettings(velocitySensitivity: value)
        );
      } else {
        throw Exception('Failed to load settings');
      }
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }

  Future<void> updateVelocitySensitivity(double value) async {
    try {
      final response = await _dio.put(
        '/api/v1/settings/workflow/velocity-sensitivity',
        data: {
          'value': value,
          'updated_by': 'frontend_user',
        },
      );

      if (response.statusCode == 200) {
        state = AsyncValue.data(
          state.value!.copyWith(velocitySensitivity: value)
        );
      } else {
        throw Exception('Failed to update setting');
      }
    } catch (e, stack) {
      state = AsyncValue.error(e, stack);
    }
  }
  
  String getRecommendation(double value) {
    if (value <= 15) {
      return "Recommended for stationary or slow-moving subjects";
    } else if (value <= 25) {
      return "Recommended for normal walking speed (default)";
    } else if (value <= 40) {
      return "Recommended for fast-moving subjects or running";
    } else {
      return "Recommended for very fast motion or unstable cameras";
    }
  }
}
```

#### 5.3.3 Add UI Tab to Settings Screen

**File**: `ppl-meta-frontend/lib/screens/settings_screen.dart` (MODIFY)

1. Update TabController length (line 20):
```dart
_tabController = TabController(length: 6, vsync: this);  // Changed from 5 to 6
```

2. Add tab (line 38):
```dart
Tab(icon: Icon(Icons.speed), text: 'Workflow'),
```

3. Add tab view (line 48):
```dart
const WorkflowSettingsTab(),
```

4. Add new tab class at end of file:

```dart
// ====================
// Workflow Settings Tab
// ====================

class WorkflowSettingsTab extends ConsumerWidget {
  const WorkflowSettingsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(workflowSettingsProvider);
    final notifier = ref.watch(workflowSettingsProvider.notifier);

    return settings.when(
      data: (data) => SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSectionHeader('Person Tracking'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'People Velocity Sensitivity',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Controls face tracking tolerance for temporal grouping across video frames',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.grey[600],
                      ),
                    ),
                    const SizedBox(height: 24),
                    Center(
                      child: Text(
                        '${data.velocitySensitivity.toStringAsFixed(0)}%',
                        style: Theme.of(context).textTheme.displaySmall?.copyWith(
                          fontWeight: FontWeight.bold,
                          color: Theme.of(context).primaryColor,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        const Icon(Icons.directions_walk, size: 16),
                        const SizedBox(width: 4),
                        const Text('Slow', style: TextStyle(fontSize: 12)),
                        Expanded(
                          child: Slider(
                            value: data.velocitySensitivity,
                            min: 5.0,
                            max: 50.0,
                            divisions: 45,
                            label: '${data.velocitySensitivity.toStringAsFixed(0)}%',
                            onChanged: (value) => notifier.updateVelocitySensitivity(value),
                          ),
                        ),
                        const Icon(Icons.directions_run, size: 16),
                        const SizedBox(width: 4),
                        const Text('Fast', style: TextStyle(fontSize: 12)),
                      ],
                    ),
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.blue[50],
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.blue[200]!),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.info_outline, color: Colors.blue[700], size: 20),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              notifier.getRecommendation(data.velocitySensitivity),
                              style: TextStyle(
                                fontSize: 12,
                                fontStyle: FontStyle.italic,
                                color: Colors.blue[700],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),
                    const Divider(),
                    const SizedBox(height: 16),
                    ExpansionTile(
                      leading: const Icon(Icons.help_outline),
                      title: const Text('How does this work?'),
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              _buildHelpItem(
                                'Face Detection',
                                'System detects faces in each video frame with position coordinates',
                              ),
                              const SizedBox(height: 12),
                              _buildHelpItem(
                                'Temporal Grouping',
                                'Faces in consecutive frames are compared using this tolerance percentage',
                              ),
                              const SizedBox(height: 12),
                              _buildHelpItem(
                                'Lower Values (5-15%)',
                                'Stricter matching - best for stationary or slow-moving people',
                              ),
                              const SizedBox(height: 12),
                              _buildHelpItem(
                                'Default (20%)',
                                'Balanced approach for normal walking speed',
                              ),
                              const SizedBox(height: 12),
                              _buildHelpItem(
                                'Higher Values (30-50%)',
                                'Looser matching - best for fast motion or jerky camera movement',
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, stack) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error, size: 64, color: Colors.red),
            const SizedBox(height: 16),
            Text('Error loading workflow settings: $error'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => ref.refresh(workflowSettingsProvider),
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16),
      child: Text(
        title,
        style: const TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  Widget _buildHelpItem(String title, String description) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 6,
          height: 6,
          margin: const EdgeInsets.only(top: 6),
          decoration: const BoxDecoration(
            shape: BoxShape.circle,
            color: Colors.blue,
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                description,
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[700],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
```

---

### Phase 4: Testing & Validation (1.5 hours)

#### 5.4.1 Unit Tests

**File**: `ppl-meta-orchestrator/tests/test_workflow_settings.py` (NEW)

```python
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_get_velocity_sensitivity_default():
    """Test retrieving default velocity sensitivity."""
    response = client.get("/api/v1/settings/workflow/velocity-sensitivity")
    assert response.status_code == 200
    data = response.json()
    assert "value" in data
    assert data["value"] == 20.0
    assert data["min_value"] == 5.0
    assert data["max_value"] == 50.0

def test_update_velocity_sensitivity_valid():
    """Test updating velocity sensitivity with valid value."""
    response = client.put(
        "/api/v1/settings/workflow/velocity-sensitivity",
        json={"value": 30.0, "updated_by": "test_user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["value"] == 30.0

def test_update_velocity_sensitivity_below_min():
    """Test updating with value below minimum."""
    response = client.put(
        "/api/v1/settings/workflow/velocity-sensitivity",
        json={"value": 3.0, "updated_by": "test_user"}
    )
    assert response.status_code == 422  # Validation error

def test_update_velocity_sensitivity_above_max():
    """Test updating with value above maximum."""
    response = client.put(
        "/api/v1/settings/workflow/velocity-sensitivity",
        json={"value": 55.0, "updated_by": "test_user"}
    )
    assert response.status_code == 422  # Validation error
```

Run tests:
```bash
cd ppl-meta-orchestrator
pytest tests/test_workflow_settings.py -v
```

#### 5.4.2 Integration Tests

**Test Script**: `test_velocity_sensitivity_integration.py`

```python
"""
Integration test for velocity sensitivity setting across services.
"""

import asyncio
import aiohttp
import json

ORCHESTRATOR_URL = "http://localhost:8002"
VISION_URL = "http://localhost:8003"

async def test_full_workflow():
    """Test complete workflow from settings update to vision service usage."""
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Get current setting
        print("📊 Step 1: Retrieving current setting...")
        async with session.get(f"{ORCHESTRATOR_URL}/api/v1/settings/workflow/velocity-sensitivity") as resp:
            data = await resp.json()
            original_value = data['value']
            print(f"   Current value: {original_value}%")
        
        # Step 2: Update setting
        print("\n✏️  Step 2: Updating setting to 35%...")
        async with session.put(
            f"{ORCHESTRATOR_URL}/api/v1/settings/workflow/velocity-sensitivity",
            json={"value": 35.0, "updated_by": "integration_test"}
        ) as resp:
            data = await resp.json()
            assert data['success'] is True
            print(f"   Updated successfully: {data['message']}")
        
        # Step 3: Verify update
        print("\n✅ Step 3: Verifying update...")
        async with session.get(f"{ORCHESTRATOR_URL}/api/v1/settings/workflow/velocity-sensitivity") as resp:
            data = await resp.json()
            assert data['value'] == 35.0
            print(f"   Verified: {data['value']}%")
        
        # Step 4: Start vision workflow (should use new setting)
        print("\n🚀 Step 4: Starting vision workflow...")
        async with session.post(
            f"{VISION_URL}/api/v1/person-objects/workflows/start",
            json={"session_uuid": "test-session-123"}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                print(f"   Workflow started: {data.get('workflow_id', 'N/A')}")
            else:
                print(f"   Note: Workflow start returned {resp.status} (expected if no test session)")
        
        # Step 5: Restore original value
        print(f"\n🔄 Step 5: Restoring original value {original_value}%...")
        async with session.put(
            f"{ORCHESTRATOR_URL}/api/v1/settings/workflow/velocity-sensitivity",
            json={"value": original_value, "updated_by": "integration_test"}
        ) as resp:
            data = await resp.json()
            print(f"   Restored: {data['message']}")
        
        print("\n✅ Integration test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_full_workflow())
```

Run integration test:
```bash
python test_velocity_sensitivity_integration.py
```

#### 5.4.3 Manual UI Testing

1. **Navigate to Settings**:
   - Open `http://localhost:3000/#/settings`
   - Click "Workflow" tab
   - Verify "People Velocity Sensitivity" slider is visible

2. **Test Slider Interaction**:
   - Drag slider to different values (e.g., 10%, 35%, 45%)
   - Verify percentage displays correctly
   - Verify recommendation text changes appropriately

3. **Test Value Persistence**:
   - Set slider to 30%
   - Refresh browser
   - Verify value is still 30%

4. **Test Workflow Integration**:
   - Set velocity sensitivity to 40%
   - Start a person objects workflow
   - Verify workflow uses 40% tolerance (check logs)

5. **Test Edge Cases**:
   - Drag slider to minimum (5%)
   - Drag slider to maximum (50%)
   - Verify no errors occur

---

## 6. Testing Strategy

### 6.1 Test Matrix

| Test Case | Expected Result | Priority |
|-----------|----------------|----------|
| Get default setting (no prior update) | Returns 20.0% | High |
| Update to valid value (e.g., 30%) | Success, persisted | High |
| Update to minimum (5%) | Success | Medium |
| Update to maximum (50%) | Success | Medium |
| Update below minimum (3%) | Validation error 422 | High |
| Update above maximum (55%) | Validation error 422 | High |
| Start workflow without tolerance param | Uses orchestrator setting | High |
| Start workflow with explicit tolerance | Uses provided value, ignores setting | High |
| Orchestrator unreachable | Vision falls back to 20.0% | Medium |
| Multiple rapid updates | Last update wins, no race conditions | Low |
| Browser refresh after update | Value persists | High |
| Recommendation text accuracy | Correct for all ranges | Medium |

### 6.2 Performance Tests

**Load Test**: Update setting 100 times concurrently
```bash
for i in {1..100}; do
  curl -X PUT http://localhost:8002/api/v1/settings/workflow/velocity-sensitivity \
    -H "Content-Type: application/json" \
    -d "{\"value\": $((RANDOM % 46 + 5)).0}" &
done
wait
```

**Expected**: No deadlocks, final value is valid, ~500ms total execution time

### 6.3 Regression Tests

Ensure existing functionality remains unchanged:
- ✅ Person objects workflows with explicit `tolerance_percent` parameter still work
- ✅ Existing database records retain their stored `tolerance_percent` values
- ✅ **Test files continue to pass WITHOUT modification** - hardcoded 20.0 values in tests remain as baseline references
- ✅ API response schemas remain backward compatible

**Important**: All 34 occurrences of hardcoded 20.0% in test files (see section 3.3) must remain unchanged. These tests validate:
1. The algorithm works correctly at the default 20% tolerance
2. Explicit tolerance_percent parameters override system settings
3. Valid tolerance ranges (5.0-50.0) are properly handled
4. Backward compatibility with original behavior

---

## 7. Rollback Plan

### 7.1 Immediate Rollback (< 5 minutes)

If critical issues arise after deployment:

1. **Database**: Set velocity_sensitivity back to 20.0
```sql
UPDATE workflow_settings 
SET setting_value = 20.0 
WHERE setting_key = 'velocity_sensitivity';
```

2. **Code**: Revert commits
```bash
git revert <commit-hash-phase-3>
git revert <commit-hash-phase-2>
git revert <commit-hash-phase-1>
git push origin main
```

3. **Services**: Restart affected services
```bash
# Restart orchestrator
cd ppl-meta-orchestrator && pkill -f uvicorn && source venv/bin/activate && uvicorn src.main:app --reload &

# Restart vision
cd ppl-meta-vision && pkill -f python && python src/main.py &
```

### 7.2 Database Cleanup

If migration needs to be reverted:

```bash
cd ppl-meta-orchestrator
source venv/bin/activate
alembic downgrade -1
```

### 7.3 Frontend Rollback

Remove workflow tab and provider:

```bash
cd ppl-meta-frontend
git checkout HEAD -- lib/screens/settings_screen.dart
git checkout HEAD -- lib/providers/settings_providers.dart
git checkout HEAD -- lib/models/settings_models.dart
flutter clean && flutter pub get
```

---

## 8. Appendices

### A. Environment Variables

No new environment variables required. System uses existing database connections.

### B. Dependencies

**Backend**:
- `aiohttp` (already installed in vision service)
- `pydantic` (already installed)

**Frontend**:
- `dio` (already installed)

### C. Documentation Updates

After implementation, update:
1. `docs/api/ORCHESTRATOR_API.md` - Add workflow settings endpoints
2. `docs/guides/SETTINGS_GUIDE.md` - Add velocity sensitivity section
3. `README.md` - Update feature list
4. `CHANGELOG.md` - Add v2.21.12 entry

### D. Performance Baselines

**Expected Query Times**:
- GET velocity_sensitivity: < 10ms
- PUT velocity_sensitivity: < 50ms (includes validation + database write)

**Database Impact**:
- New table: `workflow_settings` (1 row initially, ~10 rows max)
- Index on `setting_key` for fast lookups
- Negligible storage impact (< 1 KB)

### E. Security Considerations

**Access Control**:
- Endpoints should be protected by authentication (future enhancement)
- Consider role-based access (admin-only writes, read-only for operators)

**Validation**:
- All inputs validated at API layer
- Database constraints enforce min/max bounds
- Prevents SQL injection via parameterized queries

---

## 9. Success Criteria

Implementation is considered successful when:

✅ **Functional**:
1. Users can adjust velocity sensitivity via slider at `http://localhost:3000/#/settings`
2. Setting persists across browser refreshes and service restarts
3. New person objects workflows use the configured sensitivity
4. Explicit `tolerance_percent` parameters override the setting

✅ **Performance**:
1. Setting retrieval < 10ms
2. Setting update < 50ms
3. No impact on workflow execution time

✅ **Quality**:
1. All unit tests pass
2. Integration test completes successfully
3. Manual UI testing confirms correct behavior
4. No regression in existing functionality

✅ **Documentation**:
1. API endpoints documented in OpenAPI schema
2. User guide updated with screenshots
3. Release notes published

---

## 10. Timeline

**Total Estimated Time**: 7 hours

| Phase | Duration | Assignee |
|-------|----------|----------|
| Phase 1: Orchestrator Backend | 2 hours | Backend Developer |
| Phase 2: Vision Service Integration | 1.5 hours | Backend Developer |
| Phase 3: Frontend UI | 2 hours | Frontend Developer |
| Phase 4: Testing & Validation | 1.5 hours | QA / Developer |

**Deployment Window**: Low-risk deployment, can be done during business hours with quick rollback available.

---

## 11. Contacts

**Technical Leads**:
- Backend: [Backend Team Lead]
- Frontend: [Frontend Team Lead]
- QA: [QA Team Lead]

**Escalation**:
- Critical issues: [On-Call Engineer]
- Product questions: [Product Manager]

---

**Document Status**: Ready for Implementation  
**Next Steps**: Review with team, assign phases, schedule kickoff meeting

**Approval Required From**:
- [ ] Backend Team Lead
- [ ] Frontend Team Lead
- [ ] QA Team Lead
- [ ] Product Manager

---

## 12. Test File Reference - Hardcoded 20% Values

**IMPORTANT**: The following test files contain hardcoded 20.0% values that **WILL NOT be modified** during implementation. These serve as reference documentation and regression test baselines.

### Quick Reference Table

| Test File | Occurrences | Purpose |
|-----------|-------------|---------|
| `test_phase2_core_face_grouping.py` | 3 | Core algorithm validation |
| `test_phase3_workflow_integration.py` | 17 | Workflow integration tests |
| `test_phase4_integration_suite.py` | 8 | End-to-end integration |
| `validate_phase3_integration.py` | 3 | Phase 3 validation |
| `test_phase1_person_objects_schema.py` | 1 | Database schema tests |
| `tests/test_integration_comprehensive.py` | 1 | Performance tests |
| `setup_phase2.py` | 1 | Bootstrap/setup script |
| **TOTAL** | **34** | - |

### Detailed Listing

#### 1. `ppl-meta-vision/test_phase2_core_face_grouping.py`

**Lines with 20.0**: 114, 115, 184, 205

**Context**:
```python
# Line 114: Comment explaining calculation
# With 20% tolerance: x_tolerance = 100 * 0.2 = 20, y_tolerance = 150 * 0.2 = 30

# Line 115: Assertion validating tolerance calculation
self.assertEqual(result["x_tolerance_used"], 20.0)

# Line 184: Method call with explicit tolerance
self.sample_faces, tolerance_percent=20.0

# Line 205: Assertion checking statistics
self.assertEqual(statistics["tolerance_percent"], 20.0)
```

**Purpose**: Tests the core face grouping algorithm's distance calculation and tolerance matching with 20% as baseline.

---

#### 2. `ppl-meta-vision/test_phase3_workflow_integration.py`

**Lines with 20.0**: 59, 164, 209, 299, 307, 337, 444, 464, 521, 614, 674, 695, 800, 913, 919

**Context**:
```python
# Line 59: Mock controller initialization
self.default_tolerance_percent = 20.0

# Line 164: Test default value
self.assertEqual(self.controller.default_tolerance_percent, 20.0)

# Line 209: Workflow start with explicit tolerance
tolerance_percent=20.0,

# Lines 299, 307, 337, 614, 674, 695: JSON test data
"tolerance_percent": 20.0,

# Line 444: Range testing (includes 20.0 as middle value)
tolerance_values = [5.0, 15.0, 20.0, 30.0, 45.0]

# Line 464: Parameterized tolerance test
session_uuid=self.test_session_uuid, tolerance_percent=tolerance

# Line 521: Test with explicit 20.0
workflow_id, self.test_session_uuid, 20.0, {"test": "metadata"}

# Line 800: Engine method call
results = await engine.apply_percentage_based_tracking(test_faces, 20.0)

# Lines 913, 919: Edge case tests (1.0 and 50.0)
session_uuid="test-session", tolerance_percent=1.0
session_uuid="test-session", tolerance_percent=50.0
```

**Purpose**: Integration tests for the workflow controller, validating default behavior and explicit tolerance parameters.

---

#### 3. `ppl-meta-vision/test_phase4_integration_suite.py`

**Lines with 20.0**: 83, 281, 335, 343, 382, 435, 504

**Context**:
```python
# Line 83: Test configuration
"tolerance_percent": 20.0,

# Line 281: Workflow start parameter
tolerance_percent=20.0,

# Lines 335, 343, 382: JSON request bodies
"tolerance_percent": 20.0,

# Line 435: Database record assertion
self.assertEqual(group["Tolerance_Percent"], 20.0)

# Line 504: Engine method call
test_faces, 20.0
```

**Purpose**: End-to-end integration tests validating the complete workflow from API request to database storage.

---

#### 4. `ppl-meta-vision/validate_phase3_integration.py`

**Lines with 20.0**: 133, 187, 192

**Context**:
```python
# Line 133: Engine validation
results = await engine.apply_percentage_based_tracking(test_faces, 20.0)

# Line 187: Request validation data
"tolerance_percent": 20.0,

# Line 192: Assertion checking request model
assert request.tolerance_percent == 20.0
```

**Purpose**: Validation script for Phase 3 completion, ensuring default tolerance is properly handled.

---

#### 5. `ppl-meta-vision/test_phase1_person_objects_schema.py`

**Lines with 20.0**: 351

**Context**:
```python
# Line 351: SQL INSERT test data
VALUES (%s, %s, 10, 20.0, %s)
```

**Purpose**: Database schema test with sample person object data using default 20% tolerance.

---

#### 6. `ppl-meta-vision/tests/test_integration_comprehensive.py`

**Lines with 20.0**: 170

**Context**:
```python
# Line 170: Performance timing (NOT tolerance-related)
"total_processing_time": 120.0,  # This is 20*6 seconds, unrelated to tolerance
```

**Purpose**: Comprehensive integration test with performance metrics. The 120.0 value is coincidentally divisible by 20 but represents processing time, not tolerance.

---

#### 7. `ppl-meta-vision/setup_phase2.py`

**Lines with 20.0**: ~79 (function scope)

**Context**:
```python
# Line 79: Setup function for Phase 2
def test_face_grouping_engine():
    # Contains initialization and testing with 20.0 default
    engine = VisionFaceGroupingEngine()
    # ... tests using default 20.0 tolerance
```

**Purpose**: Bootstrap script for Phase 2 development, setting up test environment with 20% baseline.

---

### Why These Files Remain Unchanged

1. **Baseline Documentation**: Tests document the original 20% default behavior that the system was designed and validated against.

2. **Regression Safety**: If we modify tests, we lose the baseline. Tests should validate that:
   - The algorithm still works at 20% (original design)
   - Explicit tolerance_percent parameters override settings
   - The system falls back to 20% if settings are unavailable

3. **Test Independence**: Unit and integration tests should be deterministic. They test specific behaviors with known inputs, not dynamic system configuration.

4. **Backward Compatibility**: Tests prove that code changes don't break existing functionality. If workflows that explicitly pass tolerance_percent=20.0 stop working, tests will catch it.

5. **Reference Implementation**: These tests serve as documentation for developers, showing valid usage patterns and expected values.

### Post-Implementation Verification

After implementing the configurable setting, these tests should:
- ✅ **PASS** without modification
- ✅ Validate that explicit `tolerance_percent` parameters work
- ✅ Validate that the algorithm logic hasn't changed
- ✅ Serve as regression checks for the core functionality

If any of these tests fail after implementation, it indicates a breaking change that needs to be fixed in the production code, not the tests.

---

**End of Document*
