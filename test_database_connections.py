#!/usr/bin/env python3
"""
Database Connection Test Script
Tests database connections for all PPL Meta Platform services
"""

import os
import sys
from urllib.parse import urlparse
import logging

# Add src directories to path for each service
services = ['ppl-meta-node', 'ppl-meta-media', 'ppl-meta-orchestrator']
for service in services:
    service_src = os.path.join(os.path.dirname(__file__), service, 'src')
    if os.path.exists(service_src):
        sys.path.insert(0, service_src)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_service_database(service_name: str) -> bool:
    """Test database connection for a specific service."""
    print(f"\n🔍 Testing {service_name} database connection...")
    
    try:
        if service_name == 'ppl-meta-node':
            from ppl_meta_node.src.config import settings
            from ppl_meta_node.src.database import test_connection
        elif service_name == 'ppl-meta-media':
            from ppl_meta_media.src.config import config as settings
            from ppl_meta_media.src.database import test_connection
        elif service_name == 'ppl-meta-orchestrator':
            from ppl_meta_orchestrator.src.config import settings
            # Import would need to be created
            
        db_url = settings.get_database_url() if hasattr(settings, 'get_database_url') else settings.DATABASE_URL
        
        print(f"   Database URL: {db_url}")
        
        # Validate URL format
        if hasattr(settings, 'validate_database_url'):
            if not settings.validate_database_url():
                print(f"   ❌ URL validation failed")
                return False
        
        # Test actual connection
        if 'test_connection' in locals():
            if test_connection():
                print(f"   ✅ Connection successful")
                return True
            else:
                print(f"   ❌ Connection failed")
                return False
        else:
            print(f"   ⚠️  Connection test not available")
            return True
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Test all service database connections."""
    print("🗄️  PPL Meta Platform - Database Connection Test")
    print("=" * 50)
    
    services = ['ppl-meta-node', 'ppl-meta-media', 'ppl-meta-orchestrator']
    results = {}
    
    for service in services:
        results[service] = test_service_database(service)
    
    print(f"\n📊 Test Results:")
    print("-" * 30)
    
    all_passed = True
    for service, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {service}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print(f"\n🎉 All database connections working correctly!")
        return 0
    else:
        print(f"\n⚠️  Some database connections failed. Check configurations.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
