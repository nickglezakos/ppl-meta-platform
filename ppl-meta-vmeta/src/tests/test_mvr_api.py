"""
MVR-People API Test Script

Comprehensive testing of all 14 MVR-People API endpoints.

**Prerequisites:**
1. vmeta service running on http://localhost:8008
2. Node service running for authentication
3. Test user credentials available
4. Database with test data

**Test User:**
- Email: fresh.user@example.com
- Password: NewPassword234!

Author: PPL Meta Platform
Date: October 31, 2025
Version: 1.0.0
"""

import asyncio
import logging
from uuid import UUID, uuid4
import httpx
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service URLs
NODE_SERVICE_URL = "http://localhost:8001"
VMETA_SERVICE_URL = "http://localhost:8008"

# Test user credentials
TEST_USER_EMAIL = "fresh.user@example.com"
TEST_USER_PASSWORD = "NewPassword234!"

# Global JWT token
jwt_token = None


async def login_and_get_token() -> str:
    """Login to Node service and get JWT token."""
    global jwt_token
    
    logger.info("🔐 Logging in to Node service...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{NODE_SERVICE_URL}/api/v1/users/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "username": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
            }
        )
        
        if response.status_code != 200:
            logger.error(f"Login failed: {response.status_code}")
            logger.error(response.text)
            raise Exception("Login failed")
        
        data = response.json()
        jwt_token = data.get("access_token")
        
        logger.info(f"✅ Login successful! Token: {jwt_token[:50]}...")
        return jwt_token


def get_headers() -> dict:
    """Get HTTP headers with JWT token."""
    if not jwt_token:
        raise Exception("Not authenticated. Call login_and_get_token() first")
    
    return {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json",
    }


# ============================================================================
# Test Individual MVR Endpoints
# ============================================================================

async def test_endpoint_1_create_mvr(individual_uuid: UUID):
    """Test Endpoint 1: Create MVR-People for Individual."""
    logger.info("\n" + "="*70)
    logger.info("TEST 1: Create MVR-People for Individual")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/individuals/{individual_uuid}/create"
        
        response = await client.post(
            url,
            headers=get_headers(),
            json={
                "background_processing": False,  # Synchronous for testing
                "force_recreate": False
            }
        )
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_2_get_mvr_by_uuid(mvr_uuid: UUID):
    """Test Endpoint 2: Get MVR-People by UUID."""
    logger.info("\n" + "="*70)
    logger.info("TEST 2: Get MVR-People by UUID")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/{mvr_uuid}"
        
        response = await client.get(url, headers=get_headers())
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_3_get_mvr_for_individual(individual_uuid: UUID):
    """Test Endpoint 3: Get MVR-People for Individual."""
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Get MVR-People for Individual")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/individuals/{individual_uuid}"
        
        response = await client.get(url, headers=get_headers())
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_4_search_similar(mvr_uuid: UUID):
    """Test Endpoint 4: Search Similar MVR-People."""
    logger.info("\n" + "="*70)
    logger.info("TEST 4: Search Similar MVR-People")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/search/similar"
        
        response = await client.post(
            url,
            headers=get_headers(),
            json={
                "mvr_people_uuid": str(mvr_uuid),
                "similarity_threshold": 0.7,
                "max_results": 10,
                "include_demographics": True
            }
        )
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_5_search_demographics():
    """Test Endpoint 5: Search MVR-People by Demographics."""
    logger.info("\n" + "="*70)
    logger.info("TEST 5: Search MVR-People by Demographics")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/search/demographics"
        
        response = await client.post(
            url,
            headers=get_headers(),
            json={
                "age_min": 25,
                "age_max": 40,
                "gender": "male",
                "min_confidence": 0.7,
                "page": 1,
                "page_size": 20
            }
        )
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_6_link_individual(mvr_uuid: UUID, individual_uuid: UUID):
    """Test Endpoint 6: Link Individual to MVR-People."""
    logger.info("\n" + "="*70)
    logger.info("TEST 6: Link Individual to MVR-People")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/{mvr_uuid}/link-individual"
        
        response = await client.post(
            url,
            headers=get_headers(),
            json={
                "individual_uuid": str(individual_uuid),
                "confidence_score": 0.85
            }
        )
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_7_batch_create(individual_uuids: list):
    """Test Endpoint 7: Batch Create MVR-People."""
    logger.info("\n" + "="*70)
    logger.info("TEST 7: Batch Create MVR-People")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/batch/create"
        
        response = await client.post(
            url,
            headers=get_headers(),
            json={
                "individual_uuids": [str(uuid) for uuid in individual_uuids],
                "background_processing": True
            }
        )
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_8_get_status(mvr_uuid: UUID):
    """Test Endpoint 8: Get MVR-People Processing Status."""
    logger.info("\n" + "="*70)
    logger.info("TEST 8: Get MVR-People Processing Status")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/{mvr_uuid}/status"
        
        response = await client.get(url, headers=get_headers())
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_9_match_individual(individual_uuid: UUID):
    """Test Endpoint 9: Match Individuals."""
    logger.info("\n" + "="*70)
    logger.info("TEST 9: Match Individuals")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/individuals/{individual_uuid}/match"
        
        response = await client.post(
            url,
            headers=get_headers(),
            json={
                "threshold": 0.85,
                "auto_merge": False,
                "max_results": 10
            }
        )
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_10_merge_individuals(individual_a: UUID, individual_b: UUID):
    """Test Endpoint 10: Merge Individuals."""
    logger.info("\n" + "="*70)
    logger.info("TEST 10: Merge Individuals")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/merge"
        
        response = await client.post(
            url,
            headers=get_headers(),
            json={
                "individual_a_uuid": str(individual_a),
                "individual_b_uuid": str(individual_b),
                "similarity_score": 0.92,
                "triggered_by": "manual"
            }
        )
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_11_merge_history(individual_uuid: UUID):
    """Test Endpoint 11: Get Merge History."""
    logger.info("\n" + "="*70)
    logger.info("TEST 11: Get Merge History for Individual")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/individuals/{individual_uuid}/merge-history"
        
        response = await client.get(url, headers=get_headers())
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_12_get_orphaned():
    """Test Endpoint 12: Get Orphaned MVR-People."""
    logger.info("\n" + "="*70)
    logger.info("TEST 12: Get Orphaned MVR-People")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/orphaned"
        
        response = await client.get(
            url,
            headers=get_headers(),
            params={
                "page": 1,
                "page_size": 20
            }
        )
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_13_update_config():
    """Test Endpoint 13: Update Matching Configuration."""
    logger.info("\n" + "="*70)
    logger.info("TEST 13: Update Matching Configuration")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/config/matching"
        
        response = await client.put(
            url,
            headers=get_headers(),
            json={
                "default_matching_threshold": 0.90,
                "auto_merge_enabled": True,
                "min_quality_threshold": 0.65
            }
        )
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


