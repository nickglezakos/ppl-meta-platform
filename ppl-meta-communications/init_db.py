#!/usr/bin/env python3
"""
Initialize the Communications Service database.
Creates all tables defined in the models.
"""
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import create_tables, test_connection, get_db_info

# Import all models to ensure they are registered with SQLAlchemy
from src.models.communication_log import CommunicationLog
from src.models.email_template import EmailTemplate
from src.models.webhook_config import WebhookConfig

if __name__ == "__main__":
    print("🔧 Communications Service Database Initialization")
    print("=" * 60)
    
    # Test connection
    print("\n1. Testing database connection...")
    if test_connection():
        print("   ✅ Database connection successful")
    else:
        print("   ❌ Database connection failed")
        sys.exit(1)
    
    # Get database info
    print("\n2. Database information:")
    db_info = get_db_info()
    print(f"   Database: {db_info.get('database')}")
    print(f"   User: {db_info.get('user')}")
    print(f"   Status: {db_info.get('status')}")
    
    # Create tables
    print("\n3. Creating database tables...")
    try:
        create_tables()
        print("   ✅ Tables created successfully")
    except Exception as e:
        print(f"   ❌ Failed to create tables: {e}")
        sys.exit(1)
    
    print("\n✅ Database initialization complete!")
    print("=" * 60)
