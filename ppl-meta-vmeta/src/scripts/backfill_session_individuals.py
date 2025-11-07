"""
Backfill session_individuals table for existing orphaned individuals.

This script links existing individuals to their tracking sessions based on
the timestamps of their video appearances.

Issue: 145 individuals exist but session_individuals table is empty.
Root Cause: Direct INSERT into individuals table bypassed session link creation.
Fix: Match individuals to sessions via timestamp overlap.
"""

import asyncio
import logging
from uuid import UUID
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_session_individuals():
    """
    Backfill session_individuals table for all orphaned individuals.
    
    Strategy:
    1. Find all individuals without session links
    2. For each individual, get their video appearance timestamps
    3. Match to tracking session based on time range overlap
    4. Create the missing session_individuals link
    """
    
    # Use asyncpg directly to avoid complex imports
    import asyncpg
    
    # Connect directly to database
    conn_string = (
        "postgresql://postgres:localdevpass@localhost:5432/ppl_meta_vmeta"
    )
    pool = await asyncpg.create_pool(conn_string)
    
    try:
        async with pool.acquire() as conn:
            # Step 1: Find orphaned individuals (no session link)
            orphaned = await conn.fetch("""
                SELECT individual_uuid, individual_id
                FROM individuals
                WHERE individual_uuid NOT IN (
                    SELECT individual_uuid FROM session_individuals
                )
            """)
            
            logger.info(
                f"Found {len(orphaned)} individuals without session links"
            )
            
            if len(orphaned) == 0:
                logger.info("✅ No orphaned individuals - all linked!")
                return
            
            # Step 2: Get all tracking sessions
            sessions = await conn.fetch("""
                SELECT 
                    session_uuid,
                    start_time,
                    end_time,
                    collections
                FROM tracking_sessions
                WHERE status = 'completed'
                ORDER BY created_at DESC
            """)
            
            logger.info(f"Found {len(sessions)} completed tracking sessions")
            
            if len(sessions) == 0:
                logger.error(
                    "❌ No completed sessions found - "
                    "cannot determine session membership"
                )
                return
            
            success_count = 0
            failed_count = 0
            skipped_count = 0
            
            # Step 3: Process each orphaned individual
            for ind_row in orphaned:
                ind_uuid = ind_row['individual_uuid']
                ind_id = ind_row['individual_id']
                
                try:
                    # Get individual's video appearances
                    appearances = await conn.fetch("""
                        SELECT 
                            video_uuid,
                            start_timestamp,
                            end_timestamp
                        FROM individual_video_appearances
                        WHERE individual_uuid = $1
                        ORDER BY start_timestamp
                    """, ind_uuid)
                    
                    if not appearances:
                        logger.warning(
                            f"⚠️ Individual {ind_id} has no appearances - "
                            f"skipping"
                        )
                        skipped_count += 1
                        continue
                    
                    # Get time range of individual's appearances
                    first_seen = min(
                        a['start_timestamp'] for a in appearances
                    )
                    last_seen = max(
                        a['end_timestamp'] for a in appearances
                    )
                    
                    # Step 4: Find matching session(s)
                    matched_session = None
                    for session in sessions:
                        # Check if individual's time range overlaps session
                        session_start = session['start_time']
                        session_end = session['end_time']
                        
                        # Check for overlap
                        if (first_seen <= session_end and
                                last_seen >= session_start):
                            matched_session = session
                            break
                    
                    if not matched_session:
                        logger.warning(
                            f"⚠️ Individual {ind_id} "
                            f"({first_seen} - {last_seen}) "
                            f"doesn't match any session - skipping"
                        )
                        skipped_count += 1
                        continue
                    
                    # Step 5: Create session-individual link
                    await conn.execute("""
                        INSERT INTO session_individuals
                        (session_uuid, individual_uuid, processing_type, confidence_contribution)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (session_uuid, individual_uuid) DO NOTHING
                    """, matched_session['session_uuid'], ind_uuid, 'new', 0.8)
                    
                    success_count += 1
                    logger.info(
                        f"✅ Linked {ind_id} to session "
                        f"{matched_session['session_uuid']}"
                    )
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(
                        f"❌ Failed to process individual {ind_id}: {e}"
                    )
                    continue
            
            # Step 6: Summary
            logger.info("")
            logger.info("=" * 60)
            logger.info("BACKFILL SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Total orphaned individuals: {len(orphaned)}")
            logger.info(f"✅ Successfully linked: {success_count}")
            logger.info(f"⚠️ Skipped (no appearances): {skipped_count}")
            logger.info(f"❌ Failed: {failed_count}")
            logger.info("=" * 60)
            
            # Step 7: Verify results
            final_orphaned = await conn.fetchval("""
                SELECT COUNT(*)
                FROM individuals
                WHERE individual_uuid NOT IN (
                    SELECT individual_uuid FROM session_individuals
                )
            """)
            
            logger.info("")
            logger.info(f"Remaining orphaned individuals: {final_orphaned}")
            
            if final_orphaned == 0:
                logger.info("🎉 SUCCESS! All individuals now linked to sessions")
            else:
                logger.warning(
                    f"⚠️ {final_orphaned} individuals still orphaned "
                    f"(no matching sessions)"
                )
                
    except Exception as e:
        logger.error(f"❌ Backfill failed with error: {e}")
        raise
    finally:
        # Close the pool
        await pool.close()


