# MVR-People: Machine Vision Representation - People

**Date:** October 30, 2025  
**Version:** 2.0.0 - Design Specification with Matching & Merging Logic  
**Service:** ppl-meta-vmeta  
**Status:** 📋 DESIGN PHASE - NOT YET IMPLEMENTED

---

## Overview

This document outlines the design and implementation plan for the **MVR-People** (Machine Vision Representation - People) feature in the ppl-meta-vmeta service. MVR-People creates persistent machine learning representations of individuals tracked across videos, with **automatic matching and merging** capabilities to consolidate duplicate individuals and enable advanced features like similarity search, demographic analysis, and person re-identification.

---

## Executive Summary

### What is MVR-People?

MVR-People is a data object that stores machine learning-derived representations of individuals, including:
- **Face embeddings** (machine vision vectors for face recognition)
- **Age estimation** (predicted age range)
- **Gender estimation** (predicted gender classification)

### Why MVR-People?

Current cross-video individual tracking identifies the same person across videos but lacks:
- ❌ Persistent ML representations for similarity search
- ❌ Demographic information (age, gender)
- ❌ Re-identification capabilities across sessions
- ❌ Ability to search for "similar looking" individuals

MVR-People solves these problems by creating a unified ML representation per individual.

### Key Requirements

1. **Automatic MVR-People Creation**: Each Individual automatically gets an MVR-People upon creation
2. **Dynamic Matching & Merging**: When Individuals match above threshold, they merge to single MVR-People
3. **One-to-Many Relationship**: One MVR-People ↔ Many Individuals (after merging)
4. **Orphan MVR-People Tracking**: Orphaned MVR-People retain history via JSON field
5. **Best Quality Selection**: Use representative (highest quality) face from individual
6. **Configurable Matching Threshold**: Default matching threshold with update capability
7. **Independent ML Models**: Replicate ppl-meta-mini models (not import from it)
8. **Database Persistence**: Store vectors and estimates in vmeta database
9. **API Accessibility**: Expose via REST API for similarity search and retrieval

---

## Architecture

### System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                    ppl-meta-vmeta Service                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐          ┌──────────────────┐           │
│  │   Individual     │  N:1     │   MVR-People     │           │
│  │   (Existing)     │─────────▶│     (NEW)        │           │
│  └──────────────────┘          └──────────────────┘           │
│         │                               │                      │
│         │                               │                      │
│         ▼                               ▼                      │
│  ┌──────────────────┐          ┌──────────────────┐           │
│  │  Appearances     │          │  Face Embeddings │           │
│  │  (Multiple)      │          │  Age Estimate    │           │
│  │  Best Quality ──▶│          │  Gender Estimate │           │
│  └──────────────────┘          └──────────────────┘           │
│                                                                 │
│  ┌─────────────────────────────────────────────────┐          │
│  │         ML Processing Pipeline                  │          │
│  │  1. Select best quality face from individual    │          │
│  │  2. Extract face embeddings (FaceNet/ArcFace)   │          │
│  │  3. Estimate age (CNN age classifier)           │          │
│  │  4. Estimate gender (CNN gender classifier)     │          │
│  │  5. Store in MVR-People record                  │          │
│  └─────────────────────────────────────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Relationships

```
Individual (1) ─────────── (Many) Appearances
     │                          │
     │                          │
     │ (Many:1)                 │ (has best quality face)
     │                          │
     ▼                          ▼
MVR-People ◀──────────── Best Quality Face
     │                          
     ├── Face Embeddings (512D vector)
     ├── Age Estimate (min, max, confidence)
     ├── Gender Estimate (male/female, confidence)
     └── Previous Individual UUIDs (JSON array for orphaned MVR)
```

**Lifecycle:**
```
Step 1: Individual Created → MVR-People Created Automatically (1:1)
Step 2: Matching Process Compares Individuals
Step 3: If Match Score > Threshold → Merge to Better MVR-People
Step 4: Orphaned MVR-People Created → Stores Previous Individual UUIDs
Step 5: Predominant MVR-People Updated → Multiple Individuals Linked
```

**Key Constraints:**
- ✅ **Automatic Creation**: Each Individual automatically gets MVR-People on creation (1:1 initially)
- ✅ **Dynamic Merging**: Individuals merge to single MVR-People when match score > threshold
- ✅ **One-to-Many**: One MVR-People ← Many Individuals (after merging)
- ✅ **Orphan Tracking**: Orphaned MVR-People retain previous Individual UUIDs in JSON field
- ✅ **Best Quality**: MVR-People always uses best quality face from all linked Individuals
- ✅ **Active MVR Only**: Only active (non-orphaned) MVR-People used for matching

---

## Matching and Merging Logic

### Overview

The MVR-People system implements an **automatic matching and merging workflow** that consolidates Individual objects when they are determined to represent the same person. This enables person re-identification across different tracking sessions while maintaining data integrity and historical tracking.

