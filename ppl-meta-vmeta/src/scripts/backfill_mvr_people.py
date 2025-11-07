"""
Backfill MVR-People for Existing Individuals

This script creates MVR-People objects for individuals that were created
without MVR associations due to the direct INSERT bypass in cross_video_tracking_simple.py.

Root Cause: Lines 912-926 of cross_video_tracking_simple.py used direct INSERT
instead of repository.create_individual(), bypassing the MVR trigger.

Resolution: Create MVR-People for all 131 individuals that have session links
but no MVR-People associations.

Author: AI Assistant
Date: November 5, 2025
"""

import asyncio
import logging
import sys
from uuid import UUID

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


async def get_auth_token():
    """Get authentication token from the user service."""
    import aiohttp
    
    logger.info("🔑 Obtaining authentication token...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://localhost:8001/api/v1/users/login',
                data={
                    'username': 'fresh.user@example.com',
                    'password': 'NewPassword234!'
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    token = result.get('access_token')
                    logger.info("✅ Authentication successful")
                    return token
                else:
                    error_text = await response.text()
                    logger.error(
                        f"❌ Authentication failed: "
                        f"{response.status} - {error_text}"
                    )
                    return None
    except Exception as e:
        logger.error(f"❌ Failed to get auth token: {e}")
        return None


async def backfill_mvr_people():
    """
    Create MVR-People for individuals that don't have MVR associations.
    
    Strategy:
    1. Find all individuals that have session links but no MVR mappings
    2. For each individual, trigger MVR-People creation
    3. Track success/failure counts
    4. Verify all individuals now have MVR associations
    """
    logger.info("=" * 60)
    logger.info("MVR-PEOPLE BACKFILL SCRIPT")
    logger.info("=" * 60)
    logger.info("")
    logger.info("This script will create MVR-People for individuals")
    logger.info("that were created without MVR associations.")
    logger.info("")
    
    try:
        # Get authentication token
        auth_token = await get_auth_token()
        if not auth_token:
            logger.error("❌ Cannot proceed without authentication token")
            return
        
        logger.info("")
        
        # Add parent directory to path for imports
        import os
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        import asyncpg
        
        logger.info("✅ Using authenticated API calls to create MVR-People")
        logger.info("")
        
        # Connect to database
        conn_string = (
            "postgresql://postgres:localdevpass@localhost:5432/ppl_meta_vmeta"
        )
        pool = await asyncpg.create_pool(conn_string)
        
        try:
            async with pool.acquire() as conn:
                # Find individuals with session links but no MVR mappings
                orphaned = await conn.fetch("""
                    SELECT 
                        i.individual_uuid,
                        i.individual_id,
                        si.session_uuid
                    FROM individuals i
                    INNER JOIN session_individuals si 
                        ON i.individual_uuid = si.individual_uuid
                    LEFT JOIN individual_mvr_mapping imm 
                        ON i.individual_uuid = imm.individual_uuid
                    WHERE imm.mapping_uuid IS NULL
                    ORDER BY i.created_at ASC
                """)
                
                logger.info(
                    f"Found {len(orphaned)} individuals "
                    f"without MVR-People mappings"
                )
                logger.info("")
                
                if len(orphaned) == 0:
                    logger.info("✅ All individuals already have MVR associations!")
                    return
                
                # Process each individual
                success_count = 0
                failed_count = 0
                
                # We'll call the MVR-People creation API endpoint directly
                import aiohttp
                
                for row in orphaned:
                    ind_uuid = str(row['individual_uuid'])
                    ind_id = row['individual_id']
                    sess_uuid = str(row['session_uuid'])
                    
                    try:
                        # Call the create MVR-People endpoint with auth
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                f"http://localhost:8008/api/v1/mvr-people/individuals/{ind_uuid}/create",
                                json={
                                    "background_processing": False,
                                    "force_recreate": False
                                },
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": f"Bearer {auth_token}"
                                }
                            ) as response:
                                if response.status == 200:
                                    result = await response.json()
                                    mvr_uuid = result.get('mvr_people_uuid')
                                    logger.info(
                                        f"✅ Created MVR-People {mvr_uuid} for {ind_id}"
                                    )
                                    success_count += 1
                                elif response.status == 409:
                                    # Already exists - this is okay
                                    logger.info(
                                        f"✅ MVR-People already exists for {ind_id}"
                                    )
                                    success_count += 1
                                else:
                                    error_text = await response.text()
                                    logger.warning(
                                        f"⚠️ Failed to create MVR-People for {ind_id}: "
                                        f"{response.status} - {error_text[:100]}"
                                    )
                                    failed_count += 1
                            
                    except Exception as e:
                        logger.error(
                            f"❌ Failed to create MVR-People for {ind_id}: {e}"
                        )
                        failed_count += 1
                
                logger.info("")
                logger.info("=" * 60)
                logger.info("BACKFILL SUMMARY")
                logger.info("=" * 60)
                logger.info(f"Total individuals processed: {len(orphaned)}")
                logger.info(f"✅ Successfully created MVR-People: {success_count}")
                logger.info(f"❌ Failed: {failed_count}")
                logger.info("=" * 60)
                logger.info("")
                
                # Verify final state
                final_orphaned_count = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM individuals i
                    INNER JOIN session_individuals si 
                        ON i.individual_uuid = si.individual_uuid
                    LEFT JOIN individual_mvr_mapping imm 
                        ON i.individual_uuid = imm.individual_uuid
                    WHERE imm.mapping_uuid IS NULL
                """)
                
                logger.info(
                    f"Remaining individuals without MVR: {final_orphaned_count}"
                )
                
                if final_orphaned_count > 0:
                    logger.warning(
                        f"⚠️ {final_orphaned_count} individuals still "
                        f"missing MVR associations"
                    )
                else:
                    logger.info("✅ All individuals now have MVR-People associations!")
                
        finally:
            await pool.close()
            
    except Exception as e:
        logger.error(f"❌ Backfill failed with error: {e}")
        raise


async def verify_mvr_people_status():
    """
    Verify the current state of MVR-People associations.
    """
    import asyncpg
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("MVR-PEOPLE VERIFICATION")
    logger.info("=" * 60)
    
    conn_string = (
        "postgresql://postgres:localdevpass@localhost:5432/ppl_meta_vmeta"
    )
    pool = await asyncpg.create_pool(conn_string)
    
    try:
        async with pool.acquire() as conn:
            # Total individuals
            total_individuals = await conn.fetchval(
                "SELECT COUNT(*) FROM individuals"
            )
            
            # Individuals with MVR mappings
            individuals_with_mvr = await conn.fetchval("""
                SELECT COUNT(DISTINCT individual_uuid)
                FROM individual_mvr_mapping
            """)
            
            # Total MVR-People
            total_mvr_people = await conn.fetchval(
                "SELECT COUNT(*) FROM mvr_people"
            )
            
            # Total mappings
            total_mappings = await conn.fetchval(
                "SELECT COUNT(*) FROM individual_mvr_mapping"
            )
            
            logger.info(f"Total individuals: {total_individuals}")
            logger.info(f"Individuals with MVR mappings: {individuals_with_mvr}")
            logger.info(f"Total MVR-People records: {total_mvr_people}")
            logger.info(f"Total individual↔MVR mappings: {total_mappings}")
            logger.info("")
            
            if individuals_with_mvr == total_individuals:
                logger.info("✅ All individuals have MVR-People associations!")
            else:
                missing = total_individuals - individuals_with_mvr
                logger.warning(
                    f"⚠️ {missing} individuals missing MVR associations"
                )
            
            logger.info("=" * 60)
            
    finally:
        await pool.close()


async def main():
    """Main entry point."""
    try:
        await backfill_mvr_people()
        await verify_mvr_people_status()
        logger.info("")
        logger.info("✅ MVR-People backfill complete!")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Backfill interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
