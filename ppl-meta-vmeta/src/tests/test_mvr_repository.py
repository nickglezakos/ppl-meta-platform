"""
Unit Tests for MVRRepository

Tests database operations including CRUD, similarity search,
merge operations, and configuration management.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4, UUID
from typing import Optional

import asyncpg
import numpy as np
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.mvr_repository import MVRRepository, MVRRepositoryError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestMVRRepository:
    """Test suite for MVRRepository."""
    
    @pytest.fixture
    async def db_pool(self):
        """Create database connection pool for testing."""
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
    def sample_embedding(self):
        """Generate sample face embedding."""
        embedding = np.random.randn(512).astype(np.float32)
        # Normalize
        embedding = embedding / np.linalg.norm(embedding)
        return embedding
    
    @pytest.fixture
    def sample_mvr_data(self, sample_embedding):
        """Generate sample MVR-People data."""
        return {
            "face_embedding": sample_embedding,
            "featured_individual_uuid": uuid4(),
            "age_min": 25,
            "age_max": 35,
            "gender": "male",
            "quality_score": 0.85,
            "auto_created": True
        }
    
    async def test_create_mvr_people(self, repository, sample_mvr_data):
        """Test creating MVR-People record."""
        logger.info("Test: Create MVR-People")
        
        mvr_uuid = await repository.create_mvr_people(**sample_mvr_data)
        
        assert mvr_uuid is not None
        assert isinstance(mvr_uuid, UUID)
        logger.info(f"✅ Created MVR: {mvr_uuid}")
    
    async def test_get_mvr_people(self, repository, sample_mvr_data):
        """Test retrieving MVR-People by UUID."""
        logger.info("Test: Get MVR-People")
        
        # Create
        mvr_uuid = await repository.create_mvr_people(**sample_mvr_data)
        
        # Retrieve
        mvr = await repository.get_mvr_people(mvr_uuid)
        
        assert mvr is not None
        assert mvr["mvr_people_uuid"] == mvr_uuid
        assert mvr["age_min"] == 25
        assert mvr["age_max"] == 35
        assert mvr["gender"] == "male"
        assert mvr["quality_score"] == 0.85
        assert mvr["auto_created"] is True
        assert mvr["is_orphaned"] is False
        logger.info("✅ Retrieved MVR successfully")
    
    async def test_find_similar_mvr_people(
        self,
        repository,
        sample_embedding
    ):
        """Test similarity search with pgvector."""
        logger.info("Test: Find Similar MVR-People")
        
        # Create multiple MVR records with different embeddings
        mvr1_uuid = await repository.create_mvr_people(
            face_embedding=sample_embedding,
            featured_individual_uuid=uuid4(),
            quality_score=0.8
        )
        
        # Create similar embedding (small perturbation)
        similar_embedding = sample_embedding + np.random.randn(512) * 0.1
        similar_embedding = similar_embedding / np.linalg.norm(
            similar_embedding
        )
        
        mvr2_uuid = await repository.create_mvr_people(
            face_embedding=similar_embedding,
            featured_individual_uuid=uuid4(),
            quality_score=0.85
        )
        
        # Create dissimilar embedding
        dissimilar_embedding = np.random.randn(512).astype(np.float32)
        dissimilar_embedding = dissimilar_embedding / np.linalg.norm(
            dissimilar_embedding
        )
        
        mvr3_uuid = await repository.create_mvr_people(
            face_embedding=dissimilar_embedding,
            featured_individual_uuid=uuid4(),
            quality_score=0.9
        )
        
        # Search for similar
        results = await repository.find_similar_mvr_people(
            face_embedding=sample_embedding,
            threshold=0.5,
            limit=10
        )
        
        assert len(results) >= 2  # At least mvr1 and mvr2
        assert results[0]["mvr_people_uuid"] == mvr1_uuid  # Exact match
        assert results[0]["similarity"] > 0.99
        logger.info(
            f"✅ Found {len(results)} similar MVR-People "
            f"(top similarity: {results[0]['similarity']:.3f})"
        )
    
    async def test_link_individual_to_mvr(self, repository, sample_mvr_data):
        """Test creating Individual-MVR mapping."""
        logger.info("Test: Link Individual to MVR")
        
        # Create MVR
        mvr_uuid = await repository.create_mvr_people(**sample_mvr_data)
        
        # Link Individual
        individual_uuid = uuid4()
        mapping_uuid = await repository.create_individual_mvr_mapping(
            individual_uuid=individual_uuid,
            mvr_people_uuid=mvr_uuid,
            similarity_score=0.95,
            link_method="auto_create",
            is_representative=True
        )
        
        assert mapping_uuid is not None
        logger.info(f"✅ Linked Individual {individual_uuid} to MVR {mvr_uuid}")
    
    async def test_merge_mvr_people(self, repository, sample_embedding):
        """Test merging two MVR-People records."""
        logger.info("Test: Merge MVR-People")
        
        # Create two MVR records
        mvr1_uuid = await repository.create_mvr_people(
            face_embedding=sample_embedding,
            featured_individual_uuid=uuid4(),
            quality_score=0.8
        )
        
        mvr2_uuid = await repository.create_mvr_people(
            face_embedding=sample_embedding,
            featured_individual_uuid=uuid4(),
            quality_score=0.9
        )
        
        # Link individuals to mvr2 (loser)
        ind1 = uuid4()
        ind2 = uuid4()
        await repository.create_individual_mvr_mapping(
            individual_uuid=ind1,
            mvr_people_uuid=mvr2_uuid,
            similarity_score=0.95,
            link_method="auto_create",
            is_representative=True
        )
        await repository.create_individual_mvr_mapping(
            individual_uuid=ind2,
            mvr_people_uuid=mvr2_uuid,
            similarity_score=0.9,
            link_method="auto_create",
            is_representative=False
        )
        
        # Merge mvr2 into mvr1
        success = await repository.merge_mvr_people(
            source_mvr_uuid=mvr2_uuid,
            target_mvr_uuid=mvr1_uuid,
            similarity_score=0.92,
            merge_method="auto_match"
        )
        
        assert success is True
        
        # Verify mvr2 is orphaned
        mvr2 = await repository.get_mvr_people(mvr2_uuid)
        assert mvr2["is_orphaned"] is True
        assert mvr2["merged_into_mvr_uuid"] == mvr1_uuid
        
        # Verify individuals are reassigned to mvr1
        await repository.reassign_individuals_to_mvr(
            from_mvr_uuid=mvr2_uuid,
            to_mvr_uuid=mvr1_uuid
        )
        
        # Check linked individuals
        mvr1_individuals = await repository.get_linked_individuals(mvr1_uuid)
        individual_uuids = [ind["individual_uuid"] for ind in mvr1_individuals]
        
        assert ind1 in individual_uuids
        assert ind2 in individual_uuids
        
        logger.info("✅ Merge completed successfully")
    
    async def test_search_by_demographics(self, repository, sample_embedding):
        """Test demographic filtering."""
        logger.info("Test: Search by Demographics")
        
        # Create MVR with specific demographics
        mvr1_uuid = await repository.create_mvr_people(
            face_embedding=sample_embedding,
            featured_individual_uuid=uuid4(),
            age_min=25,
            age_max=35,
            gender="male",
            quality_score=0.8
        )
        
        mvr2_uuid = await repository.create_mvr_people(
            face_embedding=sample_embedding,
            featured_individual_uuid=uuid4(),
            age_min=40,
            age_max=50,
            gender="female",
            quality_score=0.85
        )
        
        # Search for males aged 20-40
        results = await repository.search_by_demographics(
            age_min=20,
            age_max=40,
            gender="male",
            limit=10
        )
        
        assert len(results) >= 1
        assert any(r["mvr_people_uuid"] == mvr1_uuid for r in results)
        assert not any(r["mvr_people_uuid"] == mvr2_uuid for r in results)
        
        logger.info(f"✅ Found {len(results)} matching demographics")
    
    async def test_get_matching_config(self, repository):
        """Test retrieving matching configuration."""
        logger.info("Test: Get Matching Config")
        
        config = await repository.get_matching_config()
        
        assert config is not None
        assert "similarity_threshold" in config
        assert "auto_merge_enabled" in config
        assert config["similarity_threshold"] == 0.85
        
        logger.info("✅ Retrieved matching config")
    
    async def test_update_matching_config(self, repository):
        """Test updating matching configuration."""
        logger.info("Test: Update Matching Config")
        
        # Update config
        success = await repository.update_matching_config(
            similarity_threshold=0.90,
            auto_merge_enabled=False,
            max_candidates_to_check=100
        )
        
        assert success is True
        
        # Verify
        config = await repository.get_matching_config()
        assert config["similarity_threshold"] == 0.90
        assert config["auto_merge_enabled"] is False
        assert config["max_candidates_to_check"] == 100
        
        # Restore default
        await repository.update_matching_config(
            similarity_threshold=0.85,
            auto_merge_enabled=True,
            max_candidates_to_check=50
        )
        
        logger.info("✅ Updated matching config")
    
    async def test_get_orphaned_mvr_people(
        self,
        repository,
        sample_embedding
    ):
        """Test retrieving orphaned MVR-People."""
        logger.info("Test: Get Orphaned MVR-People")
        
        # Create and merge MVR
        mvr1_uuid = await repository.create_mvr_people(
            face_embedding=sample_embedding,
            featured_individual_uuid=uuid4(),
            quality_score=0.9
        )
        
        mvr2_uuid = await repository.create_mvr_people(
            face_embedding=sample_embedding,
            featured_individual_uuid=uuid4(),
            quality_score=0.8
        )
        
        # Merge mvr2 into mvr1
        await repository.merge_mvr_people(
            source_mvr_uuid=mvr2_uuid,
            target_mvr_uuid=mvr1_uuid,
            similarity_score=0.92,
            merge_method="auto_match"
        )
        
        # Get orphaned
        orphaned = await repository.get_orphaned_mvr_people(limit=10)
        
        assert len(orphaned) >= 1
        assert any(o["mvr_people_uuid"] == mvr2_uuid for o in orphaned)
        
        logger.info(f"✅ Found {len(orphaned)} orphaned MVR-People")


async def run_all_tests():
    """Run all repository tests."""
    logger.info("=" * 70)
    logger.info("MVRRepository Test Suite")
    logger.info("=" * 70)
    
    test_instance = TestMVRRepository()
    
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
    
    try:
        # Run tests
        sample_embedding = np.random.randn(512).astype(np.float32)
        sample_embedding = sample_embedding / np.linalg.norm(sample_embedding)
        
        sample_mvr_data = {
            "face_embedding": sample_embedding,
            "featured_individual_uuid": uuid4(),
            "age_min": 25,
            "age_max": 35,
            "gender": "male",
            "quality_score": 0.85,
            "auto_created": True
        }
        
        await test_instance.test_create_mvr_people(
            repository,
            sample_mvr_data
        )
        await test_instance.test_get_mvr_people(repository, sample_mvr_data)
        await test_instance.test_find_similar_mvr_people(
            repository,
            sample_embedding
        )
        await test_instance.test_link_individual_to_mvr(
            repository,
            sample_mvr_data
        )
        await test_instance.test_merge_mvr_people(repository, sample_embedding)
        await test_instance.test_search_by_demographics(
            repository,
            sample_embedding
        )
        await test_instance.test_get_matching_config(repository)
        await test_instance.test_update_matching_config(repository)
        await test_instance.test_get_orphaned_mvr_people(
            repository,
            sample_embedding
        )
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ All MVRRepository tests passed!")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise
    
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
