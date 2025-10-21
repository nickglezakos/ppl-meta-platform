"""
Cross-Video Individual Tracking - Integrated Caching Service
PPL Meta Platform v2.19.13+

Orchestrates the complete caching system integration with core algorithms,
providing unified interface for cache-aware cross-video individual tracking.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4
import asyncpg

try:
    from ..models.cross_video_tracking import (
        CrossVideoTrackingConfig,
        TrackingSession,
        SessionStatus
    )
    from ..algorithms.core_algorithm import CrossVideoTrackingEngine
    from .cache_manager import CacheManager
    from .cache_clearing import CacheClearingService
    from .session_manager import SessionManager
except ImportError:
    from models.cross_video_tracking import (
        CrossVideoTrackingConfig,
        TrackingSession,
        SessionStatus
    )
    from algorithms.core_algorithm import CrossVideoTrackingEngine
    from services.cache_manager import CacheManager
    from services.cache_clearing import CacheClearingService
    from services.session_manager import SessionManager

logger = logging.getLogger(__name__)


class IntegratedCachingService:
    """
    Unified caching service orchestrating complete cache-aware tracking.
    
    Provides high-level interface for cross-video individual tracking
    with intelligent caching, session management, and performance optimization.
    """
    
    def __init__(self, db_connection: asyncpg.Connection):
        """Initialize with database connection."""
        self.db = db_connection
        
        # Initialize core components
        self.cache_manager = CacheManager(db_connection)
        self.cache_clearing = CacheClearingService(db_connection)
        self.session_manager = SessionManager(db_connection, self.cache_manager)
        self.tracking_engine = CrossVideoTrackingEngine(None)
        
        self.logger = logging.getLogger(f"{__name__}.IntegratedCachingService")
    
    async def execute_cache_aware_tracking(
        self,
        user_id: str,
        collections: List[str],
        start_time: datetime,
        end_time: datetime,
        config: CrossVideoTrackingConfig,
        background: bool = True,
        force_reprocess: bool = False
    ) -> Dict[str, Any]:
        """
        Execute cache-aware cross-video individual tracking.
        
        Args:
            user_id: User identifier
            collections: Collection IDs to process
            start_time: Time range start
            end_time: Time range end
            config: Algorithm configuration
            background: Execute in background
            force_reprocess: Force reprocessing ignoring cache
            
        Returns:
            Execution results or session information
        """
        try:
            # Clear cache if force reprocess requested
            if force_reprocess:
                await self._clear_relevant_cache(collections)
                self.logger.info("Cleared cache for force reprocessing")
            
            # Initialize tracking session
            session = await self.session_manager.initialize_tracking_session(
                user_id=user_id,
                collections=collections,
                start_time=start_time,
                end_time=end_time,
                config=config
            )
            
            session_uuid = str(session.session_uuid)
            
            # Log cache utilization analysis
            cache_hit_rate = session.calculate_cache_hit_rate()
            self.logger.info(
                f"Session {session_uuid}: {cache_hit_rate:.1f}% cache hit rate "
                f"({session.cache_hits}/{session.total_videos} videos cached)"
            )
            
            # Execute session
            execution_result = await self.session_manager.execute_tracking_session(
                session_uuid=session_uuid,
                background=background
            )
            
            # Add cache utilization info to result
            execution_result.update({
                'cache_utilization': {
                    'cache_hit_rate': cache_hit_rate,
                    'cached_videos': session.cache_hits,
                    'total_videos': session.total_videos,
                    'force_reprocess': force_reprocess
                },
                'session_info': {
                    'session_uuid': session_uuid,
                    'user_id': user_id,
                    'collections': collections,
                    'config_hash': session.config_hash
                }
            })
            
            return execution_result
            
        except Exception as e:
            self.logger.error(f"Cache-aware tracking execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'cache_utilization': {'cache_hit_rate': 0.0}
            }
    
    async def get_cache_performance_report(
        self,
        collections: Optional[List[str]] = None,
        days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Generate comprehensive cache performance report.
        
        Args:
            collections: Optional collection filter
            days_back: Days to look back for statistics
            
        Returns:
            Cache performance report
        """
        try:
            # Get cache statistics
            cache_stats = await self.cache_manager.get_cache_statistics()
            
            # Get clearing service statistics
            clearing_stats = await self.cache_clearing.get_cache_statistics()
            
            # Calculate performance metrics
            total_entries = cache_stats.get('total_cached_entries', 0)
            total_size_mb = cache_stats.get('total_cache_size_mb', 0)
            
            # Calculate hit rate trends (simplified)
            avg_access_count = (
                cache_stats.get('total_access_count', 0) / total_entries
                if total_entries > 0 else 0
            )
            
            performance_report = {
                'report_generated_at': datetime.utcnow().isoformat(),
                'cache_overview': {
                    'total_cached_entries': total_entries,
                    'total_cache_size_mb': total_size_mb,
                    'average_entry_size_kb': (
                        (total_size_mb * 1024) / total_entries
                        if total_entries > 0 else 0
                    ),
                    'unique_configurations': cache_stats.get('unique_configs', 0),
                    'unique_videos': cache_stats.get('unique_videos', 0)
                },
                'performance_metrics': {
                    'average_access_count': avg_access_count,
                    'cache_efficiency_score': self._calculate_efficiency_score(
                        cache_stats
                    ),
                    'storage_efficiency': (
                        total_entries / (total_size_mb + 1)  # Avoid division by zero
                    )
                },
                'cache_management': {
                    'last_clearing_date': clearing_stats.get(
                        'last_clearing_date', 'Never'
                    ),
                    'maintenance_frequency': 'As needed',
                    'auto_cleanup_enabled': True
                },
                'recommendations': self._generate_cache_recommendations(
                    cache_stats
                ),
                'collections_filter': collections,
                'analysis_period_days': days_back
            }
            
            return performance_report
            
        except Exception as e:
            self.logger.error(f"Failed to generate cache performance report: {e}")
            return {
                'error': str(e),
                'report_generated_at': datetime.utcnow().isoformat()
            }
    
    async def optimize_cache_storage(
        self,
        max_age_days: int = 30,
        max_size_gb: float = 5.0,
        min_access_count: int = 1
    ) -> Dict[str, Any]:
        """
        Optimize cache storage by clearing old or unused entries.
        
        Args:
            max_age_days: Maximum age for cache entries
            max_size_gb: Maximum total cache size in GB
            min_access_count: Minimum access count to keep entry
            
        Returns:
            Optimization results
        """
        try:
            optimization_start = datetime.utcnow()
            
            # Get initial cache statistics
            initial_stats = await self.cache_manager.get_cache_statistics()
            
            # Clear old entries
            cleared_old = await self.cache_clearing.clear_old_cache_entries(
                max_age_days
            )
            
            # Get statistics after clearing old entries
            after_old_stats = await self.cache_manager.get_cache_statistics()
            
            # Check if we're still over size limit
            current_size_gb = after_old_stats.get('total_cache_size_mb', 0) / 1024
            
            cleared_unused = {'deleted_count': 0, 'freed_space_mb': 0}
            if current_size_gb > max_size_gb:
                # Clear entries with low access count
                cleared_unused = await self._clear_low_access_entries(
                    min_access_count
                )
            
            # Get final statistics
            final_stats = await self.cache_manager.get_cache_statistics()
            
            optimization_time = (
                datetime.utcnow() - optimization_start
            ).total_seconds()
            
            # Calculate optimization results
            initial_size_mb = initial_stats.get('total_cache_size_mb', 0)
            final_size_mb = final_stats.get('total_cache_size_mb', 0)
            space_freed_mb = initial_size_mb - final_size_mb
            
            optimization_results = {
                'optimization_completed_at': datetime.utcnow().isoformat(),
                'processing_time_seconds': optimization_time,
                'space_optimization': {
                    'initial_size_mb': initial_size_mb,
                    'final_size_mb': final_size_mb,
                    'space_freed_mb': space_freed_mb,
                    'space_freed_percentage': (
                        (space_freed_mb / initial_size_mb * 100)
                        if initial_size_mb > 0 else 0
                    )
                },
                'entries_optimization': {
                    'initial_entries': initial_stats.get('total_cached_entries', 0),
                    'final_entries': final_stats.get('total_cached_entries', 0),
                    'entries_removed': (
                        initial_stats.get('total_cached_entries', 0) -
                        final_stats.get('total_cached_entries', 0)
                    )
                },
                'cleanup_details': {
                    'old_entries_cleared': cleared_old,
                    'unused_entries_cleared': cleared_unused,
                    'criteria': {
                        'max_age_days': max_age_days,
                        'max_size_gb': max_size_gb,
                        'min_access_count': min_access_count
                    }
                },
                'recommendations': self._generate_optimization_recommendations(
                    initial_stats, final_stats
                )
            }
            
            self.logger.info(
                f"Cache optimization completed: {space_freed_mb:.1f}MB freed, "
                f"{optimization_results['entries_optimization']['entries_removed']} "
                f"entries removed"
            )
            
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"Cache optimization failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'optimization_completed_at': datetime.utcnow().isoformat()
            }
    
    async def validate_cache_integrity(self) -> Dict[str, Any]:
        """
        Validate cache integrity and consistency.
        
        Returns:
            Validation results with issues found
        """
        try:
            validation_start = datetime.utcnow()
            
            # Validate cache integrity
            integrity_result = await self.cache_manager.validate_cache_integrity()
            
            # Additional consistency checks
            consistency_issues = await self._check_cache_consistency()
            
            validation_time = (
                datetime.utcnow() - validation_start
            ).total_seconds()
            
            validation_results = {
                'validation_completed_at': datetime.utcnow().isoformat(),
                'validation_time_seconds': validation_time,
                'integrity_check': integrity_result,
                'consistency_issues': consistency_issues,
                'overall_status': (
                    'healthy' if not integrity_result.get('issues_found', [])
                    and not consistency_issues else 'issues_found'
                ),
                'recommendations': []
            }
            
            # Generate recommendations based on issues
            if integrity_result.get('issues_found'):
                validation_results['recommendations'].append(
                    "Run cache cleanup to resolve integrity issues"
                )
            
            if consistency_issues:
                validation_results['recommendations'].append(
                    "Consider clearing affected cache entries and reprocessing"
                )
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Cache validation failed: {e}")
            return {
                'validation_completed_at': datetime.utcnow().isoformat(),
                'overall_status': 'validation_failed',
                'error': str(e)
            }
    
    async def get_session_status_with_cache_info(
        self, session_uuid: str
    ) -> Dict[str, Any]:
        """Get session status enhanced with cache utilization information."""
        try:
            # Get base session status
            status = await self.session_manager.get_session_status(session_uuid)
            
            if status.get('status') == 'not_found':
                return status
            
            # Enhance with cache information
            cache_stats = await self.cache_manager.get_cache_statistics()
            
            status.update({
                'cache_info': {
                    'total_cached_entries': cache_stats.get('total_cached_entries', 0),
                    'cache_size_mb': cache_stats.get('total_cache_size_mb', 0),
                    'session_cache_utilization': status.get('cache_hit_rate', 0)
                }
            })
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get enhanced session status: {e}")
            return {
                'session_uuid': session_uuid,
                'status': 'error',
                'error': str(e)
            }
    
    # Helper methods
    async def _clear_relevant_cache(self, collections: List[str]) -> None:
        """Clear cache entries relevant to collections."""
        try:
            await self.cache_clearing.clear_cache_for_collections(collections)
            self.logger.info(f"Cleared cache for {len(collections)} collections")
        except Exception as e:
            self.logger.warning(f"Failed to clear cache for collections: {e}")
    
    async def _clear_low_access_entries(self, min_access_count: int) -> Dict[str, int]:
        """Clear cache entries with low access count."""
        # This would implement custom clearing logic for low-access entries
        # For now, return empty result
        return {'deleted_count': 0, 'freed_space_mb': 0}
    
    async def _check_cache_consistency(self) -> List[Dict[str, Any]]:
        """Check cache consistency issues."""
        # This would implement consistency checking logic
        # For now, return empty list
        return []
    
    def _calculate_efficiency_score(self, cache_stats: Dict[str, Any]) -> float:
        """Calculate cache efficiency score (0-100)."""
        try:
            total_entries = cache_stats.get('total_cached_entries', 0)
            total_access = cache_stats.get('total_access_count', 0)
            
            if total_entries == 0:
                return 0.0
            
            # Simple efficiency calculation based on access patterns
            avg_access = total_access / total_entries
            
            # Score based on average access count (higher is better)
            # Normalize to 0-100 scale
            efficiency_score = min(100.0, avg_access * 20)
            
            return round(efficiency_score, 2)
            
        except Exception:
            return 0.0
    
    def _generate_cache_recommendations(
        self, cache_stats: Dict[str, Any]
    ) -> List[str]:
        """Generate cache optimization recommendations."""
        recommendations = []
        
        total_size_mb = cache_stats.get('total_cache_size_mb', 0)
        total_entries = cache_stats.get('total_cached_entries', 0)
        
        # Size-based recommendations
        if total_size_mb > 1000:  # > 1GB
            recommendations.append(
                "Consider running cache optimization to reduce storage usage"
            )
        
        # Entry count recommendations
        if total_entries > 10000:
            recommendations.append(
                "Large number of cache entries - consider periodic cleanup"
            )
        
        # Efficiency recommendations
        efficiency = self._calculate_efficiency_score(cache_stats)
        if efficiency < 30:
            recommendations.append(
                "Low cache efficiency detected - review caching strategy"
            )
        
        if not recommendations:
            recommendations.append("Cache performance is optimal")
        
        return recommendations
    
    def _generate_optimization_recommendations(
        self, initial_stats: Dict[str, Any], final_stats: Dict[str, Any]
    ) -> List[str]:
        """Generate post-optimization recommendations."""
        recommendations = []
        
        final_size_mb = final_stats.get('total_cache_size_mb', 0)
        space_freed = (
            initial_stats.get('total_cache_size_mb', 0) - final_size_mb
        )
        
        if space_freed > 100:  # > 100MB freed
            recommendations.append(
                "Significant space freed - consider running optimization more frequently"
            )
        
        if final_size_mb > 2000:  # Still > 2GB
            recommendations.append(
                "Cache size still large - consider more aggressive cleanup criteria"
            )
        
        if not recommendations:
            recommendations.append("Cache optimization successful - maintain current settings")
        
        return recommendations