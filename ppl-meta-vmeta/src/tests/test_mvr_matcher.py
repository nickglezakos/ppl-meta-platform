"""
Unit Tests for MVRMatcher

Tests matching and merging logic including 5-stage workflow,
quality-based winner selection, and audit trail creation.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4

import asyncpg
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.mvr_repository import MVRRepository
from services.mvr_matcher import MVRMatcher
from ml.mvr_processor import MVRProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestMVRMatcher:
    """Test suite for MVRMatcher."""
    
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
    async def matcher(self, repository, ml_processor):
        """Create matcher instance."""
        return MVRMatcher(
            repository=repository,
            ml_processor=ml_processor
        )
    
    async def test_find_matching_mvr_no_match(
        self,
        matcher,
        repository
    ):
        """Test finding match when no similar MVR exists."""
        logger.info("Test: Find Matching MVR - No Match")
        
        # Create MVR
        embedding1 = np.random.randn(512).astype(np.float32)
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        
        mvr1_uuid = await repository.create_mvr_people(
            face_embedding=embedding1,
            featured_individual_uuid=uuid4(),
            quality_score=0.85
        )
        
        ind1 = uuid4()
        await repository.create_individual_mvr_mapping(
            individual_uuid=ind1,
            mvr_people_uuid=mvr1_uuid,
            similarity_score=1.0,
            link_method="auto_create",
            is_representative=True
        )
        
        # Create completely different MVR
        embedding2 = np.random.randn(512).astype(np.float32)
        embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        mvr2_uuid = await repository.create_mvr_people(
            face_embedding=embedding2,
            featured_individual_uuid=uuid4(),
            quality_score=0.9
        )
        
        ind2 = uuid4()
        await repository.create_individual_mvr_mapping(
            individual_uuid=ind2,
            mvr_people_uuid=mvr2_uuid,
            similarity_score=1.0,
            link_method="auto_create",
            is_representative=True
        )
        
        # Try to find match for ind2
        match = await matcher.find_matching_mvr(
            individual_uuid=ind2,
            threshold=0.85
        )
        
        # Should find no match (embeddings are random/dissimilar)
        assert match is None or match["similarity"] < 0.85
        logger.info("✅ Correctly found no match for dissimilar MVR")
    
    async def test_find_matching_mvr_with_match(
        self,
        matcher,
        repository
    ):
        """Test finding match when similar MVR exists."""
        logger.info("Test: Find Matching MVR - With Match")
        
        # Create MVR with specific embedding
        embedding1 = np.random.randn(512).astype(np.float32)
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        
        mvr1_uuid = await repository.create_mvr_people(
            face_embedding=embedding1,
            featured_individual_uuid=uuid4(),
            quality_score=0.85
        )
        
        ind1 = uuid4()
        await repository.create_individual_mvr_mapping(
            individual_uuid=ind1,
            mvr_people_uuid=mvr1_uuid,
            similarity_score=1.0,
            link_method="auto_create",
            is_representative=True
        )
        
        # Create very similar MVR (small perturbation)
        embedding2 = embedding1 + np.random.randn(512) * 0.01
        embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        mvr2_uuid = await repository.create_mvr_people(
            face_embedding=embedding2,
            featured_individual_uuid=uuid4(),
            quality_score=0.9
        )
        
        ind2 = uuid4()
        await repository.create_individual_mvr_mapping(
            individual_uuid=ind2,
            mvr_people_uuid=mvr2_uuid,
            similarity_score=1.0,
            link_method="auto_create",
            is_representative=True
        )
        
        # Find match for ind2
        match = await matcher.find_matching_mvr(
            individual_uuid=ind2,
            threshold=0.85
        )
        
        assert match is not None
        assert match["mvr_people_uuid"] == mvr1_uuid
        assert match["similarity"] > 0.85
        logger.info(
            f"✅ Found match with similarity {match['similarity']:.3f}"
        )
    
    async def test_determine_merge_winner(self, matcher, repository):
        """Test quality-based winner selection."""
        logger.info("Test: Determine Merge Winner")
        
        embedding = np.random.randn(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        # Create high quality MVR
        mvr_high_uuid = await repository.create_mvr_people(
            face_embedding=embedding,
            featured_individual_uuid=uuid4(),
            quality_score=0.95
        )
        
        # Create low quality MVR
        mvr_low_uuid = await repository.create_mvr_people(
            face_embedding=embedding,
            featured_individual_uuid=uuid4(),
            quality_score=0.75
        )
        
        # Determine winner
        winner, loser = await matcher._determine_merge_winner(
            mvr_high_uuid,
            mvr_low_uuid
        )
        
        assert winner == mvr_high_uuid
        assert loser == mvr_low_uuid
        logger.info("✅ Correctly selected higher quality as winner")
    
    async def test_find_and_merge_if_match_success(
        self,
        matcher,
        repository
    ):
        """Test complete matching and merging workflow."""
        logger.info("Test: Find and Merge If Match - Success")
        
        # Create similar embeddings
        embedding1 = np.random.randn(512).astype(np.float32)
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        
        embedding2 = embedding1 + np.random.randn(512) * 0.01
        embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        # Create MVR 1 (will be winner - higher quality)
        mvr1_uuid = await repository.create_mvr_people(
            face_embedding=embedding1,
            featured_individual_uuid=uuid4(),
            quality_score=0.95
        )
        
        ind1 = uuid4()
        await repository.create_individual_mvr_mapping(
            individual_uuid=ind1,
            mvr_people_uuid=mvr1_uuid,
            similarity_score=1.0,
            link_method="auto_create",
            is_representative=True
        )
        
        # Create MVR 2 (will be loser - lower quality)
        mvr2_uuid = await repository.create_mvr_people(
            face_embedding=embedding2,
            featured_individual_uuid=uuid4(),
            quality_score=0.85
        )
        
        ind2 = uuid4()
        await repository.create_individual_mvr_mapping(
            individual_uuid=ind2,
            mvr_people_uuid=mvr2_uuid,
            similarity_score=1.0,
            link_method="auto_create",
            is_representative=True
        )
        
        # Execute matching and merging
        result = await matcher.find_and_merge_if_match(
            individual_uuid=ind2
        )
        
        assert result["matched"] is True
        assert result["merged"] is True
        assert result["winner_mvr_uuid"] == str(mvr1_uuid)
        assert result["loser_mvr_uuid"] == str(mvr2_uuid)
        assert result["similarity_score"] > 0.85
        
        # Verify loser is orphaned
        mvr2 = await repository.get_mvr_people(mvr2_uuid)
        assert mvr2["is_orphaned"] is True
        assert mvr2["merged_into_mvr_uuid"] == mvr1_uuid
        
        logger.info(
            f"✅ Successfully merged with similarity "
            f"{result['similarity_score']:.3f}"
        )
    
    async def test_find_and_merge_if_match_no_match(
        self,
        matcher,
        repository
    ):
        """Test workflow when no match is found."""
        logger.info("Test: Find and Merge If Match - No Match")
        
        # Create dissimilar embeddings
        embedding1 = np.random.randn(512).astype(np.float32)
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        
        embedding2 = np.random.randn(512).astype(np.float32)
        embedding2 = embedding2 / np.linalg.norm(embedding2)
        
        # Create MVR 1
        mvr1_uuid = await repository.create_mvr_people(
            face_embedding=embedding1,
            featured_individual_uuid=uuid4(),
            quality_score=0.85
        )
        
        ind1 = uuid4()
        await repository.create_individual_mvr_mapping(
            individual_uuid=ind1,
            mvr_people_uuid=mvr1_uuid,
            similarity_score=1.0,
            link_method="auto_create",
            is_representative=True
        )
        
        # Create MVR 2
        mvr2_uuid = await repository.create_mvr_people(
            face_embedding=embedding2,
            featured_individual_uuid=uuid4(),
            quality_score=0.9
        )
        
        ind2 = uuid4()
        await repository.create_individual_mvr_mapping(
            individual_uuid=ind2,
            mvr_people_uuid=mvr2_uuid,
            similarity_score=1.0,
            link_method="auto_create",
            is_representative=True
        )
        
        # Execute matching
        result = await matcher.find_and_merge_if_match(
            individual_uuid=ind2
        )
        
        assert result["matched"] is False
        assert result["merged"] is False
        assert result.get("winner_mvr_uuid") is None
        
        logger.info("✅ Correctly identified no match")


async def run_all_tests():
    """Run all matcher tests."""
    logger.info("=" * 70)
    logger.info("MVRMatcher Test Suite")
    logger.info("=" * 70)
    
    test_instance = TestMVRMatcher()
    
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
    matcher = MVRMatcher(repository=repository, ml_processor=ml_processor)
    
    try:
        # Run tests
        await test_instance.test_find_matching_mvr_no_match(
            matcher,
            repository
        )
        await test_instance.test_find_matching_mvr_with_match(
            matcher,
            repository
        )
        await test_instance.test_determine_merge_winner(matcher, repository)
        await test_instance.test_find_and_merge_if_match_success(
            matcher,
            repository
        )
        await test_instance.test_find_and_merge_if_match_no_match(
            matcher,
            repository
        )
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ All MVRMatcher tests passed!")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise
    
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
