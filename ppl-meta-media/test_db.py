#!/usr/bin/env python3
"""
Database connection test script.
Run this to verify your PostgreSQL connection is working.
"""

import sys
import os
from dotenv import load_dotenv

# Add src to path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_database():
    """Test database connection and display info."""
    try:
        # Force reload the environment variables
        load_dotenv(override=True)
        
        from src.database import test_connection, get_db_info
        from src.config import config
        
        print("=== Database Connection Test ===")
        print(f"Database URL: {config.get_database_url()}")
        print()
        
        # Test connection
        print("Testing connection...")
        if test_connection():
            print("✅ Connection successful!")
            
            # Get database info
            print("\nDatabase Information:")
            db_info = get_db_info()
            for key, value in db_info.items():
                print(f"  {key.capitalize()}: {value}")
        else:
            print("❌ Connection failed!")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)
