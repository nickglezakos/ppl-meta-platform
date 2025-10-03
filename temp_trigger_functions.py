async def trigger_automatic_ppl_thread_workflow(
    workflow_id: str,
    media_ids: List[str],
    total_faces: int,
    vision_response: Optional[Dict[str, Any]] = None,
):
    """
    Queue-based automatic PPL Thread trigger for completed face detection.

    This function uses Redis/Celery queue for reliable, asynchronous triggering
    of PPL Thread workflows when face detection completes.

    Benefits:
    - Reliable: Tasks survive service restarts
    - Decoupled: No direct service-to-service API calls
    - Scalable: Multiple workers can process triggers
    - Monitored: Queue status visible via Celery tools
    """
    logger.info("🎯 QUEUE TRIGGER: Starting for workflow %s", workflow_id)
    logger.info(
        "📊 QUEUE TRIGGER: %d faces detected for %d media",
        total_faces,
        len(media_ids),
    )

    if not QUEUE_AVAILABLE:
        logger.error(
            "❌ QUEUE UNAVAILABLE: Redis/Celery not available, falling back to direct trigger"
        )
        return await _legacy_direct_trigger(workflow_id, media_ids, total_faces)

    try:
        # Queue PPL Thread trigger tasks for each media item
        queued_tasks = []
        for media_id in media_ids:
            try:
                # Queue the task using Celery
                task = celery_app.send_task(
                    "trigger_ppl_thread",
                    args=[media_id, total_faces, workflow_id],
                    kwargs={"trigger_reason": "automatic_face_detection_completion"},
                    queue="ppl_thread_queue",
                )

                queued_tasks.append(
                    {"media_id": media_id, "task_id": task.id, "status": "queued"}
                )

                logger.info(
                    "✅ QUEUED: PPL Thread trigger for media %s (task: %s)",
                    media_id,
                    task.id,
                )

            except Exception as queue_error:
                logger.error(
                    "❌ QUEUE ERROR: Failed to queue PPL trigger for %s: %s",
                    media_id,
                    queue_error,
                )
                queued_tasks.append(
                    {
                        "media_id": media_id,
                        "task_id": None,
                        "status": "failed",
                        "error": str(queue_error),
                    }
                )

        # Log summary
        successful_queues = len([t for t in queued_tasks if t["status"] == "queued"])
        logger.info(
            "📋 QUEUE SUMMARY: %d/%d tasks queued successfully",
            successful_queues,
            len(media_ids),
        )

        return {
            "queued_tasks": queued_tasks,
            "successful_queues": successful_queues,
            "total_media": len(media_ids),
            "method": "queue_based",
        }

    except Exception as e:
        logger.error("❌ QUEUE TRIGGER: Unexpected error: %s", e)
        # Fallback to direct trigger if queue completely fails
        logger.info("🔄 FALLBACK: Attempting direct trigger")
        return await _legacy_direct_trigger(workflow_id, media_ids, total_faces)


async def _legacy_direct_trigger(
    workflow_id: str, media_ids: List[str], total_faces: int
) -> Dict[str, Any]:
    """
    Legacy direct API trigger as fallback when queue is unavailable.
    This is the old implementation kept for reliability.
    """
    logger.info("🔄 LEGACY TRIGGER: Using direct API calls as fallback")

    try:
        successful_triggers = 0
        async with httpx.AsyncClient() as client:
            # Use the PPL Thread workflow trigger endpoint
            ppl_trigger_payload = {
                "media_ids": (
                    media_ids[0] if media_ids else ""
                ),  # Single string, not array
                "workflow_type": "automatic_face_detection_trigger",
                "source_workflow_id": workflow_id,
                "total_faces": str(total_faces),  # Convert to string
                "trigger_reason": "legacy_fallback_trigger",
            }

            response = await client.post(
                "http://localhost:8003/api/v1/person-objects/workflow/trigger",
                json=ppl_trigger_payload,
                timeout=30.0,
            )

            if response.status_code == 200:
                result = response.json()
                successful_triggers = len(media_ids)
                logger.info(
                    "✅ LEGACY TRIGGER: Successfully triggered PPL Thread workflow: %s",
                    result,
                )
            else:
                logger.error(
                    "❌ LEGACY TRIGGER: Failed to trigger PPL Thread (status %d): %s",
                    response.status_code,
                    response.text,
                )

    except httpx.RequestError as e:
        logger.error("❌ LEGACY TRIGGER: Network error during trigger: %s", e)
    except Exception as e:
        logger.error("❌ LEGACY TRIGGER: Unexpected error during trigger: %s", e)

    return {
        "successful_triggers": successful_triggers,
        "total_media": len(media_ids),
        "method": "legacy_direct",
    }