async def verify_backfill():
    """
    Verify that backfill was successful.
    
    Checks:
    1. No orphaned individuals
    2. All session_individuals have valid references
    3. Individual counts match session records
    """
    import asyncpg
    
    # Connect directly to database
    conn_string = (
        "postgresql://postgres:localdevpass@localhost:5432/ppl_meta_vmeta"
    )
    pool = await asyncpg.create_pool(conn_string)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("VERIFICATION")
    logger.info("=" * 60)
    
    try:
        async with pool.acquire() as conn:
            # Check 1: Orphaned individuals
            orphaned_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM individuals
                WHERE individual_uuid NOT IN (
                    SELECT individual_uuid FROM session_individuals
                )
            """)
            
            logger.info(f"Orphaned individuals: {orphaned_count}")
            
            # Check 2: Total individuals vs total links
            total_individuals = await conn.fetchval("""
                SELECT COUNT(*) FROM individuals
            """)
            
            total_links = await conn.fetchval("""
                SELECT COUNT(*) FROM session_individuals
            """)
            
            logger.info(f"Total individuals: {total_individuals}")
            logger.info(f"Total session links: {total_links}")
            
            # Check 3: Individuals per session
            session_counts = await conn.fetch("""
                SELECT 
                    ts.session_uuid,
                    ts.individuals_found as expected,
                    COUNT(si.individual_uuid) as actual
                FROM tracking_sessions ts
                LEFT JOIN session_individuals si
                    ON si.session_uuid = ts.session_uuid
                WHERE ts.status = 'completed'
                GROUP BY ts.session_uuid, ts.individuals_found
                ORDER BY ts.created_at DESC
            """)
            
            logger.info("")
            logger.info("Individuals per session:")
            for row in session_counts:
                status = "✅" if row['expected'] == row['actual'] else "⚠️"
                logger.info(
                    f"  {status} Session {row['session_uuid']}: "
                    f"Expected {row['expected']}, Got {row['actual']}"
                )
            
            logger.info("=" * 60)
    finally:
        await pool.close()


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("SESSION INDIVIDUALS BACKFILL SCRIPT")
    logger.info("=" * 60)
    logger.info("")
    logger.info("This script will link orphaned individuals to their")
    logger.info("tracking sessions based on timestamp overlap.")
    logger.info("")
    
    try:
        # Run backfill
        await backfill_session_individuals()
        
        # Verify results
        await verify_backfill()
        
        logger.info("")
        logger.info("✅ Backfill complete!")
        
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
