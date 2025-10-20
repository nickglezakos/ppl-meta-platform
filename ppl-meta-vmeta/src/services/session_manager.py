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
        config: CrossVideoTrackingConfig
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
            video_data = await self._fetch_video_data(collections, start_time, end_time)
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
                session.collections, session.start_time, session.end_time
            )
            
            # Get person objects data (this would typically come from Vision service)
            person_objects_data = await self._fetch_person_objects_data(video_data)
            
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
        # Implementation would use the repository layer
        pass
    
    async def _get_session(self, session_uuid: str) -> Optional[TrackingSession]:
        """Get session from database."""
        # Implementation would use the repository layer
        return None
    
    async def _update_session_status(self, session_uuid: str, status: SessionStatus) -> None:
        """Update session status in database."""
        # Implementation would use the repository layer
        pass
    
    async def _update_session_final_status(self, session: TrackingSession) -> None:
        """Update session with final results."""
        # Implementation would use the repository layer
        pass
    
    async def _store_session_results(self, session: TrackingSession, results: Dict[str, Any]) -> None:
        """Store session results in database."""
        # Implementation would use the repository layer
        pass
    
    async def _fetch_video_data(
        self, collections: List[str], start_time: datetime, end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch video data for the given criteria."""
        # This would typically call the Media service
        return []
    
    async def _fetch_person_objects_data(
        self, videos: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch person objects data for videos."""
        # This would typically call the Vision service
        return {}