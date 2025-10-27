"""
Cross-Video Individual Tracking - Session Management Engine
PPL Meta Platform v2.19.13+

Implements session management with background processing, progress tracking,
and intelligent merging of cached and new results for incremental processing.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID, uuid4
import asyncpg
import os
import json
import aiohttp

try:
    from ..models.cross_video_tracking import (
        TrackingSession,
        SessionStatus,
        CrossVideoTrackingConfig,
        Individual,
        VideoAppearance
    )
    from ..algorithms.core_algorithm import CrossVideoTrackingEngine
    from .cache_manager import CacheManager
except ImportError:
    from models.cross_video_tracking import (
        TrackingSession,
        SessionStatus,
        CrossVideoTrackingConfig,
        Individual,
        VideoAppearance
    )
    from algorithms.core_algorithm import CrossVideoTrackingEngine
    from services.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Session management engine for cross-video tracking.
    
    Handles session lifecycle, background processing, progress tracking,
    and intelligent merging of cached and new processing results.
    """
    
    def __init__(
        self,
        db_connection: asyncpg.Connection,
        cache_manager: CacheManager
    ):
        """Initialize with database connection and cache manager."""
        self.db = db_connection
        self.cache_manager = cache_manager
        self.tracking_engine = CrossVideoTrackingEngine(None)  # Will set config per session
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(f"{__name__}.SessionManager")
    
    async def initialize_tracking_session(
        self,
        user_id: str,
        collections: List[str],
        start_time: datetime,
        end_time: datetime,
        config: CrossVideoTrackingConfig,
        auth_token: Optional[str] = None
    ) -> TrackingSession:
        """
        Initialize new tracking session with cache analysis.
        
        Args:
            user_id: User identifier
            collections: Collection IDs to process
            start_time: Time range start
            end_time: Time range end
            config: Algorithm configuration
            
        Returns:
            Created tracking session
        """
        try:
            # Create session
            session = TrackingSession(
                session_uuid=uuid4(),
                user_id=user_id,
                collections=collections,
                start_time=start_time,
                end_time=end_time,
                status=SessionStatus.INITIALIZED,
                config_hash=config.calculate_hash(),
                algorithm_config=config
            )
            
            # Get video data for the session
            # Pass user_id so media endpoints can apply authorization filters
            # Pass auth token for service-to-service authentication
            video_data = await self._fetch_video_data(
                collections, start_time, end_time, 
                user_id=user_id, auth_token=auth_token
            )
            session.total_videos = len(video_data)
            
            # Analyze cache availability
            config_hash = session.config_hash
            video_uuids = [str(v.get('video_uuid', v.get('id'))) for v in video_data]
            
            cache_availability = await self.cache_manager.analyze_cache_availability(
                video_uuids, config_hash
            )
            
            # Calculate cache statistics
            cached_videos = sum(1 for has_cache in cache_availability.values() if has_cache)
            session.cache_hits = cached_videos
            
            # Store session in database
            await self._store_session(session)
            
            cache_hit_rate = (
                (cached_videos/session.total_videos*100) 
                if session.total_videos > 0 else 0
            )
            
            self.logger.info(
                f"Initialized session {session.session_uuid}: "
                f"{session.total_videos} videos, {cached_videos} cached "
                f"({cache_hit_rate:.1f}% cache hit rate)"
            )
            
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to initialize tracking session: {e}")
            raise
    
    async def execute_tracking_session(
        self,
        session_uuid: str,
        background: bool = True
    ) -> Dict[str, Any]:
        """
        Execute tracking session in foreground or background.
        
        Args:
            session_uuid: Session identifier
            background: Whether to run in background
            
        Returns:
            Execution status and details
        """
        try:
            # Get session from database
            session = await self._get_session(session_uuid)
            if not session:
                raise ValueError(f"Session {session_uuid} not found")
            
            if session.status != SessionStatus.INITIALIZED:
                raise ValueError(f"Session {session_uuid} is not in initialized state")
            
            if background:
                # Start background execution
                task = asyncio.create_task(
                    self._execute_session_background(session)
                )
                
                # Track active session
                self.active_sessions[session_uuid] = {
                    'session': session,
                    'task': task,
                    'started_at': datetime.utcnow(),
                    'status': 'running'
                }
                
                return {
                    'session_uuid': session_uuid,
                    'execution_mode': 'background',
                    'status': 'started',
                    'message': 'Session execution started in background'
                }
            else:
                # Execute in foreground
                results = await self._execute_session_background(session)
                return {
                    'session_uuid': session_uuid,
                    'execution_mode': 'foreground',
                    'status': 'completed',
                    'results': results
                }
                
        except Exception as e:
            self.logger.error(f"Failed to execute tracking session: {e}")
            return {
                'session_uuid': session_uuid,
                'status': 'failed',
                'error': str(e)
            }
    
    async def _execute_session_background(self, session: TrackingSession) -> Dict[str, Any]:
        """Execute session processing in background."""
        session_uuid = str(session.session_uuid)
        
        try:
            # Update session status to running
            await self._update_session_status(session_uuid, SessionStatus.RUNNING)
            session.status = SessionStatus.RUNNING
            session.started_at = datetime.utcnow()
            
            self.logger.info(f"Starting background execution for session {session_uuid}")
            
            # Get video data and person objects
            video_data = await self._fetch_video_data(
                session.collections,
                session.start_time,
                session.end_time,
                user_id=session.user_id,
            )

            # Debug summary of discovered videos
            try:
                self.logger.debug(
                    "Discovered %d videos for session %s",
                    len(video_data),
                    session_uuid,
                )
            except Exception:
                pass
            
            # Get person objects data (this would typically come from Vision service)
            person_objects_data = await self._fetch_person_objects_data(video_data)

            # Debug summary of person objects per video
            try:
                counts = {v.get('video_uuid'): len(person_objects_data.get(str(v.get('video_uuid')), [])) for v in video_data}
                self.logger.debug("Person objects per video: %s", str(counts))
            except Exception:
                pass
            
            # Perform cache-aware processing
            results = await self._execute_cache_aware_processing(
                session, video_data, person_objects_data
            )
            
            # Store results and update session
            await self._store_session_results(session, results)
            
            # Update final session status
            session.completed_at = datetime.utcnow()
            session.processing_time_seconds = (
                session.completed_at - session.started_at
            ).total_seconds()
            
            if results.get('success', False):
                session.status = SessionStatus.COMPLETED
                session.individuals_found = len(results.get('individuals', []))
                session.processed_videos = session.total_videos
            else:
                session.status = SessionStatus.FAILED
            
            await self._update_session_final_status(session)
            
            # Remove from active sessions
            if session_uuid in self.active_sessions:
                del self.active_sessions[session_uuid]
            
            self.logger.info(
                f"Session {session_uuid} completed: "
                f"{session.individuals_found} individuals found, "
                f"{session.processing_time_seconds:.2f}s processing time"
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Session {session_uuid} failed: {e}")
            
            # Update session to failed status
            await self._update_session_status(session_uuid, SessionStatus.FAILED)
            
            # Remove from active sessions
            if session_uuid in self.active_sessions:
                del self.active_sessions[session_uuid]
            
            return {
                'success': False,
                'error': str(e),
                'session_uuid': session_uuid
            }
    
    async def _execute_cache_aware_processing(
        self,
        session: TrackingSession,
        video_data: List[Dict[str, Any]],
        person_objects_data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Execute processing with intelligent cache utilization."""
        try:
            # Analyze cache availability
            video_uuids = [str(v.get('video_uuid', v.get('id'))) for v in video_data]
            cache_availability = await self.cache_manager.analyze_cache_availability(
                video_uuids, session.config_hash
            )
            
            # Separate cached and non-cached videos
            cached_videos = []
            new_videos = []
            
            for video in video_data:
                video_uuid = str(video.get('video_uuid', video.get('id')))
                if cache_availability.get(video_uuid, False):
                    cached_videos.append(video)
                else:
                    new_videos.append(video)
            
            self.logger.info(
                f"Cache analysis: {len(cached_videos)} cached, "
                f"{len(new_videos)} new videos to process"
            )
            
            # Process new videos if any
            new_results = None
            if new_videos:
                # Set engine configuration
                self.tracking_engine.config = session.algorithm_config
                
                # Execute algorithm on new videos
                new_person_objects = {
                    video['video_uuid']: person_objects_data.get(str(video['video_uuid']), [])
                    for video in new_videos
                }
                
                new_results = self.tracking_engine.execute_tracking(
                    session, new_videos, new_person_objects
                )
                
                # Cache the new results
                await self._cache_new_results(session, new_videos, new_person_objects)
            
            # Retrieve cached results
            cached_results = await self._retrieve_cached_results(
                session, cached_videos
            )
            
            # Merge cached and new results
            final_results = await self._merge_cached_and_new_results(
                session, cached_results, new_results, video_data
            )
            
            return final_results
            
        except Exception as e:
            self.logger.error(f"Cache-aware processing failed: {e}")
            raise
    
    async def _merge_cached_and_new_results(
        self,
        session: TrackingSession,
        cached_results: Dict[str, Any],
        new_results: Optional[Dict[str, Any]],
        all_videos: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Intelligently merge cached and new processing results."""
        try:
            merged_individuals = []
            merged_sequences = []
            merged_overlaps = []
            
            # Combine individuals from both sources
            if cached_results.get('individuals'):
                merged_individuals.extend(cached_results['individuals'])
            
            if new_results and new_results.get('individuals'):
                merged_individuals.extend(new_results['individuals'])
            
            # Combine sequences and overlaps
            if cached_results.get('video_sequences'):
                merged_sequences.extend(cached_results['video_sequences'])
            
            if new_results and new_results.get('video_sequences'):
                merged_sequences.extend(new_results['video_sequences'])
            
            if cached_results.get('overlap_groups'):
                merged_overlaps.extend(cached_results['overlap_groups'])
            
            if new_results and new_results.get('overlap_groups'):
                merged_overlaps.extend(new_results['overlap_groups'])
            
            # Calculate combined metrics
            total_processing_time = 0
            if cached_results.get('processing_time_seconds'):
                total_processing_time += cached_results['processing_time_seconds']
            if new_results and new_results.get('processing_time_seconds'):
                total_processing_time += new_results['processing_time_seconds']
            
            # Build final results
            final_results = {
                'session_uuid': str(session.session_uuid),
                'success': True,
                'processing_time_seconds': total_processing_time,
                'video_sequences': merged_sequences,
                'overlap_groups': merged_overlaps,
                'individuals': merged_individuals,
                'cache_utilization': {
                    'cached_videos': len(cached_results.get('videos', [])),
                    'new_videos': len(new_results.get('videos', [])) if new_results else 0,
                    'total_videos': len(all_videos),
                    'cache_hit_rate': (
                        len(cached_results.get('videos', [])) / len(all_videos) * 100
                        if all_videos else 0
                    )
                },
                'algorithm_config': session.algorithm_config.dict(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            return final_results
            
        except Exception as e:
            self.logger.error(f"Failed to merge results: {e}")
            raise
    
    async def _cache_new_results(
        self,
        session: TrackingSession,
        videos: List[Dict[str, Any]],
        person_objects_data: Dict[str, List[Dict[str, Any]]]
    ) -> None:
        """Cache results from newly processed videos."""
        try:
            for video in videos:
                video_uuid = str(video.get('video_uuid', video.get('id')))
                person_objects = person_objects_data.get(video_uuid, [])
                
                if person_objects:
                    await self.cache_manager.store_cached_result(
                        video_uuid=video_uuid,
                        session_uuid=str(session.session_uuid),
                        config_hash=session.config_hash,
                        person_objects=person_objects,
                        processing_metadata={
                            'processed_at': datetime.utcnow().isoformat(),
                            'video_duration': video.get('duration_seconds', 0),
                            'person_object_count': len(person_objects)
                        }
                    )
            
            self.logger.debug(f"Cached results for {len(videos)} videos")
            
        except Exception as e:
            self.logger.warning(f"Failed to cache new results: {e}")
    
    async def _retrieve_cached_results(
        self,
        session: TrackingSession,
        videos: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Retrieve and aggregate cached results."""
        try:
            cached_individuals = []
            cached_metadata = []
            
            for video in videos:
                video_uuid = str(video.get('video_uuid', video.get('id')))
                cached_result = await self.cache_manager.get_cached_result(
                    video_uuid, session.config_hash
                )
                
                if cached_result:
                    # Process cached person objects into individuals
                    person_objects = cached_result.get('person_objects', [])
                    if isinstance(person_objects, str):
                        import json
                        person_objects = json.loads(person_objects)
                    
                    # Create individual from cached data (simplified)
                    if person_objects:
                        cached_metadata.append({
                            'video_uuid': video_uuid,
                            'person_objects': person_objects,
                            'cached_at': cached_result.get('created_at'),
                            'access_count': cached_result.get('access_count', 0)
                        })
            
            return {
                'individuals': cached_individuals,
                'videos': videos,
                'metadata': cached_metadata,
                'processing_time_seconds': 0.0  # Cached results have no processing time
            }
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve cached results: {e}")
            return {'individuals': [], 'videos': [], 'metadata': []}
    
    async def get_session_status(self, session_uuid: str) -> Dict[str, Any]:
        """Get current session status and progress."""
        try:
            # Check if session is active
            if session_uuid in self.active_sessions:
                active_info = self.active_sessions[session_uuid]
                session = active_info['session']
                
                return {
                    'session_uuid': session_uuid,
                    'status': session.status.value,
                    'progress_percentage': session.calculate_progress_percentage(),
                    'cache_hit_rate': session.calculate_cache_hit_rate(),
                    'processing_time_seconds': (
                        datetime.utcnow() - active_info['started_at']
                    ).total_seconds(),
                    'total_videos': session.total_videos,
                    'processed_videos': session.processed_videos,
                    'individuals_found': session.individuals_found,
                    'is_active': True
                }
            
            # Get from database
            session = await self._get_session(session_uuid)
            if not session:
                return {
                    'session_uuid': session_uuid,
                    'status': 'not_found',
                    'error': 'Session not found'
                }
            
            return {
                'session_uuid': session_uuid,
                'status': session.status.value,
                'progress_percentage': session.calculate_progress_percentage(),
                'cache_hit_rate': session.calculate_cache_hit_rate(),
                'processing_time_seconds': session.processing_time_seconds,
                'total_videos': session.total_videos,
                'processed_videos': session.processed_videos,
                'individuals_found': session.individuals_found,
                'is_active': False,
                'created_at': session.created_at,
                'started_at': session.started_at,
                'completed_at': session.completed_at
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get session status: {e}")
            return {
                'session_uuid': session_uuid,
                'status': 'error',
                'error': str(e)
            }
    
    async def cancel_session(self, session_uuid: str) -> Dict[str, Any]:
        """Cancel an active tracking session."""
        try:
            if session_uuid in self.active_sessions:
                active_info = self.active_sessions[session_uuid]
                task = active_info['task']
                
                # Cancel the background task
                task.cancel()
                
                # Update session status
                await self._update_session_status(session_uuid, SessionStatus.FAILED)
                
                # Remove from active sessions
                del self.active_sessions[session_uuid]
                
                self.logger.info(f"Cancelled session {session_uuid}")
                
                return {
                    'session_uuid': session_uuid,
                    'status': 'cancelled',
                    'message': 'Session cancelled successfully'
                }
            else:
                return {
                    'session_uuid': session_uuid,
                    'status': 'not_active',
                    'message': 'Session is not currently active'
                }
                
        except Exception as e:
            self.logger.error(f"Failed to cancel session: {e}")
            return {
                'session_uuid': session_uuid,
                'status': 'error',
                'error': str(e)
            }
    
    # Database operations (simplified - would use repository pattern in production)
    async def _store_session(self, session: TrackingSession) -> None:
        """Store session in database."""
        try:
            # Insert basic session record
            await self.db.execute(
                """
                INSERT INTO tracking_sessions
                (session_uuid, user_id, collections, start_time, end_time,
                 config_hash, algorithm_config, status, total_videos, cache_hits, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
                """,
                str(session.session_uuid),
                session.user_id,
                session.collections,
                session.start_time,
                session.end_time,
                session.config_hash,
                json.dumps(session.algorithm_config.dict()),
                session.status.value,
                session.total_videos,
                session.cache_hits,
            )
            self.logger.info("Stored session %s in database", str(session.session_uuid))
        except Exception as e:
            self.logger.error("Failed to store session %s: %s", str(session.session_uuid), e)
            raise
    
    async def _get_session(self, session_uuid: str) -> Optional[TrackingSession]:
        """Get session from database."""
        try:
            row = await self.db.fetchrow(
                "SELECT * FROM tracking_sessions WHERE session_uuid = $1",
                session_uuid,
            )

            if not row:
                return None

            alg_conf = row.get('algorithm_config')
            if isinstance(alg_conf, (str, bytes)):
                try:
                    alg_conf = json.loads(alg_conf)
                except Exception:
                    alg_conf = {}

            algorithm_config = CrossVideoTrackingConfig(**alg_conf) if alg_conf else None

            session = TrackingSession(
                session_uuid=row.get('session_uuid'),
                user_id=row.get('user_id'),
                collections=row.get('collections') or [],
                start_time=row.get('start_time'),
                end_time=row.get('end_time'),
                status=SessionStatus(row.get('status')),
                config_hash=row.get('config_hash') or '',
                algorithm_config=algorithm_config or CrossVideoTrackingConfig(**{}),
                total_videos=row.get('total_videos') or 0,
                processed_videos=row.get('processed_videos') or 0,
                failed_videos=row.get('failed_videos') or [],
                individuals_found=row.get('individuals_found') or 0,
                person_objects_processed=row.get('person_objects_processed') or 0,
                cache_hits=row.get('cache_hits') or 0,
                created_at=row.get('created_at'),
                started_at=row.get('started_at'),
                completed_at=row.get('completed_at'),
                processing_time_seconds=row.get('processing_time_seconds'),
            )

            return session
        except Exception as e:
            self.logger.error("Failed to get session %s: %s", session_uuid, e)
            return None
    
    async def _update_session_status(self, session_uuid: str, status: SessionStatus) -> None:
        """Update session status in database."""
        try:
            params = [session_uuid, status.value]
            set_clauses = ["status = $2", "updated_at = NOW()"]

            if status == SessionStatus.RUNNING:
                set_clauses.append("started_at = NOW()")
            if status == SessionStatus.COMPLETED:
                set_clauses.append("completed_at = NOW()")

            query = f"UPDATE tracking_sessions SET {', '.join(set_clauses)} WHERE session_uuid = $1"
            await self.db.execute(query, *params)
            self.logger.info("Updated session %s status to %s", session_uuid, status.value)
        except Exception as e:
            self.logger.error("Failed to update session %s status: %s", session_uuid, e)
    
    async def _update_session_final_status(self, session: TrackingSession) -> None:
        """Update session with final results."""
        try:
            await self.db.execute(
                """
                UPDATE tracking_sessions
                SET status = $2,
                    processed_videos = $3,
                    individuals_found = $4,
                    processing_time_seconds = $5,
                    completed_at = $6,
                    updated_at = NOW()
                WHERE session_uuid = $1
                """,
                str(session.session_uuid),
                session.status.value,
                session.processed_videos,
                session.individuals_found,
                session.processing_time_seconds,
                session.completed_at,
            )
            self.logger.info("Finalized session %s with status %s", str(session.session_uuid), session.status.value)
        except Exception as e:
            self.logger.error("Failed to update final status for session %s: %s", str(session.session_uuid), e)
    
    async def _store_session_results(self, session: TrackingSession, results: Dict[str, Any]) -> None:
        """Store session results in database.

        Minimal implementation: update processed_videos and individuals_found in
        tracking_sessions. Later this should insert individuals and appearances
        into their respective tables.
        """
        try:
            individuals = results.get('individuals', []) if isinstance(results, dict) else []
            processed_videos = results.get('video_count', session.total_videos) if isinstance(results, dict) else session.total_videos

            # Update tracking_sessions with results summary
            await self.db.execute(
                """
                UPDATE tracking_sessions
                SET processed_videos = $2,
                    individuals_found = $3,
                    updated_at = NOW()
                WHERE session_uuid = $1
                """,
                str(session.session_uuid),
                processed_videos,
                len(individuals),
            )

            self.logger.info("Stored session results for %s: videos=%s individuals=%d",
                             str(session.session_uuid), processed_videos, len(individuals))
        except Exception as e:
            self.logger.error("Failed to store session results for %s: %s", str(session.session_uuid), e)
    
    async def _fetch_video_data(
        self,
        collections: List[str],
        start_time: datetime,
        end_time: datetime,
        user_id: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch video data for the given criteria."""
        print(f"\n🔍 _fetch_video_data called: collections={collections}, time={start_time} to {end_time}, user_id={user_id}")
        self.logger.info(
            f"🔍 _fetch_video_data called: collections={collections}, "
            f"time={start_time} to {end_time}, user_id={user_id}"
        )
        
        # This should call the Media service (via Gateway or direct) to retrieve
        # media items for the specified collections and timeframe.
        results: List[Dict[str, Any]] = []

        gw = os.getenv("PPL_GATEWAY_URL", "http://localhost:8080")
        gateway_url = gw.rstrip("/")

        # If collections is a list of collection identifiers, request items
        # per collection via the gateway proxy.
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            # Use auth token from request for service-to-service communication
            headers = {}
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'
                print(f"✅ Using auth token from request for media service calls")
            else:
                # FALLBACK: Try to read from file (for testing/debugging)
                try:
                    with open('/tmp/token.txt', 'r') as f:
                        token = f.read().strip()
                        if token:
                            headers['Authorization'] = f'Bearer {token}'
                            print("⚠️ Using fallback token from /tmp/token.txt")
                except Exception:
                    pass
            
            print(f"🔐 Auth configured: {bool(headers)}, has_token={bool(auth_token)}")
            
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                for collection in collections:
                    # Determine whether collection is a UUID or a camera_device_id
                    collection_id = collection
                    try:
                        if "-" not in str(collection):
                            # Not a UUID - try to resolve by camera device id
                            lookup_url = (
                                f"{gateway_url}/api/v1/media/collections/by-camera/"
                                f"{collection}"
                            )
                            params = {}
                            if user_id:
                                params["user_id"] = user_id
                            # Log the lookup request for debugging (URL + params)
                            self.logger.debug(
                                "Collection lookup request: %s params=%s",
                                lookup_url,
                                params,
                            )

                            async with session.get(lookup_url, params=params) as lookup_resp:
                                status = lookup_resp.status
                                # Log status code
                                self.logger.debug(
                                    "Collection lookup %s -> status=%s for %s",
                                    lookup_url,
                                    status,
                                    collection,
                                )

                                if lookup_resp.status == 200:
                                    lookup_data = await lookup_resp.json()
                                    # lookup_data may be a dict representing collection
                                    if (
                                        isinstance(lookup_data, dict)
                                        and lookup_data.get("uuid")
                                    ):
                                        collection_id = lookup_data.get("uuid")

                        # Try collection items endpoint via gateway proxy
                        url = (
                            f"{gateway_url}/api/v1/media/collections/"
                            f"{collection_id}/items"
                        )
                        params = {"limit": 500}
                        if user_id:
                            params["user_id"] = user_id

                        # Log the collection items request
                        self.logger.debug(
                            "Requesting collection items: %s params=%s",
                            url,
                            params,
                        )

                        async with session.get(url, params=params) as resp:
                            status = resp.status
                            self.logger.debug(
                                "Collection items request %s -> status=%s",
                                url,
                                status,
                            )

                            if resp.status == 200:
                                data = await resp.json()
                                # Ensure data is a list
                                if isinstance(data, list):
                                    # Log number of items discovered (limited)
                                    try:
                                        sample_ids = [
                                            (it.get("uuid") or it.get("id"))
                                            for it in data[:5]
                                        ]
                                        self.logger.debug(
                                            "Collection %s returned %d items, sample ids=%s",
                                            collection_id,
                                            len(data),
                                            sample_ids,
                                        )
                                    except Exception:
                                        pass

                                    for item in data:
                                        # Normalize fields used by engine
                                        video = {
                                            "video_uuid": (
                                                item.get("uuid") or item.get("id")
                                            ),
                                            "filename": item.get("filename"),
                                            "original_filename": item.get(
                                                "original_filename"
                                            ),
                                            "created_at": item.get("created_at"),
                                            "duration_seconds": (
                                                item.get("duration_seconds")
                                                or item.get(
                                                    "technical_metadata",
                                                    {}
                                                ).get("duration_seconds")
                                            ),
                                            "file_path": item.get("file_path"),
                                            "device_name": (
                                                item.get("device_name")
                                                or item.get("camera_device_id")
                                            ),
                                        }
                                        results.append(video)
                            else:
                                self.logger.debug(
                                    "Media collection items request returned %s for %s",
                                    resp.status,
                                    collection_id,
                                )
                    except Exception as e:
                        self.logger.debug(f"Failed to fetch items for collection {collection}: {e}")

                self.logger.info(f"📦 After collection items: {len(results)} videos found")
                
                # If we didn't get any results from collections, try search endpoint
                if not results:
                    self.logger.info("🔎 No results from collection items, trying search fallback...")
                    # Use media search with multiple param name variants to be robust
                    try:
                        search_url = f"{gateway_url}/api/v1/media/search"
                        tried = []

                        candidate_param_sets = [
                            {"start_time": start_time.isoformat(), "end_time": end_time.isoformat(), "collection": ",".join(collections)},
                            {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
                            {"start_date": start_time.isoformat(), "end_date": end_time.isoformat()},
                            {"collection": ",".join(collections)},
                        ]

                        for params in candidate_param_sets:
                            try:
                                # Log the search request and params
                                self.logger.debug(
                                    "Media search request: %s params=%s",
                                    search_url,
                                    params,
                                )

                                async with session.get(search_url, params=params) as resp:
                                    tried.append((params, resp.status))
                                    self.logger.debug(
                                        "Media search %s -> status=%s params=%s",
                                        search_url,
                                        resp.status,
                                        params,
                                    )

                                    if resp.status == 200:
                                        data = await resp.json()
                                        if isinstance(data, list):
                                            potential = data
                                        elif isinstance(data, dict) and data.get('items'):
                                            potential = data.get('items')
                                        elif isinstance(data, dict) and data.get('media'):
                                            potential = data.get('media')
                                        else:
                                            potential = []

                                        # Log sample ids from potential
                                        try:
                                            sample = [
                                                (it.get('uuid') or it.get('id'))
                                                for it in potential[:5]
                                            ]
                                            self.logger.debug(
                                                "Search returned %d items, sample ids=%s",
                                                len(potential),
                                                sample,
                                            )
                                        except Exception:
                                            pass

                                        for item in potential:
                                            video = {
                                                "video_uuid": (item.get("uuid") or item.get("id")),
                                                "filename": item.get("filename"),
                                                "original_filename": item.get("original_filename"),
                                                "created_at": item.get("created_at"),
                                                "duration_seconds": (
                                                    item.get("duration_seconds") or item.get("technical_metadata", {}).get("duration_seconds")
                                                ),
                                                "file_path": item.get("file_path"),
                                                "device_name": (item.get("device_name") or item.get("camera_device_id")),
                                            }
                                            results.append(video)

                                        if results:
                                            break
                            except Exception:
                                continue

                        if not results:
                            self.logger.debug("Media search tried variants: %s", str(tried))
                    except Exception as e:
                        self.logger.debug(f"Media search failed: {e}")

        except Exception as e:
            self.logger.error(f"_fetch_video_data error: {e}")

        # Filter by timeframe if created_at fields are present
        filtered: List[Dict[str, Any]] = []
        for v in results:
            ca = v.get("created_at")
            if ca:
                try:
                    parsed = datetime.fromisoformat(ca.replace('Z', '+00:00'))
                    if parsed >= start_time and parsed <= end_time:
                        filtered.append(v)
                except Exception:
                    # if parsing fails, include the video conservatively
                    filtered.append(v)
            else:
                filtered.append(v)

        print(f"🎯 _fetch_video_data returning: {len(results)} raw, {len(filtered)} filtered")
        self.logger.info(
            f"🎯 _fetch_video_data returning: {len(results)} raw videos, "
            f"{len(filtered)} after timeframe filter"
        )
        if filtered:
            sample_ids = [v.get('video_uuid') for v in filtered[:3]]
            print(f"   Sample UUIDs: {sample_ids}")
            self.logger.info(f"   Sample video UUIDs: {sample_ids}")
        
        return filtered
    
    async def _fetch_person_objects_data(
        self, videos: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch person objects data for videos."""
        results: Dict[str, List[Dict[str, Any]]] = {}
        gw = os.getenv("PPL_GATEWAY_URL", "http://localhost:8080")
        gateway_url = gw.rstrip("/")

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for video in videos:
                    video_uuid = str(
                        video.get("video_uuid") or video.get("id")
                    )
                    if not video_uuid:
                        continue

                    # Try known vision endpoints via gateway proxy
                    vision_base = gateway_url + "/api/v1/vision"
                    candidates = [
                        vision_base + "/person-objects/media/" + video_uuid,
                        vision_base + "/face-detection/results/" + video_uuid,
                        vision_base + "/person-objects/" + video_uuid,
                    ]

                    person_list: List[Dict[str, Any]] = []
                    for url in candidates:
                        try:
                            async with session.get(url) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    # Normalize expected structure
                                    if isinstance(data, dict):
                                        po = data.get("person_objects")
                                        if po:
                                            person_list = po
                                    elif isinstance(data, list):
                                        person_list = data
                                    else:
                                        # if dict with entries, try to extract
                                        if isinstance(data, dict):
                                            # flatten common keys
                                            for k in ["detections", "results"]:
                                                val = data.get(k)
                                                if val and isinstance(
                                                    val, list
                                                ):
                                                    person_list = val
                                                    break

                                    if person_list:
                                        break
                                else:
                                    # Use logger formatting to avoid long f-strings
                                    self.logger.debug(
                                        "Vision endpoint %s returned %s",
                                        url,
                                        resp.status,
                                    )
                        except (
                            aiohttp.ClientError,
                            asyncio.TimeoutError,
                        ) as err:
                            self.logger.debug(
                                "Failed to call vision endpoint %s: %s",
                                url,
                                err,
                            )

                    results[video_uuid] = person_list

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.error("_fetch_person_objects_data error: %s", e)

        return results
