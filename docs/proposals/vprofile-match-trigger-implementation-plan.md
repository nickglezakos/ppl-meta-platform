# VProfile Match Trigger — Implementation Plan

**Date**: 2026-04-07  
**Status**: Proposal (v2 — Multi-Camera + Background Refresh)  
**Author**: PPL Meta Platform Team  

---

## 1. Overview

### 1.1 What Is VProfile Match?

VProfile Match is a new automation trigger type (`trigger_mode = 'vprofile_match'`) that compares **current instant-detection MVR results from one or more cameras** against the MVR objects of **one or more individual groups**, performing the comparison **entirely in memory** without database round-trips per evaluation cycle. Match results retain the **source camera ID** so downstream actions know which camera(s) detected the matching person.

The group MVR embeddings are **pre-loaded into memory** on trigger activation and are **periodically auto-refreshed** from the database on a **separate background queue** (configurable interval, default 10 minutes) to ensure freshness without blocking the hot comparison path.

### 1.2 Why a New Trigger Type (Not an Upgrade to `ppl_match`)?

The existing `ppl_match` trigger has been traced end-to-end in this codebase (see Sections 2.1–2.3 below). Key differences from the proposed functionality:

| Aspect | Existing `ppl_match` | Proposed `vprofile_match` |
|---|---|---|
| Group selection | Single group (`ppl_match_group_id: String(255)`) | **Multiple groups** (new `ppl_match_group_ids: JSON array`) |
| Camera selection | Single camera (`camera_device_id: String(255)`) | **Multiple cameras** (new `camera_device_ids: JSON array`) |
| Match provenance | No camera info in results | **`source_camera_id`** attached to every match |
| Embedding source | **Database query per evaluation** — fetches candidate + group member embeddings from PostgreSQL `mvr_people.face_embedding` on every Redis event | **Pre-loaded in memory** on trigger activation; **auto-refreshed every N minutes** on a separate background queue |
| Embedding freshness | Always fresh (DB per eval) | **Periodic background refresh** (default 10 min), atomic swap, content-hash change detection |
| Comparison target | `source_mvr_uuids` from Redis event → HTTP POST to vmeta `/check-duplicates` → DB query → NumPy | `source_mvr_uuids` from Redis event → **in-memory NumPy cosine similarity** |
| Latency per eval | ~100-500ms (HTTP round-trip + DB query + NumPy) | <1ms (pure in-memory numpy comparison) |
| Architecture | Media Service ↔ vmeta HTTP → vmeta DB | Media Service in-memory cache + background refresh queue + vmeta DB (load once, refresh periodically) |
| Memory lifecycle | None | Load on activate, evict on deactivate/update, LRU, **periodic background refresh** |

**Decision**: A new trigger type avoids breaking backward compatibility with existing `ppl_match` logic, keeps the single-group vs multi-group data models clean, supports multi-camera instant detection, and allows the in-memory caching + periodic refresh architecture to evolve independently.

---

## 2. Existing Codebase Context

### 2.1 Relevant Services & Files

```
ppl-meta-media/                    # Primary implementation target
├── src/models/trigger.py          # Trigger SQLAlchemy model (+ new columns)
├── src/schemas/trigger.py         # Pydantic schemas
├── src/routes/triggers.py         # Trigger CRUD endpoints
├── src/services/redis_subscriber.py  # InstantDetectionSubscriber (+ vprofile branch)
├── src/services/search_trigger_scheduler.py  # Existing search trigger scheduler (reference)
└── migrations/versions/           # Alembic migrations

ppl-meta-vmeta/                    # Backend service for embedding retrieval
├── src/api/routes/individual_groups.py     # Group API (+ new multi-embedding endpoint)
├── src/services/individual_groups_manager.py  # (+ load_multi_group_embeddings)
└── src/services/embedding_cache_service.py    # Existing embedding cache (reference)

ppl-meta-frontend/                 # Flutter client
├── lib/models/trigger_model.dart  # TriggerModel (+ vprofile fields)
└── lib/widgets/triggers_tab.dart  # Trigger creation/editing UI
```

### 2.2 Existing `ppl_match` Execution Flow (Reference)

