"""
Configuration Management
PPL Meta Platform - Cross-Video Individual Tracking

Handles runtime configuration management, parameter validation,
and algorithm settings for cross-video individual tracking.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import hashlib

# TODO: Fix relative import issue for cross-video tracking models
# from ..models.cross_video_tracking import CrossVideoTrackingConfig

logger = logging.getLogger(__name__)


@dataclass
class RuntimeSettings:
    """Runtime settings for cross-video tracking algorithm."""
    
    # Processing settings
    max_concurrent_videos: int = 5
    batch_size: int = 100
    cache_ttl_hours: int = 24
    
    # Performance settings
    enable_gpu_acceleration: bool = True
    memory_limit_mb: int = 4096
    timeout_seconds: int = 300
    
    # Debug settings
    enable_debug_logging: bool = False
    save_intermediate_results: bool = False
    debug_output_dir: Optional[str] = None
    
    # API settings
    max_sessions_per_user: int = 10
    session_cleanup_days: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'max_concurrent_videos': self.max_concurrent_videos,
            'batch_size': self.batch_size,
            'cache_ttl_hours': self.cache_ttl_hours,
            'enable_gpu_acceleration': self.enable_gpu_acceleration,
            'memory_limit_mb': self.memory_limit_mb,
            'timeout_seconds': self.timeout_seconds,
            'enable_debug_logging': self.enable_debug_logging,
            'save_intermediate_results': self.save_intermediate_results,
            'debug_output_dir': self.debug_output_dir,
            'max_sessions_per_user': self.max_sessions_per_user,
            'session_cleanup_days': self.session_cleanup_days
        }


class ConfigurationManager:
    """Manages algorithm configurations and runtime settings."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration manager."""
        self.config_file = config_file
        self.runtime_settings = RuntimeSettings()
        self.algorithm_configs: Dict[str, CrossVideoTrackingConfig] = {}
        self.default_config_name: Optional[str] = None
        
        # Load configurations if file provided
        if config_file:
            self.load_from_file(config_file)
        else:
            self._load_default_configs()
    
    def _load_default_configs(self) -> None:
        """Load default algorithm configurations."""
        logger.info("🔧 Loading default algorithm configurations...")
        
        # Fast processing configuration
        fast_config = CrossVideoTrackingConfig(
            config_name="fast_processing",
            description="Fast processing with lower accuracy",
            max_gap_seconds=10.0,
            iou_threshold=0.4,
            min_overlap_confidence=0.6,
            face_similarity_threshold=0.60,
            max_individuals_per_session=200,
            consolidation_window_minutes=30,
            enable_face_clustering=False,
            clustering_threshold=0.8,
            min_cluster_size=3,
            enable_temporal_smoothing=True,
            temporal_window_seconds=5.0,
            enable_cross_collection_tracking=False,
            is_default=False
        )
        
        # Balanced configuration (default)
        balanced_config = CrossVideoTrackingConfig(
            config_name="balanced",
            description="Balanced accuracy and performance",
            max_gap_seconds=5.0,
            iou_threshold=0.3,
            min_overlap_confidence=0.5,
            face_similarity_threshold=0.60,
            max_individuals_per_session=500,
            consolidation_window_minutes=15,
            enable_face_clustering=True,
            clustering_threshold=0.85,
            min_cluster_size=2,
            enable_temporal_smoothing=True,
            temporal_window_seconds=3.0,
            enable_cross_collection_tracking=True,
            is_default=True
        )
        
        # High accuracy configuration
        accurate_config = CrossVideoTrackingConfig(
            config_name="high_accuracy",
            description="High accuracy with detailed analysis",
            max_gap_seconds=3.0,
            iou_threshold=0.2,
            min_overlap_confidence=0.4,
            face_similarity_threshold=0.60,
            max_individuals_per_session=1000,
            consolidation_window_minutes=10,
            enable_face_clustering=True,
            clustering_threshold=0.9,
            min_cluster_size=2,
            enable_temporal_smoothing=True,
            temporal_window_seconds=2.0,
            enable_cross_collection_tracking=True,
            is_default=False
        )
        
        # Store configurations
        self.algorithm_configs = {
            "fast_processing": fast_config,
            "balanced": balanced_config,
            "high_accuracy": accurate_config
        }
        
        self.default_config_name = "balanced"
        
        logger.info(f"✅ Loaded {len(self.algorithm_configs)} default configurations")
    
    def load_from_file(self, config_file: str) -> bool:
        """Load configurations from JSON file."""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                logger.warning(f"⚠️ Config file not found: {config_file}")
                self._load_default_configs()
                return False
            
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            # Load runtime settings
            if 'runtime_settings' in config_data:
                runtime_data = config_data['runtime_settings']
                self.runtime_settings = RuntimeSettings(**runtime_data)
                logger.info("✅ Loaded runtime settings from file")
            
            # Load algorithm configurations
            if 'algorithm_configs' in config_data:
                self.algorithm_configs = {}
                
                for config_name, config_dict in config_data['algorithm_configs'].items():
                    try:
                        config = CrossVideoTrackingConfig(**config_dict)
                        self.algorithm_configs[config_name] = config
                        
                        if config.is_default:
                            self.default_config_name = config_name
                            
                    except Exception as e:
                        logger.error(f"❌ Failed to load config {config_name}: {e}")
                
                logger.info(f"✅ Loaded {len(self.algorithm_configs)} algorithm configs")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load config from {config_file}: {e}")
            self._load_default_configs()
            return False
    
    def save_to_file(self, config_file: str) -> bool:
        """Save configurations to JSON file."""
        try:
            config_data = {
                'runtime_settings': self.runtime_settings.to_dict(),
                'algorithm_configs': {
                    name: config.dict() 
                    for name, config in self.algorithm_configs.items()
                },
                'metadata': {
                    'saved_at': datetime.utcnow().isoformat(),
                    'version': '1.0',
                    'default_config': self.default_config_name
                }
            }
            
            config_path = Path(config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2, default=str)
            
            logger.info(f"✅ Saved configurations to {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save config to {config_file}: {e}")
            return False
    
    def get_config(self, config_name: str) -> Optional[CrossVideoTrackingConfig]:
        """Get algorithm configuration by name."""
        return self.algorithm_configs.get(config_name)
    
    def get_default_config(self) -> Optional[CrossVideoTrackingConfig]:
        """Get default algorithm configuration."""
        if self.default_config_name:
            return self.algorithm_configs.get(self.default_config_name)
        
        # Fallback to first available config
        if self.algorithm_configs:
            return next(iter(self.algorithm_configs.values()))
        
        return None
    
    def add_config(
        self, 
        config: CrossVideoTrackingConfig, 
        set_as_default: bool = False
    ) -> bool:
        """Add new algorithm configuration."""
        try:
            # Validate configuration
            if not self.validate_config(config):
                logger.error(f"❌ Invalid configuration: {config.config_name}")
                return False
            
            # If setting as default, unset current default
            if set_as_default:
                for existing_config in self.algorithm_configs.values():
                    existing_config.is_default = False
                config.is_default = True
                self.default_config_name = config.config_name
            
            self.algorithm_configs[config.config_name] = config
            logger.info(f"✅ Added configuration: {config.config_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add config {config.config_name}: {e}")
            return False
    
    def remove_config(self, config_name: str) -> bool:
        """Remove algorithm configuration."""
        if config_name not in self.algorithm_configs:
            logger.warning(f"⚠️ Configuration not found: {config_name}")
            return False
        
        # Don't allow removing default config if it's the only one
        if (config_name == self.default_config_name and 
            len(self.algorithm_configs) == 1):
            logger.error("❌ Cannot remove the only configuration")
            return False
        
        del self.algorithm_configs[config_name]
        
        # Set new default if removed config was default
        if config_name == self.default_config_name:
            if self.algorithm_configs:
                new_default = next(iter(self.algorithm_configs.keys()))
                self.algorithm_configs[new_default].is_default = True
                self.default_config_name = new_default
                logger.info(f"🔄 Set new default configuration: {new_default}")
            else:
                self.default_config_name = None
        
        logger.info(f"✅ Removed configuration: {config_name}")
        return True
    
    def list_configs(self) -> List[Dict[str, Any]]:
        """List all available configurations."""
        configs = []
        for name, config in self.algorithm_configs.items():
            configs.append({
                'name': name,
                'description': config.description,
                'is_default': config.is_default,
                'hash': config.get_hash(),
                'parameters': {
                    'max_gap_seconds': config.max_gap_seconds,
                    'face_similarity_threshold': config.face_similarity_threshold,
                    'max_individuals_per_session': config.max_individuals_per_session,
                    'enable_face_clustering': config.enable_face_clustering,
                    'enable_cross_collection_tracking': config.enable_cross_collection_tracking
                }
            })
        
        return sorted(configs, key=lambda x: (not x['is_default'], x['name']))
    
    def validate_config(self, config: CrossVideoTrackingConfig) -> bool:
        """Validate algorithm configuration."""
        try:
            # Basic validation
            if not config.config_name or not config.config_name.strip():
                logger.error("❌ Configuration name cannot be empty")
                return False
            
            # Parameter range validation
            validations = [
                (0.1 <= config.max_gap_seconds <= 60.0, 
                 "max_gap_seconds must be between 0.1 and 60.0"),
                (0.0 <= config.iou_threshold <= 1.0, 
                 "iou_threshold must be between 0.0 and 1.0"),
                (0.0 <= config.min_overlap_confidence <= 1.0, 
                 "min_overlap_confidence must be between 0.0 and 1.0"),
                (0.5 <= config.face_similarity_threshold <= 1.0, 
                 "face_similarity_threshold must be between 0.5 and 1.0"),
                (1 <= config.max_individuals_per_session <= 10000, 
                 "max_individuals_per_session must be between 1 and 10000"),
                (1 <= config.consolidation_window_minutes <= 120, 
                 "consolidation_window_minutes must be between 1 and 120"),
            ]
            
            for condition, message in validations:
                if not condition:
                    logger.error(f"❌ {message}")
                    return False
            
            # Clustering validation
            if config.enable_face_clustering:
                if not (0.5 <= config.clustering_threshold <= 1.0):
                    logger.error("❌ clustering_threshold must be between 0.5 and 1.0")
                    return False
                
                if not (1 <= config.min_cluster_size <= 10):
                    logger.error("❌ min_cluster_size must be between 1 and 10")
                    return False
            
            # Temporal smoothing validation
            if config.enable_temporal_smoothing:
                if not (0.1 <= config.temporal_window_seconds <= 30.0):
                    logger.error("❌ temporal_window_seconds must be between 0.1 and 30.0")
                    return False
            
            logger.info(f"✅ Configuration validation passed: {config.config_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            return False
    
    def create_config_hash(self, config: CrossVideoTrackingConfig) -> str:
        """Create hash for configuration."""
        # Use algorithm-relevant parameters only
        relevant_params = {
            'max_gap_seconds': config.max_gap_seconds,
            'iou_threshold': config.iou_threshold,
            'min_overlap_confidence': config.min_overlap_confidence,
            'face_similarity_threshold': config.face_similarity_threshold,
            'enable_face_clustering': config.enable_face_clustering,
            'clustering_threshold': config.clustering_threshold,
            'enable_temporal_smoothing': config.enable_temporal_smoothing,
            'temporal_window_seconds': config.temporal_window_seconds,
            'enable_cross_collection_tracking': config.enable_cross_collection_tracking
        }
        
        config_str = json.dumps(relevant_params, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def update_runtime_settings(self, **kwargs) -> None:
        """Update runtime settings."""
        for key, value in kwargs.items():
            if hasattr(self.runtime_settings, key):
                setattr(self.runtime_settings, key, value)
                logger.info(f"✅ Updated runtime setting {key}: {value}")
            else:
                logger.warning(f"⚠️ Unknown runtime setting: {key}")
    
    def get_runtime_settings(self) -> RuntimeSettings:
        """Get current runtime settings."""
        return self.runtime_settings
    
    def reset_to_defaults(self) -> None:
        """Reset all configurations to defaults."""
        logger.info("🔄 Resetting configurations to defaults...")
        self.runtime_settings = RuntimeSettings()
        self._load_default_configs()
        logger.info("✅ Reset to default configurations completed")


# Global configuration manager instance
config_manager = ConfigurationManager()


def get_config_manager() -> ConfigurationManager:
    """Get global configuration manager instance."""
    return config_manager


def initialize_config_manager(config_file: Optional[str] = None) -> ConfigurationManager:
    """Initialize configuration manager with optional config file."""
    global config_manager
    config_manager = ConfigurationManager(config_file)
    return config_manager