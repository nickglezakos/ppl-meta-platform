"""
Cross-Video Individual Tracking - Cache Management Models
PPL Meta Platform v2.19.13+

This module contains Pydantic models for cache management operations,
including cache clearing requests, responses, and statistics.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


# =============================================
# CACHE CLEARING REQUEST MODELS
# =============================================

class ClearCollectionCacheRequest(BaseModel):
    """
    Request to clear cache for specific collections.
    
    Used for testing and development to clear cached results
    for specific collections with optional time and config filters.
    """
    
    collections: List[str] = Field(
        description="Collections to clear cache for",
        min_items=1,
        max_items=50
    )
    start_time: Optional[datetime] = Field(
        default=None,
        description="Optional time range filter start"
    )
    end_time: Optional[datetime] = Field(
        default=None,
        description="Optional time range filter end"
    )
    config_filter: Optional[str] = Field(
        default=None,
        description="Optional algorithm config hash filter"
    )
    force_clear: bool = Field(
        default=False,
        description="Force clear even if sessions are running"
    )
    
    @validator('collections')
    def validate_collection_names(cls, v):
        """Validate collection names."""
        for collection in v:
            if not collection or not collection.strip():
                raise ValueError("Collection names cannot be empty")
            if len(collection) > 100:
                raise ValueError("Collection names cannot exceed 100 characters")
        return v
    
    @validator('end_time')
    def end_after_start(cls, v, values):
        """Ensure end_time is after start_time if both provided."""
        if v is not None and 'start_time' in values and values['start_time'] is not None:
            if v <= values['start_time']:
                raise ValueError('end_time must be after start_time')
        return v
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "collections": ["warehouse_cameras", "entrance_cameras"],
                "start_time": "2025-10-19T00:00:00",
                "end_time": "2025-10-20T00:00:00",
                "config_filter": "abc123def456",
                "force_clear": False
            }
        }


class ClearVideoCacheRequest(BaseModel):
    """
    Request to clear cache for specific videos.
    
    Used for targeted cache clearing when specific videos
    need to be reprocessed with fresh results.
    """
    
    video_uuids: List[UUID] = Field(
        description="Specific video UUIDs to clear",
        min_items=1,
        max_items=1000
    )
    config_filter: Optional[str] = Field(
        default=None,
        description="Optional algorithm config hash filter"
    )
    cascade_individuals: bool = Field(
        default=True,
        description="Also remove affected individuals"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "video_uuids": [
                    "123e4567-e89b-12d3-a456-426614174000",
                    "987fcdeb-51a2-43d1-9f12-123456789abc"
                ],
                "config_filter": "abc123def456",
                "cascade_individuals": True
            }
        }


# =============================================
# CACHE CLEARING RESPONSE MODELS
# =============================================

class ClearCacheResponse(BaseModel):
    """
    Response from cache clearing operations.
    
    Provides comprehensive information about what was cleared
    and the impact of the operation.
    """
    
    message: str = Field(description="Operation summary message")
    
    # Operation-specific results
    collections_cleared: Optional[List[str]] = Field(
        default=None,
        description="Collections that had cache cleared"
    )
    videos_cleared: Optional[List[str]] = Field(
        default=None,
        description="Video UUIDs that had cache cleared"
    )
    
    # Detailed impact metrics
    cached_videos_removed: Optional[int] = Field(
        default=None,
        description="Number of cached video records removed"
    )
    cached_individuals_removed: Optional[int] = Field(
        default=None,
        description="Number of cached individuals removed"
    )
    cached_records_removed: Optional[int] = Field(
        default=None,
        description="Total number of cache records removed"
    )
    processing_sessions_affected: Optional[int] = Field(
        default=None,
        description="Number of processing sessions affected"
    )
    individuals_affected: Optional[int] = Field(
        default=None,
        description="Number of individuals affected"
    )
    
    # Summary metrics for destructive operations
    total_individuals_removed: Optional[int] = Field(
        default=None,
        description="Total individuals completely removed"
    )
    total_sessions_removed: Optional[int] = Field(
        default=None,
        description="Total sessions completely removed"
    )
    total_cache_records_removed: Optional[int] = Field(
        default=None,
        description="Total cache records removed"
    )
    total_video_states_removed: Optional[int] = Field(
        default=None,
        description="Total video processing states removed"
    )
    
    # Operation metadata
    operation_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the operation was performed"
    )
    warning: Optional[str] = Field(
        default=None,
        description="Warning message if applicable"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "message": "Cache cleared for 2 collections",
                "collections_cleared": ["warehouse_cameras", "entrance_cameras"],
                "cached_videos_removed": 45,
                "cached_individuals_removed": 12,
                "cached_records_removed": 67,
                "processing_sessions_affected": 3,
                "operation_timestamp": "2025-10-20T10:30:00Z"
            }
        }


# =============================================
# CACHE STATUS AND STATISTICS MODELS
# =============================================

class CacheStatusResponse(BaseModel):
    """
    Cache status and statistics response.
    
    Provides comprehensive information about the current state
    of the cache system including usage metrics and efficiency.
    """
    
    # Core cache metrics
    total_cached_videos: int = Field(
        ge=0,
        description="Total number of videos with cached results"
    )
    total_individuals: int = Field(
        ge=0,
        description="Total number of individuals stored"
    )
    total_sessions: int = Field(
        ge=0,
        description="Total number of tracking sessions"
    )
    cache_size_mb: float = Field(
        ge=0.0,
        description="Total cache storage size in megabytes"
    )
    
    # Temporal information
    oldest_cache_entry: Optional[datetime] = Field(
        default=None,
        description="Timestamp of oldest cache entry"
    )
    newest_cache_entry: Optional[datetime] = Field(
        default=None,
        description="Timestamp of newest cache entry"
    )
    
    # Coverage information
    collections_covered: List[str] = Field(
        description="List of collections with cached data"
    )
    
    # Performance metrics
    hit_rate_last_30_days: float = Field(
        ge=0.0,
        le=100.0,
        description="Cache hit rate percentage over last 30 days"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "total_cached_videos": 156,
                "total_individuals": 43,
                "total_sessions": 8,
                "cache_size_mb": 24.67,
                "oldest_cache_entry": "2025-10-15T08:30:00Z",
                "newest_cache_entry": "2025-10-20T10:15:00Z",
                "collections_covered": ["warehouse_cameras", "entrance_cameras"],
                "hit_rate_last_30_days": 67.3
            }
        }


class CacheStatistics(BaseModel):
    """
    Internal cache statistics structure.
    
    Used internally for cache analysis and monitoring.
    Not directly exposed to API users.
    """
    
    total_videos: int = Field(ge=0, description="Total cached videos")
    total_individuals: int = Field(ge=0, description="Total individuals")
    total_sessions: int = Field(ge=0, description="Total sessions")
    cache_size_mb: float = Field(ge=0.0, description="Cache size in MB")
    oldest_entry: Optional[datetime] = Field(default=None, description="Oldest cache entry")
    newest_entry: Optional[datetime] = Field(default=None, description="Newest cache entry")
    collections: List[str] = Field(description="Collections with cached data")
    hit_rate_30d: float = Field(ge=0.0, le=1.0, description="30-day hit rate (0.0-1.0)")
    
    def to_response(self) -> CacheStatusResponse:
        """Convert to API response format."""
        return CacheStatusResponse(
            total_cached_videos=self.total_videos,
            total_individuals=self.total_individuals,
            total_sessions=self.total_sessions,
            cache_size_mb=self.cache_size_mb,
            oldest_cache_entry=self.oldest_entry,
            newest_cache_entry=self.newest_entry,
            collections_covered=self.collections,
            hit_rate_last_30_days=self.hit_rate_30d * 100.0  # Convert to percentage
        )


# =============================================
# CACHE CLEARING STATISTICS MODELS
# =============================================

class ClearCacheStats(BaseModel):
    """
    Statistics from cache clearing operations.
    
    Internal model used to track the impact of cache clearing
    operations for logging and response generation.
    """
    
    individuals: int = Field(ge=0, description="Individuals removed")
    sessions: int = Field(ge=0, description="Sessions removed")
    cache_records: int = Field(ge=0, description="Cache records removed")
    video_states: int = Field(ge=0, description="Video states removed")
    videos: int = Field(ge=0, description="Videos affected")
    individuals_affected: int = Field(ge=0, description="Individuals affected but not removed")
    
    def to_response(self, message: str, **kwargs) -> ClearCacheResponse:
        """Convert to API response format."""
        return ClearCacheResponse(
            message=message,
            cached_individuals_removed=self.individuals,
            total_sessions_removed=self.sessions,
            total_cache_records_removed=self.cache_records,
            total_video_states_removed=self.video_states,
            cached_videos_removed=self.videos,
            individuals_affected=self.individuals_affected,
            **kwargs
        )


# =============================================
# CACHE ANALYSIS MODELS
# =============================================

class CacheEfficiencyMetrics(BaseModel):
    """
    Cache efficiency analysis metrics.
    
    Provides detailed analysis of cache performance
    for optimization and monitoring purposes.
    """
    
    # Hit rate metrics
    overall_hit_rate: float = Field(ge=0.0, le=1.0, description="Overall cache hit rate")
    hit_rate_by_collection: Dict[str, float] = Field(description="Hit rates by collection")
    hit_rate_trend_7d: List[float] = Field(description="7-day hit rate trend")
    hit_rate_trend_30d: List[float] = Field(description="30-day hit rate trend")
    
    # Performance metrics
    avg_cache_lookup_time_ms: float = Field(ge=0.0, description="Average cache lookup time")
    cache_miss_penalty_ms: float = Field(ge=0.0, description="Average time penalty for cache misses")
    
    # Storage metrics
    cache_size_trend_mb: List[float] = Field(description="Cache size trend over time")
    largest_cache_entries: List[Dict[str, Any]] = Field(description="Largest cache entries")
    
    # Usage patterns
    most_accessed_videos: List[Dict[str, Any]] = Field(description="Most frequently accessed videos")
    least_accessed_videos: List[Dict[str, Any]] = Field(description="Least accessed videos")
    access_pattern_by_hour: Dict[int, int] = Field(description="Access patterns by hour of day")
    
    # Efficiency recommendations
    recommendations: List[str] = Field(description="Cache optimization recommendations")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "overall_hit_rate": 0.673,
                "hit_rate_by_collection": {
                    "warehouse_cameras": 0.72,
                    "entrance_cameras": 0.65
                },
                "avg_cache_lookup_time_ms": 2.3,
                "cache_miss_penalty_ms": 1250.0,
                "recommendations": [
                    "Consider increasing cache retention for high-traffic collections",
                    "Archive rarely accessed cache entries older than 90 days"
                ]
            }
        }


class CacheMaintenanceReport(BaseModel):
    """
    Cache maintenance operation report.
    
    Provides detailed information about cache maintenance
    operations such as cleanup and optimization.
    """
    
    operation_type: str = Field(description="Type of maintenance operation")
    started_at: datetime = Field(description="Operation start time")
    completed_at: datetime = Field(description="Operation completion time")
    
    # Before/after metrics
    cache_entries_before: int = Field(ge=0, description="Cache entries before operation")
    cache_entries_after: int = Field(ge=0, description="Cache entries after operation")
    cache_size_before_mb: float = Field(ge=0.0, description="Cache size before (MB)")
    cache_size_after_mb: float = Field(ge=0.0, description="Cache size after (MB)")
    
    # Operation results
    entries_removed: int = Field(ge=0, description="Number of entries removed")
    entries_optimized: int = Field(ge=0, description="Number of entries optimized")
    space_recovered_mb: float = Field(ge=0.0, description="Storage space recovered (MB)")
    
    # Performance impact
    performance_improvement_percent: Optional[float] = Field(
        default=None,
        description="Estimated performance improvement percentage"
    )
    
    # Operation summary
    success: bool = Field(description="Whether operation completed successfully")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    
    def duration_seconds(self) -> float:
        """Calculate operation duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "operation_type": "cleanup_old_entries",
                "started_at": "2025-10-20T02:00:00Z",
                "completed_at": "2025-10-20T02:15:30Z",
                "cache_entries_before": 1250,
                "cache_entries_after": 980,
                "cache_size_before_mb": 156.7,
                "cache_size_after_mb": 124.3,
                "entries_removed": 270,
                "space_recovered_mb": 32.4,
                "success": True
            }
        }


