"""
VProfile Match Worker

Manages in-memory MVR embedding comparison for vprofile_match triggers.

Provides:
- EmbeddingCache: In-memory LRU cache of group member face embeddings
- VProfileMatchWorker: Lifecycle management, evaluation, multi-camera support,
  and periodic background cache refresh
"""

import asyncio
import os
import time
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx
import numpy as np
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.trigger import Trigger

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


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
    embedding_matrix: Optional[np.ndarray] = None  # Pre-computed Nx512 matrix

    def __post_init__(self):
        if self.members:
            self.embedding_matrix = np.stack([m.embedding for m in self.members])


# ---------------------------------------------------------------------------
# EmbeddingCache
# ---------------------------------------------------------------------------


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

    # --- Public API ---------------------------------------------------------

    def load_group(self, group_id: str, group_name: str, members_data: List[Dict]) -> CachedGroup:
        """Load a group's member embeddings into cache."""
        members = []
        for member in members_data:
            embedding = np.array(member['face_embedding'], dtype=np.float32)
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

        matrix_bytes = group.embedding_matrix.nbytes if group.embedding_matrix is not None else 0
        matrix_shape = group.embedding_matrix.shape if group.embedding_matrix is not None else (0,)
        logger.info(
            "Loaded group %s (%s) with %d members (%d bytes, shape=%s)",
            group_name, group_id, len(members), matrix_bytes, matrix_shape,
        )
        return group

    def evict_group(self, group_id: str):
        """Remove a group from cache."""
        if group_id in self._groups:
            group_name = self._groups[group_id].group_name
            del self._groups[group_id]
            self._lru_order.remove(group_id)
            logger.info("Evicted group %s (%s) from cache", group_name, group_id)

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
            exclude_uuids: MVR UUIDs to skip

        Returns:
            List of match dicts sorted by similarity descending.
            Each dict has: group_id, group_name, matched_member_uuid,
            existing_member_name, group_member_number, similarity_score,
            source_mvr_uuid (None, filled by caller), source_camera_id (None).
        """
        matches = []

        for group in self._groups.values():
            if group.embedding_matrix is None or len(group.members) == 0:
                continue

            # Batch cosine similarity: (N x 512) @ (512,) = (N,)
            logger.info("  🔬 cache_shape=%s source_shape=%s", 
                       group.embedding_matrix.shape, source_embedding.shape)
            similarities = group.embedding_matrix @ source_embedding

            # Debug: log all scores
            top_scores = sorted([(float(similarities[i]), group.members[i].mvr_people_uuid[:12], group.members[i].name) 
                                 for i in range(len(similarities))], reverse=True)
            logger.info("  🔬 vs group %s (%s): top scores=%s", group.group_name, group.group_id[:12], 
                       [(f"{s:.4f}", n or u) for s, u, n in top_scores[:3]])

            # Find top-k above threshold
            above_threshold = similarities >= threshold
            if not np.any(above_threshold):
                continue

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
                    'source_mvr_uuid': None,
                    'source_camera_id': None,
                })

        matches.sort(key=lambda m: m['similarity_score'], reverse=True)
        return matches

    def compute_content_hash(self) -> str:
        """
        Compute a deterministic hash of current cache contents.

        Used by the background refresh to decide whether an atomic swap is needed.
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

    # --- Properties ---------------------------------------------------------

    @property
    def memory_usage_bytes(self) -> int:
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

    # --- Internal -----------------------------------------------------------

    def _touch(self, group_id: str):
        if group_id in self._lru_order:
            self._lru_order.remove(group_id)
        self._lru_order.append(group_id)

    def _enforce_memory_limit(self):
        while self.memory_usage_bytes > self._max_memory_bytes and self._lru_order:
            lru_group_id = self._lru_order[0]
            self.evict_group(lru_group_id)


# ---------------------------------------------------------------------------
# VProfileMatchWorker
# ---------------------------------------------------------------------------


