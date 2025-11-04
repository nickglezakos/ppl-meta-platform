#!/usr/bin/env python3
"""
Run MVR-People Database Migration
PPL Meta Platform - vmeta service

Applies migration 002_mvr_people_schema.sql to create MVR-People tables.

Usage:
    python run_mvr_migration.py [--dry-run]
    
Created: October 31, 2025
"""

import asyncio
import asyncpg
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    print("⚠️  No .env file found, using environment variables or defaults")

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'ppl_meta')
DB_USER = os.getenv('DB_USER', 'ppl_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'ppl_password')

CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


async def verify_database_connection():
    """Test database connectivity."""
    print("🔍 Verifying database connection...")
    try:
        conn = await asyncpg.connect(CONNECTION_STRING)
        version = await conn.fetchval('SELECT version()')
        print(f"✅ Connected to PostgreSQL")
        print(f"   Version: {version.split(',')[0]}")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def verify_pgvector():
    """Verify pgvector extension is installed."""
    print("\n🔍 Verifying pgvector extension...")
    try:
        conn = await asyncpg.connect(CONNECTION_STRING)
        result = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        await conn.close()
        
        if result:
            print("✅ pgvector extension is installed")
            return True
        else:
            print("⚠️  pgvector extension not found")
            print("   Installing pgvector...")
            try:
                conn = await asyncpg.connect(CONNECTION_STRING)
                await conn.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
                await conn.close()
                print("✅ pgvector extension installed")
                return True
            except Exception as e:
                print(f"❌ Failed to install pgvector: {e}")
                return False
    except Exception as e:
        print(f"❌ Failed to verify pgvector: {e}")
        return False


async def check_existing_tables():
    """Check if MVR-People tables already exist."""
    print("\n🔍 Checking for existing MVR-People tables...")
    try:
        conn = await asyncpg.connect(CONNECTION_STRING)
        
        tables = ['mvr_people', 'individual_mvr_mapping', 'mvr_merge_audit_log', 'mvr_matching_config']
        existing_tables = []
        
        for table in tables:
            exists = await conn.fetchval(
                f"SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')"
            )
            if exists:
                existing_tables.append(table)
        
        await conn.close()
        
        if existing_tables:
            print(f"⚠️  Found {len(existing_tables)} existing MVR-People tables:")
            for table in existing_tables:
                print(f"   • {table}")
            return existing_tables
        else:
            print("✅ No existing MVR-People tables found (clean slate)")
            return []
            
    except Exception as e:
        print(f"❌ Failed to check existing tables: {e}")
        return []


async def verify_individuals_table():
    """Verify that the individuals table exists (required foreign key)."""
    print("\n🔍 Verifying individuals table exists...")
    try:
        conn = await asyncpg.connect(CONNECTION_STRING)
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'individuals')"
        )
        await conn.close()
        
        if exists:
            print("✅ individuals table exists (required for foreign keys)")
            return True
        else:
            print("❌ individuals table NOT found!")
            print("   MVR-People tables require the individuals table from migration 001")
            print("   Please run 001_cross_video_tracking_schema.sql first")
            return False
    except Exception as e:
        print(f"❌ Failed to verify individuals table: {e}")
        return False


async def run_migration(dry_run=False):
    """Execute the MVR-People migration."""
    migration_file = Path(__file__).parent.parent / 'migrations' / '002_mvr_people_schema.sql'
    
    if not migration_file.exists():
        print(f"❌ Migration file not found: {migration_file}")
        return False
    
    print(f"\n📄 Migration file: {migration_file}")
    
    # Read migration SQL
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    print(f"   Size: {len(migration_sql)} characters")
    print(f"   Lines: {len(migration_sql.splitlines())}")
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
        print("\n--- Migration SQL Preview (first 500 chars) ---")
        print(migration_sql[:500])
        print("...")
        print(f"\n✅ Dry run complete. Use without --dry-run to apply migration.")
        return True
    
    print("\n🚀 Applying migration...")
    print("=" * 80)
    
    try:
        conn = await asyncpg.connect(CONNECTION_STRING)
        
        # Execute migration (PostgreSQL allows multiple statements)
        await conn.execute(migration_sql)
        
        await conn.close()
        
        print("=" * 80)
        print("✅ Migration applied successfully!")
        return True
        
    except Exception as e:
        print("=" * 80)
        print(f"❌ Migration failed: {e}")
        print("\nError details:")
        print(str(e))
        return False


async def verify_migration():
    """Verify migration was successful."""
    print("\n🔍 Verifying migration...")
    try:
        conn = await asyncpg.connect(CONNECTION_STRING)
        
        # Count tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('mvr_people', 'individual_mvr_mapping', 'mvr_merge_audit_log', 'mvr_matching_config')
            ORDER BY table_name
        """)
        
        print(f"\n✅ Found {len(tables)} MVR-People tables:")
        for table in tables:
            print(f"   • {table['table_name']}")
        
        # Count indexes
        indexes = await conn.fetch("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename IN ('mvr_people', 'individual_mvr_mapping', 'mvr_merge_audit_log')
        """)
        
        print(f"\n✅ Created {len(indexes)} indexes")
        
        # Check configuration
        config = await conn.fetchrow("SELECT * FROM mvr_matching_config WHERE config_id = 1")
        if config:
            print(f"\n✅ Default configuration loaded:")
            print(f"   • Similarity Threshold: {config['similarity_threshold']}")
            print(f"   • Auto-Merge Enabled: {config['auto_merge_enabled']}")
            print(f"   • Max Candidates: {config['max_candidates_to_check']}")
        
        await conn.close()
        
        print("\n" + "=" * 80)
        print("🎉 MVR-PEOPLE MIGRATION COMPLETE!")
        print("=" * 80)
        print("\n📋 Next Steps:")
        print("   1. ✅ Phase 1: Database Schema - COMPLETE")
        print("   2. ⏭️  Phase 2: ML Models Setup")
        print("   3. ⏭️  Phase 3: Core Service Implementation")
        print("   4. ⏭️  Phase 4: API Implementation")
        print("\n📖 Design Document: docs/vision-vmeta/MVR_PEOPLE_DESIGN.md")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


async def main():
    """Main migration runner."""
    print("=" * 80)
    print("MVR-PEOPLE DATABASE MIGRATION")
    print("PPL Meta Platform - vmeta service")
    print("=" * 80)
    print(f"\nDatabase: {DB_NAME}@{DB_HOST}:{DB_PORT}")
    print(f"User: {DB_USER}")
    
    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv
    
    # Pre-flight checks
    if not await verify_database_connection():
        sys.exit(1)
    
    if not await verify_pgvector():
        sys.exit(1)
    
    if not await verify_individuals_table():
        sys.exit(1)
    
    existing = await check_existing_tables()
    if existing and not dry_run:
        print("\n⚠️  WARNING: Some MVR-People tables already exist!")
        print("   The migration may fail if tables/constraints already exist.")
        response = input("\n   Continue anyway? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Migration cancelled by user")
            sys.exit(0)
    
    # Run migration
    success = await run_migration(dry_run)
    
    if not success:
        sys.exit(1)
    
    # Verify (only if not dry-run)
    if not dry_run:
        if not await verify_migration():
            sys.exit(1)
    
    print("\n✅ All done!")


if __name__ == "__main__":
    asyncio.run(main())