# =============================================
# PERMISSION AND SECURITY MODELS
# =============================================

class CacheManagementPermissions(BaseModel):
    """
    Cache management permission checking.
    
    Defines the required permissions for different
    cache management operations.
    """
    
    user_id: str = Field(description="User identifier")
    can_view_cache_stats: bool = Field(description="Can view cache statistics")
    can_clear_collection_cache: bool = Field(description="Can clear collection cache")
    can_clear_video_cache: bool = Field(description="Can clear video cache")
    can_clear_all_cache: bool = Field(description="Can perform destructive full clear")
    can_run_maintenance: bool = Field(description="Can run cache maintenance operations")
    
    # Permission levels
    is_cache_manager: bool = Field(description="Has cache manager role")
    is_developer: bool = Field(description="Has developer role")
    is_admin: bool = Field(description="Has admin role")
    
    @validator('can_clear_all_cache')
    def admin_required_for_full_clear(cls, v, values):
        """Ensure only admins can clear all cache."""
        if v and not values.get('is_admin', False):
            raise ValueError('Admin role required for full cache clearing')
        return v
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "user_id": "user123",
                "can_view_cache_stats": True,
                "can_clear_collection_cache": True,
                "can_clear_video_cache": True,
                "can_clear_all_cache": False,
                "can_run_maintenance": True,
                "is_cache_manager": True,
                "is_developer": True,
                "is_admin": False
            }
        }


# =============================================
# MODEL REGISTRY
# =============================================

# Export all models for easy importing
__all__ = [
    # Request Models
    'ClearCollectionCacheRequest',
    'ClearVideoCacheRequest',
    
    # Response Models
    'ClearCacheResponse',
    'CacheStatusResponse',
    
    # Statistics Models
    'CacheStatistics',
    'ClearCacheStats',
    'CacheEfficiencyMetrics',
    'CacheMaintenanceReport',
    
    # Permission Models
    'CacheManagementPermissions'
]