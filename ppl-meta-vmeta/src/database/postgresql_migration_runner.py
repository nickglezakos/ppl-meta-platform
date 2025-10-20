"""
PostgreSQL Migration Runner
PPL Meta Platform - Cross-Video Individual Tracking

Production migration runner for PostgreSQL with pgvector support.
Runs all database migrations and initializes the schema for cross-video tracking.

Created: October 20, 2025
Author: PPL Meta Platform Team
"""

import asyncio
import asyncpg
import argparse
import sys
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PostgreSQLMigrationRunner:
    """PostgreSQL migration runner for cross-video tracking feature."""
    
    def __init__(self, connection_string: str):
        """Initialize migration runner."""
        self.connection_string = connection_string
        self.migrations_dir = Path(__file__).parent / "migrations"
    
    async def connect(self) -> asyncpg.Connection:
        """Create database connection."""
        try:
            conn = await asyncpg.connect(self.connection_string)
            logger.info("✅ PostgreSQL connection established")
            return conn
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise
    
    async def ensure_extensions(self) -> bool:
        """Ensure required PostgreSQL extensions are installed."""
        logger.info("🔧 Ensuring PostgreSQL extensions...")
        
        try:
            conn = await self.connect()
            
            # Enable required extensions
            extensions = [
                'uuid-ossp',    # UUID generation
                'vector'        # pgvector for face embeddings
            ]
            
            for extension in extensions:
                try:
                    await conn.execute(f'CREATE EXTENSION IF NOT EXISTS "{extension}"')
                    logger.info(f"✅ Extension enabled: {extension}")
                except Exception as e:
                    logger.error(f"❌ Failed to enable extension {extension}: {e}")
                    await conn.close()
                    return False
            
            await conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to ensure extensions: {e}")
            return False
    
    async def apply_migration(self, migration_file: str) -> bool:
        """Apply a specific migration file."""
        migration_path = self.migrations_dir / migration_file
        
        if not migration_path.exists():
            logger.error(f"❌ Migration file not found: {migration_path}")
            return False
        
        logger.info(f"🔄 Applying migration: {migration_file}")
        
        try:
            conn = await self.connect()
            
            # Read migration file
            with open(migration_path, 'r') as f:
                migration_sql = f.read()
            
            # Execute migration
            await conn.execute(migration_sql)
            
            logger.info(f"✅ Migration applied successfully: {migration_file}")
            await conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply migration {migration_file}: {e}")
            if 'conn' in locals():
                await conn.close()
            return False
    
    async def validate_schema(self) -> bool:
        """Validate that all required tables and functions exist."""
        logger.info("🔍 Validating cross-video tracking schema...")
        
        required_tables = [
            'algorithm_configurations',
            'tracking_sessions',
            'individuals',
            'individual_video_appearances',
            'video_processing_states',
            'cached_person_objects',
            'session_individuals'
        ]
        
        try:
            conn = await self.connect()
            
            logger.info("📋 Schema validation results:")
            all_tables_exist = True
            
            for table_name in required_tables:
                try:
                    result = await conn.fetchval("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = $1
                        )
                    """, table_name)
                    
                    if result:
                        logger.info(f"  ✅ {table_name}: EXISTS")
                    else:
                        logger.error(f"  ❌ {table_name}: MISSING")
                        all_tables_exist = False
                        
                except Exception as e:
                    logger.error(f"  ❌ {table_name}: ERROR - {e}")
                    all_tables_exist = False
            
            if all_tables_exist:
                logger.info("✅ All required tables exist")
            else:
                logger.error("❌ Some required tables are missing")
            
            await conn.close()
            return all_tables_exist
                
        except Exception as e:
            logger.error(f"❌ Schema validation failed: {e}")
            return False
    
    async def test_pgvector_functionality(self) -> bool:
        """Test pgvector extension functionality."""
        logger.info("🧪 Testing pgvector functionality...")
        
        try:
            conn = await self.connect()
            
            # Test vector operations
            test_queries = [
                # Test vector creation
                "SELECT '[1,2,3]'::vector as test_vector",
                
                # Test vector similarity (cosine distance)
                "SELECT 1 - ('[1,2,3]'::vector <=> '[1,2,3]'::vector) as similarity",
                
                # Test vector dimensions
                "SELECT vector_dims('[1,2,3,4,5]'::vector) as dimensions"
            ]
            
            for i, query in enumerate(test_queries, 1):
                try:
                    result = await conn.fetchval(query)
                    logger.info(f"  ✅ Vector test {i}: {result}")
                except Exception as e:
                    logger.error(f"  ❌ Vector test {i} failed: {e}")
                    await conn.close()
                    return False
            
            logger.info("✅ pgvector functionality working correctly")
            await conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ pgvector functionality test failed: {e}")
            return False
    
    async def insert_default_configurations(self) -> bool:
        """Insert default algorithm configurations."""
        logger.info("🔧 Inserting default algorithm configurations...")
        
        try:
            conn = await self.connect()
            
            # Default configurations with vector-optimized settings
            configs = [
                {
                    'config_name': 'fast_processing',
                    'description': 'Fast processing with lower accuracy',
                    'config': {
                        'max_gap_seconds': 10.0,
                        'iou_threshold': 0.4,
                        'min_overlap_confidence': 0.6,
                        'face_similarity_threshold': 0.75,
                        'vector_similarity_threshold': 0.8,
                        'max_individuals_per_session': 200,
                        'consolidation_window_minutes': 30,
                        'enable_face_clustering': False,
                        'clustering_threshold': 0.8,
                        'min_cluster_size': 3,
                        'enable_temporal_smoothing': True,
                        'temporal_window_seconds': 5.0,
                        'enable_cross_collection_tracking': False,
                        'vector_dimensions': 512
                    },
                    'is_default': False
                },
                {
                    'config_name': 'balanced',
                    'description': 'Balanced accuracy and performance',
                    'config': {
                        'max_gap_seconds': 5.0,
                        'iou_threshold': 0.3,
                        'min_overlap_confidence': 0.5,
                        'face_similarity_threshold': 0.8,
                        'vector_similarity_threshold': 0.85,
                        'max_individuals_per_session': 500,
                        'consolidation_window_minutes': 15,
                        'enable_face_clustering': True,
                        'clustering_threshold': 0.85,
                        'min_cluster_size': 2,
                        'enable_temporal_smoothing': True,
                        'temporal_window_seconds': 3.0,
                        'enable_cross_collection_tracking': True,
                        'vector_dimensions': 512
                    },
                    'is_default': True
                },
                {
                    'config_name': 'high_accuracy',
                    'description': 'High accuracy with detailed vector analysis',
                    'config': {
                        'max_gap_seconds': 3.0,
                        'iou_threshold': 0.2,
                        'min_overlap_confidence': 0.4,
                        'face_similarity_threshold': 0.85,
                        'vector_similarity_threshold': 0.9,
                        'max_individuals_per_session': 1000,
                        'consolidation_window_minutes': 10,
                        'enable_face_clustering': True,
                        'clustering_threshold': 0.9,
                        'min_cluster_size': 2,
                        'enable_temporal_smoothing': True,
                        'temporal_window_seconds': 2.0,
                        'enable_cross_collection_tracking': True,
                        'vector_dimensions': 512
                    },
                    'is_default': False
                }
            ]
            
            for config in configs:
                try:
                    await conn.execute("""
                        INSERT INTO algorithm_configurations 
                        (config_name, description, config, is_default, created_at)
                        VALUES ($1, $2, $3, $4, NOW())
                        ON CONFLICT (config_name) DO UPDATE SET
                            description = EXCLUDED.description,
                            config = EXCLUDED.config,
                            is_default = EXCLUDED.is_default
                    """, 
                        config['config_name'],
                        config['description'], 
                        json.dumps(config['config']),
                        config['is_default']
                    )
                    
                    logger.info(f"✅ Inserted/updated config: {config['config_name']}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to insert config {config['config_name']}: {e}")
                    await conn.close()
                    return False
            
            logger.info(f"✅ Successfully processed {len(configs)} configurations")
            await conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to insert default configurations: {e}")
            return False
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and information."""
        try:
            conn = await self.connect()
            
            # Get table counts
            table_stats = {}
            tables = [
                'algorithm_configurations',
                'tracking_sessions', 
                'individuals',
                'individual_video_appearances',
                'video_processing_states',
                'cached_person_objects',
                'session_individuals'
            ]
            
            for table in tables:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                table_stats[table] = count
            
            # Get PostgreSQL version
            pg_version = await conn.fetchval("SELECT version()")
            
            # Check pgvector extension
            vector_version = await conn.fetchval("""
                SELECT extversion FROM pg_extension WHERE extname = 'vector'
            """)
            
            stats = {
                'postgresql_version': pg_version,
                'pgvector_version': vector_version or 'Not installed',
                'table_counts': table_stats,
                'total_records': sum(table_stats.values())
            }
            
            await conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get database stats: {e}")
            return {}


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Cross-Video Tracking PostgreSQL Migration Runner")
    parser.add_argument("--apply", help="Apply specific migration file")
    parser.add_argument("--setup-all", action="store_true", help="Run complete setup")
    parser.add_argument("--validate-schema", action="store_true", help="Validate schema only")
    parser.add_argument("--test-pgvector", action="store_true", help="Test pgvector functionality")
    parser.add_argument("--database-stats", action="store_true", help="Show database statistics")
    parser.add_argument("--db-url", help="Database connection URL", 
                       default="postgresql://ppl_user:ppl_password@localhost:5432/ppl_meta")
    
    args = parser.parse_args()
    
    if not any([args.apply, args.setup_all, args.validate_schema, args.test_pgvector, args.database_stats]):
        parser.print_help()
        return
    
    # Initialize migration runner
    runner = PostgreSQLMigrationRunner(args.db_url)
    
    try:
        if args.database_stats:
            stats = await runner.get_database_stats()
            if stats:
                logger.info("📊 Database Statistics:")
                logger.info(f"  PostgreSQL: {stats.get('postgresql_version', 'Unknown')}")
                logger.info(f"  pgvector: {stats.get('pgvector_version', 'Unknown')}")
                logger.info(f"  Total records: {stats.get('total_records', 0)}")
                logger.info("  Table counts:")
                for table, count in stats.get('table_counts', {}).items():
                    logger.info(f"    {table}: {count}")
        
        if args.test_pgvector:
            success = await runner.test_pgvector_functionality()
            if not success:
                sys.exit(1)
        
        if args.apply:
            success = await runner.apply_migration(args.apply)
            if not success:
                sys.exit(1)
        
        if args.validate_schema:
            success = await runner.validate_schema()
            if not success:
                sys.exit(1)
        
        if args.setup_all:
            logger.info("🚀 Running complete PostgreSQL setup...")
            
            # 1. Ensure extensions
            if not await runner.ensure_extensions():
                logger.error("❌ Extension setup failed")
                sys.exit(1)
            
            # 2. Apply core schema migration
            if not await runner.apply_migration("002_cross_video_tracking_schema.sql"):
                logger.error("❌ Schema migration failed")
                sys.exit(1)
            
            # 3. Apply indexes migration
            if not await runner.apply_migration("003_cross_video_tracking_indexes.sql"):
                logger.error("❌ Indexes migration failed")
                sys.exit(1)
            
            # 4. Test pgvector functionality
            if not await runner.test_pgvector_functionality():
                logger.error("❌ pgvector functionality test failed")
                sys.exit(1)
            
            # 5. Validate schema
            if not await runner.validate_schema():
                logger.error("❌ Schema validation failed")
                sys.exit(1)
            
            # 6. Insert default configurations
            if not await runner.insert_default_configurations():
                logger.error("❌ Default configuration insertion failed")
                sys.exit(1)
            
            # 7. Show final statistics
            stats = await runner.get_database_stats()
            if stats:
                logger.info("📊 Final Database Statistics:")
                logger.info(f"  PostgreSQL: {stats.get('postgresql_version', 'Unknown')}")
                logger.info(f"  pgvector: {stats.get('pgvector_version', 'Unknown')}")
                logger.info(f"  Total records: {stats.get('total_records', 0)}")
            
            logger.info("🎉 Complete PostgreSQL setup successful!")
            logger.info("✅ Cross-video individual tracking database ready!")
    
    except Exception as e:
        logger.error(f"💥 Migration runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())