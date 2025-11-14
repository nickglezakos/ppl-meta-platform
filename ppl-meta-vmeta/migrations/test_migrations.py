#!/usr/bin/env python3
"""
Test script to execute batch processing database migrations.
This script will:
1. Connect to the PostgreSQL database
2. Execute migrations 006-009 in order
3. Verify table creation
4. Test helper functions
5. Display configuration summary
"""

import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from typing import List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'ppl_meta'),
    'user': os.getenv('DB_USER', 'ppl_user'),
    'password': os.getenv('DB_PASSWORD', 'ppl_password')
}

# Migration files to execute in order
MIGRATIONS = [
    '006_batch_processing_state.sql',
    '007_batch_video_assignments.sql',
    '008_batch_processing_history.sql',
    '009_batch_processing_config.sql'
]

class MigrationTester:
    """Test runner for batch processing migrations."""
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.migrations_dir = Path(__file__).parent.parent / 'migrations'
        
    def connect(self) -> bool:
        """Connect to PostgreSQL database."""
        try:
            print(f"📡 Connecting to database {DB_CONFIG['database']}@{DB_CONFIG['host']}...")
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            self.cursor = self.conn.cursor()
            print("✅ Connected successfully\n")
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("\n📡 Database connection closed")
    
    def execute_migration(self, migration_file: str) -> bool:
        """Execute a single migration file."""
        migration_path = self.migrations_dir / migration_file
        
        if not migration_path.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        print(f"🔄 Executing migration: {migration_file}")
        
        try:
            with open(migration_path, 'r') as f:
                sql = f.read()
            
            self.cursor.execute(sql)
            print(f"✅ Migration completed: {migration_file}\n")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {migration_file}")
            print(f"   Error: {e}\n")
            return False
    
    def verify_tables(self) -> bool:
        """Verify that all tables were created successfully."""
        print("🔍 Verifying table creation...")
        
        tables = [
            'batch_processing_state',
            'batch_video_assignments',
            'batch_processing_history',
            'batch_processing_config'
        ]
        
        all_exist = True
        
        for table in tables:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table,))
            
            exists = self.cursor.fetchone()[0]
            status = "✅" if exists else "❌"
            print(f"   {status} {table}")
            
            if not exists:
                all_exist = False
        
        print()
        return all_exist
    
    def verify_indexes(self) -> bool:
        """Verify that indexes were created."""
        print("🔍 Verifying indexes...")
        
        self.cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                indexname
            FROM pg_indexes
            WHERE tablename IN (
                'batch_processing_state',
                'batch_video_assignments',
                'batch_processing_history',
                'batch_processing_config'
            )
            ORDER BY tablename, indexname
        """)
        
        indexes = self.cursor.fetchall()
        print(f"   Found {len(indexes)} indexes:")
        for schema, table, index in indexes[:10]:  # Show first 10
            print(f"   • {table}.{index}")
        
        if len(indexes) > 10:
            print(f"   ... and {len(indexes) - 10} more")
        
        print()
        return len(indexes) > 0
    
    def verify_functions(self) -> bool:
        """Verify that helper functions were created."""
        print("🔍 Verifying helper functions...")
        
        functions = [
            'get_next_batch_number',
            'get_batch_videos',
            'is_video_in_batch',
            'get_next_sequence_number',
            'archive_batch_to_history',
            'get_collection_batch_stats',
            'get_batch_processing_config',
            'update_batch_size'
        ]
        
        all_exist = True
        
        for func in functions:
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM pg_proc
                    WHERE proname = %s
                )
            """, (func,))
            
            exists = self.cursor.fetchone()[0]
            status = "✅" if exists else "❌"
            print(f"   {status} {func}()")
            
            if not exists:
                all_exist = False
        
        print()
        return all_exist
    
    def test_config_functions(self):
        """Test configuration helper functions."""
        print("🧪 Testing configuration functions...")
        
        try:
            # Test getting global config
            self.cursor.execute("""
                SELECT batch_size_threshold, partial_batch_min_videos
                FROM get_batch_processing_config(NULL)
            """)
            
            result = self.cursor.fetchone()
            if result:
                batch_size, min_videos = result
                print(f"   ✅ Global config: batch_size={batch_size}, min_videos={min_videos}")
            else:
                print("   ❌ Failed to get global config")
                return False
            
            # Test update_batch_size function
            test_collection = 'test-collection-123'
            self.cursor.execute("""
                SELECT update_batch_size(%s, 7)
            """, (test_collection,))
            
            # Verify the update
            self.cursor.execute("""
                SELECT batch_size_threshold
                FROM batch_processing_config
                WHERE collection_id = %s
            """, (test_collection,))
            
            result = self.cursor.fetchone()
            if result and result[0] == 7:
                print(f"   ✅ Updated batch size for {test_collection}")
                
                # Clean up test data
                self.cursor.execute("""
                    DELETE FROM batch_processing_config
                    WHERE collection_id = %s
                """, (test_collection,))
            else:
                print(f"   ❌ Failed to update batch size")
                return False
            
            print()
            return True
            
        except Exception as e:
            print(f"   ❌ Function test failed: {e}\n")
            return False
    
    def display_config_summary(self):
        """Display configuration summary."""
        print("📋 Configuration Summary:")
        
        try:
            self.cursor.execute("""
                SELECT 
                    config_scope,
                    batch_size_threshold,
                    partial_batch_min_videos,
                    partial_batch_timeout_minutes,
                    max_concurrent_batches,
                    worker_pool_size
                FROM batch_processing_config_summary
            """)
            
            configs = self.cursor.fetchall()
            
            for config in configs:
                scope, batch_size, min_videos, timeout, max_concurrent, workers = config
                print(f"\n   {scope}:")
                print(f"   • Batch Size: {batch_size} videos")
                print(f"   • Min Partial: {min_videos} videos")
                print(f"   • Timeout: {timeout} minutes")
                print(f"   • Max Concurrent: {max_concurrent} batches")
                print(f"   • Workers: {workers}")
            
            print()
            
        except Exception as e:
            print(f"   ❌ Failed to get config summary: {e}\n")
    
    def run_all_tests(self) -> bool:
        """Run all migration tests."""
        print("=" * 60)
        print("🧪 Batch Processing Migration Tests")
        print("=" * 60)
        print()
        
        if not self.connect():
            return False
        
        try:
            # Execute migrations
            print("📦 Executing migrations...")
            print("-" * 60)
            
            for migration in MIGRATIONS:
                if not self.execute_migration(migration):
                    print("❌ Migration execution failed")
                    return False
            
            # Verify tables
            print("=" * 60)
            if not self.verify_tables():
                print("❌ Table verification failed")
                return False
            
            # Verify indexes
            if not self.verify_indexes():
                print("❌ Index verification failed")
                return False
            
            # Verify functions
            if not self.verify_functions():
                print("❌ Function verification failed")
                return False
            
            # Test functions
            if not self.test_config_functions():
                print("❌ Function tests failed")
                return False
            
            # Display config summary
            self.display_config_summary()
            
            print("=" * 60)
            print("✅ All tests passed!")
            print("=" * 60)
            return True
            
        finally:
            self.disconnect()

def main():
    """Main entry point."""
    tester = MigrationTester()
    
    # Check if migrations directory exists
    if not tester.migrations_dir.exists():
        print(f"❌ Migrations directory not found: {tester.migrations_dir}")
        sys.exit(1)
    
    # Run tests
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
