"""
Unit Tests for Batch Configuration Service
PPL Meta Platform - Continuous Individuals and MVR Pipeline

Tests for batch configuration loading, caching, and hierarchical resolution.

Created: November 13, 2025
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from datetime import datetime, timedelta
from uuid import uuid4
import yaml

from src.models.batch_processing import BatchProcessingConfig
from src.services.batch_config import BatchConfigService


@pytest.fixture
def mock_repository():
    """Mock database repository."""
    repo = Mock()
    repo.fetch_one = AsyncMock()
    repo.execute = AsyncMock()
    return repo


@pytest.fixture
def sample_yaml_config():
    """Sample YAML configuration."""
    return {
        'global': {
            'batch_size_threshold': 5,
            'partial_batch': {
                'min_videos': 2,
                'timeout_minutes': 10,
                'max_wait_hours': 24,
                'recording_stop_event': {
                    'enabled': True,
                    'trigger_delay_seconds': 2
                },
                'timeout_fallback': {
                    'enabled': True
                }
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
        },
        'collections': {
            'test-collection-123': {
                'batch_size_threshold': 3,
                'partial_batch': {
                    'min_videos': 1,
                    'timeout_minutes': 5
                }
            }
        }
    }


@pytest.fixture
def config_service(mock_repository, sample_yaml_config, tmp_path):
    """Create config service with mocked dependencies."""
    config_file = tmp_path / "batch_processing.yml"
    with open(config_file, 'w') as f:
        yaml.dump(sample_yaml_config, f)
    
    service = BatchConfigService(
        repository=mock_repository,
        config_path=str(config_file)
    )
    return service


class TestBatchConfigService:
    """Test suite for BatchConfigService."""
    
    def test_initialization(self, mock_repository, tmp_path):
        """Test service initialization."""
        config_path = str(tmp_path / "test_config.yml")
        service = BatchConfigService(mock_repository, config_path)
        
        assert service.repository == mock_repository
        assert service.config_path == config_path
        assert service._yaml_config is None
        assert service._global_db_config is None
        assert len(service._collection_configs) == 0
    
    def test_load_yaml_config(self, config_service, sample_yaml_config):
        """Test YAML configuration loading."""
        config = config_service.load_yaml_config()
        
        assert config is not None
        assert config['global']['batch_size_threshold'] == 5
        assert 'test-collection-123' in config['collections']
    
    def test_yaml_config_caching(self, config_service):
        """Test YAML configuration caching."""
        # First load
        config1 = config_service.load_yaml_config()
        load_time1 = config_service._yaml_loaded_at
        
        # Second load (should use cache)
        config2 = config_service.load_yaml_config()
        load_time2 = config_service._yaml_loaded_at
        
        assert config1 == config2
        assert load_time1 == load_time2
    
    def test_yaml_config_force_reload(self, config_service):
        """Test forced YAML configuration reload."""
        # First load
        config_service.load_yaml_config()
        load_time1 = config_service._yaml_loaded_at
        
        # Force reload
        config_service.load_yaml_config(force_reload=True)
        load_time2 = config_service._yaml_loaded_at
        
        assert load_time2 > load_time1
    
    @pytest.mark.asyncio
    async def test_get_global_config_from_db(self, config_service, mock_repository):
        """Test getting global config from database."""
        # Mock database response
        mock_repository.fetch_one.return_value = {
            'id': 1,
            'collection_id': None,
            'batch_size_threshold': 7,
            'partial_batch_min_videos': 3,
            'partial_batch_timeout_minutes': 15,
            'partial_batch_max_wait_hours': 48,
            'enable_recording_stop_event': True,
            'recording_stop_trigger_delay_seconds': 5,
            'enable_timeout_fallback': True,
            'max_concurrent_batches': 5,
            'worker_pool_size': 5,
            'max_batch_memory_gb': 4,
            'max_videos_per_session': 20,
            'max_processing_time_seconds': 600,
            'enable_event_triggering': True,
            'enable_polling_fallback': False,
            'polling_interval_seconds': 60,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        config = await config_service.get_global_config()
        
        assert config is not None
        assert config.batch_size_threshold == 7
        assert config.collection_id is None
        mock_repository.fetch_one.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_global_config_fallback_to_yaml(
        self, config_service, mock_repository
    ):
        """Test global config falls back to YAML when DB fails."""
        # Mock database returns None
        mock_repository.fetch_one.return_value = None
        
        config = await config_service.get_global_config()
        
        assert config is not None
        assert config.batch_size_threshold == 5  # From YAML
        assert config.partial_batch_min_videos == 2
    
    @pytest.mark.asyncio
    async def test_get_collection_config_from_db(
        self, config_service, mock_repository
    ):
        """Test getting collection-specific config from database."""
        collection_id = 'test-collection-456'
        
        # Mock database response
        mock_repository.fetch_one.return_value = {
            'id': 2,
            'collection_id': collection_id,
            'batch_size_threshold': 10,
            'partial_batch_min_videos': 5,
            'partial_batch_timeout_minutes': 20,
            'partial_batch_max_wait_hours': 24,
            'enable_recording_stop_event': False,
            'recording_stop_trigger_delay_seconds': 0,
            'enable_timeout_fallback': True,
            'max_concurrent_batches': 2,
            'worker_pool_size': 2,
            'max_batch_memory_gb': 1,
            'max_videos_per_session': 5,
            'max_processing_time_seconds': 180,
            'enable_event_triggering': True,
            'enable_polling_fallback': True,
            'polling_interval_seconds': 45,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        config = await config_service.get_collection_config(collection_id)
        
        assert config is not None
        assert config.collection_id == collection_id
        assert config.batch_size_threshold == 10
    
    @pytest.mark.asyncio
    async def test_get_collection_config_from_yaml(self, config_service, mock_repository):
        """Test getting collection config from YAML."""
        collection_id = 'test-collection-123'
        
        # Mock database returns None (no DB config)
        mock_repository.fetch_one.return_value = None
        
        config = await config_service.get_collection_config(collection_id)
        
        assert config is not None
        assert config.batch_size_threshold == 3  # From YAML override
        assert config.partial_batch_min_videos == 1
    
    @pytest.mark.asyncio
    async def test_get_collection_config_fallback_to_global(
        self, config_service, mock_repository
    ):
        """Test collection config falls back to global."""
        collection_id = 'unknown-collection'
        
        # Mock database returns None for both collection and global
        mock_repository.fetch_one.return_value = None
        
        config = await config_service.get_collection_config(collection_id)
        
        assert config is not None
        assert config.batch_size_threshold == 5  # From global YAML
    
    @pytest.mark.asyncio
    async def test_update_batch_size(self, config_service, mock_repository):
        """Test updating batch size."""
        collection_id = 'test-collection'
        new_size = 8
        
        # Mock successful update
        mock_repository.execute.return_value = None
        mock_repository.fetch_one.return_value = {
            'id': 1,
            'collection_id': collection_id,
            'batch_size_threshold': new_size,
            'partial_batch_min_videos': 2,
            'partial_batch_timeout_minutes': 10,
            'partial_batch_max_wait_hours': 24,
            'enable_recording_stop_event': True,
            'recording_stop_trigger_delay_seconds': 2,
            'enable_timeout_fallback': True,
            'max_concurrent_batches': 3,
            'worker_pool_size': 3,
            'max_batch_memory_gb': 2,
            'max_videos_per_session': 10,
            'max_processing_time_seconds': 300,
            'enable_event_triggering': True,
            'enable_polling_fallback': True,
            'polling_interval_seconds': 30,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        config = await config_service.update_batch_size(new_size, collection_id)
        
        assert config.batch_size_threshold == new_size
        mock_repository.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_batch_size_validation(self, config_service):
        """Test batch size validation."""
        with pytest.raises(ValueError, match="between 2 and 50"):
            await config_service.update_batch_size(1, 'test')
        
        with pytest.raises(ValueError, match="between 2 and 50"):
            await config_service.update_batch_size(51, 'test')
    
    def test_calculate_timeout(self, config_service):
        """Test timeout calculation."""
        config = BatchProcessingConfig(
            batch_size_threshold=5,
            partial_batch_timeout_minutes=10
        )
        
        now = datetime.utcnow()
        timeout = config_service.calculate_timeout(config, now)
        
        expected = now + timedelta(minutes=10)
        assert abs((timeout - expected).total_seconds()) < 1
    
    def test_is_timeout_enabled(self, config_service):
        """Test timeout enabled check."""
        config_enabled = BatchProcessingConfig(
            batch_size_threshold=5,
            enable_timeout_fallback=True
        )
        config_disabled = BatchProcessingConfig(
            batch_size_threshold=5,
            enable_timeout_fallback=False
        )
        
        assert config_service.is_timeout_enabled(config_enabled)
        assert not config_service.is_timeout_enabled(config_disabled)
    
    def test_is_recording_stop_enabled(self, config_service):
        """Test recording stop enabled check."""
        config_enabled = BatchProcessingConfig(
            batch_size_threshold=5,
            enable_recording_stop_event=True
        )
        config_disabled = BatchProcessingConfig(
            batch_size_threshold=5,
            enable_recording_stop_event=False
        )
        
        assert config_service.is_recording_stop_enabled(config_enabled)
        assert not config_service.is_recording_stop_enabled(config_disabled)
    
    def test_clear_cache(self, config_service):
        """Test cache clearing."""
        # Load some config to populate cache
        config_service.load_yaml_config()
        config_service._global_db_config = Mock()
        config_service._collection_configs['test'] = Mock()
        
        # Clear cache
        config_service.clear_cache()
        
        assert config_service._yaml_config is None
        assert config_service._global_db_config is None
        assert len(config_service._collection_configs) == 0
        assert config_service._yaml_loaded_at is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