### Visual Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Automatic MVR-People Creation                                 │
│─────────────────────────────────────────────────────────────────────────│
│                                                                         │
│  Individual A Created  ────────▶  MVR-People A Created (1:1)           │
│  (Quality: 0.75)                  - Face Embedding: [0.1, 0.2, ...]    │
│                                   - Age: 25-35                          │
│                                   - Gender: Male                        │
│                                   - Status: Active                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: Matching Process (Background Task)                            │
│─────────────────────────────────────────────────────────────────────────│
│                                                                         │
│  Search Similar MVR-People:                                            │
│  - Cosine Similarity Search                                            │
│  - Threshold: 0.85 (configurable)                                      │
│  - Exclude Orphaned MVR-People                                         │
│                                                                         │
│  MATCH FOUND! ✓                                                        │
│  ┌────────────────────────────────────────────┐                       │
│  │ MVR-People B (Existing)                    │                       │
│  │ - Quality: 0.88                            │                       │
│  │ - Similarity to A: 0.92 (above threshold!) │                       │
│  │ - Status: Active                           │                       │
│  │ - Linked Individuals: 1                    │                       │
│  └────────────────────────────────────────────┘                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: Merge Decision (Quality Comparison)                           │
│─────────────────────────────────────────────────────────────────────────│
│                                                                         │
│  Compare Quality Scores:                                               │
│  - MVR-People A: 0.75                                                  │
│  - MVR-People B: 0.88  ◀─── WINNER (Predominant)                      │
│                                                                         │
│  Decision: Merge Individual A to MVR-People B                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: Merge Execution                                               │
│─────────────────────────────────────────────────────────────────────────│
│                                                                         │
│  1. Reassign Individual A:                                             │
│     Individual A ───X───▶ MVR-People A (old link removed)             │
│     Individual A ────────▶ MVR-People B (new link added)              │
│                                                                         │
│  2. Mark MVR-People A as Orphaned:                                     │
│     ┌──────────────────────────────────────┐                          │
│     │ MVR-People A (ORPHANED)              │                          │
│     │ - is_orphaned: TRUE                  │                          │
│     │ - orphaned_at: 2025-10-30 14:30:00   │                          │
│     │ - merged_into_mvr_uuid: B            │                          │
│     │ - previous_individual_uuids: [A]     │                          │
│     │ - total_linked_individuals: 0        │                          │
│     └──────────────────────────────────────┘                          │
│                                                                         │
│  3. Update MVR-People B (Predominant):                                 │
│     ┌──────────────────────────────────────┐                          │
│     │ MVR-People B (ACTIVE)                │                          │
│     │ - Status: Active                     │                          │
│     │ - Linked Individuals: [A, B]         │                          │
│     │ - total_linked_individuals: 2        │                          │
│     │ - Quality: 0.88 (unchanged)          │                          │
│     └──────────────────────────────────────┘                          │
│                                                                         │
│  4. Create Audit Log:                                                  │
│     - Predominant: MVR-People B                                        │
│     - Orphaned: MVR-People A                                           │
│     - Similarity: 0.92                                                 │
│     - Merged At: 2025-10-30 14:30:00                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: Post-Merge State                                              │
│─────────────────────────────────────────────────────────────────────────│
│                                                                         │
│  ACTIVE MVR-People:                                                    │
│  ┌─────────────────────────────────────────────────────────┐          │
│  │ MVR-People B                                            │          │
│  │ ┌──────────────┐  ┌──────────────┐                     │          │
│  │ │Individual A  │  │Individual B  │                     │          │
│  │ │(Reassigned)  │  │(Original)    │                     │          │
│  │ └──────────────┘  └──────────────┘                     │          │
│  │ Total Linked: 2                                        │          │
│  │ Quality: 0.88 (from Individual B's best face)          │          │
│  └─────────────────────────────────────────────────────────┘          │
│                                                                         │
│  ORPHANED MVR-People:                                                  │
│  ┌─────────────────────────────────────────────────────────┐          │
│  │ MVR-People A (ORPHAN)                                   │          │
│  │ - No active Individual links                            │          │
│  │ - Retains history: previous_individual_uuids: [A]       │          │
│  │ - Excluded from similarity searches                     │          │
│  │ - Retained for audit trail                              │          │
│  └─────────────────────────────────────────────────────────┘          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Workflow Stages

#### Stage 1: Automatic MVR-People Creation

**Trigger:** Individual object created in database

**Action:**
1. System automatically creates corresponding MVR-People object
2. Initial state: 1:1 relationship (Individual ↔ MVR-People)
3. Extract face embedding from best quality face
4. Calculate age/gender estimates
5. Link Individual to MVR-People via `individual_mvr_mapping`

**Result:**
- Every Individual has exactly one MVR-People initially
- MVR-People status: `active`
- Relationship: `is_representative = TRUE`

```python
# Automatic creation on Individual insert
async def create_individual(self, individual_data: dict) -> UUID:
    """Create Individual and auto-create MVR-People."""
    
    # Create Individual
    individual_uuid = await self.db.insert_individual(individual_data)
    
    # Auto-create MVR-People (background task)
    mvr_people_uuid = await self.mvr_service.create_mvr_people_async(
        individual_uuid=individual_uuid,
        auto_created=True
    )
    
    return individual_uuid
```

---

#### Stage 2: Matching Process

**Trigger:** 
- New Individual created (compare with existing)
- Manual matching request via API
- Scheduled batch matching job

**Matching Algorithm:**

```python
async def find_matching_individuals(
    self, 
    individual_uuid: UUID, 
    threshold: float = 0.85  # Configurable matching threshold
) -> List[dict]:
    """
    Find Individuals that match the given Individual based on face similarity.
    
    Args:
        individual_uuid: UUID of Individual to match
        threshold: Cosine similarity threshold (0.0-1.0), default 0.85
        
    Returns:
        List of matching Individuals with similarity scores
    """
    # Get MVR-People for this Individual
    source_mvr = await self.db.get_mvr_for_individual(individual_uuid)
    
    if not source_mvr or not source_mvr['face_embedding_vector']:
        return []
    
    # Search for similar MVR-People (only active, non-orphaned)
    similar_mvr = await self.db.search_similar_mvr_people(
        embedding_vector=source_mvr['face_embedding_vector'],
        threshold=threshold,
        exclude_orphaned=True,  # Only search active MVR-People
        exclude_uuid=source_mvr['mvr_people_uuid']  # Exclude self
    )
    
    # Return matching Individuals with scores
    matches = []
    for mvr in similar_mvr:
        individuals = await self.db.get_individuals_for_mvr(mvr['mvr_people_uuid'])
        for individual in individuals:
            matches.append({
                'individual_uuid': individual['individual_uuid'],
                'mvr_people_uuid': mvr['mvr_people_uuid'],
                'similarity_score': mvr['similarity_score'],
                'quality_score': mvr['quality_score']
            })
    
    return matches
```

**Matching Criteria:**
- **Primary:** Face embedding cosine similarity > threshold
- **Secondary:** Age range overlap (if available)
- **Secondary:** Gender match (if confidence > 0.7)
- **Exclusions:** Orphaned MVR-People excluded from matching

**Default Threshold:** 0.85 (85% similarity)
- Can be configured per deployment
- Can be overridden per API call
- Stored in configuration table

---

#### Stage 3: Merge Decision

**Decision Logic:**

When two Individuals match above threshold:
1. Compare quality scores of their MVR-People
2. Select MVR-People with **higher quality score** as "predominant"
3. Merge both Individuals to predominant MVR-People
4. Mark other MVR-People as "orphaned"

```python
async def merge_individuals_to_best_mvr(
    self, 
    individual_a_uuid: UUID, 
    individual_b_uuid: UUID,
    similarity_score: float
) -> dict:
    """
    Merge two Individuals to the MVR-People with better quality score.
    
    Args:
        individual_a_uuid: First Individual
        individual_b_uuid: Second Individual
        similarity_score: Similarity score from matching
        
    Returns:
        Merge result with predominant and orphaned MVR-People UUIDs
    """
    # Get MVR-People for both Individuals
    mvr_a = await self.db.get_mvr_for_individual(individual_a_uuid)
    mvr_b = await self.db.get_mvr_for_individual(individual_b_uuid)
    
    # Determine predominant MVR-People (higher quality score wins)
    if mvr_a['quality_score'] >= mvr_b['quality_score']:
        predominant_mvr = mvr_a
        orphaned_mvr = mvr_b
        individual_to_reassign = individual_b_uuid
    else:
        predominant_mvr = mvr_b
        orphaned_mvr = mvr_a
        individual_to_reassign = individual_a_uuid
    
    # Execute merge
    result = await self._execute_merge(
        predominant_mvr_uuid=predominant_mvr['mvr_people_uuid'],
        orphaned_mvr_uuid=orphaned_mvr['mvr_people_uuid'],
        individual_to_reassign=individual_to_reassign,
        similarity_score=similarity_score
    )
    
    return result
```

**Quality Score Comparison:**
- Face quality score from best appearance
- Higher quality = more reliable representation
- Tie-breaker: Earlier creation timestamp

---

#### Stage 4: Merge Execution

**Steps:**

1. **Reassign Individual to Predominant MVR-People**
   - Update `individual_mvr_mapping` table
   - Link reassigned Individual to predominant MVR-People
   - Set `is_representative = FALSE` (unless it has better quality)

2. **Mark Orphaned MVR-People**
   - Set `is_orphaned = TRUE`
   - Store previous Individual UUID(s) in `previous_individual_uuids` JSON field
   - Set `orphaned_at` timestamp
   - Set `merged_into_mvr_uuid` to track where it merged

3. **Update Predominant MVR-People**
   - Increment `total_linked_individuals` counter
   - Re-evaluate best quality face (compare all linked Individuals)
   - Update face embedding if new Individual has better quality
   - Update age/gender if better confidence

4. **Create Merge Audit Log**
   - Log merge event with similarity score
   - Track which MVR-People was orphaned
   - Track which Individual was reassigned

```python
async def _execute_merge(
    self,
    predominant_mvr_uuid: UUID,
    orphaned_mvr_uuid: UUID,
    individual_to_reassign: UUID,
    similarity_score: float
) -> dict:
    """Execute the merge operation with all database updates."""
    
    async with self.db.transaction():
        # 1. Get previous Individual UUIDs from orphaned MVR
        prev_individuals = await self.db.get_individuals_for_mvr(orphaned_mvr_uuid)
        prev_uuids = [ind['individual_uuid'] for ind in prev_individuals]
        
        # 2. Reassign Individual to predominant MVR-People
        await self.db.update_individual_mvr_mapping(
            individual_uuid=individual_to_reassign,
            old_mvr_uuid=orphaned_mvr_uuid,
            new_mvr_uuid=predominant_mvr_uuid,
            confidence_score=similarity_score
        )
        
        # 3. Mark orphaned MVR-People
        await self.db.update_mvr_people(
            mvr_people_uuid=orphaned_mvr_uuid,
            updates={
                'is_orphaned': True,
                'orphaned_at': datetime.now(),
                'merged_into_mvr_uuid': predominant_mvr_uuid,
                'previous_individual_uuids': json.dumps(prev_uuids),
                'total_linked_individuals': 0
            }
        )
        
        # 4. Update predominant MVR-People
        await self._update_predominant_mvr_after_merge(predominant_mvr_uuid)
        
        # 5. Create audit log
        await self.db.insert_merge_audit_log({
            'predominant_mvr_uuid': predominant_mvr_uuid,
            'orphaned_mvr_uuid': orphaned_mvr_uuid,
            'reassigned_individual_uuid': individual_to_reassign,
            'similarity_score': similarity_score,
            'merged_at': datetime.now()
        })
        
    return {
        'success': True,
        'predominant_mvr_uuid': predominant_mvr_uuid,
        'orphaned_mvr_uuid': orphaned_mvr_uuid,
        'reassigned_individual': individual_to_reassign,
        'similarity_score': similarity_score
    }
```

---

#### Stage 5: Post-Merge Updates

**Predominant MVR-People Updates:**

After merging, the predominant MVR-People must re-evaluate its representative face:

```python
async def _update_predominant_mvr_after_merge(self, mvr_people_uuid: UUID):
    """Update predominant MVR-People after merging."""
    
    # Get all Individuals linked to this MVR-People
    individuals = await self.db.get_individuals_for_mvr(mvr_people_uuid)
    
    # Find best quality face across ALL linked Individuals
    best_face = await self._find_best_quality_face_across_individuals(
        [ind['individual_uuid'] for ind in individuals]
    )
    
    # Check if best face changed
    current_mvr = await self.db.get_mvr_people(mvr_people_uuid)
    
    if best_face['face_uuid'] != current_mvr['representative_face_uuid']:
        # New best face found - regenerate embeddings
        new_embedding = await self.ml_processor.extract_face_embedding(
            best_face['image']
        )
        new_age = await self.ml_processor.estimate_age(best_face['image'])
        new_gender = await self.ml_processor.estimate_gender(best_face['image'])
        
        # Update MVR-People
        await self.db.update_mvr_people(
            mvr_people_uuid=mvr_people_uuid,
            updates={
                'representative_individual_uuid': best_face['individual_uuid'],
                'representative_face_uuid': best_face['face_uuid'],
                'quality_score': best_face['quality_score'],
                'face_embedding_vector': new_embedding['vector'],
                'estimated_age_min': new_age['min_age'],
                'estimated_age_max': new_age['max_age'],
                'estimated_age_mean': new_age['mean_age'],
                'age_confidence': new_age['confidence'],
                'estimated_gender': new_gender['gender'],
                'gender_confidence': new_gender['confidence'],
                'total_linked_individuals': len(individuals),
                'updated_at': datetime.now()
            }
        )
        
        # Update is_representative flag in mapping table
        await self.db.update_representative_individual(
            mvr_people_uuid=mvr_people_uuid,
            new_representative_uuid=best_face['individual_uuid']
        )
```

---

### Matching Threshold Configuration

**Configuration Table:**

```sql
CREATE TABLE mvr_matching_config (
    config_id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Default configuration
INSERT INTO mvr_matching_config (config_key, config_value, description) VALUES
('default_matching_threshold', '{"threshold": 0.85}'::jsonb, 'Default cosine similarity threshold for matching Individuals'),
('auto_merge_enabled', '{"enabled": true}'::jsonb, 'Enable automatic merging when matches found'),
('min_quality_threshold', '{"threshold": 0.6}'::jsonb, 'Minimum face quality score to use for matching'),
('age_range_tolerance', '{"years": 10}'::jsonb, 'Maximum age difference to consider for matching'),
('gender_match_required', '{"required": false}'::jsonb, 'Require gender match for merging');
```

**API to Update Threshold:**

```python
# Endpoint: PUT /api/v1/mvr-people/config/matching-threshold
async def update_matching_threshold(threshold: float):
    """Update default matching threshold (0.0-1.0)."""
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Threshold must be between 0.0 and 1.0")
    
    await self.db.update_config('default_matching_threshold', {'threshold': threshold})
    
    return {
        'config_key': 'default_matching_threshold',
        'old_value': old_threshold,
        'new_value': threshold,
        'updated_at': datetime.now()
    }
```

---

### Orphaned MVR-People Management

**Orphaned MVR-People Characteristics:**
- `is_orphaned = TRUE`
- `total_linked_individuals = 0`
- `previous_individual_uuids` contains JSON array of former Individual UUIDs
- `merged_into_mvr_uuid` points to predominant MVR-People
- Excluded from similarity searches
- Retained for audit/historical purposes

**Data Retention:**

```python
# Option 1: Soft delete (recommended)
# Keep orphaned MVR-People indefinitely for audit trail

# Option 2: Archive after time period
async def archive_old_orphaned_mvr(days: int = 90):
    """Archive orphaned MVR-People older than specified days."""
    cutoff_date = datetime.now() - timedelta(days=days)
    
    orphaned_mvr = await self.db.get_orphaned_mvr_before_date(cutoff_date)
    
    for mvr in orphaned_mvr:
        # Move to archive table
        await self.db.move_to_archive('mvr_people_archive', mvr)
        # Delete from main table
        await self.db.delete_mvr_people(mvr['mvr_people_uuid'])
```

**Orphan History Query:**

```python
# Get merge history for an Individual
async def get_merge_history(individual_uuid: UUID) -> List[dict]:
    """Get all MVR-People this Individual was ever linked to."""
    
    # Current MVR-People
    current_mvr = await self.db.get_mvr_for_individual(individual_uuid)
    
    # Find orphaned MVR-People that contain this Individual UUID
    orphaned_mvr = await self.db.query(
        "SELECT * FROM mvr_people WHERE previous_individual_uuids::jsonb ? $1",
        str(individual_uuid)
    )
    
    return {
        'individual_uuid': individual_uuid,
        'current_mvr_people': current_mvr,
        'previous_mvr_people': orphaned_mvr,
        'total_merges': len(orphaned_mvr)
    }
```

---

## Data Model

### Database Schema

#### Table: `mvr_people`

```sql
CREATE TABLE mvr_people (
    -- Primary Key
    mvr_people_uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Source Information
    representative_individual_uuid UUID NOT NULL,  -- Which individual provided the best face
    representative_face_uuid UUID,  -- Specific face used for embeddings
    quality_score FLOAT,  -- Quality score of representative face
    
    -- Face Embeddings (Machine Vision Vector)
    face_embedding_vector FLOAT[],  -- 512-dimensional face embedding
    embedding_model_name VARCHAR(100),  -- e.g., "facenet_512", "arcface_r100"
    embedding_model_version VARCHAR(50),  -- e.g., "1.0.0"
    
    -- Age Estimation
    estimated_age_min INTEGER,  -- Lower bound of age range
    estimated_age_max INTEGER,  -- Upper bound of age range
    estimated_age_mean FLOAT,  -- Mean predicted age
    age_confidence FLOAT,  -- Confidence score (0.0-1.0)
    age_model_name VARCHAR(100),  -- e.g., "age_estimator_v1"
    age_model_version VARCHAR(50),
    
    -- Gender Estimation
    estimated_gender VARCHAR(20),  -- "male", "female", "unknown"
    gender_confidence FLOAT,  -- Confidence score (0.0-1.0)
    gender_model_name VARCHAR(100),  -- e.g., "gender_classifier_v1"
    gender_model_version VARCHAR(50),
    
    -- Metadata
    total_linked_individuals INTEGER DEFAULT 1,  -- How many individuals link to this
    processing_status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    processing_error TEXT,  -- Error message if processing failed
    
    -- Orphaning and Merging Fields (NEW)
    is_orphaned BOOLEAN DEFAULT FALSE,  -- True if this MVR-People has been merged into another
    orphaned_at TIMESTAMP WITH TIME ZONE,  -- When this MVR-People was orphaned
    merged_into_mvr_uuid UUID,  -- UUID of predominant MVR-People this merged into
    previous_individual_uuids JSONB,  -- JSON array of Individual UUIDs that were linked before orphaning
    auto_created BOOLEAN DEFAULT FALSE,  -- True if created automatically with Individual
    
    -- Indexes and Constraints
    CONSTRAINT valid_age_range CHECK (estimated_age_min >= 0 AND estimated_age_max <= 120),
    CONSTRAINT valid_age_order CHECK (estimated_age_min <= estimated_age_max),
    CONSTRAINT valid_confidence CHECK (age_confidence >= 0 AND age_confidence <= 1),
    CONSTRAINT valid_gender_confidence CHECK (gender_confidence >= 0 AND gender_confidence <= 1),
    CONSTRAINT valid_quality CHECK (quality_score >= 0 AND quality_score <= 1),
    FOREIGN KEY (merged_into_mvr_uuid) REFERENCES mvr_people(mvr_people_uuid) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX idx_mvr_people_representative_individual ON mvr_people(representative_individual_uuid);
CREATE INDEX idx_mvr_people_status ON mvr_people(processing_status);
CREATE INDEX idx_mvr_people_created ON mvr_people(created_at);
CREATE INDEX idx_mvr_people_orphaned ON mvr_people(is_orphaned);  -- NEW: Filter orphaned MVR
CREATE INDEX idx_mvr_people_merged_into ON mvr_people(merged_into_mvr_uuid);  -- NEW: Track merge chains
CREATE INDEX idx_mvr_people_active ON mvr_people(is_orphaned, processing_status) WHERE is_orphaned = FALSE;  -- NEW: Active MVR only

-- Vector similarity index (for fast similarity search)
-- Requires pgvector extension: CREATE EXTENSION vector;
-- CREATE INDEX idx_mvr_people_embedding ON mvr_people USING ivfflat (face_embedding_vector vector_cosine_ops) WHERE is_orphaned = FALSE;  -- Only index active MVR
```

#### Table: `individual_mvr_mapping` (Junction Table)

```sql
CREATE TABLE individual_mvr_mapping (
    -- Composite Primary Key
    individual_uuid UUID NOT NULL,
    mvr_people_uuid UUID NOT NULL,
    
    -- Timestamps
    linked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Metadata
    is_representative BOOLEAN DEFAULT FALSE,  -- Is this the individual that provided the face?
    confidence_score FLOAT,  -- Confidence that this individual matches this MVR
    
    -- Constraints
    PRIMARY KEY (individual_uuid, mvr_people_uuid),
    FOREIGN KEY (individual_uuid) REFERENCES cross_video_individuals(individual_uuid) ON DELETE CASCADE,
    FOREIGN KEY (mvr_people_uuid) REFERENCES mvr_people(mvr_people_uuid) ON DELETE CASCADE,
    
    -- Only one representative per MVR-People
    CONSTRAINT unique_representative UNIQUE (mvr_people_uuid, is_representative) WHERE is_representative = TRUE
);

-- Indexes
CREATE INDEX idx_individual_mvr_individual ON individual_mvr_mapping(individual_uuid);
CREATE INDEX idx_individual_mvr_mvr ON individual_mvr_mapping(mvr_people_uuid);
CREATE INDEX idx_individual_mvr_representative ON individual_mvr_mapping(mvr_people_uuid) WHERE is_representative = TRUE;
```

#### Table: `mvr_merge_audit_log` (NEW - Merge History)

```sql
CREATE TABLE mvr_merge_audit_log (
    -- Primary Key
    merge_id SERIAL PRIMARY KEY,
    
    -- Merge Details
    predominant_mvr_uuid UUID NOT NULL,  -- MVR-People that survived the merge
    orphaned_mvr_uuid UUID NOT NULL,  -- MVR-People that was orphaned
    reassigned_individual_uuid UUID NOT NULL,  -- Individual that was reassigned
    
    -- Merge Metadata
    similarity_score FLOAT NOT NULL,  -- Similarity score that triggered merge
    merge_triggered_by VARCHAR(50) DEFAULT 'auto',  -- 'auto', 'manual', 'batch'
    merge_threshold FLOAT NOT NULL,  -- Threshold used for matching
    
    -- Quality Comparison
    predominant_quality_score FLOAT,  -- Quality of predominant MVR face
    orphaned_quality_score FLOAT,  -- Quality of orphaned MVR face
    
    -- Timestamps
    merged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Optional: User who triggered manual merge
    triggered_by_user_uuid UUID,
    
    -- Constraints
    FOREIGN KEY (predominant_mvr_uuid) REFERENCES mvr_people(mvr_people_uuid) ON DELETE CASCADE,
    FOREIGN KEY (orphaned_mvr_uuid) REFERENCES mvr_people(mvr_people_uuid) ON DELETE CASCADE,
    FOREIGN KEY (reassigned_individual_uuid) REFERENCES cross_video_individuals(individual_uuid) ON DELETE CASCADE,
    CONSTRAINT valid_similarity CHECK (similarity_score >= 0 AND similarity_score <= 1),
    CONSTRAINT valid_threshold CHECK (merge_threshold >= 0 AND merge_threshold <= 1)
);

-- Indexes
CREATE INDEX idx_merge_audit_predominant ON mvr_merge_audit_log(predominant_mvr_uuid);
CREATE INDEX idx_merge_audit_orphaned ON mvr_merge_audit_log(orphaned_mvr_uuid);
CREATE INDEX idx_merge_audit_individual ON mvr_merge_audit_log(reassigned_individual_uuid);
CREATE INDEX idx_merge_audit_timestamp ON mvr_merge_audit_log(merged_at);
```

#### Table: `mvr_matching_config` (NEW - Configuration)

```sql
CREATE TABLE mvr_matching_config (
    config_id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Default configuration values
INSERT INTO mvr_matching_config (config_key, config_value, description) VALUES
('default_matching_threshold', '{"threshold": 0.85}'::jsonb, 'Default cosine similarity threshold for matching Individuals'),
('auto_merge_enabled', '{"enabled": true}'::jsonb, 'Enable automatic merging when matches found above threshold'),
('min_quality_threshold', '{"threshold": 0.6}'::jsonb, 'Minimum face quality score to use for matching'),
('age_range_tolerance', '{"years": 10}'::jsonb, 'Maximum age difference to consider for secondary matching'),
('gender_match_required', '{"required": false}'::jsonb, 'Require gender match for merging (secondary filter)'),
('orphan_retention_days', '{"days": 365}'::jsonb, 'Days to retain orphaned MVR-People before archiving');

-- Index
CREATE INDEX idx_mvr_config_key ON mvr_matching_config(config_key);
```

### Data Model Classes

#### Python Models (Pydantic)

```python
# File: ppl-meta-vmeta/src/models/mvr_people.py

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from datetime import datetime
from uuid import UUID

class FaceEmbedding(BaseModel):
    """Face embedding vector with metadata."""
    vector: List[float] = Field(..., min_items=512, max_items=512)
    model_name: str = Field(..., example="facenet_512")
    model_version: str = Field(..., example="1.0.0")
    
    @validator('vector')
    def validate_vector_length(cls, v):
        if len(v) != 512:
            raise ValueError('Face embedding must be 512-dimensional')
        return v

class AgeEstimate(BaseModel):
    """Age estimation with range and confidence."""
    min_age: int = Field(..., ge=0, le=120)
    max_age: int = Field(..., ge=0, le=120)
    mean_age: float = Field(..., ge=0, le=120)
    confidence: float = Field(..., ge=0.0, le=1.0)
    model_name: str = Field(..., example="age_estimator_v1")
    model_version: str = Field(..., example="1.0.0")
    
    @validator('max_age')
    def validate_age_range(cls, v, values):
        if 'min_age' in values and v < values['min_age']:
            raise ValueError('max_age must be >= min_age')
        return v

class GenderEstimate(BaseModel):
    """Gender estimation with confidence."""
    gender: Literal["male", "female", "unknown"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    model_name: str = Field(..., example="gender_classifier_v1")
    model_version: str = Field(..., example="1.0.0")

class MVRPeopleCreate(BaseModel):
    """Request model for creating MVR-People."""
    representative_individual_uuid: UUID
    representative_face_uuid: Optional[UUID] = None
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    auto_created: bool = False  # NEW: Track if auto-created with Individual

class MVRPeopleResponse(BaseModel):
    """Response model for MVR-People."""
    mvr_people_uuid: UUID
    created_at: datetime
    updated_at: datetime
    
    # Source
    representative_individual_uuid: UUID
    representative_face_uuid: Optional[UUID]
    quality_score: Optional[float]
    
    # Embeddings
    face_embedding: Optional[FaceEmbedding]
    
    # Estimates
    age_estimate: Optional[AgeEstimate]
    gender_estimate: Optional[GenderEstimate]
    
    # Metadata
    total_linked_individuals: int
    processing_status: Literal["pending", "processing", "completed", "failed"]
    processing_error: Optional[str]
    
    # NEW: Orphaning and Merging Fields
    is_orphaned: bool = False
    orphaned_at: Optional[datetime] = None
    merged_into_mvr_uuid: Optional[UUID] = None
    previous_individual_uuids: Optional[List[UUID]] = None  # Parsed from JSONB
    auto_created: bool = False
    
    class Config:
        orm_mode = True

class IndividualMVRMapping(BaseModel):
    """Mapping between Individual and MVR-People."""
    individual_uuid: UUID
    mvr_people_uuid: UUID
    linked_at: datetime
    is_representative: bool
    confidence_score: Optional[float]
    
    class Config:
        orm_mode = True

class MVRMergeRequest(BaseModel):
    """Request to merge two Individuals to single MVR-People."""
    individual_a_uuid: UUID
    individual_b_uuid: UUID
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    triggered_by: Literal["auto", "manual", "batch"] = "manual"

class MVRMergeResponse(BaseModel):
    """Response from merge operation."""
    success: bool
    predominant_mvr_uuid: UUID
    orphaned_mvr_uuid: UUID
    reassigned_individual_uuid: UUID
    similarity_score: float
    predominant_quality_score: float
    orphaned_quality_score: float
    merged_at: datetime
    
class MVRMergeAuditLog(BaseModel):
    """Audit log entry for merge operation."""
    merge_id: int
    predominant_mvr_uuid: UUID
    orphaned_mvr_uuid: UUID
    reassigned_individual_uuid: UUID
    similarity_score: float
    merge_triggered_by: str
    merge_threshold: float
    predominant_quality_score: Optional[float]
    orphaned_quality_score: Optional[float]
    merged_at: datetime
    triggered_by_user_uuid: Optional[UUID]
    
    class Config:
        orm_mode = True

class MVRMatchingConfig(BaseModel):
    """Configuration for MVR-People matching."""
    default_matching_threshold: float = Field(0.85, ge=0.0, le=1.0)
    auto_merge_enabled: bool = True
    min_quality_threshold: float = Field(0.6, ge=0.0, le=1.0)
    age_range_tolerance: int = Field(10, ge=0)
    gender_match_required: bool = False
    orphan_retention_days: int = Field(365, ge=1)


class MVRPeopleResponse(BaseModel):
    """Response model for MVR-People."""
    mvr_people_uuid: UUID
    created_at: datetime
    updated_at: datetime
    
    # Source
    representative_individual_uuid: UUID
    representative_face_uuid: Optional[UUID]
    quality_score: Optional[float]
    
    # Embeddings
    face_embedding: Optional[FaceEmbedding]
    
    # Estimates
    age_estimate: Optional[AgeEstimate]
    gender_estimate: Optional[GenderEstimate]
    
    # Metadata
    total_linked_individuals: int
    processing_status: Literal["pending", "processing", "completed", "failed"]
    processing_error: Optional[str]
    
    # NEW: Remove duplicate - already defined above with orphaning fields
    
    class Config:
        orm_mode = True

class IndividualMVRMapping(BaseModel):
    """Mapping between Individual and MVR-People."""
    individual_uuid: UUID
    mvr_people_uuid: UUID
    linked_at: datetime
    is_representative: bool
    confidence_score: Optional[float]
    
    class Config:
        orm_mode = True
```

---

## Machine Learning Models

### Model Specifications

MVR-People uses the **same models** as ppl-meta-mini but **implemented independently** (not imported from ppl-meta-mini).

#### 1. Face Embedding Model

**Purpose:** Generate 512-dimensional face representation for similarity search

**Options:**
- **FaceNet** (Inception ResNet V1)
  - Input: 160×160 RGB face image
  - Output: 512-dimensional embedding vector
  - Pre-trained on VGGFace2 or MS-Celeb-1M
  
- **ArcFace** (ResNet-100)
  - Input: 112×112 RGB face image
  - Output: 512-dimensional embedding vector
  - Higher accuracy, slightly slower

**Recommended:** FaceNet for balance of speed and accuracy

**Implementation:**
```python
# File: ppl-meta-vmeta/src/ml/face_embedding.py

from facenet_pytorch import InceptionResnetV1
import torch
import numpy as np
from PIL import Image

class FaceEmbeddingExtractor:
    """Extract face embeddings using FaceNet."""
    
    MODEL_NAME = "facenet_512"
    MODEL_VERSION = "1.0.0"
    EMBEDDING_SIZE = 512
    
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
    
    def extract_embedding(self, face_image: np.ndarray) -> np.ndarray:
        """
        Extract 512D face embedding from face image.
        
        Args:
            face_image: RGB face image (H, W, 3)
            
        Returns:
            512-dimensional embedding vector
        """
        # Preprocess (resize to 160x160, normalize)
        face_tensor = self._preprocess(face_image)
        
        # Extract embedding
        with torch.no_grad():
            embedding = self.model(face_tensor)
        
        return embedding.cpu().numpy().flatten()
    
    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        """Preprocess face image for FaceNet."""
        # Resize to 160x160
        pil_image = Image.fromarray(image)
        pil_image = pil_image.resize((160, 160))
        
        # Convert to tensor and normalize
        img_tensor = torch.from_numpy(np.array(pil_image)).float()
        img_tensor = img_tensor.permute(2, 0, 1).unsqueeze(0)
        img_tensor = (img_tensor - 127.5) / 128.0
        
        return img_tensor.to(self.device)
```

#### 2. Age Estimation Model

**Purpose:** Estimate age range of person

**Options:**
- **UTKFace Age Model** (CNN)
  - Input: 64×64 RGB face image
  - Output: Age regression (0-120 years)
  - Trained on UTKFace dataset (20k+ images)

- **DEX Age Model** (VGG-16 based)
  - Input: 224×224 RGB face image
  - Output: Age distribution (0-100 years)
  - Higher accuracy, slower

**Recommended:** UTKFace model for speed

**Implementation:**
```python
# File: ppl-meta-vmeta/src/ml/age_estimator.py

import torch
import torch.nn as nn
import numpy as np

class AgeEstimator:
    """Estimate age from face image."""
    
    MODEL_NAME = "age_estimator_v1"
    MODEL_VERSION = "1.0.0"
    
    def __init__(self, model_path: str):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self._load_model(model_path).to(self.device)
    
    def estimate_age(self, face_image: np.ndarray) -> dict:
        """
        Estimate age from face image.
        
        Args:
            face_image: RGB face image (H, W, 3)
            
        Returns:
            {
                'min_age': int,
                'max_age': int,
                'mean_age': float,
                'confidence': float
            }
        """
        # Preprocess
        face_tensor = self._preprocess(face_image)
        
        # Predict
        with torch.no_grad():
            age_output = self.model(face_tensor)
            mean_age = age_output.item()
        
        # Calculate range (±5 years)
        min_age = max(0, int(mean_age - 5))
        max_age = min(120, int(mean_age + 5))
        
        # Confidence based on model certainty
        confidence = 0.8  # Placeholder - calculate from model output variance
        
        return {
            'min_age': min_age,
            'max_age': max_age,
            'mean_age': mean_age,
            'confidence': confidence
        }
    
    def _load_model(self, model_path: str) -> nn.Module:
        """Load pre-trained age estimation model."""
        # Load model architecture and weights
        model = torch.load(model_path)
        model.eval()
        return model
    
    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        """Preprocess face image for age model."""
        # Resize to 64x64
        from PIL import Image
        pil_image = Image.fromarray(image)
        pil_image = pil_image.resize((64, 64))
        
        # Convert to tensor and normalize
        img_tensor = torch.from_numpy(np.array(pil_image)).float()
        img_tensor = img_tensor.permute(2, 0, 1).unsqueeze(0)
        img_tensor = img_tensor / 255.0
        
        return img_tensor.to(self.device)
```

#### 3. Gender Estimation Model

**Purpose:** Classify gender of person

**Options:**
- **Simple CNN Classifier**
  - Input: 64×64 RGB face image
  - Output: Binary classification (male/female)
  - Fast and accurate for frontal faces

**Implementation:**
```python
# File: ppl-meta-vmeta/src/ml/gender_estimator.py

import torch
import torch.nn as nn
import numpy as np

class GenderEstimator:
    """Estimate gender from face image."""
    
    MODEL_NAME = "gender_classifier_v1"
    MODEL_VERSION = "1.0.0"
    
    def __init__(self, model_path: str):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self._load_model(model_path).to(self.device)
    
    def estimate_gender(self, face_image: np.ndarray) -> dict:
        """
        Estimate gender from face image.
        
        Args:
            face_image: RGB face image (H, W, 3)
            
        Returns:
            {
                'gender': 'male' | 'female' | 'unknown',
                'confidence': float
            }
        """
        # Preprocess
        face_tensor = self._preprocess(face_image)
        
        # Predict
        with torch.no_grad():
            output = self.model(face_tensor)
            probabilities = torch.softmax(output, dim=1)
            male_prob = probabilities[0][0].item()
            female_prob = probabilities[0][1].item()
        
        # Determine gender
        if male_prob > female_prob:
            gender = "male"
            confidence = male_prob
        else:
            gender = "female"
            confidence = female_prob
        
        # If confidence is low, mark as unknown
        if confidence < 0.6:
            gender = "unknown"
        
        return {
            'gender': gender,
            'confidence': confidence
        }
    
    def _load_model(self, model_path: str) -> nn.Module:
        """Load pre-trained gender classification model."""
        model = torch.load(model_path)
        model.eval()
        return model
    
    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        """Preprocess face image for gender model."""
        from PIL import Image
        pil_image = Image.fromarray(image)
        pil_image = pil_image.resize((64, 64))
        
        img_tensor = torch.from_numpy(np.array(pil_image)).float()
        img_tensor = img_tensor.permute(2, 0, 1).unsqueeze(0)
        img_tensor = img_tensor / 255.0
        
        return img_tensor.to(self.device)
```

### Model Files Location

```
ppl-meta-vmeta/
├── models/                        # NEW: ML model weights directory
│   ├── facenet_vggface2.pt       # FaceNet pre-trained weights
│   ├── age_estimator_utkface.pt  # Age estimation model
│   ├── gender_classifier.pt      # Gender classification model
│   └── README.md                 # Model documentation
├── src/
│   ├── ml/                       # NEW: ML processing modules
│   │   ├── __init__.py
│   │   ├── face_embedding.py     # FaceEmbedding extractor
│   │   ├── age_estimator.py      # Age estimation
│   │   ├── gender_estimator.py   # Gender estimation
│   │   └── mvr_processor.py      # Orchestrates all ML processing
│   ├── models/
│   │   ├── mvr_people.py         # NEW: MVR-People Pydantic models
│   ├── database/
│   │   ├── repository.py         # Add MVR-People repository methods
│   ├── services/
│   │   ├── mvr_service.py        # NEW: MVR-People business logic
│   ├── api/
│   │   └── v1/
│   │       ├── mvr_people.py     # NEW: MVR-People API endpoints
```

---

## Processing Pipeline

### Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: Individual Creation                                    │
│ - Cross-video tracking creates Individual                      │
│ - Individual has multiple appearances                          │
│ - Each appearance has faces with quality scores                │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: Trigger MVR-People Creation                            │
│ - Automatically after individual creation (background task)    │
│ - OR manually via API endpoint                                 │
│ - OR batch processing for existing individuals                 │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Select Best Quality Face                               │
│ - Query all appearances for individual                         │
│ - For each appearance, get person objects from Orchestrator    │
│ - Calculate quality score for each face:                       │
│   - Sharpness (40%)                                            │
│   - Brightness (30%)                                           │
│   - Face size (20%)                                            │
│   - Confidence (10%)                                           │
│ - Select face with highest quality score                       │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: Extract Face Embedding                                 │
│ - Load best quality face image                                 │
│ - Preprocess for FaceNet (resize to 160×160, normalize)        │
│ - Run through FaceNet model                                    │
│ - Extract 512-dimensional embedding vector                     │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: Estimate Age                                           │
│ - Load best quality face image                                 │
│ - Preprocess for Age model (resize to 64×64)                   │
│ - Run through Age estimation model                             │
│ - Output: mean age, min age, max age, confidence               │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 6: Estimate Gender                                        │
│ - Load best quality face image                                 │
│ - Preprocess for Gender model (resize to 64×64)                │
│ - Run through Gender classification model                      │
│ - Output: gender (male/female/unknown), confidence             │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 7: Create MVR-People Record                               │
│ - Insert into mvr_people table:                                │
│   - face_embedding_vector (512D float array)                   │
│   - estimated_age_min, max, mean                               │
│   - estimated_gender                                           │
│   - model names and versions                                   │
│   - quality_score, representative_individual_uuid              │
│ - Insert into individual_mvr_mapping table:                    │
│   - Link individual to MVR-People                              │
│   - Mark as representative                                     │
└────────────────────────┬────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 8: MVR-People Ready                                       │
│ - Status: 'completed'                                          │
│ - Available for:                                               │
│   - Similarity search                                          │
│   - Demographic filtering                                      │
│   - Person re-identification                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Background Processing

**Asynchronous Task Queue:**
```python
# File: ppl-meta-vmeta/src/services/mvr_service.py

import asyncio
from typing import Optional
from uuid import UUID

class MVRService:
    """Service for creating and managing MVR-People."""
    
    def __init__(self, db, ml_processor):
        self.db = db
        self.ml_processor = ml_processor
        self.processing_queue = asyncio.Queue()
        self.active_tasks = {}
    
    async def create_mvr_people_async(self, individual_uuid: UUID) -> UUID:
        """
        Create MVR-People for individual (async background task).
        
        Args:
            individual_uuid: UUID of individual
            
        Returns:
            mvr_people_uuid: UUID of created MVR-People record
        """
        # Create pending record
        mvr_people_uuid = await self.db.create_mvr_people_record(
            individual_uuid=individual_uuid,
            status='pending'
        )
        
        # Queue for background processing
        await self.processing_queue.put({
            'mvr_people_uuid': mvr_people_uuid,
            'individual_uuid': individual_uuid
        })
        
        # Start background task if not running
        if mvr_people_uuid not in self.active_tasks:
            task = asyncio.create_task(
                self._process_mvr_people(mvr_people_uuid, individual_uuid)
            )
            self.active_tasks[mvr_people_uuid] = task
        
        return mvr_people_uuid
    
    async def _process_mvr_people(self, mvr_people_uuid: UUID, individual_uuid: UUID):
        """Background task to process MVR-People creation."""
        try:
            # Update status
            await self.db.update_mvr_people_status(mvr_people_uuid, 'processing')
            
            # Step 1: Get best quality face
            best_face = await self._get_best_quality_face(individual_uuid)
            
            # Step 2: Extract face embedding
            embedding = await self.ml_processor.extract_face_embedding(best_face['image'])
            
            # Step 3: Estimate age
            age_estimate = await self.ml_processor.estimate_age(best_face['image'])
            
            # Step 4: Estimate gender
            gender_estimate = await self.ml_processor.estimate_gender(best_face['image'])
            
            # Step 5: Update MVR-People record
            await self.db.update_mvr_people(
                mvr_people_uuid=mvr_people_uuid,
                face_embedding=embedding,
                age_estimate=age_estimate,
                gender_estimate=gender_estimate,
                representative_face_uuid=best_face['face_uuid'],
                quality_score=best_face['quality_score'],
                status='completed'
            )
            
        except Exception as e:
            # Update status to failed
            await self.db.update_mvr_people_status(
                mvr_people_uuid,
                'failed',
                error=str(e)
            )
            raise
        finally:
            # Remove from active tasks
            if mvr_people_uuid in self.active_tasks:
                del self.active_tasks[mvr_people_uuid]
```

---

## API Endpoints

### Authentication and Authorization

**⚠️ IMPORTANT: All API endpoints require authentication.**

All MVR-People endpoints follow the same authentication architecture as existing vmeta service endpoints:

1. **JWT Token Required:** All requests must include valid JWT token in Authorization header
2. **User Authentication:** Users must authenticate via Node service login endpoint
3. **Token Format:** `Authorization: Bearer {jwt_token}`

**Test User Credentials:**

For all testing and development, use the following test user:

```bash
# Login to get JWT token
curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!'

# Response includes access_token
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "email": "fresh.user@example.com",
    "user_uuid": "..."
  }
}

# Use token in subsequent requests
curl -X GET 'http://localhost:8008/api/v1/mvr-people/{uuid}' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
```

**Test User Details:**
- **Email:** `fresh.user@example.com`
- **Password:** `NewPassword234!`
- **Login Endpoint:** `POST http://localhost:8001/api/v1/users/login`
- **Content-Type:** `application/x-www-form-urlencoded`

---

### Service Architecture

**⚠️ IMPORTANT: MVR-People endpoints follow vmeta service architectural patterns.**

All MVR-People endpoints operate using the same service architecture as existing vmeta endpoints:

**Service Layer Integration:**
1. **Database Access:** Direct PostgreSQL access via vmeta database connection
2. **Orchestrator Integration:** Call Orchestrator service for person objects and appearance data
3. **Vision Service:** ML processing happens within vmeta service (not external calls)
4. **Node Service:** Authentication and user management only
5. **No Gateway Routing:** Direct service-to-service communication (Orchestrator ↔ vmeta)

**Architectural Consistency:**
- Same database repository patterns as vmeta Individual endpoints
- Same error handling and response formats
- Same logging and monitoring approach
- Same async/await patterns for ML processing
- Same background task processing (Celery/asyncio)

**Example Service Flow:**
```
Client Request with JWT
    ↓
vmeta Service (MVR-People Endpoint)
    ↓
Authentication Check (verify JWT with Node service)
    ↓
Database Query (vmeta PostgreSQL)
    ↓ (if needed)
Orchestrator API Call (get person objects)
    ↓
ML Processing (FaceNet, Age/Gender models - internal)
    ↓
Database Write (vmeta PostgreSQL)
    ↓
Response to Client
```

---

### REST API Specification

#### 1. Create MVR-People for Individual

**Endpoint:** `POST /api/v1/mvr-people/individuals/{individual_uuid}/create`

**Description:** Create MVR-People representation for an individual

**Request:**
```http
POST /api/v1/mvr-people/individuals/5c73fd34-737a-48c7-a69a-f17b40adbead/create
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "background_processing": true,  // Optional, default: true
  "force_recreate": false  // Optional, recreate if already exists
}
```

**Response (202 Accepted - Background Processing):**
```json
{
  "mvr_people_uuid": "abc123-def456-...",
  "individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
  "status": "pending",
  "message": "MVR-People creation queued for background processing",
  "estimated_completion_seconds": 10
}
```

**Response (200 OK - Synchronous Processing):**
```json
{
  "mvr_people_uuid": "abc123-def456-...",
  "individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
  "status": "completed",
  "face_embedding": {
    "vector": [0.123, -0.456, ...],  // 512 values
    "model_name": "facenet_512",
    "model_version": "1.0.0"
  },
  "age_estimate": {
    "min_age": 25,
    "max_age": 35,
    "mean_age": 30.5,
    "confidence": 0.85,
    "model_name": "age_estimator_v1",
    "model_version": "1.0.0"
  },
  "gender_estimate": {
    "gender": "male",
    "confidence": 0.92,
    "model_name": "gender_classifier_v1",
    "model_version": "1.0.0"
  },
  "representative_individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
  "quality_score": 0.91,
  "created_at": "2025-10-30T12:00:00Z",
  "updated_at": "2025-10-30T12:00:10Z"
}
```

---

#### 2. Get MVR-People by UUID

**Endpoint:** `GET /api/v1/mvr-people/{mvr_people_uuid}`

**Description:** Retrieve MVR-People record by UUID

**Request:**
```http
GET /api/v1/mvr-people/abc123-def456-...
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "mvr_people_uuid": "abc123-def456-...",
  "status": "completed",
  "face_embedding": { ... },
  "age_estimate": { ... },
  "gender_estimate": { ... },
  "representative_individual_uuid": "5c73fd34-...",
  "representative_face_uuid": "face-uuid-...",
  "quality_score": 0.91,
  "total_linked_individuals": 3,
  "linked_individuals": [
    {
      "individual_uuid": "5c73fd34-...",
      "is_representative": true,
      "linked_at": "2025-10-30T12:00:00Z"
    },
    {
      "individual_uuid": "other-uuid-...",
      "is_representative": false,
      "linked_at": "2025-10-30T13:00:00Z"
    }
  ],
  "created_at": "2025-10-30T12:00:00Z",
  "updated_at": "2025-10-30T12:00:10Z"
}
```

---

#### 3. Get MVR-People for Individual

**Endpoint:** `GET /api/v1/mvr-people/individuals/{individual_uuid}`

**Description:** Get MVR-People linked to an individual

**Request:**
```http
GET /api/v1/mvr-people/individuals/5c73fd34-737a-48c7-a69a-f17b40adbead
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
  "mvr_people": {
    "mvr_people_uuid": "abc123-def456-...",
    "status": "completed",
    "face_embedding": { ... },
    "age_estimate": { ... },
    "gender_estimate": { ... },
    "is_representative": true
  }
}
```

**Response (404 Not Found - No MVR-People):**
```json
{
  "detail": "No MVR-People found for individual",
  "individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
  "suggestion": "Create MVR-People using POST /api/v1/mvr-people/individuals/{uuid}/create"
}
```

---

#### 4. Search Similar MVR-People (Similarity Search)

**Endpoint:** `POST /api/v1/mvr-people/search/similar`

**Description:** Find similar people using face embedding similarity

**Request:**
```http
POST /api/v1/mvr-people/search/similar
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "mvr_people_uuid": "abc123-def456-...",  // OR
  "face_embedding": [0.123, -0.456, ...],  // 512D vector
  "similarity_threshold": 0.7,  // Cosine similarity threshold (0-1)
  "max_results": 10,
  "include_demographics": true  // Include age/gender filters
}
```

**Response (200 OK):**
```json
{
  "query_mvr_people_uuid": "abc123-def456-...",
  "total_results": 5,
  "results": [
    {
      "mvr_people_uuid": "similar-1-...",
      "similarity_score": 0.95,
      "age_estimate": { ... },
      "gender_estimate": { ... },
      "total_linked_individuals": 2
    },
    {
      "mvr_people_uuid": "similar-2-...",
      "similarity_score": 0.87,
      "age_estimate": { ... },
      "gender_estimate": { ... },
      "total_linked_individuals": 1
    }
  ]
}
```

---

#### 5. Search MVR-People by Demographics

**Endpoint:** `POST /api/v1/mvr-people/search/demographics`

**Description:** Search MVR-People by age/gender filters

**Request:**
```http
POST /api/v1/mvr-people/search/demographics
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "age_min": 25,
  "age_max": 40,
  "gender": "male",  // Optional: "male", "female", "unknown"
  "min_confidence": 0.7,  // Minimum confidence for age/gender
  "page": 1,
  "page_size": 20
}
```

**Response (200 OK):**
```json
{
  "total_results": 145,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "mvr_people_uuid": "result-1-...",
      "age_estimate": {
        "min_age": 28,
        "max_age": 38,
        "mean_age": 33.2,
        "confidence": 0.82
      },
      "gender_estimate": {
        "gender": "male",
        "confidence": 0.89
      },
      "total_linked_individuals": 2,
      "created_at": "2025-10-30T12:00:00Z"
    }
  ]
}
```

---

#### 6. Link Individual to Existing MVR-People

**Endpoint:** `POST /api/v1/mvr-people/{mvr_people_uuid}/link-individual`

**Description:** Link an individual to existing MVR-People (for person re-identification)

**Request:**
```http
POST /api/v1/mvr-people/abc123-def456-.../link-individual
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "individual_uuid": "new-individual-uuid-...",
  "confidence_score": 0.85  // Similarity confidence
}
```

**Response (200 OK):**
```json
{
  "mvr_people_uuid": "abc123-def456-...",
  "individual_uuid": "new-individual-uuid-...",
  "linked_at": "2025-10-30T14:00:00Z",
  "confidence_score": 0.85,
  "total_linked_individuals": 4
}
```

---

#### 7. Batch Create MVR-People

**Endpoint:** `POST /api/v1/mvr-people/batch/create`

**Description:** Create MVR-People for multiple individuals (batch processing)

**Request:**
```http
POST /api/v1/mvr-people/batch/create
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "individual_uuids": [
    "uuid-1",
    "uuid-2",
    "uuid-3"
  ],
  "background_processing": true
}
```

**Response (202 Accepted):**
```json
{
  "total_queued": 3,
  "batch_id": "batch-uuid-...",
  "status": "processing",
  "individual_uuids": ["uuid-1", "uuid-2", "uuid-3"],
  "estimated_completion_seconds": 30
}
```

---

#### 8. Get MVR-People Processing Status

**Endpoint:** `GET /api/v1/mvr-people/{mvr_people_uuid}/status`

**Description:** Check processing status of MVR-People creation

**Request:**
```http
GET /api/v1/mvr-people/abc123-def456-.../status
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "mvr_people_uuid": "abc123-def456-...",
  "status": "processing",  // pending, processing, completed, failed
  "created_at": "2025-10-30T12:00:00Z",
  "started_at": "2025-10-30T12:00:01Z",
  "completed_at": null,
  "processing_error": null,
  "progress_percentage": 60,
  "current_step": "Extracting face embedding"
}
```

---

#### 9. Match Individuals (Find Similar)

**Endpoint:** `POST /api/v1/mvr-people/individuals/{individual_uuid}/match`

**Description:** Find other Individuals that match the given Individual based on face similarity

**Request:**
```http
POST /api/v1/mvr-people/individuals/5c73fd34-737a-48c7-a69a-f17b40adbead/match
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "threshold": 0.85,  // Optional, override default
  "auto_merge": false,  // If true, automatically merge matches above threshold
  "max_results": 10
}
```

**Response (200 OK):**
```json
{
  "individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
  "matches": [
    {
      "individual_uuid": "match-uuid-1",
      "mvr_people_uuid": "mvr-uuid-1",
      "similarity_score": 0.92,
      "quality_score": 0.88,
      "age_estimate": {"min_age": 25, "max_age": 35, "mean_age": 30.5},
      "gender_estimate": {"gender": "male", "confidence": 0.91},
      "above_threshold": true
    },
    {
      "individual_uuid": "match-uuid-2",
      "mvr_people_uuid": "mvr-uuid-2",
      "similarity_score": 0.78,
      "quality_score": 0.75,
      "above_threshold": false
    }
  ],
  "total_matches": 2,
  "matches_above_threshold": 1,
  "threshold_used": 0.85
}
```

---

#### 10. Merge Individuals to Single MVR-People

**Endpoint:** `POST /api/v1/mvr-people/merge`

**Description:** Manually merge two Individuals to single MVR-People (predominant based on quality)

**Request:**
```http
POST /api/v1/mvr-people/merge
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "individual_a_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
  "individual_b_uuid": "match-uuid-1",
  "similarity_score": 0.92,  // Required for audit
  "triggered_by": "manual"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "predominant_mvr_uuid": "mvr-uuid-1",
  "orphaned_mvr_uuid": "mvr-uuid-2",
  "reassigned_individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
  "similarity_score": 0.92,
  "predominant_quality_score": 0.88,
  "orphaned_quality_score": 0.75,
  "merged_at": "2025-10-30T14:30:00Z",
  "message": "Individual 5c73fd34... reassigned to MVR-People mvr-uuid-1 (better quality). MVR-People mvr-uuid-2 orphaned."
}
```

---

#### 11. Get Merge History for Individual

**Endpoint:** `GET /api/v1/mvr-people/individuals/{individual_uuid}/merge-history`

**Description:** Get all merge operations involving this Individual

**Request:**
```http
GET /api/v1/mvr-people/individuals/5c73fd34-737a-48c7-a69a-f17b40adbead/merge-history
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "individual_uuid": "5c73fd34-737a-48c7-a69a-f17b40adbead",
  "current_mvr_people": {
    "mvr_people_uuid": "mvr-uuid-1",
    "is_orphaned": false,
    "total_linked_individuals": 3
  },
  "previous_mvr_people": [
    {
      "mvr_people_uuid": "mvr-uuid-2",
      "is_orphaned": true,
      "orphaned_at": "2025-10-30T14:30:00Z",
      "merged_into_mvr_uuid": "mvr-uuid-1"
    }
  ],
  "merge_events": [
    {
      "merge_id": 42,
      "predominant_mvr_uuid": "mvr-uuid-1",
      "orphaned_mvr_uuid": "mvr-uuid-2",
      "similarity_score": 0.92,
      "merged_at": "2025-10-30T14:30:00Z",
      "triggered_by": "manual"
    }
  ],
  "total_merges": 1
}
```

---

#### 12. Get Orphaned MVR-People

**Endpoint:** `GET /api/v1/mvr-people/orphaned`

**Description:** List all orphaned MVR-People (for audit/cleanup)

**Request:**
```http
GET /api/v1/mvr-people/orphaned?page=1&page_size=20&orphaned_after=2025-10-01
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "total_orphaned": 156,
  "page": 1,
  "page_size": 20,
  "results": [
    {
      "mvr_people_uuid": "orphan-uuid-1",
      "is_orphaned": true,
      "orphaned_at": "2025-10-30T14:30:00Z",
      "merged_into_mvr_uuid": "predominant-uuid",
      "previous_individual_uuids": ["ind-uuid-1", "ind-uuid-2"],
      "quality_score": 0.75,
      "created_at": "2025-10-15T10:00:00Z"
    }
  ]
}
```

---

#### 13. Update Matching Configuration

**Endpoint:** `PUT /api/v1/mvr-people/config/matching`

**Description:** Update matching threshold and other configuration

**Request:**
```http
PUT /api/v1/mvr-people/config/matching
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "default_matching_threshold": 0.90,
  "auto_merge_enabled": true,
  "min_quality_threshold": 0.65
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "updated_config": {
    "default_matching_threshold": 0.90,
    "auto_merge_enabled": true,
    "min_quality_threshold": 0.65,
    "age_range_tolerance": 10,
    "gender_match_required": false,
    "orphan_retention_days": 365
  },
  "updated_at": "2025-10-30T15:00:00Z"
}
```

---

#### 14. Get Matching Configuration

**Endpoint:** `GET /api/v1/mvr-people/config/matching`

**Description:** Get current matching configuration

**Request:**
```http
GET /api/v1/mvr-people/config/matching
Authorization: Bearer {jwt_token}
```

**Response (200 OK):**
```json
{
  "default_matching_threshold": 0.85,
  "auto_merge_enabled": true,
  "min_quality_threshold": 0.6,
  "age_range_tolerance": 10,
  "gender_match_required": false,
  "orphan_retention_days": 365,
  "last_updated": "2025-10-30T12:00:00Z"
}
```

---

## Use Cases

### 1. Person Re-Identification Across Sessions

**Scenario:** User creates a new tracking session. System automatically checks if tracked individuals match existing MVR-People.

**Flow:**
1. User creates new cross-video tracking session
2. Session finds individual "ind_new_001"
3. System extracts face from best appearance
4. System generates face embedding for "ind_new_001"
5. System searches MVR-People database for similar embeddings
6. If similarity > 0.85, link "ind_new_001" to existing MVR-People
7. User sees: "This person was previously seen on Oct 15, 2025"

**API Calls:**
```bash
# Step 1: Create MVR-People for new individual
POST /api/v1/mvr-people/individuals/ind_new_001/create

# Step 2: Search for similar MVR-People
POST /api/v1/mvr-people/search/similar
{
  "mvr_people_uuid": "mvr_new_001",
  "similarity_threshold": 0.85,
  "max_results": 5
}

# Step 3: Link to existing MVR-People if match found
POST /api/v1/mvr-people/mvr_existing_001/link-individual
{
  "individual_uuid": "ind_new_001",
  "confidence_score": 0.91
}
```

---

### 2. Demographic Search and Filtering

**Scenario:** Security team wants to find all male individuals aged 25-40 seen in the last week.

**Flow:**
1. User opens demographics search interface
2. User selects: Gender=Male, Age=25-40, Date Range=Last 7 days
3. System queries MVR-People database
4. Returns matching individuals with appearance history
5. User reviews results and can view detailed tracking

**API Call:**
```bash
POST /api/v1/mvr-people/search/demographics
{
  "age_min": 25,
  "age_max": 40,
  "gender": "male",
  "min_confidence": 0.7,
  "date_range": {
    "start": "2025-10-23T00:00:00Z",
    "end": "2025-10-30T23:59:59Z"
  }
}
```

---

### 3. Similarity Search for Person of Interest

**Scenario:** Security has a photo of a person of interest. Find all similar-looking individuals in the system.

**Flow:**
1. User uploads photo of person of interest
2. System extracts face embedding from uploaded photo
3. System searches MVR-People database for similar embeddings
4. Returns ranked list of similar individuals
5. User reviews matches and their tracking history

**API Call:**
```bash
POST /api/v1/mvr-people/search/similar
{
  "face_embedding": [0.123, -0.456, ...],  // From uploaded photo
  "similarity_threshold": 0.75,
  "max_results": 20,
  "include_demographics": true
}
```

---

### 4. Automatic Matching and Merging

**Scenario:** System automatically creates MVR-People for new Individuals, then checks for matches and merges when similarity is high.

**Flow:**
1. User creates new Individual "ind_new_001" in tracking session
2. System automatically creates MVR-People "mvr_new_001" (1:1)
3. System extracts face embedding from best quality face
4. Background task searches for similar MVR-People (threshold = 0.85)
5. Match found: "mvr_existing_001" with similarity 0.92
6. Compare quality scores: mvr_existing_001 (0.88) vs mvr_new_001 (0.75)
7. Merge to predominant: mvr_existing_001 wins (higher quality)
8. Reassign "ind_new_001" to "mvr_existing_001"
9. Mark "mvr_new_001" as orphaned, store previous Individual UUID
10. Update "mvr_existing_001" to 2 linked Individuals
11. User sees: "This person matches existing record from Oct 15, 2025"

**Implementation:**
```python
# In ppl-meta-vmeta/src/services/individual_service.py

async def create_individual_with_auto_mvr(self, individual_data: dict) -> dict:
    """Create Individual with automatic MVR-People creation and matching."""
    
    # Create Individual
    individual_uuid = await self.db.insert_individual(individual_data)
    
    # Auto-create MVR-People (1:1 initially)
    mvr_uuid = await self.mvr_service.create_mvr_people_async(
        individual_uuid=individual_uuid,
        auto_created=True
    )
    
    # Get matching configuration
    config = await self.db.get_config('default_matching_threshold')
    threshold = config['threshold']
    auto_merge = (await self.db.get_config('auto_merge_enabled'))['enabled']
    
    # Search for matching Individuals
    matches = await self.mvr_service.find_matching_individuals(
        individual_uuid=individual_uuid,
        threshold=threshold
    )
    
    # If auto-merge enabled and match found above threshold
    if auto_merge and matches:
        best_match = matches[0]  # Highest similarity
        
        if best_match['similarity_score'] >= threshold:
            # Execute automatic merge
            merge_result = await self.mvr_service.merge_individuals_to_best_mvr(
                individual_a_uuid=individual_uuid,
                individual_b_uuid=best_match['individual_uuid'],
                similarity_score=best_match['similarity_score']
            )
            
            return {
                'individual_uuid': individual_uuid,
                'mvr_people_uuid': merge_result['predominant_mvr_uuid'],
                'auto_merged': True,
                'merged_with_individual': best_match['individual_uuid'],
                'similarity_score': best_match['similarity_score'],
                'orphaned_mvr_uuid': merge_result['orphaned_mvr_uuid']
            }
    
    # No match or auto-merge disabled
    return {
        'individual_uuid': individual_uuid,
        'mvr_people_uuid': mvr_uuid,
        'auto_merged': False,
        'potential_matches': len(matches)
    }
```

---

### 5. Manual Review and Merge

**Scenario:** Auto-merge is disabled. User manually reviews potential matches and decides to merge.

**Flow:**
1. New Individual created, MVR-People created (no auto-merge)
2. User opens Individual detail page
3. UI shows "Potential Matches: 2 individuals with similarity > 0.80"
4. User clicks "Review Matches"
5. UI displays side-by-side comparison of face images, demographics
6. User clicks "Merge" on best match
7. System merges to predominant MVR-People based on quality
8. UI shows "Merged successfully. This person now linked to 3 appearances."

**API Calls:**
```bash
# Step 1: Find matches
POST /api/v1/mvr-people/individuals/ind_new_001/match
{
  "threshold": 0.80,
  "auto_merge": false,
  "max_results": 5
}

# Step 2: User reviews and decides to merge
POST /api/v1/mvr-people/merge
{
  "individual_a_uuid": "ind_new_001",
  "individual_b_uuid": "ind_existing_005",
  "similarity_score": 0.89,
  "triggered_by": "manual"
}
```

---

### 6. Orphan Cleanup and Audit

**Scenario:** System administrator reviews orphaned MVR-People for cleanup.

**Flow:**
1. Admin opens "MVR-People Management" dashboard
2. Filters for orphaned MVR-People older than 90 days
3. Reviews orphan history (which Individuals, when merged, where)
4. Decides to archive orphans older than 365 days
5. Runs archive job, moves to archive table
6. Audit log preserved for compliance

**API Call:**
```bash
# Get orphaned MVR-People
GET /api/v1/mvr-people/orphaned?orphaned_after=2024-07-01&page_size=100

# Archive old orphans (admin endpoint)
POST /api/v1/mvr-people/admin/archive-orphans
{
  "orphaned_before": "2024-10-30",
  "retention_days": 365,
  "dry_run": false
}
```

---

## Performance Considerations

### Processing Time Estimates

Per individual MVR-People creation:
- **Face selection:** ~500ms (API calls to Orchestrator)
- **Face embedding extraction:** ~100ms (GPU) / ~500ms (CPU)
- **Age estimation:** ~50ms (GPU) / ~200ms (CPU)
- **Gender estimation:** ~50ms (GPU) / ~200ms (CPU)
- **Database write:** ~50ms
- **Similarity search (matching):** ~100ms (with pgvector index)
- **Merge execution (if match found):** ~200ms

**Total: ~1s (GPU) / ~1.8s (CPU) per individual with auto-matching**

### Optimization Strategies

1. **GPU Acceleration**
   - Use CUDA-enabled models for 3-5x speedup
   - Batch processing for multiple faces simultaneously

2. **Caching**
   - Cache Orchestrator responses (person objects)
   - Cache best quality face selections

3. **Parallel Processing**
   - Process multiple individuals concurrently
   - Use asyncio for I/O-bound operations

4. **Lazy Loading**
   - Only create MVR-People when needed (not automatically)
   - Option: Create on-demand when user requests demographics/similarity

5. **Background Tasks**
   - Use Celery or asyncio for background processing
   - Don't block API responses waiting for ML processing

---

## Database Performance

### Vector Similarity Search

**Requirement:** Fast similarity search over 512D embeddings

**Solution:** pgvector extension for PostgreSQL

**Setup:**
```sql
-- Install pgvector extension
CREATE EXTENSION vector;

-- Modify face_embedding_vector column type
ALTER TABLE mvr_people 
  ALTER COLUMN face_embedding_vector TYPE vector(512);

-- Create IVFFlat index for fast cosine similarity
CREATE INDEX idx_mvr_people_embedding_ivfflat 
  ON mvr_people 
  USING ivfflat (face_embedding_vector vector_cosine_ops)
  WITH (lists = 100);

-- Query example (cosine similarity)
SELECT 
  mvr_people_uuid,
  1 - (face_embedding_vector <=> $1::vector) AS similarity
FROM mvr_people
WHERE 1 - (face_embedding_vector <=> $1::vector) > 0.7
ORDER BY face_embedding_vector <=> $1::vector
LIMIT 10;
```

**Performance:**
- Without index: O(n) - ~1s for 100k records
- With IVFFlat index: O(log n) - ~50ms for 100k records

---

## Testing Strategy

### Real-World Testing with USB Camera

**Primary Testing Method:** Real video recordings from USB camera with human subjects

This testing approach validates the complete MVR-People workflow using actual camera footage and real faces, ensuring the system works end-to-end in production scenarios.

---

#### Test Setup Requirements

**Hardware:**
- USB Camera 0 (default system camera)
- Computer with camera access
- Adequate lighting for face detection

**Software:**
- ppl-meta-cameras service running (port 8005)
- ppl-meta-orchestrator service running (port 8002)
- ppl-meta-vmeta service running (port 8008)
- ppl-meta-vision service running (port 8003 - face detection)
- ppl-meta-node service running (port 8001 - authentication)

**Authentication:**
- **Test User:** `fresh.user@example.com`
- **Password:** `NewPassword234!`
- **Login Endpoint:** `POST http://localhost:8001/api/v1/users/login`
- **Required:** JWT token must be obtained before testing
- **Token Usage:** Include in all API requests: `Authorization: Bearer {token}`

**Test Subject:**
- At least one person (tester) available for recording
- Ideally 2-3 different people for comprehensive testing

---

#### Authentication Setup for Testing

**Step 0: Authenticate and Get JWT Token**

```bash
# Login to get JWT token (required for all subsequent requests)
curl -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!'

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "email": "fresh.user@example.com",
    "user_uuid": "abc123-def456-..."
  }
}

# Save the access_token for use in all subsequent API calls
export JWT_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**⚠️ IMPORTANT:** All MVR-People endpoints require authentication. Include the JWT token in the Authorization header for every request.

---

#### Test Procedure: Consecutive Video Recording

**Objective:** Create multiple consecutive videos of the same person to test MVR-People creation and matching/merging

**Step 1: Record First Video Sequence**

```bash
# Start camera recording via Cameras API
POST http://localhost:8005/api/v1/cameras/0/start-recording
{
  "duration_seconds": 30,
  "recording_name": "mvr_test_person1_video1"
}

# Tester walks in front of camera for 30 seconds
# Multiple appearances of same person expected
# System should detect faces and create person objects

# Stop recording
POST http://localhost:8005/api/v1/cameras/0/stop-recording
```

**Expected Result:**
- Video saved: `mvr_test_person1_video1.mp4`
- Vision analysis completed
- Person objects created
- Individual created (e.g., `individual_001`)
- MVR-People automatically created (e.g., `mvr_001`)
- Face embeddings extracted
- Age/gender estimated

---

**Step 2: Record Second Video Sequence (Same Person)**

```bash
# Wait 2-3 minutes for processing to complete

# Start second recording
POST http://localhost:8005/api/v1/cameras/0/start-recording
{
  "duration_seconds": 30,
  "recording_name": "mvr_test_person1_video2"
}

# SAME tester walks in front of camera again
# Different appearance (different angle, lighting, position)
# Should trigger matching and merging

# Stop recording
POST http://localhost:8005/api/v1/cameras/0/stop-recording
```

**Expected Result:**
- Video saved: `mvr_test_person1_video2.mp4`
- Vision analysis completed
- New Individual created (e.g., `individual_002`)
- MVR-People auto-created (e.g., `mvr_002`)
- **Matching triggered:** Similarity search finds `mvr_001`
- **Similarity score:** > 0.85 (threshold)
- **Merge executed:**
  - Compare quality: `mvr_001` (0.88) vs `mvr_002` (0.75)
  - Predominant: `mvr_001` (higher quality)
  - Reassign `individual_002` to `mvr_001`
  - Orphan `mvr_002`
- **Final state:**
  - `mvr_001`: Active, linked to [`individual_001`, `individual_002`]
  - `mvr_002`: Orphaned, previous_individual_uuids: [`individual_002`]

---

**Step 3: Record Third Video Sequence (Same Person)**

```bash
# Start third recording
POST http://localhost:8005/api/v1/cameras/0/start-recording
{
  "duration_seconds": 30,
  "recording_name": "mvr_test_person1_video3"
}

# SAME tester, different conditions (e.g., different clothing, glasses)
# Tests robustness of face matching

# Stop recording
POST http://localhost:8005/api/v1/cameras/0/stop-recording
```

**Expected Result:**
- Video saved: `mvr_test_person1_video3.mp4`
- New Individual created (e.g., `individual_003`)
- MVR-People auto-created (e.g., `mvr_003`)
- **Matching triggered:** Finds `mvr_001` (already has 2 individuals)
- **Similarity score:** > 0.85
- **Merge executed:**
  - Reassign `individual_003` to `mvr_001`
  - Orphan `mvr_003`
- **Final state:**
  - `mvr_001`: Active, linked to [`individual_001`, `individual_002`, `individual_003`]
  - `mvr_002`: Orphaned
  - `mvr_003`: Orphaned

---

#### Test Procedure: Multi-Person Testing

**Objective:** Test MVR-People with multiple different people (no merging expected)

**Step 4: Record Different Person (Video 4)**

```bash
# New person (Person B) in front of camera
POST http://localhost:8005/api/v1/cameras/0/start-recording
{
  "duration_seconds": 30,
  "recording_name": "mvr_test_person2_video1"
}

# Different tester (or dramatically different appearance)
# Should NOT match with Person 1's MVR-People

# Stop recording
POST http://localhost:8005/api/v1/cameras/0/stop-recording
```

**Expected Result:**
- New Individual created (e.g., `individual_004`)
- New MVR-People created (e.g., `mvr_004`)
- **Matching triggered:** Searches active MVR-People
- **Similarity scores:** All < 0.85 (no match with `mvr_001`)
- **No merge:** `individual_004` stays with `mvr_004`
- **Final state:**
  - `mvr_001`: Active, 3 individuals (Person 1)
  - `mvr_004`: Active, 1 individual (Person 2)

---

**Step 5: Record Person 2 Consecutive Video (Video 5)**

```bash
# Same Person B returns
POST http://localhost:8005/api/v1/cameras/0/start-recording
{
  "duration_seconds": 30,
  "recording_name": "mvr_test_person2_video2"
}

# Person B walks again
# Should match with mvr_004

# Stop recording
POST http://localhost:8005/api/v1/cameras/0/stop-recording
```

**Expected Result:**
- New Individual created (e.g., `individual_005`)
- MVR-People auto-created (e.g., `mvr_005`)
- **Matching triggered:** Finds `mvr_004` (Person 2)
- **Similarity score:** > 0.85
- **Merge executed:** Merge to predominant MVR-People
- **Final state:**
  - `mvr_001`: Active, 3 individuals (Person 1)
  - `mvr_004`: Active, 2 individuals (Person 2) - assuming better quality
  - `mvr_005`: Orphaned

---

#### Test Verification Checklist

After completing all 5 video recordings, verify:

**✅ Individual Creation:**
- [ ] 5 Individuals created (one per video)
- [ ] Each Individual has appearances with person objects
- [ ] Each Individual has face detections with quality scores

**✅ MVR-People Auto-Creation:**
- [ ] 5 MVR-People created initially (1:1 with Individuals)
- [ ] All MVR-People have face embeddings (512D vectors)
- [ ] All MVR-People have age estimates
- [ ] All MVR-People have gender estimates
- [ ] All MVR-People marked as `auto_created: true`

**✅ Matching Process:**
- [ ] Videos 2, 3, 5 triggered matching (same person returning)
- [ ] Video 4 did NOT trigger merge (different person)
- [ ] Similarity scores calculated correctly
- [ ] Only active MVR-People searched (orphans excluded)

**✅ Merging Process:**
- [ ] 3 merge operations executed (videos 2, 3, 5)
- [ ] Quality scores compared correctly
- [ ] Predominant MVR-People selected (highest quality)
- [ ] Individuals reassigned to predominant MVR-People
- [ ] 3 MVR-People orphaned (`mvr_002`, `mvr_003`, `mvr_005`)

**✅ Orphan Tracking:**
- [ ] Orphaned MVR-People have `is_orphaned: true`
- [ ] Orphaned MVR-People have `orphaned_at` timestamp
- [ ] Orphaned MVR-People have `merged_into_mvr_uuid` pointing to predominant
- [ ] Orphaned MVR-People have `previous_individual_uuids` in JSONB field
- [ ] Orphaned MVR-People have `total_linked_individuals: 0`

**✅ Final State:**
- [ ] 2 active MVR-People (`mvr_001` for Person 1, `mvr_004` for Person 2)
- [ ] `mvr_001` linked to 3 Individuals (videos 1, 2, 3)
- [ ] `mvr_004` linked to 2 Individuals (videos 4, 5)
- [ ] 3 orphaned MVR-People
- [ ] Total 5 Individuals, 5 MVR-People (2 active, 3 orphaned)

**✅ Audit Trail:**
- [ ] 3 entries in `mvr_merge_audit_log` table
- [ ] Each entry has predominant/orphaned UUIDs
- [ ] Each entry has similarity scores
- [ ] Each entry has merge timestamp

**✅ API Responses:**
- [ ] GET `/api/v1/mvr-people/{mvr_001}` returns 3 linked individuals
- [ ] GET `/api/v1/mvr-people/orphaned` returns 3 orphaned MVR-People
- [ ] GET `/api/v1/mvr-people/individuals/{individual_002}/merge-history` shows merge event

---

#### Database Queries for Verification

**Query 1: Check Active MVR-People**
```sql
SELECT 
  mvr_people_uuid,
  total_linked_individuals,
  quality_score,
  is_orphaned,
  created_at
FROM mvr_people
WHERE is_orphaned = FALSE
ORDER BY created_at;

-- Expected: 2 rows (mvr_001, mvr_004)
```

**Query 2: Check Orphaned MVR-People**
```sql
SELECT 
  mvr_people_uuid,
  orphaned_at,
  merged_into_mvr_uuid,
  previous_individual_uuids
FROM mvr_people
WHERE is_orphaned = TRUE
ORDER BY orphaned_at;

-- Expected: 3 rows (mvr_002, mvr_003, mvr_005)
```

**Query 3: Check Individual-MVR Mappings**
```sql
SELECT 
  individual_uuid,
  mvr_people_uuid,
  is_representative,
  confidence_score,
  linked_at
FROM individual_mvr_mapping
ORDER BY linked_at;

-- Expected: 5 rows (all individuals mapped to active MVR-People)
```

**Query 4: Check Merge Audit Log**
```sql
SELECT 
  merge_id,
  predominant_mvr_uuid,
  orphaned_mvr_uuid,
  similarity_score,
  merged_at
FROM mvr_merge_audit_log
ORDER BY merged_at;

-- Expected: 3 rows (merges from videos 2, 3, 5)
```

---

### Unit Tests

1. **ML Model Tests**
   - Test face embedding extraction with sample images
   - Test age estimation accuracy against labeled dataset
   - Test gender classification accuracy against labeled dataset
   - Test preprocessing functions (resize, normalize)
   - Test model loading and initialization

2. **Database Tests**
   - Test MVR-People CRUD operations
   - Test individual-MVR mapping insert/update/delete
   - Test similarity search queries with known embeddings
   - Test orphaning operations
   - Test JSONB field updates (previous_individual_uuids)
   - Test configuration table updates

3. **Service Tests**
   - Test MVR creation workflow
   - Test best quality face selection algorithm
   - Test matching algorithm (similarity threshold)
   - Test merge decision logic (quality comparison)
   - Test orphan creation
   - Test error handling (missing faces, low quality, etc.)

---

### Integration Tests

1. **End-to-End MVR Creation**
   - Create individual → Select best face → Generate embeddings → Store MVR
   - Verify all fields populated correctly
   - Verify auto_created flag set

2. **End-to-End Matching and Merging**
   - Create Individual A with MVR-People A
   - Create Individual B with MVR-People B (similar face)
   - Trigger matching process
   - Verify similarity calculated correctly
   - Verify merge executed if above threshold
   - Verify orphan created
   - Verify audit log entry

3. **Similarity Search**
   - Create multiple MVR-People with known embeddings
   - Search for similar ones with various thresholds
   - Verify results ranked by similarity
   - Verify orphaned MVR-People excluded

4. **API Tests**
   - Test all 14 endpoints
   - Test authentication and authorization
   - Test error responses (404, 400, 500)
   - Test pagination for list endpoints
   - Test threshold configuration updates

---

### Performance Tests

1. **Load Testing**
   - Create 1000 MVR-People records concurrently
   - Measure average processing time per individual
   - Measure matching overhead
   - Test concurrent processing with background tasks

2. **Similarity Search Benchmark**
   - Database with 10k, 100k, 1M MVR-People
   - Measure query response time with pgvector index
   - Compare with/without indexes
   - Test with various similarity thresholds

3. **Merge Operation Benchmark**
   - Measure merge execution time (reassign, orphan, update)
   - Test with varying numbers of linked individuals
   - Measure audit log write performance

---

### Real-World Test Scenarios

**Scenario 1: Same Person, Different Sessions**
- Record person on Monday → MVR-People created
- Record same person on Friday → Should match and merge
- Expected: 1 active MVR-People with 2 individuals

**Scenario 2: Same Person, Different Appearance**
- Record person without glasses → MVR-People created
- Record same person with glasses → Should still match
- Expected: Merge successful if similarity > threshold

**Scenario 3: Similar-Looking People (False Positive Test)**
- Record Person A → MVR-People A
- Record Person B (similar features) → MVR-People B
- Expected: NO merge if similarity < threshold

**Scenario 4: Low Quality Face**
- Record person with poor lighting → Low quality score
- Record same person with good lighting → High quality score
- Expected: Merge to high-quality MVR-People

**Scenario 5: Multiple Consecutive Videos**
- Record same person 5 times in a row
- Expected: 1 active MVR-People, 4 orphaned MVR-People
- Expected: All 5 individuals linked to predominant MVR-People

---

### Automated Test Execution Script

**Create test script:** `tests/mvr_people/test_mvr_real_camera.py`

```python
#!/usr/bin/env python3
"""
MVR-People Real Camera Test Script

Tests MVR-People creation, matching, and merging using real USB camera recordings.

Requirements:
- USB Camera 0 accessible
- All PPL Meta services running
- At least one human subject for recording

Usage:
    python tests/mvr_people/test_mvr_real_camera.py
"""

import asyncio
import requests
import time
from datetime import datetime
from typing import List, Dict
import json

class MVRPeopleRealCameraTest:
    """Test MVR-People with real camera recordings."""
    
    def __init__(self):
        self.cameras_url = "http://localhost:8005"
        self.vmeta_url = "http://localhost:8008"
        self.orchestrator_url = "http://localhost:8002"
        
        self.test_videos = []
        self.individuals = []
        self.mvr_people = []
        
    def log(self, message: str):
        """Log test messages with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def wait_for_processing(self, seconds: int = 30):
        """Wait for video processing to complete."""
        self.log(f"⏳ Waiting {seconds}s for processing...")
        for i in range(seconds, 0, -1):
            print(f"   {i}s remaining...", end='\r')
            time.sleep(1)
        print()
    
    def record_video(self, video_name: str, duration: int = 30) -> Dict:
        """Record video from USB camera 0."""
        self.log(f"🎥 Starting recording: {video_name}")
        
        # Start recording
        response = requests.post(
            f"{self.cameras_url}/api/v1/cameras/0/start-recording",
            json={
                "duration_seconds": duration,
                "recording_name": video_name
            }
        )
        response.raise_for_status()
        recording = response.json()
        
        self.log(f"   Recording started, ID: {recording['recording_id']}")
        self.log(f"   👤 Please walk in front of camera for {duration} seconds...")
        
        # Wait for recording to complete
        time.sleep(duration + 2)
        
        # Stop recording
        response = requests.post(
            f"{self.cameras_url}/api/v1/cameras/0/stop-recording"
        )
        response.raise_for_status()
        
        self.log(f"   ✅ Recording completed: {video_name}")
        self.test_videos.append(recording)
        
        return recording
    
    def get_individuals_from_video(self, video_uuid: str) -> List[Dict]:
        """Get individuals created from video analysis."""
        self.log(f"🔍 Fetching individuals for video: {video_uuid}")
        
        response = requests.get(
            f"{self.vmeta_url}/api/v1/individuals",
            params={"video_uuid": video_uuid}
        )
        response.raise_for_status()
        individuals = response.json()
        
        self.log(f"   Found {len(individuals)} individual(s)")
        self.individuals.extend(individuals)
        
        return individuals
    
    def get_mvr_for_individual(self, individual_uuid: str) -> Dict:
        """Get MVR-People for individual."""
        response = requests.get(
            f"{self.vmeta_url}/api/v1/mvr-people/individuals/{individual_uuid}"
        )
        
        if response.status_code == 200:
            mvr = response.json()
            self.mvr_people.append(mvr)
            return mvr
        else:
            return None
    
    def verify_merge(self, individual_uuid: str) -> Dict:
        """Verify merge history for individual."""
        response = requests.get(
            f"{self.vmeta_url}/api/v1/mvr-people/individuals/{individual_uuid}/merge-history"
        )
        response.raise_for_status()
        
        return response.json()
    
    def get_orphaned_mvr(self) -> List[Dict]:
        """Get all orphaned MVR-People."""
        response = requests.get(
            f"{self.vmeta_url}/api/v1/mvr-people/orphaned"
        )
        response.raise_for_status()
        
        return response.json()
    
    def run_test_sequence(self):
        """Run complete test sequence."""
        self.log("=" * 80)
        self.log("🚀 MVR-People Real Camera Test - Starting")
        self.log("=" * 80)
        
        # Video 1: Person 1, First Appearance
        self.log("\n📹 TEST 1: Recording Person 1 - Video 1")
        video1 = self.record_video("mvr_test_person1_video1", duration=30)
        self.wait_for_processing(30)
        
        individuals_v1 = self.get_individuals_from_video(video1['video_uuid'])
        if individuals_v1:
            ind1_uuid = individuals_v1[0]['individual_uuid']
            mvr1 = self.get_mvr_for_individual(ind1_uuid)
            
            self.log(f"   ✅ Individual 1 created: {ind1_uuid}")
            self.log(f"   ✅ MVR-People 1 created: {mvr1['mvr_people_uuid']}")
            self.log(f"   - Quality Score: {mvr1.get('quality_score', 'N/A')}")
            self.log(f"   - Age: {mvr1['age_estimate']['min_age']}-{mvr1['age_estimate']['max_age']}")
            self.log(f"   - Gender: {mvr1['gender_estimate']['gender']}")
        
        # Video 2: Same Person 1, Second Appearance (Should Merge)
        self.log("\n📹 TEST 2: Recording Same Person 1 - Video 2 (Expect Merge)")
        self.log("   👤 IMPORTANT: Same person should walk in front of camera again")
        input("   Press ENTER when ready to record...")
        
        video2 = self.record_video("mvr_test_person1_video2", duration=30)
        self.wait_for_processing(30)
        
        individuals_v2 = self.get_individuals_from_video(video2['video_uuid'])
        if individuals_v2:
            ind2_uuid = individuals_v2[0]['individual_uuid']
            mvr2 = self.get_mvr_for_individual(ind2_uuid)
            
            self.log(f"   ✅ Individual 2 created: {ind2_uuid}")
            
            # Check if merged
            merge_history = self.verify_merge(ind2_uuid)
            
            if merge_history.get('total_merges', 0) > 0:
                self.log(f"   ✅ MERGE DETECTED!")
                self.log(f"   - Current MVR: {merge_history['current_mvr_people']['mvr_people_uuid']}")
                self.log(f"   - Merged from: {len(merge_history.get('previous_mvr_people', []))} orphaned MVR")
                self.log(f"   - Similarity Score: {merge_history['merge_events'][0]['similarity_score']}")
            else:
                self.log(f"   ⚠️ NO MERGE - Individual 2 has own MVR: {mvr2['mvr_people_uuid']}")
        
        # Video 3: Same Person 1, Third Appearance (Should Merge Again)
        self.log("\n📹 TEST 3: Recording Same Person 1 - Video 3 (Expect Merge)")
        self.log("   👤 IMPORTANT: Same person one more time")
        input("   Press ENTER when ready to record...")
        
        video3 = self.record_video("mvr_test_person1_video3", duration=30)
        self.wait_for_processing(30)
        
        individuals_v3 = self.get_individuals_from_video(video3['video_uuid'])
        if individuals_v3:
            ind3_uuid = individuals_v3[0]['individual_uuid']
            merge_history = self.verify_merge(ind3_uuid)
            
            self.log(f"   ✅ Individual 3 created: {ind3_uuid}")
            
            if merge_history.get('total_merges', 0) > 0:
                self.log(f"   ✅ MERGE DETECTED!")
                self.log(f"   - Current MVR: {merge_history['current_mvr_people']['mvr_people_uuid']}")
                self.log(f"   - Total linked individuals: {merge_history['current_mvr_people']['total_linked_individuals']}")
        
        # Video 4: Different Person (Should NOT Merge)
        self.log("\n📹 TEST 4: Recording Person 2 - Video 1 (Expect NO Merge)")
        self.log("   👤 IMPORTANT: Different person should walk in front of camera")
        input("   Press ENTER when ready to record...")
        
        video4 = self.record_video("mvr_test_person2_video1", duration=30)
        self.wait_for_processing(30)
        
        individuals_v4 = self.get_individuals_from_video(video4['video_uuid'])
        if individuals_v4:
            ind4_uuid = individuals_v4[0]['individual_uuid']
            mvr4 = self.get_mvr_for_individual(ind4_uuid)
            merge_history = self.verify_merge(ind4_uuid)
            
            self.log(f"   ✅ Individual 4 created: {ind4_uuid}")
            self.log(f"   ✅ MVR-People 4 created: {mvr4['mvr_people_uuid']}")
            
            if merge_history.get('total_merges', 0) == 0:
                self.log(f"   ✅ NO MERGE (Correct - Different person)")
            else:
                self.log(f"   ❌ UNEXPECTED MERGE - Check threshold or face similarity")
        
        # Video 5: Person 2 Again (Should Merge with Person 2's MVR)
        self.log("\n📹 TEST 5: Recording Person 2 - Video 2 (Expect Merge with Person 2)")
        self.log("   👤 IMPORTANT: Same Person 2 should return")
        input("   Press ENTER when ready to record...")
        
        video5 = self.record_video("mvr_test_person2_video2", duration=30)
        self.wait_for_processing(30)
        
        individuals_v5 = self.get_individuals_from_video(video5['video_uuid'])
        if individuals_v5:
            ind5_uuid = individuals_v5[0]['individual_uuid']
            merge_history = self.verify_merge(ind5_uuid)
            
            self.log(f"   ✅ Individual 5 created: {ind5_uuid}")
            
            if merge_history.get('total_merges', 0) > 0:
                self.log(f"   ✅ MERGE DETECTED!")
                self.log(f"   - Merged with Person 2's MVR")
        
        # Final Summary
        self.log("\n" + "=" * 80)
        self.log("📊 TEST SUMMARY")
        self.log("=" * 80)
        
        # Get orphaned MVR-People
        orphaned = self.get_orphaned_mvr()
        
        self.log(f"Total Videos Recorded: {len(self.test_videos)}")
        self.log(f"Total Individuals Created: {len(self.individuals)}")
        self.log(f"Total Orphaned MVR-People: {len(orphaned.get('results', []))}")
        
        # Expected results
        self.log("\n✅ EXPECTED RESULTS:")
        self.log("   - 5 Individuals created")
        self.log("   - 5 MVR-People created initially")
        self.log("   - 2 Active MVR-People (Person 1, Person 2)")
        self.log("   - 3 Orphaned MVR-People (from merges)")
        self.log("   - Person 1 MVR linked to 3 Individuals (videos 1,2,3)")
        self.log("   - Person 2 MVR linked to 2 Individuals (videos 4,5)")
        
        self.log("\n" + "=" * 80)
        self.log("✅ Test Sequence Complete!")
        self.log("=" * 80)


if __name__ == "__main__":
    test = MVRPeopleRealCameraTest()
    
    try:
        test.run_test_sequence()
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
```

**Run the test:**
```bash
# Make sure all services are running
cd /Users/nickgklezakos/Documents/ppl-meta-code

# Start services if not running
# (Use VS Code task: 🚀 Start All Local Python Services)

# Run test script
python tests/mvr_people/test_mvr_real_camera.py
```

---

## Security Considerations

### Data Privacy

1. **Biometric Data Protection**
   - Face embeddings are **biometric data** (GDPR/CCPA)
   - Implement encryption at rest
   - Implement access controls

2. **Consent Management**
   - Track consent for face recognition
   - Allow deletion of MVR-People on request

3. **Anonymization**
   - Option to anonymize age/gender estimates
   - Option to delete face embeddings while keeping metadata

### Authentication & Authorization

1. **API Security**
   - JWT token required for all endpoints
   - Role-based access control (RBAC)
   - Audit logging for MVR-People access

2. **Rate Limiting**
   - Limit similarity search queries (expensive operation)
   - Limit batch creation requests

---

## Migration Plan

### Phase 1: Database Schema (Week 1)

1. Create `mvr_people` table
2. Create `individual_mvr_mapping` table
3. Add indexes
4. Install pgvector extension

### Phase 2: ML Models Setup (Week 1-2)

1. Download/train FaceNet model
2. Download/train Age estimation model
3. Download/train Gender classification model
4. Create ML processing modules
5. Test models independently

### Phase 3: Core Service Implementation (Week 2-3)

1. Implement MVRService
2. Implement MVRProcessor (orchestrates ML models)
3. Implement best quality face selection
4. **NEW:** Implement matching algorithm (similarity search)
5. **NEW:** Implement merge logic (predominant selection, orphaning)
6. Implement background task processing
7. Add database repository methods

### Phase 4: API Implementation (Week 3-4)

1. Create MVR-People CRUD endpoints
2. Implement similarity search
3. Implement demographic search
4. **NEW:** Implement matching endpoints (find similar Individuals)
5. **NEW:** Implement merge endpoints (manual/automatic)
6. **NEW:** Implement configuration endpoints (threshold updates)
7. **NEW:** Implement orphan management endpoints
8. Add batch processing
9. Add status endpoints

### Phase 5: Integration & Testing (Week 4-5)

1. Integrate with existing Individual creation workflow
2. **NEW:** Test automatic MVR-People creation on Individual insert
3. **NEW:** Test automatic matching and merging
4. **NEW:** Test orphan tracking and history
5. End-to-end testing
6. Performance testing (with merge overhead)
7. Security testing
8. Documentation

### Phase 6: Deployment (Week 5-6)

1. Deploy to staging
2. Run migration scripts (including new tables)
3. **NEW:** Configure matching threshold (default 0.85)
4. **NEW:** Enable/disable auto-merge feature
5. Create MVR-People for existing individuals (batch)
6. **NEW:** Run initial matching pass (find duplicates)
7. Monitor performance and merge rates
8. Deploy to production

---

## Success Metrics

### Accuracy Metrics

- **Face Embedding Quality:** Similarity score > 0.9 for same person
- **Age Estimation Accuracy:** Within ±5 years, 80% of time
- **Gender Classification Accuracy:** > 95% accuracy
- **NEW - Matching Accuracy:** > 95% true positive rate for matches above threshold
- **NEW - Merge Precision:** < 5% false positive merge rate

### Performance Metrics

- **MVR Creation Time:** < 1 second per individual (GPU) including matching
- **Similarity Search Time:** < 100ms for 100k records
- **Merge Execution Time:** < 300ms per merge operation
- **Batch Processing Throughput:** > 100 individuals/minute with auto-matching

### Business Metrics

- **MVR-People Coverage:** > 90% of individuals have MVR-People
- **Re-identification Rate:** Successfully link 70% of returning individuals via matching
- **Merge Rate:** 10-20% of new Individuals automatically merged
- **Orphan Growth:** Track orphaned MVR-People growth rate
- **Search Effectiveness:** Similarity search returns relevant results 80% of time

---

## Future Enhancements

### Phase 2 Features (Future)

1. **Advanced Matching**
   - Multi-stage matching (face + body + clothing)
   - Temporal matching (same person over time with age changes)
   - Probabilistic merging (confidence-based thresholds)

2. **Smart Orphan Management**
   - Auto-archive old orphans
   - Orphan analytics dashboard
   - Merge chain visualization

3. **Multi-Modal Embeddings**
   - Combine face, body, clothing embeddings
   - Gait recognition for walking patterns

4. **Temporal Analysis**
   - Track age changes over time
   - Detect same person across years

5. **Advanced Demographics**
   - Ethnicity estimation
   - Expression analysis (happy, sad, neutral)
   - Accessories detection (glasses, hats, masks)

6. **Privacy Features**
   - Differential privacy for embeddings
   - Federated learning for model updates
   - On-device processing option

7. **Integration Features**
   - Export to external systems (Watchlist APIs)
   - Import from mugshot databases
   - Real-time alerts for VIP/Person of Interest

---

## Conclusion

MVR-People brings powerful machine learning capabilities to the ppl-meta-vmeta service, enabling:

✅ **Automatic MVR-People creation** on Individual creation (1:1 initially)  
✅ **Intelligent matching** based on face similarity and configurable threshold  
✅ **Dynamic merging** to predominant MVR-People (quality-based selection)  
✅ **Orphan tracking** with full audit history via JSON fields  
✅ **Persistent ML representations** of individuals  
✅ **Similarity search** for person re-identification  
✅ **Demographic filtering** (age, gender)  
✅ **Cross-session tracking** of returning individuals  
✅ **Advanced analytics** for security and business intelligence

**Architecture Highlights:**
- **Automatic Creation:** Each Individual gets MVR-People automatically (1:1 → 1:N after merging)
- **Configurable Matching:** Default 0.85 threshold, updateable via API
- **Quality-Based Merging:** Predominant MVR-People selected by quality score
- **Orphan Management:** Orphaned MVR-People retain history via JSONB field
- **Audit Trail:** Complete merge history in mvr_merge_audit_log table
- Independent ML models (same as ppl-meta-mini but not imported)
- Async background processing for performance
- Vector similarity search with pgvector (active MVR-People only)
- RESTful API with 14 comprehensive endpoints

**Key Workflow:**
1. Individual created → MVR-People auto-created (1:1)
2. Background task searches for similar MVR-People (threshold check)
3. If match found → Compare quality scores → Merge to predominant
4. Orphaned MVR-People stores previous Individual UUIDs
5. Predominant MVR-People links to multiple Individuals

**Implementation Timeline:** 5-6 weeks from design to production

**Next Steps:**
1. Review and approve design document
2. Set up development environment with ML models
3. **Prepare USB Camera 0 for real-world testing**
4. **Recruit 2-3 test subjects for video recording**
5. Begin Phase 1 (Database Schema) implementation with new merge tables
6. **Execute real-camera test suite (5 videos minimum)**

---

**Document Status:** ✅ READY FOR REVIEW  
**Last Updated:** October 30, 2025 (Updated with Real-World Testing Procedures)  
**Author:** PPL Meta Platform Team  
**Version:** 2.1.0 - Updated with Real-World Camera Testing Strategy