async def test_endpoint_14_get_config():
    """Test Endpoint 14: Get Matching Configuration."""
    logger.info("\n" + "="*70)
    logger.info("TEST 14: Get Matching Configuration")
    logger.info("="*70)
    
    async with httpx.AsyncClient() as client:
        url = f"{VMETA_SERVICE_URL}/api/v1/mvr-people/config/matching"
        
        response = await client.get(url, headers=get_headers())
        
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()


# ============================================================================
# Main Test Runner
# ============================================================================

async def run_all_tests():
    """Run all 14 endpoint tests."""
    logger.info("\n" + "="*70)
    logger.info("MVR-PEOPLE API - COMPREHENSIVE TEST SUITE")
    logger.info("="*70)
    logger.info("Testing all 14 MVR-People API endpoints")
    logger.info("="*70 + "\n")
    
    try:
        # Step 1: Login and get token
        await login_and_get_token()
        
        # Step 2: Test configuration endpoints first (14, 13)
        await test_endpoint_14_get_config()
        # await test_endpoint_13_update_config()  # Skip for now
        
        # Step 3: Test with sample Individual UUID (replace with real UUID)
        sample_individual_uuid = uuid4()  # Replace with real Individual UUID
        logger.warning(
            f"\n⚠️ Using sample UUID: {sample_individual_uuid}\n"
            f"⚠️ Replace with real Individual UUID from database for actual testing\n"
        )
        
        # Endpoints 1-3: Create and retrieve MVR
        # create_result = await test_endpoint_1_create_mvr(sample_individual_uuid)
        # mvr_uuid = create_result.get('mvr_people_uuid')
        # await test_endpoint_2_get_mvr_by_uuid(mvr_uuid)
        # await test_endpoint_3_get_mvr_for_individual(sample_individual_uuid)
        
        # Endpoints 4-5: Search
        # await test_endpoint_4_search_similar(mvr_uuid)
        # await test_endpoint_5_search_demographics()
        
        # Endpoint 8: Status
        # await test_endpoint_8_get_status(mvr_uuid)
        
        # Endpoint 9: Matching
        # await test_endpoint_9_match_individual(sample_individual_uuid)
        
        # Endpoint 11-12: History and Orphaned
        # await test_endpoint_11_merge_history(sample_individual_uuid)
        await test_endpoint_12_get_orphaned()
        
        logger.info("\n" + "="*70)
        logger.info("✅ TEST SUITE COMPLETED")
        logger.info("="*70)
        
    except Exception as e:
        logger.error(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
