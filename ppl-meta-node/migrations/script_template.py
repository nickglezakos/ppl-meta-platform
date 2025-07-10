#!/usr/bin/env python3
"""
Migration Script Template for PPL Meta Node Service

This script helps with database migration management.
"""

import os
import sys

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    from src.config import settings
    from src.database import SessionLocal, engine

    # Import all models to ensure they're registered
    from src.models import app_setting, installation_info, log, otp, role, user
    from src.models.user import Base

    print(f"✅ Successfully loaded models")
    print(f"✅ Database URL: {settings.get_database_url()}")

    # Test database connection
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print(f"✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

    # List all tables that would be created
    print(f"\n📋 Tables to be managed by migrations:")
    for table_name in Base.metadata.tables.keys():
        print(f"   - {table_name}")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the node service directory")
except Exception as e:
    print(f"❌ Error: {e}")