class VProfileMatchWorker:
    """
    Manages in-memory MVR embedding comparison for vprofile_match triggers.

    Lifecycle:
    1. On trigger activation/creation: loads group embeddings into cache
    2. On each instant-detection event: extracts source MVR UUIDs from one or
       more cameras, fetches their embeddings from vmeta, and compares against
       cached groups
    3. Background refresh: periodically re-fetches group embeddings from vmeta
       DB on a separate asyncio queue; atomically swaps cache if changes detected
    4. On trigger deactivation/deletion: evicts from cache
    """

    def __init__(self, embedding_cache: EmbeddingCache):
        self.cache = embedding_cache
        self.vmeta_service_url = os.getenv("VMETA_SERVICE_URL", "http://localhost:8008")
        self._active_trigger_ids: Set[str] = set()
        self._batch_fetch_timeout = float(os.getenv("VPROFILE_BATCH_FETCH_TIMEOUT", "5.0"))
        self._refresh_interval = int(os.getenv("VPROFILE_CACHE_REFRESH_INTERVAL_SECONDS", "600"))
        self._refresh_task: Optional[asyncio.Task] = None

        # Auth token for vmeta calls (cached, same pattern as SearchTriggerScheduler)
        self._auth_token: Optional[str] = None
        self._auth_token_expiry: float = 0.0

    # ------------------------------------------------------------------
    # Startup Auto-Load
    # ------------------------------------------------------------------

    async def load_all_active_triggers(self):
        """
        Load group embeddings for all active vprofile_match triggers at startup.
        
        Called during service initialization to restore in-memory caches
        that were wiped when the process restarted.
        """
        db: Session = SessionLocal()
        try:
            triggers = db.query(Trigger).filter(
                Trigger.is_active == True,
                Trigger.trigger_mode == 'vprofile_match',
            ).all()

            if not triggers:
                logger.info("No active vprofile_match triggers to restore on startup")
                return

            logger.info("Restoring %d active vprofile_match trigger(s) on startup", len(triggers))
            for trigger in triggers:
                try:
                    await self.activate_trigger(trigger)
                except Exception as e:
                    logger.error(
                        "Failed to restore vprofile trigger %s on startup: %s",
                        trigger.uuid, e,
                    )
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Trigger Lifecycle
    # ------------------------------------------------------------------

    async def activate_trigger(self, trigger: Trigger):
        """
        Load all group embeddings for a vprofile_match trigger into memory.
        Starts the background refresh loop if this is the first active trigger.
        """
        group_ids_raw = getattr(trigger, 'ppl_match_group_ids', None)
        if not group_ids_raw:
            logger.warning("Trigger %s has no ppl_match_group_ids", trigger.uuid)
            return

        try:
            group_ids = json.loads(group_ids_raw) if isinstance(group_ids_raw, str) else group_ids_raw
        except (json.JSONDecodeError, TypeError):
            logger.error("Invalid ppl_match_group_ids for trigger %s: %s", trigger.uuid, group_ids_raw)
            return

        if not group_ids:
            return

        auth_token = await self._get_auth_token()
        headers = {"Authorization": auth_token} if auth_token else {}

        async with httpx.AsyncClient(timeout=self._batch_fetch_timeout) as client:
            response = await client.post(
                f"{self.vmeta_service_url}/api/v1/individual-groups/multi-embedding-load",
                json={"group_ids": group_ids, "include_demographics": True},
                headers=headers,
            )

            if response.status_code != 200:
                logger.error(
                    "Failed to load embeddings for trigger %s: %d %s",
                    trigger.uuid, response.status_code, response.text[:200],
                )
                return

            data = response.json()

        groups_data = data.get('groups', {})
        for group_id, group_info in groups_data.items():
            self.cache.load_group(
                group_id=group_id,
                group_name=group_info.get('name', group_id),
                members_data=group_info.get('members', []),
            )

        self._active_trigger_ids.add(str(trigger.uuid))

        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._refresh_loop())

        logger.info(
            "Activated vprofile_match trigger %s — %d groups, %d bytes in cache",
            trigger.uuid, len(group_ids), self.cache.memory_usage_bytes,
        )

    async def deactivate_trigger(self, trigger_uuid: str, group_ids: Optional[List[str]] = None):
        """
        Evict trigger's groups from cache.
        Stops the refresh loop if no active triggers remain.
        """
        self._active_trigger_ids.discard(trigger_uuid)

        if group_ids:
            for gid in group_ids:
                if not self._is_group_used_by_any_active_trigger(gid, exclude_trigger=trigger_uuid):
                    self.cache.evict_group(gid)

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

        Returns:
            (passed: bool, reason: str, match_info: Optional[dict])
        """
        threshold = float(getattr(trigger, 'ppl_match_similarity_threshold', 0.75) or 0.75)
        top_k = int(getattr(trigger, 'ppl_match_top_k', 1) or 1)
        negate = bool(getattr(trigger, 'ppl_match_negate', False))

        source_mvr_uuids = detection_data.get('source_mvr_uuids', [])
        source_camera_id = detection_data.get('camera_id')

        if not source_mvr_uuids:
            return False, "No source MVR UUIDs in detection data", None

        all_matches = []
        matched_members = set()

        for source_uuid in source_mvr_uuids:
            source_emb = source_embedding_map.get(source_uuid)
            if source_emb is None:
                logger.info("  🔬 Source uuid %s not in embedding map (keys=%s)", source_uuid[:12], list(source_embedding_map.keys())[:3] if source_embedding_map else [])
                continue

            logger.info("  🔬 source_shape=%s, cache_groups=%d", source_emb.shape, self.cache.group_count)
            matches = self.cache.compare_source_against_all_groups(
                source_embedding=source_emb,
                threshold=threshold,
                top_k=top_k,
                exclude_uuids=matched_members,
            )

            if matches:
                logger.info("  🔬 Source %s: %d matches above %.2f", source_uuid[:12], len(matches), threshold)
                for m in matches[:3]:
                    logger.info("    → %s (score=%.4f)", m.get('existing_member_name') or m['matched_member_uuid'][:12], m['similarity_score'])
            else:
                logger.info("  🔬 Source %s: 0 matches above %.2f", source_uuid[:12], threshold)

            for match in matches:
                match['source_mvr_uuid'] = source_uuid
                match['source_camera_id'] = source_camera_id
                matched_members.add(match['matched_member_uuid'])

            all_matches.extend(matches)

        all_matches.sort(key=lambda m: m['similarity_score'], reverse=True)

        group_ids_raw = getattr(trigger, 'ppl_match_group_ids', '[]')
        try:
            group_ids_list = json.loads(group_ids_raw) if isinstance(group_ids_raw, str) else (group_ids_raw or [])
        except (json.JSONDecodeError, TypeError):
            group_ids_list = []

        if negate:
            if len(all_matches) == 0:
                match_info = {
                    'group_ids': group_ids_list,
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

        # Normal mode
        if all_matches:
            best = all_matches[0]
            match_info = {
                'group_ids': group_ids_list,
                'threshold': threshold,
                'negated': False,
                'total_candidates': len(source_mvr_uuids),
                'matches_found': len(all_matches),
                'source_camera_id': source_camera_id,
                'top_k_results': all_matches[:top_k],
                'best_match': best,
            }
            camera_label = source_camera_id or 'unknown camera'
            member_label = best.get('existing_member_name') or best['matched_member_uuid']
            return True, f"Matched {member_label} on {camera_label} score={best['similarity_score']:.3f}", match_info

        return False, "No group members matched above threshold", None

    async def _get_auth_token(self) -> Optional[str]:
        """Get an auth token for inter-service calls. Cached until expiry."""
        now = time.monotonic()
        if self._auth_token and now < self._auth_token_expiry:
            return self._auth_token

        node_service_url = os.getenv("NODE_SERVICE_URL", "http://localhost:8001")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{node_service_url}/api/v1/users/login",
                    data={
                        "username": os.getenv("SERVICE_USERNAME", "fresh.user@example.com"),
                        "password": os.getenv("SERVICE_PASSWORD", "NewPassword234!"),
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if resp.status_code == 200:
                    token = resp.json().get("access_token")
                    self._auth_token = f"Bearer {token}"
                    self._auth_token_expiry = now + 3500  # ~1 hour
                    return self._auth_token
        except Exception:
            logger.exception("Failed to obtain auth token for vprofile worker")
        return None

    async def fetch_source_embeddings(self, source_mvr_uuids: List[str]) -> Dict[str, np.ndarray]:
        """
        Resolve source UUIDs to embeddings via vmeta's resolve-embeddings endpoint.
        
        The endpoint intelligently resolves each UUID through:
        1. Direct MVR lookup in mvr_people
        2. individual_mvr_mapping → mvr_people
        3. individual_video_appearances → individual_mvr_mapping → mvr_people
        
        Returns {original_uuid: normalized_embedding}.
        """
        if not source_mvr_uuids:
            return {}

        auth_token = await self._get_auth_token()
        headers = {"Authorization": auth_token} if auth_token else {}
        headers["Content-Type"] = "application/json"

        embedding_map = {}

        try:
            async with httpx.AsyncClient(timeout=self._batch_fetch_timeout) as client:
                response = await client.post(
                    f"{self.vmeta_service_url}/api/v1/individual-groups/resolve-embeddings",
                    json={"uuids": source_mvr_uuids},
                    headers=headers,
                )
                
                if response.status_code != 200:
                    logger.warning(
                        "resolve-embeddings returned %d: %s",
                        response.status_code, response.text[:200],
                    )
                    return {}
                
                data = response.json()
                embeddings_data = data.get("embeddings", {})
                
                for uuid_str, emb_list in embeddings_data.items():
                    if emb_list and isinstance(emb_list, list):
                        emb = np.array(emb_list, dtype=np.float32)
                        norm = np.linalg.norm(emb)
                        if norm > 0:
                            emb = emb / norm
                        embedding_map[uuid_str] = emb
                
                logger.info("  🔬 Resolved %d/%d source embeddings", len(embedding_map), len(source_mvr_uuids))
        except Exception as e:
            logger.warning("Failed to resolve embeddings: %s", e)

        return embedding_map

    # ------------------------------------------------------------------
    # Multi-Camera Support
    # ------------------------------------------------------------------

    def get_camera_device_ids(self, trigger: Trigger) -> List[str]:
        """
        Resolve the list of camera device IDs for a trigger.
        For vprofile_match triggers, uses camera_device_ids (JSON array).
        Falls back to legacy camera_device_id if the array is empty.
        """
        camera_ids_raw = getattr(trigger, 'camera_device_ids', None)
        if camera_ids_raw:
            try:
                ids = json.loads(camera_ids_raw) if isinstance(camera_ids_raw, str) else camera_ids_raw
                if ids and isinstance(ids, list):
                    return ids
            except (json.JSONDecodeError, TypeError):
                pass

        legacy_id = getattr(trigger, 'camera_device_id', None)
        if legacy_id:
            return [legacy_id]

        return []

    # ------------------------------------------------------------------
    # Background Cache Refresh
    # ------------------------------------------------------------------

    async def start_refresh_loop(self):
        """Start the background cache refresh loop (idempotent)."""
        if self._refresh_task is None or self._refresh_task.done():
            self._refresh_task = asyncio.create_task(self._refresh_loop())
            logger.info("Background refresh loop started (interval=%ds)", self._refresh_interval)

    async def _refresh_loop(self):
        """
        Periodically refresh group embeddings from vmeta DB.

        Runs on a separate asyncio task. Never blocks evaluation.
        On failure, keeps existing cache (graceful degradation).
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
                    "Will retry in %ds.", self._refresh_interval,
                )

    async def _refresh_all_groups(self):
        """
        Fetch fresh embeddings and atomically swap cache if changes detected.
        """
        current_group_ids = self.cache.group_ids
        if not current_group_ids:
            return

        old_hash = self.cache.compute_content_hash()
        old_member_count = sum(len(g.members) for g in self.cache.get_all_loaded_groups())

        new_cache = self.cache.clone_empty()

        auth_token = await self._get_auth_token()
        headers = {"Authorization": auth_token} if auth_token else {}

        async with httpx.AsyncClient(timeout=self._batch_fetch_timeout) as client:
            response = await client.post(
                f"{self.vmeta_service_url}/api/v1/individual-groups/multi-embedding-load",
                json={"group_ids": current_group_ids, "include_demographics": True},
                headers=headers,
            )

            if response.status_code != 200:
                logger.error(
                    "Background refresh fetch failed: HTTP %d — keeping existing cache",
                    response.status_code,
                )
                return

            data = response.json()

            for gid, ginfo in data.get('groups', {}).items():
                new_cache.load_group(gid, ginfo['name'], ginfo['members'])

        new_hash = new_cache.compute_content_hash()

        if old_hash == new_hash:
            logger.debug(
                "Background refresh skipped — no changes detected (%d groups, %d members)",
                len(current_group_ids), old_member_count,
            )
            return

        new_member_count = sum(len(g.members) for g in new_cache.get_all_loaded_groups())
        diff = new_member_count - old_member_count

        # Atomic swap — single reference assignment (safe under GIL)
        self.cache = new_cache

        logger.info(
            "🔄 Background cache refreshed: %d → %d members (Δ=%+d), %d groups",
            old_member_count, new_member_count, diff, len(current_group_ids),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_group_used_by_any_active_trigger(self, group_id: str, exclude_trigger: str = "") -> bool:
        """Check if any active vprofile trigger references this group."""
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


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_worker: Optional[VProfileMatchWorker] = None


def get_vprofile_worker() -> VProfileMatchWorker:
    """Get or create the global VProfileMatchWorker singleton."""
    global _worker
    if _worker is None:
        max_memory = int(os.getenv("VPROFILE_CACHE_MAX_MEMORY_MB", "512")) * 1024 * 1024
        cache = EmbeddingCache(max_memory_bytes=max_memory)
        _worker = VProfileMatchWorker(embedding_cache=cache)
    return _worker