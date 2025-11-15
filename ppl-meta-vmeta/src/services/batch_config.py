"""
Batch Configuration Service
PPL Meta Platform - Continuous Individuals and MVR Pipeline

Service for loading and managing batch processing configuration from
YAML files and PostgreSQL database with hierarchical config resolution.

Created: November 13, 2025
Author: PPL Meta Platform Team
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from models.batch_processing import BatchProcessingConfig
from database.batch_repository import BatchProcessingRepository


logger = logging.getLogger(__name__)


class BatchConfigService:
    """
    Service for managing batch processing configuration.
    
    Handles:
    - Loading YAML configuration file
    - Reading database configuration
    - Hierarchical config resolution (collection -> global)
    - Configuration caching
    - Dynamic config updates
    """
    
    def __init__(
        self,
        repository: BatchProcessingRepository,
        config_path: Optional[str] = None
    ):
        """
        Initialize batch configuration service.
        
        Args:
            repository: Database repository for config queries
            config_path: Path to batch_processing.yml file
        """
        self.repository = repository
        self.config_path = config_path or self._get_default_config_path()
        
        # Configuration cache
        self._yaml_config: Optional[Dict[str, Any]] = None
        self._global_db_config: Optional[BatchProcessingConfig] = None
        self._collection_configs: Dict[str, BatchProcessingConfig] = {}
        
        # Cache timestamps
        self._yaml_loaded_at: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes
        
        logger.info(
            f"BatchConfigService initialized with config: {self.config_path}"
        )
    
    def _get_default_config_path(self) -> str:
        """Get default path to batch_processing.yml."""
        # Try environment variable first
        env_path = os.getenv('BATCH_PROCESSING_CONFIG_PATH')
        if env_path and Path(env_path).exists():
            return env_path
        
        # Try standard locations
        candidates = [
            Path(__file__).parent.parent.parent / 'config' / 'batch_processing.yml',
            Path.cwd() / 'config' / 'batch_processing.yml',
            Path('/etc/ppl-meta/batch_processing.yml'),
        ]
        
        for path in candidates:
            if path.exists():
                return str(path)
        
        # Return first candidate as default
        return str(candidates[0])
    
    def _should_reload_yaml(self) -> bool:
        """Check if YAML config should be reloaded."""
        if not self._yaml_loaded_at:
            return True
        
        age = (datetime.utcnow() - self._yaml_loaded_at).total_seconds()
        return age > self._cache_ttl_seconds
    
    def load_yaml_config(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load batch processing configuration from YAML file.
        
        Args:
            force_reload: Force reload even if cached
            
        Returns:
            Dictionary with configuration data
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        if not force_reload and self._yaml_config and not self._should_reload_yaml():
            return self._yaml_config
        
        config_path = Path(self.config_path)
        
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            # Return minimal default config
            return self._get_default_yaml_config()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._yaml_config = yaml.safe_load(f)
            
            self._yaml_loaded_at = datetime.utcnow()
            logger.info(f"Loaded YAML config from {config_path}")
            
            return self._yaml_config
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML config: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load YAML config: {e}")
            raise
    
    def _get_default_yaml_config(self) -> Dict[str, Any]:
        """Get default YAML configuration."""
        return {
            'global': {
                'batch_size_threshold': 5,
                'partial_batch': {
                    'min_videos': 2,
                    'timeout_minutes': 10,
                    'max_wait_hours': 24,
                    'recording_stop_event': {'enabled': True, 'trigger_delay_seconds': 2},
                    'timeout_fallback': {'enabled': True}
                },
                'concurrency': {
                    'max_concurrent_batches': 3,
                    'worker_pool_size': 3
                },
                'resources': {
                    'max_batch_memory_gb': 2,
                    'max_videos_per_session': 10,
                    'max_processing_time_seconds': 300
                },
                'events': {
                    'event_triggering_enabled': True,
                    'polling_fallback_enabled': True,
                    'polling_interval_seconds': 30
                }
            }
        }
    
    async def get_global_config(
        self,
        force_reload: bool = False
    ) -> BatchProcessingConfig:
        """
        Get global batch processing configuration.
        
        Reads from database with fallback to YAML defaults.
        
        Args:
            force_reload: Force reload from database
            
        Returns:
            Global batch processing configuration
        """
        if not force_reload and self._global_db_config:
            return self._global_db_config
        
        try:
            # Try to get from database
            result = await self.repository.fetch_one(
                """
                SELECT * FROM batch_processing_config
                WHERE collection_id IS NULL
                """
            )
            
            if result:
                self._global_db_config = BatchProcessingConfig(**result)
                logger.debug("Loaded global config from database")
                return self._global_db_config
            
        except Exception as e:
            logger.warning(f"Failed to load global config from database: {e}")
        
        # Fallback to YAML
        yaml_config = self.load_yaml_config()
        global_yaml = yaml_config.get('global', {})
        
        self._global_db_config = self._yaml_to_config_model(global_yaml)
        logger.debug("Using global config from YAML")
        
        return self._global_db_config
    
    async def get_collection_config(
        self,
        collection_id: str,
        force_reload: bool = False
    ) -> BatchProcessingConfig:
        """
        Get configuration for specific collection.
        
        Resolution order:
        1. Collection-specific database config
        2. Collection-specific YAML config
        3. Global database config
        4. Global YAML config
        
        Args:
            collection_id: Collection identifier
            force_reload: Force reload from database
            
        Returns:
            Effective configuration for collection
        """
        # Check cache
        if not force_reload and collection_id in self._collection_configs:
            return self._collection_configs[collection_id]
        
        try:
            # Try collection-specific database config
            result = await self.repository.fetch_one(
                """
                SELECT * FROM batch_processing_config
                WHERE collection_id = %s
                """,
                (collection_id,)
            )
            
            if result:
                config = BatchProcessingConfig(**result)
                self._collection_configs[collection_id] = config
                logger.debug(f"Loaded config for {collection_id} from database")
                return config
        
        except Exception as e:
            logger.warning(
                f"Failed to load collection config from database: {e}"
            )
        
        # Try YAML collection config
        yaml_config = self.load_yaml_config()
        collections = yaml_config.get('collections', {})
        
        if collection_id in collections:
            collection_yaml = collections[collection_id]
            config = self._yaml_to_config_model(
                collection_yaml,
                collection_id=collection_id
            )
            self._collection_configs[collection_id] = config
            logger.debug(f"Loaded config for {collection_id} from YAML")
            return config
        
        # Fallback to global config
        global_config = await self.get_global_config()
        self._collection_configs[collection_id] = global_config
        logger.debug(f"Using global config for {collection_id}")
        
        return global_config
    
    def _yaml_to_config_model(
        self,
        yaml_data: Dict[str, Any],
        collection_id: Optional[str] = None
    ) -> BatchProcessingConfig:
        """
        Convert YAML configuration to BatchProcessingConfig model.
        
        Args:
            yaml_data: YAML configuration dictionary
            collection_id: Collection ID if collection-specific
            
        Returns:
            BatchProcessingConfig instance
        """
        partial = yaml_data.get('partial_batch', {})
        concurrency = yaml_data.get('concurrency', {})
        resources = yaml_data.get('resources', {})
        events = yaml_data.get('events', {})
        
        rec_stop = partial.get('recording_stop_event', {})
        timeout_fb = partial.get('timeout_fallback', {})
        
        return BatchProcessingConfig(
            collection_id=collection_id,
            batch_size_threshold=yaml_data.get('batch_size_threshold', 5),
            
            # Partial batch
            partial_batch_min_videos=partial.get('min_videos', 2),
            partial_batch_timeout_minutes=partial.get('timeout_minutes', 10),
            partial_batch_max_wait_hours=partial.get('max_wait_hours', 24),
            
            # Recording stop event
            enable_recording_stop_event=rec_stop.get('enabled', True),
            recording_stop_trigger_delay_seconds=rec_stop.get(
                'trigger_delay_seconds', 2
            ),
            
            # Timeout fallback
            enable_timeout_fallback=timeout_fb.get('enabled', True),
            
            # Concurrency
            max_concurrent_batches=concurrency.get('max_concurrent_batches', 3),
            worker_pool_size=concurrency.get('worker_pool_size', 3),
            
            # Resources
            max_batch_memory_gb=resources.get('max_batch_memory_gb', 2),
            max_videos_per_session=resources.get('max_videos_per_session', 10),
            max_processing_time_seconds=resources.get(
                'max_processing_time_seconds', 300
            ),
            
            # Events
            enable_event_triggering=events.get('event_triggering_enabled', True),
            enable_polling_fallback=events.get('polling_fallback_enabled', True),
            polling_interval_seconds=events.get('polling_interval_seconds', 30)
        )
    
    async def update_batch_size(
        self,
        batch_size: int,
        collection_id: Optional[str] = None
    ) -> BatchProcessingConfig:
        """
        Update batch size threshold in database.
        
        Args:
            batch_size: New batch size (2-50)
            collection_id: Collection ID or None for global
            
        Returns:
            Updated configuration
            
        Raises:
            ValueError: If batch size is invalid
        """
        if batch_size < 2 or batch_size > 50:
            raise ValueError("Batch size must be between 2 and 50")
        
        try:
            # Use database function to update
            await self.repository.execute(
                "SELECT update_batch_size(%s, %s)",
                (collection_id, batch_size)
            )
            
            logger.info(
                f"Updated batch size to {batch_size} for "
                f"{'global' if not collection_id else collection_id}"
            )
            
            # Invalidate cache
            if collection_id:
                self._collection_configs.pop(collection_id, None)
            else:
                self._global_db_config = None
            
            # Return updated config
            if collection_id:
                return await self.get_collection_config(collection_id, force_reload=True)
            else:
                return await self.get_global_config(force_reload=True)
        
        except Exception as e:
            logger.error(f"Failed to update batch size: {e}")
            raise
    
    def calculate_timeout(
        self,
        config: BatchProcessingConfig,
        last_video_time: Optional[datetime] = None
    ) -> datetime:
        """
        Calculate when batch should timeout.
        
        Args:
            config: Batch processing configuration
            last_video_time: Time of last video, defaults to now
            
        Returns:
            Timeout datetime
        """
        if not last_video_time:
            last_video_time = datetime.utcnow()
        
        timeout_delta = timedelta(minutes=config.partial_batch_timeout_minutes)
        return last_video_time + timeout_delta
    
    def is_timeout_enabled(self, config: BatchProcessingConfig) -> bool:
        """
        Check if timeout fallback is enabled.
        
        Args:
            config: Batch processing configuration
            
        Returns:
            True if timeout is enabled
        """
        return config.enable_timeout_fallback
    
    def is_recording_stop_enabled(self, config: BatchProcessingConfig) -> bool:
        """
        Check if recording stop event is enabled.
        
        Args:
            config: Batch processing configuration
            
        Returns:
            True if recording stop event is enabled
        """
        return config.enable_recording_stop_event
    
    def clear_cache(self):
        """Clear all cached configurations."""
        self._yaml_config = None
        self._global_db_config = None
        self._collection_configs.clear()
        self._yaml_loaded_at = None
        logger.info("Configuration cache cleared")