**Instant-detection path** (what we're extending):

```
Camera Service (Celery task)
  → POST /api/v1/instant-detection-storage (vmeta)  [persists MVRs to tracking_sessions/individuals]
  → PUBLISH Redis "instant-detection" channel
    {camera_id, people_count, demographics, source_mvr_uuids: [...], ...}

InstantDetectionSubscriber (redis_subscriber.py)
  → _handle_instant_detection(data)
    → queries DB for active triggers on camera_id
    → if trigger.trigger_mode == "ppl_match":
        → _evaluate_ppl_match(trigger, data)  [line 557]
          → extracts source_mvr_uuids from event
          → for each source_mvr_uuid:
              → POST vmeta /api/v1/individual-groups/{group_id}/check-duplicates
                → DB fetch candidate embedding (mvr_people.face_embedding)
                → DB fetch all group member embeddings
                → NumPy cosine similarity
              → return matches
          → if matches found above threshold → fire trigger
```

### 2.3 Key Finding: No In-Memory Caching Exists

After exhaustive code review across `ppl-meta-media`, `ppl-meta-vmeta`, `ppl-meta-cameras`, and `ppl-meta-orchestrator`:

- The `_evaluate_ppl_match` method calls vmeta's `/check-duplicates` endpoint **on every Redis event**
- vmeta's `check_for_duplicates()` queries PostgreSQL `mvr_people.face_embedding` **on every call**
- There is **no embedding cache** in either path
- The `source_mvr_uuids` in the Redis event are **string UUIDs only** — no embeddings are transmitted via Redis
- Triggers filter by **single** `camera_device_id` — no multi-camera support exists

---

## 3. Proposed Architecture

### 3.1 High-Level Data Flow

```
                        ┌─────────────────────────────────────────┐
                        │        VProfile Match Worker (NEW)       │
                        │                                         │
  Trigger Activated ──▶ │  1. Load group embeddings from vmeta DB │
  (create/update/       │     (all groups for all active triggers) │
   toggle on)           │  2. Cache in memory                      │
                        │     {group_id: [embeddings]}             │
                        │                                         │
                        │  ┌─────────────────────────────────────┐ │
                        │  │ Background Refresh Queue (NEW)      │ │
                        │  │  (separate asyncio task)            │ │
                        │  │  1. Sleep(refresh_interval)          │ │
                        │  │  2. Fetch fresh embeddings from      │ │
                        │  │     vmeta DB (HTTP batch)            │ │
                        │  │  3. Compute content hash             │ │
                        │  │  4. If changed → atomic cache swap  │ │
                        │  └──────────────┬──────────────────────┘ │
                        │                │ (never blocks eval)     │
                        └────────────────┼────────────────────────┘
                                         │
  Redis "instant-      ┌────────────────▼────────────────────────┐
  detection" ─────────▶│  3. Listen for events on channel         │
  channel              │     (from camera_1, camera_2, ...)      │
                       │                                         │
                       │  4. Filter: event.camera_id IN           │
                       │     trigger.camera_device_ids?           │
                       │     ✓ → continue                         │
                       │                                         │
                       │  5. For each event:                      │
                       │     a. Extract source_mvr UUIDs          │
                       │     b. Record source_camera_id           │
                       │     c. Fetch their embeddings            │
                       │        from vmeta DB (batch query)       │
                       │     d. Cosine sim against all            │
                       │        cached group embeddings           │
                       │     e. Score ≥ threshold?                │
                       │        → Match result includes           │
                       │          source_camera_id for            │
                       │          downstream provenance          │
                       │        → Fire!                           │
                       └─────────────────────────────────────────┘
                                         │
  Trigger Deactivated ──▶ 6. Evict from memory
  (toggle off/delete)       (if no other trigger references group)
```

### 3.2 Component Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        ppl-meta-media                                │
│                                                                      │
│  ┌─────────────────────┐    ┌──────────────────────────────────────┐ │
│  │ Existing:            │    │ NEW: VProfileMatchWorker            │ │
│  │ InstantDetection     │    │                                      │ │
│  │ Subscriber           │    │  ┌────────────────────────────────┐  │ │
│  │ (redis_subscriber.py)│    │  │ EmbeddingCache                  │  │ │
│  │                      │    │  │ - Dict[str, CachedGroup]        │  │ │
│  │ _handle_instant_     │    │  │ - load(group_ids)               │  │ │
│  │   detection(data)    │    │  │ - evict(group_id)               │  │ │
│  │   │                  │    │  │ - compare(source_emb,           │  │ │
│  │   ├─ ppl_match ──────┤    │  │           threshold)            │  │ │
│  │   │  (existing)      │    │  │ - compute_content_hash()        │  │ │
│  │   │                  │    │  │ - memory_usage_bytes            │  │ │
│  │   └─ vprofile_match ─┤    │  └───────────────┬────────────────┘  │ │
│  │      (NEW branch)    │    │                  │                   │ │
│  │       │              │    │  ┌───────────────▼────────────────┐  │ │
│  │       │ multi-camera │    │  │ VProfileEvaluator               │  │ │
│  │       │ filter +     │    │  │ - evaluate(event_data,          │  │ │
│  │       │ camera_id    │    │  │            triggers)            │  │ │
│  │       │ in results   │    │  │ - batch_fetch_source_           │  │ │
│  │       │              │    │  │   embeddings(uuids)            │  │ │
│  │       └──────────────┼────┤  │ - attach source_camera_id       │  │ │
│  │                      │    │  └───────────────┬────────────────┘  │ │
│  │                      │    │                  │                   │ │
│  │                      │    │  ┌───────────────▼────────────────┐  │ │
│  │                      │    │  │ VProfileLifecycle               │  │ │
│  │                      │    │  │ - on_activate(trigger)          │  │ │
│  │                      │    │  │ - on_deactivate(trigger)        │  │ │
│  │                      │    │  │ - on_update(trigger)            │  │ │
│  │                      │    │  └────────────────────────────────┘  │ │
│  │                      │    │                                      │ │
│  │                      │    │  ┌────────────────────────────────┐  │ │
│  │                      │    │  │ BackgroundRefreshQueue (NEW)    │  │ │
│  │                      │    │  │  (separate asyncio task)        │  │ │
│  │                      │    │  │  - start_refresh_loop()         │  │ │
│  │                      │    │  │  - _refresh_all_groups()        │  │ │
│  │                      │    │  │  - compute_content_hash()       │  │ │
│  │                      │    │  │  - atomic cache swap            │  │ │
│  │                      │    │  │  - interval: env-configurable   │  │ │
│  │                      │    │  └────────────────────────────────┘  │ │
│  │                      │    └──────────────────────────────────────┘ │
│  └─────────────────────┘                                              │
│                                                                      │
│  ┌─────────────────────┐                                             │
│  │ NEW: Group Change    │  Redis pub/sub "group-updated" channel      │
│  │ Invalidator          │  → reloads affected group in cache          │
│  └─────────────────────┘                                             │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ HTTP (load once, periodic refresh)
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        ppl-meta-vmeta                                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ NEW endpoint:                                                    ││
│  │ POST /api/v1/individual-groups/multi-embedding-load               ││
│  │                                                                  ││
│  │ Request:  {"group_ids": ["g1", "g2", ...],                       ││
│  │            "include_demographics": true}                          ││
│  │                                                                  ││
│  │ Response: {"groups": {                                           ││
│  │   "g1": {"name": "...",                                          ││
│  │     "members": [{                                                ││
│  │       "mvr_people_uuid": "...",                                  ││
│  │       "face_embedding": [0.1, 0.2, ...],  // 512-dim             ││
│  │       "name": "...",                                             ││
│  │       "member_number": 1,                                        ││
│  │       "demographics": {"age": 32, "gender": "male"}              ││
│  │     }, ...]                                                      ││
│  │   }, ...                                                         ││
│  │ }}                                                               ││
│  │                                                                  ││
│  │ Implementation:                                                  ││
│  │ IndividualGroupsManager.load_multi_group_embeddings()            ││
│  │   → Single DB query joining group_membership + mvr_people        ││
│  │   → Fetches all embeddings in one round-trip                     ││
│  │   → Returns parsed numpy-compatible JSON                         ││
│  └──────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Database Schema Changes

### 4.1 Migration: Add VProfile Fields

**File**: `ppl-meta-media/migrations/versions/XXX_add_vprofile_match_fields.py`

```python
"""Add vprofile_match fields to triggers table

Revision ID: XXXX
Revises: add_ppl_match_negate_to_triggers
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('triggers',
        sa.Column('ppl_match_group_ids', sa.Text(), nullable=True,
                  comment='JSON array of group IDs for vprofile_match mode')
    )
    op.add_column('triggers',
        sa.Column('camera_device_ids', sa.Text(), nullable=True,
                  comment='JSON array of camera device IDs for vprofile_match multi-camera mode (e.g., ["usb_camera_0", "rtsp_192.168.1.76_554"])')
    )

def downgrade():
    op.drop_column('triggers', 'camera_device_ids')
    op.drop_column('triggers', 'ppl_match_group_ids')
```

### 4.2 Updated Trigger Model

**File**: `ppl-meta-media/src/models/trigger.py`

Add after line 139 (after `ppl_match_negate`):

```python
# VProfile multi-group match configuration
ppl_match_group_ids = Column(
    Text,
    nullable=True,
    comment='JSON array of individual group IDs for vprofile_match mode (e.g., ["group-uuid-1", "group-uuid-2"])'
)

# VProfile multi-camera configuration
camera_device_ids = Column(
    Text,
    nullable=True,
    comment='JSON array of camera device IDs for vprofile_match multi-camera mode (e.g., ["usb_camera_0", "rtsp_192.168.1.76_554"])'
)
```

Update the `trigger_mode` comment (line 114) to include the new mode:

```python
trigger_mode = Column(
    String(30),
    nullable=False,
    default="demographic",
    index=True,
    comment="Trigger mode: demographic | ppl_match | search | search_demographic | vprofile_match"
)
```

---

## 5. New Component: VProfileMatchWorker

### 5.1 File Structure

**New file**: `ppl-meta-media/src/services/vprofile_match_worker.py`

### 5.2 Core Classes

#### 5.2.1 `EmbeddingCache`

```python
import hashlib
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


@dataclass
class CachedMember:
    """A single group member's cached data for fast comparison."""
    mvr_people_uuid: str
    embedding: np.ndarray          # 512-dimensional FaceNet512 embedding (L2-normalized)
    name: Optional[str] = None
    member_number: Optional[int] = None
    demographics: Dict = field(default_factory=dict)


@dataclass
class CachedGroup:
    """A cached individual group with all member embeddings loaded."""
    group_id: str
    group_name: str
    members: List[CachedMember]
    loaded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    embedding_matrix: Optional[np.ndarray] = None  # Pre-computed Nx512 matrix for batch comparison

    def __post_init__(self):
        if self.members:
            self.embedding_matrix = np.stack([m.embedding for m in self.members])


class EmbeddingCache:
    """
    In-memory cache of individual group member embeddings.
    
    - Loaded once on trigger activation
    - Periodically refreshed on a background queue (never blocks evaluations)
    - Evicted on trigger deactivation or update
    - Supports LRU eviction when memory limit is reached
    - Supports atomic swap for background refresh (no locks needed)
    """
    
    def __init__(self, max_memory_bytes: int = 512 * 1024 * 1024):  # 512 MB default
        self._groups: Dict[str, CachedGroup] = {}
        self._max_memory_bytes = max_memory_bytes
        self._lru_order: List[str] = []  # Most recently used at end
    
    def load_group(self, group_id: str, group_name: str, members_data: List[Dict]) -> CachedGroup:
        """Load a group's member embeddings into cache."""
        members = []
        for member in members_data:
            embedding = np.array(member['face_embedding'], dtype=np.float32)
            # Normalize for cosine similarity
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            members.append(CachedMember(
                mvr_people_uuid=member['mvr_people_uuid'],
                embedding=embedding,
                name=member.get('name'),
                member_number=member.get('member_number'),
                demographics=member.get('demographics', {}),
            ))
        
        group = CachedGroup(
            group_id=group_id,
            group_name=group_name,
            members=members,
        )
        
        self._groups[group_id] = group
        self._touch(group_id)
        self._enforce_memory_limit()
        
        logger.info(
            f"Loaded group {group_name} ({group_id}) with {len(members)} members "
            f"({group.embedding_matrix.nbytes if group.embedding_matrix is not None else 0} bytes)"
        )
        return group
    
    def evict_group(self, group_id: str):
        """Remove a group from cache."""
        if group_id in self._groups:
            group_name = self._groups[group_id].group_name
            del self._groups[group_id]
            self._lru_order.remove(group_id)
            logger.info(f"Evicted group {group_name} ({group_id}) from cache")
    
    def get_group(self, group_id: str) -> Optional[CachedGroup]:
        """Get a cached group, updating LRU order."""
        group = self._groups.get(group_id)
        if group:
            self._touch(group_id)
        return group
    
    def get_all_loaded_groups(self) -> List[CachedGroup]:
        return list(self._groups.values())
    
    def compare_source_against_all_groups(
        self, 
        source_embedding: np.ndarray, 
        threshold: float,
        top_k: int = 1,
        exclude_uuids: Optional[set] = None,
    ) -> List[Dict]:
        """
        Compare a single source embedding against all cached group members.
        
        Args:
            source_embedding: Normalized 512-dim embedding of the source MVR
            threshold: Minimum cosine similarity (0-1)
            top_k: Max matches per group
            exclude_uuids: MVR UUIDs to skip (e.g., already matched)
            
        Returns:
            List of match dicts sorted by similarity descending
        """
        matches = []
        
        for group in self._groups.values():
            if group.embedding_matrix is None or len(group.members) == 0:
                continue
            
            # Batch cosine similarity: (N x 512) @ (512,) = (N,)
            similarities = group.embedding_matrix @ source_embedding
            
            # Find top-k above threshold
            above_threshold = similarities >= threshold
            if not np.any(above_threshold):
                continue
            
            # Get indices of matches above threshold, sorted by similarity descending
            threshold_indices = np.where(above_threshold)[0]
            threshold_scores = similarities[threshold_indices]
            sorted_local_indices = np.argsort(threshold_scores)[::-1][:top_k]
            
            for local_idx in sorted_local_indices:
                original_idx = threshold_indices[local_idx]
                member = group.members[original_idx]
                if exclude_uuids and member.mvr_people_uuid in exclude_uuids:
                    continue
                
                matches.append({
                    'group_id': group.group_id,
                    'group_name': group.group_name,
                    'matched_member_uuid': member.mvr_people_uuid,
                    'existing_member_name': member.name,
                    'group_member_number': member.member_number,
                    'similarity_score': float(similarities[original_idx]),
                    'source_mvr_uuid': None,   # Filled by caller
                    'source_camera_id': None,  # Filled by caller (multi-camera provenance)
                })
        
        matches.sort(key=lambda m: m['similarity_score'], reverse=True)
        return matches
    
    def compute_content_hash(self) -> str:
        """
        Compute a deterministic hash of current cache contents for change detection.
        
        Used by the background refresh queue to decide whether an atomic swap
        is needed (skip if unchanged).
        """
        hasher = hashlib.sha256()
        for group_id in sorted(self._groups.keys()):
            group = self._groups[group_id]
            member_uuids = sorted(m.mvr_people_uuid for m in group.members)
            hasher.update(f"{group_id}:{','.join(member_uuids)}".encode())
        return hasher.hexdigest()
    
    def clone_empty(self) -> 'EmbeddingCache':
        """Create a new empty cache with the same memory limit (for atomic swap)."""
        return EmbeddingCache(max_memory_bytes=self._max_memory_bytes)
    
    @property
    def memory_usage_bytes(self) -> int:
        """Estimate total memory used by cached embeddings."""
        total = 0
        for group in self._groups.values():
            if group.embedding_matrix is not None:
                total += group.embedding_matrix.nbytes
        return total
    
    @property
    def group_count(self) -> int:
        return len(self._groups)
    
    @property
    def group_ids(self) -> List[str]:
        return list(self._groups.keys())
    
    def clear(self):
        """Evict all groups."""
        group_ids = list(self._groups.keys())
        for gid in group_ids:
            self.evict_group(gid)
    
    def _touch(self, group_id: str):
        """Update LRU order for a group."""
        if group_id in self._lru_order:
            self._lru_order.remove(group_id)
        self._lru_order.append(group_id)
    
    def _enforce_memory_limit(self):
        """Evict least recently used groups until under memory limit."""
        while self.memory_usage_bytes > self._max_memory_bytes and self._lru_order:
            lru_group_id = self._lru_order[0]
            self.evict_group(lru_group_id)
```

#### 5.2.2 `VProfileMatchWorker`

```python
import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timezone

import httpx
import numpy as np
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.trigger import Trigger

logger = logging.getLogger(__name__)


class VProfileMatchWorker:
    """
    Manages in-memory MVR embedding comparison for vprofile_match triggers.
    
    Lifecycle:
    1. On trigger activation/creation: loads group embeddings into EmbeddingCache
    2. On each instant-detection event: extracts source MVR UUIDs from one or more
       cameras, fetches their embeddings from vmeta, and compares against cached groups
    3. Background refresh: periodically re-fetches group embeddings from vmeta DB
       on a separate asyncio queue, atomically swaps cache if changes detected
    4. On trigger deactivation/deletion: evicts from cache
    """
    
    def __init__(self, embedding_cache: EmbeddingCache):
        self.cache = embedding_cache
        self.vmeta_service_url = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")
        self._active_trigger_ids: Set[str] = set()
        self._batch_fetch_timeout = float(os.getenv("VPROFILE_BATCH_FETCH_TIMEOUT", "5.0"))
        self._refresh_interval = int(os.getenv("VPROFILE_CACHE_REFRESH_INTERVAL_SECONDS", "600"))
        self._refresh_task: Optional[asyncio.Task] = None
    
    # ------------------------------------------------------------------
    # Trigger Lifecycle
    # ------------------------------------------------------------------
    
    async def activate_trigger(self, trigger: Trigger):
        """
        Load all group embeddings for a vprofile_match trigger into memory.
        Called when a trigger is created, updated (group list changed), or toggled on.
        Starts the background refresh loop if this is the first active trigger.
        """
        group_ids_raw = getattr(trigger, 'ppl_match_group_ids', None)
        if not group_ids_raw:
            logger.warning(f"Trigger {trigger.uuid} has no ppl_match_group_ids")
            return
        
        try:
            group_ids = json.loads(group_ids_raw) if isinstance(group_ids_raw, str) else group_ids_raw
        except (json.JSONDecodeError, TypeError):
            logger.error(f"Invalid ppl_match_group_ids for trigger {trigger.uuid}: {group_ids_raw}")
            return
        
        if not group_ids:
            return
        
        # Load embeddings from vmeta
        async with httpx.AsyncClient(timeout=self._batch_fetch_timeout) as client:
            response = await client.post(
                f"{self.vmeta_service_url}/api/v1/individual-groups/multi-embedding-load",
                json={"group_ids": group_ids, "include_demographics": True},
            )
            
            if response.status_code != 200:
                logger.error(
                    f"Failed to load embeddings for trigger {trigger.uuid}: "
                    f"{response.status_code} {response.text[:200]}"
                )
                return
            
            data = response.json()
        
        # Populate cache
        groups_data = data.get('groups', {})
        for group_id, group_info in groups_data.items():
            self.cache.load_group(
                group_id=group_id,
                group_name=group_info.get('name', group_id),
                members_data=group_info.get('members', []),
            )
        
        self._active_trigger_ids.add(str(trigger.uuid))
        
        # Start refresh loop on first activation
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._refresh_loop())
        
        logger.info(
            f"Activated vprofile_match trigger {trigger.uuid} — "
            f"{len(group_ids)} groups, {self.cache.memory_usage_bytes:,} bytes in cache"
        )
    
    async def deactivate_trigger(self, trigger_uuid: str, group_ids: Optional[List[str]] = None):
        """
        Evict trigger's groups from cache.
        If group_ids not provided, evicts all groups that are not referenced by any other active trigger.
        Stops the refresh loop if no active triggers remain.
        """
        self._active_trigger_ids.discard(trigger_uuid)
        
        if group_ids:
            for gid in group_ids:
                # Only evict if no other active trigger references this group
                if not self._is_group_used_by_any_active_trigger(gid, exclude_trigger=trigger_uuid):
                    self.cache.evict_group(gid)
        
        # Stop refresh loop if no active triggers
        if not self._active_trigger_ids and self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            logger.info("Background refresh loop stopped — no active vprofile triggers")
    
    # ------------------------------------------------------------------
    # Evaluation (hot path — never blocks)
    # ------------------------------------------------------------------
    
    async def evaluate(
        self,
        trigger: Trigger,
        detection_data: Dict[str, Any],
        source_embedding_map: Dict[str, np.ndarray],
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        Evaluate a vprofile_match trigger against instant detection results.
        
        The detection_data includes source_camera_id and source_mvr_uuids.
        Match results include source_camera_id for downstream provenance.
        
        Args:
            trigger: The Trigger model instance
            detection_data: Raw Redis event data (includes camera_id as source_camera_id)
            source_embedding_map: {mvr_uuid: normalized_embedding} pre-fetched from vmeta
            
        Returns:
            (passed, reason, match_info)
        """
        threshold = float(getattr(trigger, 'ppl_match_similarity_threshold', 0.75) or 0.75)
        top_k = int(getattr(trigger, 'ppl_match_top_k', 1) or 1)
        negate = bool(getattr(trigger, 'ppl_match_negate', False))
        
        source_mvr_uuids = detection_data.get('source_mvr_uuids', [])
        source_camera_id = detection_data.get('camera_id')  # Track which camera detected this
        
        if not source_mvr_uuids:
            return False, "No source MVR UUIDs in detection data", None
        
        all_matches = []
        matched_members = set()
        
        for source_uuid in source_mvr_uuids:
            source_emb = source_embedding_map.get(source_uuid)
            if source_emb is None:
                continue
            
            matches = self.cache.compare_source_against_all_groups(
                source_embedding=source_emb,
                threshold=threshold,
                top_k=top_k,
                exclude_uuids=matched_members,
            )
            
            for match in matches:
                match['source_mvr_uuid'] = source_uuid
                match['source_camera_id'] = source_camera_id  # Multi-camera provenance
                matched_members.add(match['matched_member_uuid'])
            
            all_matches.extend(matches)
        
        all_matches.sort(key=lambda m: m['similarity_score'], reverse=True)
        
        if negate:
            # Negate mode: fire when NO members matched
            if len(all_matches) == 0:
                match_info = {
                    'group_ids': json.loads(getattr(trigger, 'ppl_match_group_ids', '[]') or '[]'),
                    'threshold': threshold,
                    'negated': True,
                    'total_candidates': len(source_mvr_uuids),
                    'matches_found': 0,
                    'source_camera_id': source_camera_id,
                    'best_match': None,
                }
                return True, f"No group members matched on camera {source_camera_id} (negate mode)", match_info
            else:
                return False, f"Negate mode: {len(all_matches)} match(es) found on camera {source_camera_id} — skipping fire", None
        else:
            # Normal mode: fire when at least one member matched
            if all_matches:
                best = all_matches[0]
                match_info = {
                    'group_ids': json.loads(getattr(trigger, 'ppl_match_group_ids', '[]') or '[]'),
                    'threshold': threshold,
                    'negated': False,
                    'total_candidates': len(source_mvr_uuids),
                    'matches_found': len(all_matches),
                    'source_camera_id': source_camera_id,  # Camera that detected the match
                    'top_k_results': all_matches[:top_k],
                    'best_match': best,
                }
                camera_label = source_camera_id or 'unknown camera'
                return True, f"Matched {best.get('existing_member_name') or best['matched_member_uuid']} on {camera_label} score={best['similarity_score']:.3f}", match_info
            else:
                return False, "No group members matched above threshold", None
    
    async def fetch_source_embeddings(self, source_mvr_uuids: List[str]) -> Dict[str, np.ndarray]:
        """
        Batch-fetch embeddings for a list of source MVR UUIDs from vmeta.
        
        Uses vmeta's existing MVR endpoint. Returns {mvr_uuid: normalized_embedding}.
        """
        if not source_mvr_uuids:
            return {}
        
        embedding_map = {}
        
        async with httpx.AsyncClient(timeout=self._batch_fetch_timeout) as client:
            for mvr_uuid in source_mvr_uuids:
                try:
                    response = await client.get(
                        f"{self.vmeta_service_url}/api/v1/mvr-people/{mvr_uuid}"
                    )
                    if response.status_code == 200:
                        data = response.json()
                        emb_raw = data.get('face_embedding')
                        if emb_raw:
                            emb = np.array(emb_raw, dtype=np.float32)
                            norm = np.linalg.norm(emb)
                            if norm > 0:
                                emb = emb / norm
                            embedding_map[mvr_uuid] = emb
                except Exception as e:
                    logger.warning(f"Failed to fetch embedding for {mvr_uuid}: {e}")
        
        return embedding_map
    
    # ------------------------------------------------------------------
    # Multi-Camera Support
    # ------------------------------------------------------------------
    
    def get_camera_device_ids(self, trigger: Trigger) -> List[str]:
        """
        Resolve the list of camera device IDs for a trigger.
        
        For vprofile_match triggers, uses camera_device_ids (JSON array).
        Falls back to the legacy camera_device_id (single scalar) if the array is empty.
        """
        camera_ids_raw = getattr(trigger, 'camera_device_ids', None)
        if camera_ids_raw:
            try:
                ids = json.loads(camera_ids_raw) if isinstance(camera_ids_raw, str) else camera_ids_raw
                if ids and isinstance(ids, list):
                    return ids
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Fallback to legacy single camera
        legacy_id = getattr(trigger, 'camera_device_id', None)
        if legacy_id:
            return [legacy_id]
        
        return []
    
    # ------------------------------------------------------------------
    # Background Cache Refresh Queue
    # ------------------------------------------------------------------
    
    async def start_refresh_loop(self):
        """Start the background cache refresh loop (idempotent)."""
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._refresh_loop())
            logger.info(
                f"Background refresh loop started (interval={self._refresh_interval}s)"
            )
    
    async def _refresh_loop(self):
        """
        Periodically refresh group embeddings from vmeta DB.
        
        Runs on a separate asyncio task. Never blocks the evaluation hot path.
        On failure, logs the error and retries on the next cycle — existing cache
        remains in place (graceful degradation).
        """
        while self._active_trigger_ids:
            try:
                await asyncio.sleep(self._refresh_interval)
                
                if not self._active_trigger_ids:
                    break
                
                await self._refresh_all_groups()
                
            except asyncio.CancelledError:
                logger.info("Background refresh loop cancelled")
                break
            except Exception:
                logger.exception(
                    "Background cache refresh failed — keeping existing cache. "
                    "Will retry in %ds.", self._refresh_interval
                )
    
    async def _refresh_all_groups(self):
        """
        Fetch fresh embeddings and atomically swap cache if changes detected.
        
        Steps:
        1. Compute content hash of current cache
        2. Build a new EmbeddingCache with fresh data from vmeta
        3. Compute content hash of new cache
        4. If hashes differ → atomic swap (single reference assignment)
        5. Log delta (members added/removed)
        """
        current_group_ids = self.cache.group_ids
        if not current_group_ids:
            return
        
        old_hash = self.cache.compute_content_hash()
        old_member_count = sum(len(g.members) for g in self.cache.get_all_loaded_groups())
        
        # Build new cache from fresh vmeta data
        new_cache = self.cache.clone_empty()
        
        async with httpx.AsyncClient(timeout=self._batch_fetch_timeout) as client:
            response = await client.post(
                f"{self.vmeta_service_url}/api/v1/individual-groups/multi-embedding-load",
                json={"group_ids": current_group_ids, "include_demographics": True},
            )
            
            if response.status_code != 200:
                logger.error(
                    f"Background refresh fetch failed: HTTP {response.status_code} — "
                    f"keeping existing cache"
                )
                return
            
            data = response.json()
            
            for gid, ginfo in data.get('groups', {}).items():
                new_cache.load_group(gid, ginfo['name'], ginfo['members'])
        
        new_hash = new_cache.compute_content_hash()
        
        if old_hash == new_hash:
            logger.debug(
                f"Background refresh skipped — no changes detected "
                f"({len(current_group_ids)} groups, {old_member_count} members)"
            )
            return
        
        new_member_count = sum(len(g.members) for g in new_cache.get_all_loaded_groups())
        diff = new_member_count - old_member_count
        
        # Atomic swap — single reference assignment (safe under GIL)
        self.cache = new_cache
        
        logger.info(
            f"🔄 Background cache refreshed: {old_member_count} → {new_member_count} "
            f"members (Δ={diff:+d}), {len(current_group_ids)} groups"
        )
    
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    
    def _is_group_used_by_any_active_trigger(self, group_id: str, exclude_trigger: str) -> bool:
        """Check if any active vprofile trigger (other than exclude_trigger) references this group."""
        db: Session = SessionLocal()
        try:
            triggers = db.query(Trigger).filter(
                Trigger.is_active == True,
                Trigger.trigger_mode == 'vprofile_match',
                Trigger.uuid != exclude_trigger,
            ).all()
            
            for trigger in triggers:
                group_ids_raw = getattr(trigger, 'ppl_match_group_ids', None)
                if group_ids_raw:
                    try:
                        ids = json.loads(group_ids_raw) if isinstance(group_ids_raw, str) else group_ids_raw
                        if group_id in ids:
                            return True
                    except (json.JSONDecodeError, TypeError):
                        pass
            return False
        finally:
            db.close()
    
    @property
    def active_trigger_count(self) -> int:
        return len(self._active_trigger_ids)
    
    @property
    def refresh_interval(self) -> int:
        return self._refresh_interval


# Module-level singleton
_worker: Optional[VProfileMatchWorker] = None


def get_vprofile_worker() -> VProfileMatchWorker:
    """Get or create the global VProfileMatchWorker singleton."""
    global _worker
    if _worker is None:
        max_memory = int(os.getenv("VPROFILE_CACHE_MAX_MEMORY_MB", "512")) * 1024 * 1024
        cache = EmbeddingCache(max_memory_bytes=max_memory)
        _worker = VProfileMatchWorker(embedding_cache=cache)
    return _worker
```

### 5.3 Integration into Existing `redis_subscriber.py`

In `InstantDetectionSubscriber._handle_instant_detection()`, add a new branch after the existing `ppl_match` evaluation (around line 405):

```python
# In _handle_instant_detection, after the ppl_match branch:
elif trigger_mode == "vprofile_match":
    logger.info("  🔎 Evaluating vprofile_match mode (in-memory, multi-camera)")
    worker = get_vprofile_worker()
    
    # Multi-camera filter: check if this event's camera is in the trigger's camera list
    event_camera_id = data.get('camera_id')
    allowed_cameras = worker.get_camera_device_ids(trigger)
    if allowed_cameras and event_camera_id not in allowed_cameras:
        logger.debug(f"  ⏭️ Camera {event_camera_id} not in trigger's camera list, skipping")
        continue
    
    # Fetch source embeddings
    source_mvr_uuids = self._extract_source_mvr_uuids(data)
    source_embedding_map = await worker.fetch_source_embeddings(source_mvr_uuids)
    
    if not source_embedding_map:
        logger.info("  ❌ SKIP: No source embeddings resolved")
        self._log_execution(db=db, trigger=trigger, passed=False,
                           reason="No source embeddings resolved",
                           match_info=None, detection_data=self._current_detection_data,
                           action_executed=False)
        continue
    
    passed, reason, match_info = await worker.evaluate(trigger, data, source_embedding_map)
    
    if not passed:
        logger.info(f"  ❌ SKIP: {reason}")
        self._log_execution(db=db, trigger=trigger, passed=False,
                           reason=reason, match_info=match_info,
                           detection_data=self._current_detection_data,
                           action_executed=False)
        continue
    
    logger.info(f"  ✅ vprofile_match MET: {reason}")
```

### 5.4 Trigger Lifecycle Hooks

In `ppl-meta-media/src/routes/triggers.py`, add hooks to the CRUD operations:

```python
# After creating a vprofile_match trigger:
if trigger.trigger_mode == 'vprofile_match' and trigger.is_active:
    worker = get_vprofile_worker()
    await worker.activate_trigger(trigger)

# After updating a vprofile_match trigger:
if trigger.trigger_mode == 'vprofile_match':
    worker = get_vprofile_worker()
    if trigger.is_active:
        await worker.activate_trigger(trigger)  # Reload (handles group/camera list changes)
    else:
        await worker.deactivate_trigger(str(trigger.uuid))

# After deleting a vprofile_match trigger:
if trigger.trigger_mode == 'vprofile_match':
    worker = get_vprofile_worker()
    group_ids = json.loads(trigger.ppl_match_group_ids or '[]')
    await worker.deactivate_trigger(str(trigger.uuid), group_ids=group_ids)
```

### 5.5 Group Membership Change Invalidation

When a group's members are modified externally (via vmeta group CRUD), the background refresh will pick up changes on the next cycle (within `_refresh_interval` seconds). For near-real-time invalidation:

```python
# In vmeta group member add/remove endpoints:
# After modifying group members, publish to Redis:
# PUBLISH "group-updated" {"group_id": "...", "action": "members_changed"}

# In VProfileMatchWorker, subscribe to this channel and trigger immediate refresh:
async def _group_updated_handler(self, message: Dict):
    group_id = message.get('group_id')
    if group_id and self._is_group_used_by_any_active_trigger(group_id):
        logger.info(f"Group {group_id} updated — triggering immediate cache refresh")
        await self._refresh_all_groups()
```

---

## 6. New VMeta Endpoint

### 6.1 `POST /api/v1/individual-groups/multi-embedding-load`

**File**: `ppl-meta-vmeta/src/api/routes/individual_groups.py`

Add after the existing camera-search endpoint (line 554):

```python
from models.individual_group import (
    # ... existing imports ...
    MultiEmbeddingLoadRequest,
    MultiEmbeddingLoadResponse,
)


@router.post("/multi-embedding-load", response_model=MultiEmbeddingLoadResponse)
async def load_multi_group_embeddings(
    request_body: MultiEmbeddingLoadRequest,
    manager: IndividualGroupsManager = Depends(get_groups_manager),
) -> MultiEmbeddingLoadResponse:
    """
    Load face embeddings for all members of multiple groups in a single call.
    
    Used by the VProfile Match Worker to pre-load embeddings into memory
    for fast in-memory comparison against instant detection results,
    and for periodic background cache refresh.
    
    Args:
        request_body: Group IDs to load + options
        
    Returns:
        Embedding data for all group members, organized by group
    """
    try:
        result = await manager.load_multi_group_embeddings(
            group_ids=request_body.group_ids,
            include_demographics=request_body.include_demographics,
        )
        return result
    except Exception as e:
        logger.error(f"Error loading multi-group embeddings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load group embeddings: {str(e)}"
        )
```

### 6.2 Request/Response Models

**File**: `ppl-meta-vmeta/src/models/individual_group.py`

```python
class MultiEmbeddingLoadRequest(BaseModel):
    group_ids: List[str] = Field(..., min_length=1, max_length=50)
    include_demographics: bool = Field(default=True)


class GroupMemberEmbedding(BaseModel):
    mvr_people_uuid: str
    face_embedding: List[float]  # 512-dimensional
    name: Optional[str] = None
    member_number: Optional[int] = None
    demographics: Optional[Dict[str, Any]] = None


class GroupEmbeddingData(BaseModel):
    name: str
    member_count: int
    members: List[GroupMemberEmbedding]


class MultiEmbeddingLoadResponse(BaseModel):
    groups: Dict[str, GroupEmbeddingData]
    total_members: int
    total_groups: int
```

### 6.3 Manager Method

**File**: `ppl-meta-vmeta/src/services/individual_groups_manager.py`

```python
async def load_multi_group_embeddings(
    self,
    group_ids: List[str],
    include_demographics: bool = True,
) -> Dict[str, Any]:
    """
    Load embeddings for all members across multiple groups in a single DB query.
    
    Returns data structured for the MultiEmbeddingLoadResponse.
    """
    if not group_ids:
        return {"groups": {}, "total_members": 0, "total_groups": 0}
    
    result = {"groups": {}, "total_members": 0}
    
    async with self.db.pool.acquire() as conn:
        # Single query joining group_membership + mvr_people
        # Uses pgvector's face_embedding column cast to text for JSON serialization
        query = """
            SELECT 
                gm.group_id,
                ig.name as group_name,
                mp.mvr_people_uuid,
                mp.face_embedding::text as face_embedding_text,
                mp.name as member_name,
                gm.member_number,
                mp.age_estimate,
                mp.gender_estimate
            FROM group_membership gm
            JOIN individual_groups ig ON gm.group_id = ig.id
            JOIN mvr_people mp ON gm.mvr_people_uuid = mp.mvr_people_uuid
            WHERE gm.group_id = ANY($1::text[])
              AND mp.face_embedding IS NOT NULL
            ORDER BY gm.group_id, gm.member_number
        """
        
        rows = await conn.fetch(query, group_ids)
        
        # Group results by group_id
        group_members: Dict[str, List[Dict]] = {}
        group_names: Dict[str, str] = {}
        
        for row in rows:
            gid = str(row['group_id'])
            group_names[gid] = row['group_name'] or gid
            
            # Parse pgvector text format: '[0.1,0.2,...]'
            emb_text = row['face_embedding_text']
            embedding = [float(x) for x in emb_text.strip('[]').split(',')]
            
            member = {
                'mvr_people_uuid': str(row['mvr_people_uuid']),
                'face_embedding': embedding,
                'name': row['member_name'],
                'member_number': row['member_number'],
            }
            
            if include_demographics:
                member['demographics'] = {
                    'age': row['age_estimate'],
                    'gender': row['gender_estimate'],
                }
            
            group_members.setdefault(gid, []).append(member)
        
        total_members = 0
        for gid in group_ids:
            members = group_members.get(gid, [])
            total_members += len(members)
            result['groups'][gid] = {
                'name': group_names.get(gid, gid),
                'member_count': len(members),
                'members': members,
            }
        
        result['total_members'] = total_members
        result['total_groups'] = len(group_ids)
    
    return result
```

---

## 7. Frontend Changes

### 7.1 Trigger Model

**File**: `ppl-meta-frontend/lib/models/trigger_model.dart`

Add new fields to `TriggerModel`:

```dart
@JsonKey(name: 'ppl_match_group_ids')
final List<String>? pplMatchGroupIds;

@JsonKey(name: 'camera_device_ids')
final List<String>? cameraDeviceIds;

@JsonKey(name: 'trigger_mode')
final String triggerMode;  // Add 'vprofile_match' to default
```

Add to `TriggerCreateRequest`:

```dart
@JsonKey(name: 'ppl_match_group_ids')
final List<String>? pplMatchGroupIds;

@JsonKey(name: 'camera_device_ids')
final List<String>? cameraDeviceIds;
```

Update `conditionsDisplay`:

```dart
String get conditionsDisplay {
  if (triggerMode == 'vprofile_match') {
    final groupCount = pplMatchGroupIds?.length ?? 0;
    final cameraCount = cameraDeviceIds?.length ?? 0;
    return 'VProfile: $groupCount group(s), $cameraCount camera(s)';
  }
  if (triggerMode == 'ppl_match') {
    return 'Group: ${pplMatchGroupId ?? 'Not set'}';
  }
  // ... existing modes
}
```

### 7.2 Trigger Creation/Edit UI

**File**: `ppl-meta-frontend/lib/widgets/triggers_tab.dart`

Add a new trigger mode option in the creation dialog:

```dart
// In the trigger mode dropdown:
DropdownMenuItem(
  value: 'vprofile_match',
  child: Row(
    children: [
      Icon(Icons.people_outline, size: 18),
      SizedBox(width: 8),
      Text('VProfile Match (Multi-Group, Multi-Camera)'),
    ],
  ),
),
```

When `vprofile_match` is selected, show two multi-select pickers:

```dart
// Multi-camera picker
if (triggerMode == 'vprofile_match') {
  return Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      // Camera selection
      Text('Select Cameras:', style: TextStyle(fontWeight: FontWeight.bold)),
      SizedBox(height: 8),
      Wrap(
        spacing: 8,
        children: cameras.map((camera) =>
          FilterChip(
            label: Text(camera.name ?? camera.deviceId),
            selected: selectedCameraIds.contains(camera.deviceId),
            onSelected: (selected) {
              setState(() {
                if (selected) {
                  selectedCameraIds.add(camera.deviceId);
                } else {
                  selectedCameraIds.remove(camera.deviceId);
                }
              });
            },
          ),
        ).toList(),
      ),
      SizedBox(height: 16),
      
      // Group selection
      Text('Select Groups:', style: TextStyle(fontWeight: FontWeight.bold)),
      SizedBox(height: 8),
      Wrap(
        spacing: 8,
        children: _availableGroups.map((group) =>
          FilterChip(
            label: Text(group.name),
            selected: selectedGroupIds.contains(group.id),
            onSelected: (selected) {
              setState(() {
                if (selected) {
                  selectedGroupIds.add(group.id);
                } else {
                  selectedGroupIds.remove(group.id);
                }
              });
            },
          ),
        ).toList(),
      ),
    ],
  );
}
```

### 7.3 Generated Code

After model changes, run:

```bash
cd ppl-meta-frontend
flutter pub run build_runner build --delete-conflicting-outputs
```

---

## 8. Memory Management

### 8.1 Cache Lifecycle

| Event | Action |
|---|---|
| Trigger created (active, vprofile_match) | `worker.activate_trigger(trigger)` — loads all groups |
| Trigger updated (group/camera list changed, active) | `worker.activate_trigger(trigger)` — reloads (handles adds/removals) |
| Trigger toggled off | `worker.deactivate_trigger(uuid, group_ids)` |
| Trigger deleted | `worker.deactivate_trigger(uuid, group_ids)` |
| Background refresh timer fires | `_refresh_all_groups()` — fetches fresh data, atomic swap if changed |
| Group member added/removed (external edit) | Redis pub/sub "group-updated" → immediate refresh; fallback: next periodic cycle |
| Memory limit exceeded | LRU eviction of least recently used groups |

### 8.2 Background Cache Refresh (Separate Queue)

The background refresh runs on a **separate asyncio task** and **never blocks the evaluation hot path**:

1. **Isolation**: Evaluations read from `self.cache` (O(1) reference read). The refresh builds a completely new `EmbeddingCache` instance in the background.
2. **Atomic swap**: When the new cache is ready, `self.cache = new_cache` is a single Python assignment (atomic under GIL). No locks, no mutexes, no contention.
3. **Change detection**: Before swapping, `compute_content_hash()` compares old and new cache contents. If identical (no group membership changes), the swap is skipped entirely.
4. **Graceful degradation**: If the refresh HTTP call fails (vmeta down, network issue), the existing cache stays in place and a warning is logged. The next cycle will retry.
5. **Configurable interval**: Controlled by `VPROFILE_CACHE_REFRESH_INTERVAL_SECONDS` (default: 600 = 10 minutes).

```
  Evaluation Path (hot, <1ms)         Background Refresh (cold, ~200ms)
  ═══════════════════════════         ═══════════════════════════════════
  source_embedding →                  asyncio.sleep(refresh_interval)
  self.cache.compare() →              ↓
  fire trigger                        POST vmeta /multi-embedding-load
                                      ↓
  (reads current cache reference)     build new EmbeddingCache
                                      ↓
                                      compute_content_hash()
                                      ↓
                                      if old_hash != new_hash:
                                          self.cache = new_cache  ← atomic swap
```

### 8.3 Memory Estimation

- Single 512-dim float32 embedding: 512 × 4 bytes = **2 KB**
- Group of 10 members: **20 KB**
- 50 groups of 10 members each: **1 MB**
- 500 groups: **10 MB**

The default 512 MB limit supports ~25,000 groups with 10 members each — well above expected usage.

### 8.4 Configuration (Environment Variables)

```bash
# ppl-meta-media .env
VPROFILE_CACHE_MAX_MEMORY_MB=512              # Max cache size in MB
VPROFILE_BATCH_FETCH_TIMEOUT=5.0               # vmeta fetch timeout in seconds
VPROFILE_SOURCE_EMBEDDING_FETCH_TIMEOUT=2.0    # Per-MVR fetch timeout
VPROFILE_CACHE_REFRESH_INTERVAL_SECONDS=600    # Background cache refresh interval (default 10 min)
```

---

## 9. Testing Plan

### 9.1 Unit Tests

**File**: `ppl-meta-media/tests/test_vprofile_match.py`

| Test | Description |
|---|---|
| `test_embedding_cache_load_and_retrieve` | Load a group, verify members and embedding matrix shape |
| `test_embedding_cache_cosine_similarity` | Compare a known-similar embedding, verify score > 0.9 |
| `test_embedding_cache_threshold_filtering` | Low threshold includes, high threshold excludes |
| `test_embedding_cache_lru_eviction` | Exceed memory limit, verify oldest groups evicted |
| `test_embedding_cache_clear` | Verify all groups removed |
| `test_embedding_cache_content_hash` | Verify identical content produces same hash, changed content different hash |
| `test_embedding_cache_clone_empty` | Verify clone creates independent empty cache with same memory limit |
| `test_vprofile_match_evaluate_match` | Source embedding matches group member → passed=True |
| `test_vprofile_match_evaluate_no_match` | Random source embedding → passed=False |
| `test_vprofile_match_evaluate_negate` | Negate mode: match present → skip; no match → fire |
| `test_vprofile_match_evaluate_top_k` | Verify only top_k results returned |
| `test_vprofile_match_source_camera_id` | Verify match results include source_camera_id from detection data |
| `test_vprofile_match_multi_camera_filter` | Event from allowed camera passes; event from disallowed camera skipped |
| `test_background_refresh_no_change` | Identical content → no swap, log "skipped" |
| `test_background_refresh_with_change` | Changed member list → atomic swap, log delta |
| `test_background_refresh_atomic_swap` | Verify evaluations continue reading old cache during refresh build |
| `test_multi_group_embedding_load` | Verify vmeta endpoint returns correct structure |

### 9.2 Integration Tests

| Test | Description |
|---|---|
| `test_full_pipeline_single_camera` | Create trigger → load embeddings → simulate Redis event → verify evaluation |
| `test_full_pipeline_multi_camera` | Create trigger with 3 cameras → events from each → verify all fire with correct source_camera_id |
| `test_trigger_lifecycle` | Create → activate → deactivate → verify cache eviction + refresh loop stops |
| `test_group_update_invalidation` | Update group members → verify cache reloaded on next refresh cycle |
| `test_concurrent_evaluations` | Multiple triggers, concurrent evaluations from different cameras |

### 9.3 Performance Benchmarks

| Benchmark | Target |
|---|---|
| Single embedding cosine similarity (512-dim) | < 10 μs |
| 10,000 embeddings comparison | < 10 ms |
| Group load from vmeta (10 groups, 100 members) | < 500 ms |
| Background refresh cycle (no changes) | < 200 ms (including HTTP) |
| End-to-end evaluation latency (Redis event → match result) | < 50 ms |
| Cache atomic swap duration | < 1 μs (single reference assignment) |

---

## 10. Migration & Rollout

### 10.1 Database Migration

```bash
cd ppl-meta-media
alembic revision -m "add_vprofile_match_fields"
# Edit the generated migration file with the SQL from Section 4.1
alembic upgrade head
```

### 10.2 Backward Compatibility

- Existing `ppl_match`, `search`, `search_demographic`, and `demographic` triggers are unaffected
- New `ppl_match_group_ids` and `camera_device_ids` columns are nullable — existing rows remain `NULL`
- Frontend model adds optional fields with sensible defaults
- Legacy `camera_device_id` single-camera field still works as fallback
- New trigger mode is opt-in via the UI

### 10.3 Rollout Steps

1. **Phase 1**: Deploy vmeta `multi-embedding-load` endpoint
2. **Phase 2**: Deploy media service with `VProfileMatchWorker` and background refresh (feature-flagged off)
3. **Phase 3**: Deploy frontend with vprofile UI including multi-camera/group pickers (hidden behind feature flag)
4. **Phase 4**: Enable feature flag, smoke test with single trigger, single camera
5. **Phase 5**: Test multi-camera, multi-group scenarios
6. **Phase 6**: Full rollout

### 10.4 Feature Flag

```python
# ppl-meta-media .env
VPROFILE_MATCH_ENABLED=true
```

---

## 11. OpenAPI Contract

### 11.1 New Endpoint: Multi Embedding Load

```yaml
post:
  summary: Load multi-group embeddings
  operationId: loadMultiGroupEmbeddings
  tags: [individual-groups]
  requestBody:
    required: true
    content:
      application/json:
        schema:
          type: object
          required: [group_ids]
          properties:
            group_ids:
              type: array
              items:
                type: string
              minItems: 1
              maxItems: 50
              description: List of individual group IDs
            include_demographics:
              type: boolean
              default: true
  responses:
    '200':
      description: Embeddings loaded successfully
      content:
        application/json:
          schema:
            type: object
            properties:
              groups:
                type: object
                additionalProperties:
                  type: object
                  properties:
                    name:
                      type: string
                    member_count:
                      type: integer
                    members:
                      type: array
                      items:
                        type: object
                        properties:
                          mvr_people_uuid:
                            type: string
                          face_embedding:
                            type: array
                            items:
                              type: number
                            minItems: 512
                            maxItems: 512
                          name:
                            type: string
                            nullable: true
                          member_number:
                            type: integer
                            nullable: true
                          demographics:
                            type: object
                            nullable: true
              total_members:
                type: integer
              total_groups:
                type: integer
    '500':
      description: Server error
```

---

## 12. Summary of Files Changed

### New Files
1. `ppl-meta-media/src/services/vprofile_match_worker.py` — EmbeddingCache + VProfileMatchWorker + BackgroundRefreshQueue
2. `ppl-meta-media/migrations/versions/XXX_add_vprofile_match_fields.py` — DB migration (2 new columns)
3. `docs/proposals/vprofile-match-trigger-implementation-plan.md` — This document

### Modified Files
4. `ppl-meta-media/src/models/trigger.py` — Add `ppl_match_group_ids` + `camera_device_ids` columns
5. `ppl-meta-media/src/services/redis_subscriber.py` — Add `vprofile_match` evaluation branch with multi-camera filter and source_camera_id
6. `ppl-meta-media/src/routes/triggers.py` — Add lifecycle hooks (create/update/delete) + group change invalidation
7. `ppl-meta-media/src/schemas/trigger.py` — Add vprofile fields to Pydantic schemas
8. `ppl-meta-vmeta/src/api/routes/individual_groups.py` — New `multi-embedding-load` endpoint
9. `ppl-meta-vmeta/src/services/individual_groups_manager.py` — `load_multi_group_embeddings()` method
10. `ppl-meta-vmeta/src/models/individual_group.py` — New request/response models
11. `ppl-meta-frontend/lib/models/trigger_model.dart` — Add vprofile fields (groups + cameras)
12. `ppl-meta-frontend/lib/widgets/triggers_tab.dart` — Multi-select group picker + multi-select camera picker UI
13. `ppl-meta-media/src/main.py` or equivalent — Initialize VProfileMatchWorker + start refresh loop on startup

---

## Appendix A: Comparison with Existing Approaches

| Feature | `ppl_match` (instant) | `search` (historical) | `vprofile_match` (NEW) |
|---|---|---|---|
| Data source | Redis event MVR UUIDs | Stored video MVRs | Redis event MVR UUIDs |
| Camera count | Single | Single (via camera_ids) | **Multiple** (camera_device_ids JSON array) |
| Group count | Single | Single | **Multiple** (ppl_match_group_ids JSON array) |
| Match provenance | No camera info | Camera from query | **source_camera_id** in every match result |
| Embedding cache | None (DB per eval) | None (DB per eval) | **In-memory (load once, periodic refresh)** |
| Embedding freshness | Always fresh (DB per eval) | Always fresh (DB per eval) | **Background refresh every N minutes** (configurable, default 10 min) |
| Comparison target | Group members in DB | Group members in DB | **Cached group members** |
| vmeta endpoint used | `POST /{group_id}/check-duplicates` | `POST /{group_id}/camera-search` | **`POST /multi-embedding-load`** + `GET /mvr-people/{uuid}` |
| Latency profile | HTTP POST + DB query | HTTP POST + Media query + DB | **HTTP batch (load/refresh) + in-memory (eval)** |
| Use case | Real-time person recognition | Historical footage search | **Real-time multi-group, multi-camera recognition** |

## Appendix B: Key Design Decisions

1. **Normalized embeddings**: All embeddings are L2-normalized at load time, making cosine similarity a simple dot product (`emb @ source_emb`).

2. **Batch matrix comparison**: Instead of comparing each source embedding against each group member one-by-one, the `CachedGroup.embedding_matrix` (N×512) enables a single matrix-vector multiplication per source.

3. **Separate source embedding fetch**: Source MVR embeddings from instant detection are fetched on-demand from vmeta (not cached), since the set of active MVRs changes with every detection cycle.

4. **Background refresh with atomic swap**: The refresh builds a completely new cache instance on a separate asyncio task. The swap is a single reference assignment — no locks, no contention with the evaluation hot path. Content hashing prevents unnecessary swaps when nothing changed.

5. **Multi-camera provenance**: Every match result includes `source_camera_id` so downstream actions (notifications, signage, webhooks) know which camera detected the person. This enables scenarios like "show matched person on the nearest signage display."

6. **Singleton worker pattern**: A single `VProfileMatchWorker` instance manages all vprofile triggers, ensuring shared embedding cache and preventing duplicate loads of the same group across triggers.

7. **Graceful degradation**: If the background refresh or source embedding fetch fails, the existing cache remains in place. The system never degrades to a broken state — it continues evaluating with the last-known-good embeddings.