"""
Test MVR-People Health Endpoint

Simple test to validate the /api/v1/mvr-people/health endpoint.

Author: PPL Meta Platform
Date: November 1, 2025
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import httpx
import json
from datetime import datetime


async def test_mvr_health_endpoint():
    """Test MVR-People health check endpoint."""
    
    print("=" * 80)
    print("🏥 MVR-People Health Check Test")
    print("=" * 80)
    print()
    
    # vmeta service URL
    base_url = "http://localhost:8008"
    health_url = f"{base_url}/api/v1/mvr-people/health"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print(f"📡 Testing endpoint: {health_url}")
            print()
            
            # Make request
            response = await client.get(health_url)
            
            print(f"📊 Response Status: {response.status_code}")
            print()
            
            # Parse response
            if response.status_code in [200, 503]:
                data = response.json()
                
                # Display overall status
                status = data.get('status', 'unknown')
                timestamp = data.get('timestamp', 'unknown')
                version = data.get('version', 'unknown')
                
                status_emoji = {
                    'healthy': '✅',
                    'degraded': '⚠️',
                    'unhealthy': '❌'
                }.get(status, '❓')
                
                print(f"{status_emoji} Overall Status: {status.upper()}")
                print(f"🕐 Timestamp: {timestamp}")
                print(f"📦 Version: {version}")
                print()
                
                # Database health
                print("📊 DATABASE HEALTH:")
                db = data.get('database', {})
                print(f"  • Connected: {'✅' if db.get('connected') else '❌'}")
                print(f"  • Pool Size: {db.get('pool_size', 0)}")
                print(f"  • Idle Connections: {db.get('idle_connections', 0)}")
                print(f"  • Response Time: {db.get('response_time_ms', 0):.2f}ms")
                print(f"  • pgvector: {'✅' if db.get('pgvector_available') else '❌'}")
                print()
                
                # ML Models health
                print("🧠 ML MODELS HEALTH:")
                ml = data.get('ml_models', {})
                print(f"  • FaceNet: {'✅' if ml.get('facenet_loaded') else '❌'}")
                print(f"  • Age Model: {'✅' if ml.get('age_model_loaded') else '❌'}")
                print(f"  • Gender Model: {'✅' if ml.get('gender_model_loaded') else '❌'}")
                print(f"  • Total Loaded: {ml.get('total_models_loaded', 0)}/3")
                print(f"  • Load Time: {ml.get('model_load_time_ms', 0):.2f}ms")
                print()
                
                # Processing queue health
                print("⚙️ PROCESSING QUEUE:")
                queue = data.get('processing_queue', {})
                print(f"  • Queue Size: {queue.get('queue_size', 0)}")
                print(f"  • Processing: {queue.get('processing_tasks', 0)}")
                print(f"  • Pending: {queue.get('pending_tasks', 0)}")
                print(f"  • Failed (1h): {queue.get('failed_tasks_last_hour', 0)}")
                print(f"  • Avg Time: {queue.get('average_processing_time_ms', 0):.2f}ms")
                print()
                
                # Statistics
                print("📈 SYSTEM STATISTICS:")
                stats = data.get('statistics', {})
                print(f"  • Total MVR-People: {stats.get('total_mvr_people', 0)}")
                print(f"  • Active MVR: {stats.get('active_mvr_people', 0)}")
                print(f"  • Orphaned MVR: {stats.get('orphaned_mvr_people', 0)}")
                print(f"  • Individuals with MVR: {stats.get('individuals_with_mvr', 0)}")
                print(f"  • Total Merges: {stats.get('total_merge_operations', 0)}")
                print(f"  • Avg Quality: {stats.get('average_quality_score', 0):.3f}")
                print()
                
                # Warnings and errors
                warnings = data.get('warnings', [])
                errors = data.get('errors', [])
                
                if warnings:
                    print("⚠️  WARNINGS:")
                    for warning in warnings:
                        print(f"  • {warning}")
                    print()
                
                if errors:
                    print("❌ ERRORS:")
                    for error in errors:
                        print(f"  • {error}")
                    print()
                
                # Additional metadata
                uptime = data.get('uptime_seconds', 0)
                last_mvr = data.get('last_mvr_created_at')
                last_merge = data.get('last_merge_at')
                
                print("ℹ️  METADATA:")
                print(f"  • Uptime: {uptime:.2f}s")
                print(f"  • Last MVR Created: {last_mvr or 'Never'}")
                print(f"  • Last Merge: {last_merge or 'Never'}")
                print()
                
                # Save full response to file
                output_file = Path(__file__).parent / "mvr_health_response.json"
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                print(f"💾 Full response saved to: {output_file}")
                print()
                
                # Test result
                if response.status_code == 200:
                    print("✅ TEST PASSED - Health endpoint working!")
                    return True
                else:
                    print("⚠️  TEST WARNING - Endpoint returned 503 (unhealthy)")
                    return False
                    
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except httpx.ConnectError:
        print("❌ CONNECTION ERROR - vmeta service not running on localhost:8008")
        print()
        print("💡 Start the service with:")
        print("   cd ppl-meta-vmeta/src && uvicorn main:app --host 0.0.0.0 --port 8008 --reload")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_comparison_with_main_health():
    """Compare MVR health endpoint with main /health endpoint."""
    
    print("=" * 80)
    print("🔄 Comparison: Main Health vs MVR Health")
    print("=" * 80)
    print()
    
    base_url = "http://localhost:8008"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get main health
            main_response = await client.get(f"{base_url}/health")
            main_data = main_response.json()
            
            print("📊 MAIN HEALTH (/health):")
            print(f"  • Status: {main_data.get('status', 'unknown')}")
            print(f"  • Service: {main_data.get('service', 'unknown')}")
            print(f"  • Version: {main_data.get('version', 'unknown')}")
            print()
            
            # Get MVR health
            mvr_response = await client.get(f"{base_url}/api/v1/mvr-people/health")
            mvr_data = mvr_response.json()
            
            print("📊 MVR-PEOPLE HEALTH (/api/v1/mvr-people/health):")
            print(f"  • Status: {mvr_data.get('status', 'unknown')}")
            print(f"  • Database: {'✅' if mvr_data.get('database', {}).get('connected') else '❌'}")
            print(f"  • ML Models: {mvr_data.get('ml_models', {}).get('total_models_loaded', 0)}/3")
            print(f"  • Total MVR: {mvr_data.get('statistics', {}).get('total_mvr_people', 0)}")
            print()
            
            print("✅ Both endpoints working!")
            
    except Exception as e:
        print(f"⚠️  Could not compare endpoints: {e}")


if __name__ == "__main__":
    print()
    print("🚀 Starting MVR-People Health Endpoint Tests")
    print()
    
    # Run main test
    success = asyncio.run(test_mvr_health_endpoint())
    
    print()
    print("=" * 80)
    
    # Run comparison test if main test passed
    if success:
        print()
        asyncio.run(test_comparison_with_main_health())
        print()
        print("=" * 80)
    
    print()
    if success:
        print("✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ TESTS FAILED")
        sys.exit(1)
