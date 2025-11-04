"""
Example Integration: MVR-People Automatic Creation

This file demonstrates how to integrate MVR-People automatic creation
into the Individual creation workflow.

INTEGRATION POINT:
==================
After creating an Individual in the database, call the MVR trigger function
to automatically create MVR-People and perform matching/merging.

Example usage in database/repository.py create_individual() method:
```python
async def create_individual(
    self,
    session_id: UUID,
    first_appearance: VideoAppearance,
    confidence_score: float
) -> UUID:
    # ... existing Individual creation code ...
    
    # Trigger automatic MVR-People creation
    from background.mvr_helper import trigger_mvr_creation
    
    await trigger_mvr_creation(
        individual_uuid=individual_uuid,
        session_uuid=session_id,
        auto_match=True  # Enable automatic matching and merging
    )
    
    return individual_uuid
```

WHAT HAPPENS:
=============
1. Individual is created in database (blocking)
2. MVR creation is triggered in background (non-blocking)
3. Background processor:
   a. Fetches person objects from Orchestrator
   b. Selects best quality face
   c. Processes face with ML models (embedding, age, gender)
   d. Creates MVR-People record
   e. Links Individual to MVR
   f. Searches for similar MVR-People
   g. If match found above threshold: merges (quality-based winner)
   h. Returns result and updates statistics

BENEFITS:
=========
- Non-blocking: Individual creation doesn't wait for MVR processing
- Automatic: No manual intervention needed
- Quality-based: Best quality faces are selected
- Intelligent merging: Duplicate people are automatically consolidated
- Audit trail: Complete history of merges
- Statistics: Track matching success rates

CONFIGURATION:
==============
- Similarity threshold: 0.85 (default, configurable via mvr_matching_config)
- Auto-merge enabled: True (default)
- Max retries: 3 (configurable)
- Retry delay: 5 seconds (configurable)

MONITORING:
===========
Background processing statistics available via:
- mvr_background_processor.get_statistics()
- mvr_background_processor.get_task_status(individual_uuid)
- mvr_background_processor.get_all_pending_tasks()
"""

import logging
from uuid import UUID
from typing import Optional

# This import makes MVR functionality available
from background.mvr_helper import trigger_mvr_creation, is_mvr_enabled

logger = logging.getLogger(__name__)


async def example_individual_creation_with_mvr(
    session_id: UUID,
    individual_uuid: UUID
) -> None:
    """
    Example of how to integrate MVR creation into Individual workflow.
    
    This shows the minimal integration needed in the Individual creation code.
    """
    # Step 1: Create Individual (existing code)
    # ... existing Individual creation logic ...
    
    # Step 2: Trigger MVR creation (new code - just one line!)
    if is_mvr_enabled():
        success = await trigger_mvr_creation(
            individual_uuid=individual_uuid,
            session_uuid=session_id,
            auto_match=True
        )
        
        if success:
            logger.info(
                f"✅ MVR processing started for Individual {individual_uuid}"
            )
        else:
            logger.warning(
                f"⚠️ MVR processing failed to start for Individual "
                f"{individual_uuid}"
            )
    else:
        logger.debug(
            f"ℹ️ MVR processing disabled, skipping Individual "
            f"{individual_uuid}"
        )


async def example_check_mvr_status(individual_uuid: UUID) -> dict:
    """
    Example of how to check MVR processing status.
    
    Useful for monitoring or debugging.
    """
    from background import mvr_helper
    
    hook = mvr_helper.get_mvr_integration_hook()
    if hook is None:
        return {"status": "mvr_not_available"}
    
    background_processor = hook.background_processor
    status = await background_processor.get_task_status(individual_uuid)
    
    return status


async def example_get_mvr_statistics() -> dict:
    """
    Example of how to get MVR processing statistics.
    
    Useful for monitoring system performance.
    """
    from background import mvr_helper
    
    hook = mvr_helper.get_mvr_integration_hook()
    if hook is None:
        return {"status": "mvr_not_available"}
    
    background_processor = hook.background_processor
    stats = await background_processor.get_statistics()
    
    return stats


# =====================================================================
# ACTUAL INTEGRATION CODE
# =====================================================================
# To integrate into repository.py, add this to create_individual():

"""
    # At the end of create_individual() method, after Individual is created:
    
    # Trigger automatic MVR-People creation and matching
    from background.mvr_helper import trigger_mvr_creation, is_mvr_enabled
    
    if is_mvr_enabled():
        await trigger_mvr_creation(
            individual_uuid=individual_uuid,
            session_uuid=session_id,
            auto_match=True
        )
    
    logger.info(f"✅ Created individual: {individual_uuid}")
    return individual_uuid
"""
