"""
Unit Tests for MVRService

Tests MVR-People service layer including automatic creation,
search operations, and integration with ML processor.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

import asyncpg
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.mvr_repository import MVRRepository
from services.mvr_service import MVRService
from ml.mvr_processor import MVRProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestMVRService:
    """Test suite for MVRService."""
    
    @pytest.fixture
    async def db_pool(self):
        """Create database connection pool."""
        pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "ppl_user"),
            password=os.getenv("DB_PASSWORD", "ppl_password"),
            database=os.getenv("DB_NAME", "ppl_meta"),
            min_size=2,
            max_size=10
        )
        yield pool
        await pool.close()
    
    @pytest.fixture
    async def repository(self, db_pool):
        """Create repository instance."""
        return MVRRepository(connection_pool=db_pool)
    
    @pytest.fixture
    def ml_processor(self):
        """Create ML processor instance."""
        return MVRProcessor()
    
    @pytest.fixture
    async def service(self, repository, ml_processor):
        """Create service instance."""
        return MVRService(
            repository=repository,
            ml_processor=ml_processor
        )
    
    @pytest.fixture
    def sample_face_image(self):
        """Generate sample face image."""
        # Create synthetic 224x224x3 RGB image
        return np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    
    async def test_get_mvr_people(self, service, repository):
        """Test retrieving MVR-People by UUID."""
        logger.info("Test: Get MVR-People via Service")
        
        # Create MVR directly via repository
        embedding = np.random.randn(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        mvr_uuid = await repository.create_mvr_people(
            face_embedding=embedding,
            featured_individual_uuid=uuid4(),
            quality_score=0.85
        )
        
        # Retrieve via service
        mvr = await service.get_mvr_people(mvr_uuid)
        
        assert mvr is not None
        assert mvr["mvr_people_uuid"] == mvr_uuid
        logger.info("✅ Retrieved MVR via service")
    
    async def test_search_similar(self, service, repository):
        """Test similarity search via service."""
        logger.info("Test: Search Similar MVR-People")
        
        # Create MVR
        embedding = np.random.randn(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        mvr_uuid = await repository.create_mvr_people(
            face_embedding=embedding,
            featured_individual_uuid=uuid4(),
            quality_score=0.9
        )
        
        # Search
        results = await service.search_similar(
            face_embedding=embedding,
            threshold=0.5,
            limit=10
        )
        
        assert len(results) >= 1
        assert results[0]["mvr_people_uuid"] == mvr_uuid
        logger.info(f"✅ Found {len(results)} similar MVR-People")
    
    async def test_search_by_demographics(self, service, repository):
        """Test demographic search via service."""
        logger.info("Test: Search by Demographics")
        
        # Create MVR with demographics
        embedding = np.random.randn(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        mvr_uuid = await repository.create_mvr_people(
            face_embedding=embedding,
            featured_individual_uuid=uuid4(),
            age_min=30,
            age_max=40,
            gender="female",
            quality_score=0.85
        )
        
        # Search
        results = await service.search_by_demographics(
            age_min=25,
            age_max=45,
            gender="female",
            limit=10
        )
        
        assert len(results) >= 1
        assert any(r["mvr_people_uuid"] == mvr_uuid for r in results)
        logger.info(f"✅ Found {len(results)} matching demographics")
    
    async def test_get_matching_config(self, service):
        """Test retrieving matching configuration."""
        logger.info("Test: Get Matching Config via Service")
        
        config = await service.get_matching_config()
        
        assert config is not None
        assert "similarity_threshold" in config
        logger.info("✅ Retrieved matching config")
    
    async def test_update_matching_config(self, service):
        """Test updating matching configuration."""
        logger.info("Test: Update Matching Config via Service")
        
        success = await service.update_matching_config({
            "similarity_threshold": 0.88
        })
        
        assert success is True
        
        # Verify
        config = await service.get_matching_config()
        assert config["similarity_threshold"] == 0.88
        
        # Restore
        await service.update_matching_config({
            "similarity_threshold": 0.85
        })
        
        logger.info("✅ Updated matching config")
    
    async def test_create_mvr_from_individual_mock(
        self,
        service,
        ml_processor,
        sample_face_image
    ):
        """Test MVR creation with mocked Orchestrator."""
        logger.info("Test: Create MVR from Individual (Mock)")
        
        individual_uuid = uuid4()
        session_uuid = uuid4()
        
        # Mock Orchestrator response
        mock_person_objects = [{
            "person_uuid": str(uuid4()),
            "video_uuid": str(uuid4()),
            "frame_number": 100,
            "bbox": [100, 100, 200, 200],
            "quality_score": 0.9,
            "face_crop": sample_face_image.tolist()
        }]
        
        # Mock the Orchestrator client
        with patch.object(
            service,
            '_fetch_person_objects_for_individual',
            new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_person_objects
            
            # Create MVR
            mvr_data = await service.create_mvr_people_from_individual(
                individual_uuid=individual_uuid,
                session_uuid=session_uuid
            )
            
            assert mvr_data is not None
            assert "mvr_people_uuid" in mvr_data
            assert mvr_data["featured_individual_uuid"] == individual_uuid
            
            logger.info(
                f"✅ Created MVR {mvr_data['mvr_people_uuid']} "
                f"from Individual {individual_uuid}"
            )


async def run_all_tests():
    """Run all service tests."""
    logger.info("=" * 70)
    logger.info("MVRService Test Suite")
    logger.info("=" * 70)
    
    test_instance = TestMVRService()
    
    # Create fixtures
    pool = await asyncpg.create_pool(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        user=os.getenv("DB_USER", "ppl_user"),
        password=os.getenv("DB_PASSWORD", "ppl_password"),
        database=os.getenv("DB_NAME", "ppl_meta"),
        min_size=2,
        max_size=10
    )
    
    repository = MVRRepository(connection_pool=pool)
    ml_processor = MVRProcessor()
    service = MVRService(repository=repository, ml_processor=ml_processor)
    
    try:
        # Run tests
        await test_instance.test_get_mvr_people(service, repository)
        await test_instance.test_search_similar(service, repository)
        await test_instance.test_search_by_demographics(service, repository)
        await test_instance.test_get_matching_config(service)
        await test_instance.test_update_matching_config(service)
        
        # Test with mock
        sample_face_image = np.random.randint(
            0, 255, (224, 224, 3), dtype=np.uint8
        )
        await test_instance.test_create_mvr_from_individual_mock(
            service,
            ml_processor,
            sample_face_image
        )
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ All MVRService tests passed!")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise
    
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
