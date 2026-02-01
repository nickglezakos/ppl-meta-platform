#!/usr/bin/env python3
"""
Script to run database migrations for ppl-meta-cameras service.
Usage: python run_migration.py <migration_file.sql>
"""

import sys
import os
from sqlalchemy import text

# Add src to path to import database module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import engine

def run_migration(migration_file):
    """Run a SQL migration file."""
    print(f"📦 Running migration: {migration_file}")
    
    # Read migration file
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    # Execute migration
    try:
        with engine.connect() as conn:
            # Split by semicolon to handle multiple statements
            statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
            
            for statement in statements:
                if statement:
                    print(f"  ➜ Executing: {statement[:60]}...")
                    conn.execute(text(statement))
            
            conn.commit()
        
        print(f"✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_migration.py <migration_file.sql>")
        sys.exit(1)
    
    migration_file = sys.argv[1]
    
    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)
    
    success = run_migration(migration_file)
    sys.exit(0 if success else 1)
