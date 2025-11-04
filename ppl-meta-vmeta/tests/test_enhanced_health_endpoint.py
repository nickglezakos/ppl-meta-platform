"""
Test Enhanced vmeta Health Endpoint with MVR-People Status

Validates that the /health endpoint includes MVR-People system status.

Author: PPL Meta Platform
Date: November 1, 2025
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import httpx
import json


async def test_enhanced_health_endpoint():
    """Test enhanced vmeta health endpoint with MVR-People integration."""
    
    print("=" * 80)
    print("🏥 Enhanced vmeta Health Endpoint Test")
    print("=" * 80)
    print()
    
    base_url = "http://localhost:8008"
    health_url = f"{base_url}/health"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"📡 Testing endpoint: {health_url}")
            print()
            
            response = await client.get(health_url)
            
            if response.status_code == 200:
                data = response.json()
                
                # Core vmeta service info
                print("📊 CORE SERVICE:")
                print(f"  • Status: {data.get('status', 'unknown')}")
                print(f"  • Service: {data.get('service', 'unknown')}")
                print(f"  • Version: {data.get('version', 'unknown')}")
                print(f"  • Response Time: {data.get('response_time_ms', 0):.2f}ms")
                print()
                
                # MVR-People status
                mvr = data.get('mvr_people', {})
                available = mvr.get('mvr_people_available', False)
                
                status_emoji = '✅' if available else '❌'
                print(f"{status_emoji} MVR-PEOPLE SYSTEM:")
                print(f"  • Available: {'Yes' if available else 'No'}")
                
                if available:
                    # Database
                    db = mvr.get('database', {})
                    db_connected = db.get('connected', False)
                    print(f"  • Database: {'✅' if db_connected else '❌'} Connected")
                    if db_connected:
                        print(f"    - Pool Size: {db.get('pool_size', 0)}")
                        print(f"    - Idle: {db.get('idle_connections', 0)}")
                    
                    # ML Models
                    ml = mvr.get('ml_models', {})
                    loaded = ml.get('total_loaded', 0)
                    expected = ml.get('total_expected', 3)
                    print(f"  • ML Models: {loaded}/{expected} loaded")
                    
                    # Statistics
                    stats = mvr.get('statistics', {})
                    print(f"  • Statistics:")
                    print(f"    - Total MVR: {stats.get('total_mvr_people', 0)}")
                    print(f"    - Active: {stats.get('active_mvr_people', 0)}")
                    print(f"    - Orphaned: {stats.get('orphaned_mvr_people', 0)}")
                    print(f"    - Individuals: {stats.get('individuals_with_mvr', 0)}")
                else:
                    error = mvr.get('error', 'Unknown error')
                    print(f"  • Error: {error}")
                
                print()
                
                # Save response
                output_file = Path(__file__).parent / "enhanced_health_response.json"
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"💾 Full response saved to: {output_file}")
                print()
                
                # Validate required fields
                print("🔍 VALIDATION:")
                validations = [
                    ("Core status field", 'status' in data),
                    ("Service name", data.get('service') == 'vmeta'),
                    ("MVR-People section", 'mvr_people' in data),
                    ("MVR availability flag", 'mvr_people_available' in mvr),
                    ("Response time", 'response_time_ms' in data),
                ]
                
                all_valid = True
                for check_name, result in validations:
                    emoji = '✅' if result else '❌'
                    print(f"  {emoji} {check_name}")
                    if not result:
                        all_valid = False
                
                print()
                
                if all_valid:
                    print("✅ ALL VALIDATIONS PASSED")
                    print()
                    print("📋 SUMMARY:")
                    print(f"  • vmeta service: healthy")
                    print(f"  • MVR-People: {'available' if available else 'unavailable'}")
                    if available and db_connected:
                        print(f"  • Database: connected")
                        print(f"  • MVR records: {stats.get('total_mvr_people', 0)}")
                    return True
                else:
                    print("❌ SOME VALIDATIONS FAILED")
                    return False
                    
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except httpx.ConnectError:
        print("❌ CONNECTION ERROR - vmeta service not running")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def compare_with_nginx():
    """Test health endpoint via nginx proxy."""
    
    print("=" * 80)
    print("🌐 Health Check via Nginx Proxy")
    print("=" * 80)
    print()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test via nginx (if running)
            try:
                nginx_response = await client.get("http://localhost/health/vmeta")
                nginx_data = nginx_response.json()
                
                print("✅ Nginx proxy is running")
                print(f"  • Status via nginx: {nginx_data.get('status')}")
                print(f"  • MVR available: {nginx_data.get('mvr_people', {}).get('mvr_people_available', False)}")
                print()
            except:
                print("⚠️  Nginx not running or vmeta route not configured")
                print()
                
    except Exception as e:
        print(f"⚠️  Could not test nginx: {e}")
        print()


if __name__ == "__main__":
    print()
    print("🚀 Starting Enhanced Health Endpoint Tests")
    print()
    
    # Run main test
    success = asyncio.run(test_enhanced_health_endpoint())
    
    print()
    print("=" * 80)
    
    # Test via nginx if main test passed
    if success:
        print()
        asyncio.run(compare_with_nginx())
        print()
        print("=" * 80)
    
    print()
    if success:
        print("✅ ALL TESTS PASSED")
        print()
        print("💡 The /health endpoint now includes MVR-People system status!")
        print("   • Use it for monitoring and health checks")
        print("   • No authentication required")
        print("   • Includes database, ML models, and statistics")
        sys.exit(0)
    else:
        print("❌ TESTS FAILED")
        sys.exit(1)
