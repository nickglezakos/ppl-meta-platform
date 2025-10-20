"""
Cross-Video Individual Tracking Models Package
PPL Meta Platform v2.19.13+

This package contains all Pydantic models for the cross-video individual
tracking algorithm including core models, cache management, and API models.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

# Import all models for easy access
try:
    from .cross_video_tracking import (
        # Enums
        SessionStatus,
        ProcessingStatus,
        ProcessingType,
        
        # Core Models
        CrossVideoTrackingConfig,
        BoundingBox,
        VideoAppearance,
        Individual,
        TrackingSession,
        
        # Processing Models
        VideoProcessingState,
        CachedResult,
        SessionIndividual,
        
        # Configuration Models
        AlgorithmConfiguration,
        
        # Utility Functions
        generate_cache_key,
        validate_collections
    )
    
    from .cache_management import (
        # Request Models
        ClearCollectionCacheRequest,
        ClearVideoCacheRequest,
        
        # Response Models
        ClearCacheResponse,
        CacheStatusResponse,
        
        # Statistics Models
        CacheStatistics,
        ClearCacheStats,
        CacheEfficiencyMetrics,
        CacheMaintenanceReport,
        
        # Permission Models
        CacheManagementPermissions
    )
    
    MODELS_AVAILABLE = True
    
except ImportError as e:
    # Fallback for development when pydantic might not be installed
    print(f"Warning: Could not import cross-video tracking models: {e}")
    print("This is expected during development setup.")
    MODELS_AVAILABLE = False


# Version information
__version__ = "1.0.0"
__author__ = "PPL Meta Platform Team"
__created__ = "2025-10-20"

# Model registry for validation and documentation
MODEL_REGISTRY = {
    "core_models": [
        "CrossVideoTrackingConfig",
        "BoundingBox", 
        "VideoAppearance",
        "Individual",
        "TrackingSession"
    ],
    "processing_models": [
        "VideoProcessingState",
        "CachedResult",
        "SessionIndividual"
    ],
    "cache_models": [
        "ClearCollectionCacheRequest",
        "ClearVideoCacheRequest",
        "ClearCacheResponse", 
        "CacheStatusResponse",
        "CacheStatistics",
        "ClearCacheStats"
    ],
    "config_models": [
        "AlgorithmConfiguration"
    ]
}

# Export all available models
if MODELS_AVAILABLE:
    __all__ = [
        # Core Models
        "CrossVideoTrackingConfig",
        "BoundingBox",
        "VideoAppearance", 
        "Individual",
        "TrackingSession",
        
        # Processing Models
        "VideoProcessingState",
        "CachedResult",
        "SessionIndividual",
        
        # Cache Management Models
        "ClearCollectionCacheRequest",
        "ClearVideoCacheRequest",
        "ClearCacheResponse",
        "CacheStatusResponse",
        "CacheStatistics",
        "ClearCacheStats",
        
        # Configuration Models
        "AlgorithmConfiguration",
        
        # Enums
        "SessionStatus",
        "ProcessingStatus", 
        "ProcessingType",
        
        # Utilities
        "generate_cache_key",
        "validate_collections",
        
        # Package info
        "MODELS_AVAILABLE",
        "MODEL_REGISTRY"
    ]
else:
    __all__ = ["MODELS_AVAILABLE", "MODEL_REGISTRY"]


def get_model_info():
    """Get information about available models."""
    return {
        "models_available": MODELS_AVAILABLE,
        "version": __version__,
        "created": __created__,
        "model_count": sum(len(models) for models in MODEL_REGISTRY.values()),
        "model_registry": MODEL_REGISTRY
    }