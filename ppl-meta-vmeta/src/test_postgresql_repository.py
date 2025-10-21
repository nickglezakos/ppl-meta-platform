"""
PostgreSQL Repository Validation Test
PPL Meta Platform - Cross-Video Individual Tracking

Comprehensive test suite to validate the PostgreSQL repository implementation
and ensure all CRUD operations work correctly with the actual database schema.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from database.repository import CrossVideoTrackingRepository, DatabaseError
from models.cross_video_tracking import (
    CrossVideoTrackingConfig,
    VideoAppearance,
    BoundingBox,
    ProcessingStatus,
    SessionStatus
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PostgreSQLRepositoryValidator:
    """Comprehensive validator for PostgreSQL repository operations."""
    
    def __init__(self, connection_string: str):
        """Initialize validator with database connection."""
        self.connection_string = connection_string
        self.repository = CrossVideoTrackingRepository(connection_string)
        self.test_session_id = None
        self.test_individual_id = None
        self.test_config_name = f"test_config_{uuid4().hex[:8]}"
    
    async def run_all_tests(self) -> bool:
        """Run all validation tests."""
        logger.info("🚀 Starting PostgreSQL Repository Validation")
        logger.info("=" * 60)
        
        try:
            # Initialize repository
            await self.repository.initialize()
            logger.info("✅ Repository initialized successfully")
            
            # Test algorithm configurations
            if not await self.test_algorithm_configurations():
                return False
            
            # Test tracking sessions
            if not await self.test_tracking_sessions():
                return False
            
            # Test individuals and appearances
            if not await self.test_individuals():
                return False
            
            # Test video processing states
            if not await self.test_video_processing_states():
                return False
            
            # Test session individuals relationships
            if not await self.test_session_individuals():
                return False
            
            # Clean up test data
            await self.cleanup_test_data()
            
            logger.info("=" * 60)
            logger.info("🎉 All PostgreSQL Repository Tests Passed!")
            return True
            
        except Exception as e:
            logger.error(f"💥 Validation failed: {e}")
            return False
        finally:
            await self.repository.close()
    
    async def test_algorithm_configurations(self) -> bool:
        """Test algorithm configuration operations."""
        logger.info("🔧 Testing Algorithm Configuration Operations...")
        
        try:
            # Create test configuration
            test_config = CrossVideoTrackingConfig(
                config_name=self.test_config_name,
                description="Test configuration for validation",
                max_gap_seconds=5,
                iou_threshold=0.4,
                min_overlap_confidence=0.6,
                is_default=False
            )
            
            # Test creation
            config_name = await self.repository.create_algorithm_config(test_config)
            assert config_name == self.test_config_name
            logger.info(f"  ✅ Created config: {config_name}")
            
            # Test retrieval
            retrieved_config = await self.repository.get_algorithm_config(config_name)
            assert retrieved_config is not None
            assert retrieved_config.config_name == self.test_config_name
            assert retrieved_config.max_gap_seconds == 5
            logger.info(f"  ✅ Retrieved config: {retrieved_config.config_name}")
            
            # Test get default configuration
            default_config = await self.repository.get_default_algorithm_config()
            assert default_config is not None
            assert default_config.is_default == True
            logger.info(f"  ✅ Retrieved default config: {default_config.config_name}")
            
            logger.info("✅ Algorithm Configuration tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Algorithm Configuration test failed: {e}")
            return False
    
    async def test_tracking_sessions(self) -> bool:
        """Test tracking session operations."""
        logger.info("📊 Testing Tracking Session Operations...")
        
        try:
            # Get default config for session
            config = await self.repository.get_default_algorithm_config()
            assert config is not None
            
            # Create test session
            start_time = datetime.utcnow()
            end_time = start_time + timedelta(hours=2)
            
            session_id = await self.repository.create_tracking_session(
                user_id="test_user",
                collections=["collection1", "collection2"],
                start_time=start_time,
                end_time=end_time,
                config=config
            )
            
            self.test_session_id = session_id
            logger.info(f"  ✅ Created session: {session_id}")
            
            # Test retrieval
            retrieved_session = await self.repository.get_tracking_session(session_id)
            assert retrieved_session is not None
            assert retrieved_session.user_id == "test_user"
            assert len(retrieved_session.collections) == 2
            logger.info(f"  ✅ Retrieved session: {retrieved_session.session_uuid}")
            
            # Test status update
            success = await self.repository.update_session_status(
                session_id, 
                SessionStatus.RUNNING,
                {"processed_videos": 5, "total_videos": 10}
            )
            assert success == True
            logger.info("  ✅ Updated session status")
            
            logger.info("✅ Tracking Session tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Tracking Session test failed: {e}")
            return False
    
    async def test_individuals(self) -> bool:
        """Test individual and video appearance operations."""
        logger.info("👥 Testing Individual Operations...")
        
        try:
            assert self.test_session_id is not None, "Session must be created first"
            
            # Create test video appearance
            video_appearance = VideoAppearance(
                video_uuid=uuid4(),
                person_object_uuid=uuid4(),
                start_timestamp=datetime.utcnow(),
                end_timestamp=datetime.utcnow() + timedelta(minutes=3),
                entry_bbox=BoundingBox(x1=100, y1=50, x2=200, y2=150),
                exit_bbox=BoundingBox(x1=150, y1=75, x2=250, y2=175),
                confidence=0.85,
                representative_faces=[{"quality": "high", "embedding": "test"}],
                movement_pattern={"direction": "left_to_right", "speed": "slow"}
            )
            
            # Create individual
            individual_id = await self.repository.create_individual(
                session_id=self.test_session_id,
                first_appearance=video_appearance,
                confidence_score=0.85
            )
            
            self.test_individual_id = individual_id
            logger.info(f"  ✅ Created individual: {individual_id}")
            
            # Create additional appearance
            second_appearance = VideoAppearance(
                video_uuid=uuid4(),
                person_object_uuid=uuid4(),
                start_timestamp=datetime.utcnow() + timedelta(minutes=5),
                end_timestamp=datetime.utcnow() + timedelta(minutes=8),
                entry_bbox=BoundingBox(x1=120, y1=60, x2=220, y2=160),
                exit_bbox=BoundingBox(x1=170, y1=85, x2=270, y2=185),
                confidence=0.90
            )
            
            # Add appearance to individual
            success = await self.repository.add_appearance_to_individual(
                individual_id, second_appearance
            )
            assert success == True
            logger.info("  ✅ Added appearance to individual")
            
            logger.info("✅ Individual tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Individual test failed: {e}")
            return False
    
    async def test_video_processing_states(self) -> bool:
        """Test video processing state operations."""
        logger.info("🎬 Testing Video Processing State Operations...")
        
        try:
            assert self.test_session_id is not None, "Session must be created first"
            
            video_uuid = uuid4()
            
            # Create processing state
            await self.repository.create_video_processing_state(
                video_uuid=video_uuid,
                session_uuid=self.test_session_id,
                processing_status=ProcessingStatus.PENDING,
                person_objects_count=0
            )
            logger.info(f"  ✅ Created processing state for video: {video_uuid}")
            
            # Update processing state
            success = await self.repository.update_video_processing_state(
                video_uuid=video_uuid,
                session_uuid=self.test_session_id,
                processing_status=ProcessingStatus.COMPLETED,
                person_objects_count=3,
                processing_time_ms=1500.0
            )
            assert success == True
            logger.info("  ✅ Updated processing state")
            
            logger.info("✅ Video Processing State tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Video Processing State test failed: {e}")
            return False
    
    async def test_session_individuals(self) -> bool:
        """Test session-individuals relationship operations."""
        logger.info("🔗 Testing Session-Individual Relationships...")
        
        try:
            assert self.test_session_id is not None, "Session must be created first"
            assert self.test_individual_id is not None, "Individual must be created first"
            
            # Get individuals for session
            individuals = await self.repository.get_individuals_by_session(
                self.test_session_id
            )
            assert len(individuals) >= 1
            logger.info(f"  ✅ Retrieved {len(individuals)} individuals for session")
            
            # Get sessions for individual
            sessions = await self.repository.get_sessions_by_individual(
                self.test_individual_id
            )
            assert len(sessions) >= 1
            logger.info(f"  ✅ Retrieved {len(sessions)} sessions for individual")
            
            logger.info("✅ Session-Individual relationship tests passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Session-Individual relationship test failed: {e}")
            return False
    
    async def test_database_connection(self) -> bool:
        """Test basic database connectivity."""
        logger.info("🔌 Testing Database Connection...")
        
        try:
            conn = await self.repository.get_connection()
            
            # Test basic query
            result = await conn.fetchval("SELECT 1")
            assert result == 1
            
            # Test pgvector functionality
            vector_result = await conn.fetchval("SELECT '[1,2,3]'::vector")
            assert vector_result is not None
            
            await self.repository.release_connection(conn)
            logger.info("✅ Database connection test passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            return False
    
    async def cleanup_test_data(self) -> None:
        """Clean up test data created during validation."""
        logger.info("🧹 Cleaning up test data...")
        
        try:
            conn = await self.repository.get_connection()
            
            # Clean up in reverse order of dependencies
            if self.test_individual_id:
                # Remove video appearances
                await conn.execute("""
                    DELETE FROM individual_video_appearances 
                    WHERE individual_uuid = $1
                """, self.test_individual_id)
                
                # Remove session-individual relationships
                await conn.execute("""
                    DELETE FROM session_individuals 
                    WHERE individual_uuid = $1
                """, self.test_individual_id)
                
                # Remove individual
                await conn.execute("""
                    DELETE FROM individuals 
                    WHERE individual_uuid = $1
                """, self.test_individual_id)
            
            if self.test_session_id:
                # Remove video processing states
                await conn.execute("""
                    DELETE FROM video_processing_states 
                    WHERE session_uuid = $1
                """, self.test_session_id)
                
                # Remove session
                await conn.execute("""
                    DELETE FROM tracking_sessions 
                    WHERE session_uuid = $1
                """, self.test_session_id)
            
            # Remove test config
            await conn.execute("""
                DELETE FROM algorithm_configurations 
                WHERE config_name = $1
            """, self.test_config_name)
            
            await self.repository.release_connection(conn)
            logger.info("✅ Test data cleaned up successfully")
            
        except Exception as e:
            logger.error(f"⚠️ Cleanup warning: {e}")


async def main():
    """Main validation entry point."""
    # Use the same connection string as our PostgreSQL setup
    connection_string = "postgresql://nickgklezakos@localhost:5432/ppl_meta_vmeta"
    
    validator = PostgreSQLRepositoryValidator(connection_string)
    
    # Initialize repository first
    await validator.repository.initialize()
    
    # Run basic connectivity test first
    if not await validator.test_database_connection():
        logger.error("❌ Database connectivity test failed")
        sys.exit(1)
    
    # Run comprehensive validation
    success = await validator.run_all_tests()
    
    if success:
        logger.info("🎉 PostgreSQL Repository Validation PASSED!")
        logger.info("✅ Ready for Phase 1 Integration Testing!")
    else:
        logger.error("❌ PostgreSQL Repository Validation FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())