"""
Redis Pub/Sub Subscriber for Trigger Evaluation
Listens to instant-detection channel and evaluates triggers in real-time
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.trigger import Trigger
from src.models.signage import SignageDevice
from src.services.signage_service import SignageService, SignagePlaybackService
from src.schemas.signage import PlaybackControlRequest, PlaybackCommand, PlaybackParameters

logger = logging.getLogger(__name__)


class InstantDetectionSubscriber:
    """
    Subscribes to Redis instant-detection channel and evaluates triggers.
    
    This replaces the webhook-based approach with a pub/sub pattern that:
    - Doesn't block the cameras service
    - Allows multiple consumers (triggers, analytics, UI)
    - Scales better with high-frequency updates
    """
    
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        
        self.redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        self.redis: aioredis.Redis = None
        self.pubsub: aioredis.client.PubSub = None
        self.running = False
        self._task = None
        
    async def start(self):
        """Start subscribing to instant-detection channel"""
        if self.running:
            logger.warning("Subscriber already running")
            return
        
        try:
            # Connect to Redis
            self.redis = await aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                encoding="utf-8"
            )
            
            # Create pubsub and subscribe
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe("instant-detection")
            
            self.running = True
            logger.info("✅ Subscribed to instant-detection Redis channel")
            
            # Start listening loop
            self._task = asyncio.create_task(self._listen_loop())
            
        except Exception as e:
            logger.error(f"❌ Failed to start Redis subscriber: {e}")
            raise
    
    async def stop(self):
        """Stop subscribing"""
        self.running = False
        
        if self._task:
            self._task.cancel()
        
        if self.pubsub:
            await self.pubsub.unsubscribe("instant-detection")
            await self.pubsub.close()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("✅ Stopped instant-detection subscriber")
    
    async def _listen_loop(self):
        """Listen for messages and evaluate triggers"""
        try:
            logger.info("🎧 Listening for instant detection events...")
            
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        # Parse message
                        data = json.loads(message["data"])
                        
                        # Evaluate triggers
                        await self._handle_instant_detection(data)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Invalid JSON from instant-detection: {e}")
                    except Exception as e:
                        logger.error(f"❌ Error handling instant detection: {e}", exc_info=True)
                        
        except asyncio.CancelledError:
            logger.info("🛑 Listen loop cancelled")
        except Exception as e:
            logger.error(f"❌ Listen loop error: {e}")
    
    async def _handle_instant_detection(self, data: Dict):
        """
        Handle instant detection event and evaluate triggers.
        
        This is the same logic as the webhook endpoint, but driven by Redis Pub/Sub.
        """
        camera_id = data.get("camera_id")
        people_count = data.get("people_count", 0)
        demographics = data.get("demographics", {})
        timestamp = data.get("timestamp")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🔔 INSTANT DETECTION EVENT (Redis Pub/Sub)")
        logger.info(f"{'='*80}")
        logger.info(f"📷 Camera ID: {camera_id}")
        logger.info(f"👥 People Count: {people_count}")
        logger.info(f"📊 Demographics: {demographics}")
        logger.info(f"⏰ Timestamp: {timestamp}")
        
        db: Session = SessionLocal()
        
        try:
            # Find active triggers for this camera
            triggers = db.query(Trigger).filter(
                Trigger.is_active == True,
                Trigger.camera_device_id == camera_id
            ).all()
            
            if not triggers:
                logger.info(f"  ℹ️  No active demographic triggers for camera {camera_id}")
                return
            
            logger.info(f"  🔍 Found {len(triggers)} active trigger(s) to evaluate")
            
            triggers_fired = 0
            fired_trigger_ids = []
            now = datetime.now(timezone.utc)
            
            # Evaluate each trigger
            for trigger in triggers:
                logger.info(f"\n--- Evaluating Trigger #{trigger.id}: '{trigger.name}' ---")
                
                # Check cooldown
                if trigger.last_fired_at:
                    cooldown_end = trigger.last_fired_at + timedelta(seconds=trigger.cooldown_seconds)
                    if now < cooldown_end:
                        remaining = (cooldown_end - now).total_seconds()
                        logger.info(f"  ⏸️  SKIP: In cooldown ({remaining:.1f}s remaining)")
                        continue
                
                # Evaluate conditions
                conditions = json.loads(trigger.demographic_conditions)
                logger.info(f"  📋 Conditions to evaluate: {json.dumps(conditions, indent=4)}")
                
                if not self._evaluate_conditions(conditions, demographics, people_count):
                    logger.info(f"  ❌ SKIP: Conditions NOT met")
                    continue
                
                logger.info(f"  ✅ Conditions MET!")
                
                # FIRE!
                logger.info(f"\n🔥🔥🔥 TRIGGER FIRED! 🔥🔥🔥")
                triggers_fired += 1
                fired_trigger_ids.append(trigger.id)
                trigger.last_fired_at = datetime.now(timezone.utc)
                
                # Execute action if configured
                if trigger.action_uuid:
                    await self._execute_trigger_action(trigger, db)
            
            # Commit all updates
            db.commit()
            
            logger.info(f"\n✅ EVALUATION COMPLETE (Redis Pub/Sub)")
            logger.info(f"   Triggers Evaluated: {len(triggers)}")
            logger.info(f"   Triggers Fired: {triggers_fired}")
            logger.info(f"   Fired IDs: {fired_trigger_ids}")
            
        except Exception as e:
            logger.error(f"❌ Error evaluating triggers: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
    
    def _evaluate_conditions(self, conditions, demographics, people_count):
        """Evaluate demographic conditions (same logic as webhook endpoint)"""
        logger.info(f"  🔍 Evaluating {len(conditions)} condition(s)")
        logger.info(f"     Input people_count: {people_count}")
        logger.info(f"     Input demographics: {demographics}")
        
        for idx, condition in enumerate(conditions, 1):
            field = condition.get('field')
            operator = condition.get('operator')
            threshold = condition.get('value')
            
            logger.info(f"     Condition {idx}: {field} {operator} {threshold}")
            
            if field == 'people_count':
                actual_value = people_count
                logger.info(f"       Actual people_count: {actual_value}")
            else:
                actual_value = demographics.get(field)
                logger.info(f"       Actual {field}: {actual_value}")
            
            if actual_value is None:
                logger.info(f"       ❌ FAIL: Field '{field}' not in data")
                return False
            
            threshold = float(threshold)
            actual_value = float(actual_value)
            
            logger.info(f"       Comparing: {actual_value} {operator} {threshold}")
            
            if operator == 'gte' and not (actual_value >= threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT >= {threshold}")
                return False
            elif operator == 'lte' and not (actual_value <= threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT <= {threshold}")
                return False
            elif operator == 'eq' and not (actual_value == threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT == {threshold}")
                return False
            elif operator == 'gt' and not (actual_value > threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT > {threshold}")
                return False
            elif operator == 'lt' and not (actual_value < threshold):
                logger.info(f"       ❌ FAIL: {actual_value} NOT < {threshold}")
                return False
            else:
                logger.info(f"       ✅ PASS")
        
        logger.info(f"  ✅ ALL CONDITIONS PASSED")
        return True
    
    async def _execute_trigger_action(self, trigger: Trigger, db: Session):
        """Execute the action associated with this trigger"""
        from src.models.user_trigger_action import UserTriggerAction
        
        logger.info(f"  🎬 Executing trigger action...")
        logger.info(f"     Action UUID: {trigger.action_uuid}")
        
        # Look up the action
        action = db.query(UserTriggerAction).filter(
            UserTriggerAction.uuid == trigger.action_uuid
        ).first()
        
        if not action:
            logger.error(f"     ❌ Action not found: {trigger.action_uuid}")
            return
        
        logger.info(f"     Action Type: {action.action_type}")
        logger.info(f"     Action Name: {action.name}")
        
        # Handle digital_signage action type
        if action.action_type == "digital_signage":
            await self._execute_signage_action(action, db)
        else:
            logger.warning(f"     ⚠️ Unsupported action type: {action.action_type}")
    
    async def _execute_signage_action(self, action, db: Session):
        """Execute signage playlist switch action from action config"""
        logger.info(f"  📺 Executing digital signage action...")
        
        try:
            # Parse action_config to get signage settings
            config = json.loads(action.action_config) if isinstance(action.action_config, str) else action.action_config
            
            device_ids = config.get("device_ids", [])
            playlist_id = config.get("playlist_id")
            transition_mode = config.get("transition_mode", "immediate")
            
            logger.info(f"     Target Playlist UUID: {playlist_id}")
            logger.info(f"     Transition Mode: {transition_mode}")
            logger.info(f"     Target Device IDs: {device_ids}")
            
            if not device_ids or not playlist_id:
                logger.error(f"     ❌ Missing device_ids or playlist_id in action config")
                return
            
            playback_service = SignagePlaybackService(db)
            
            for device_uuid_str in device_ids:
                try:
                    device_uuid = UUID(device_uuid_str)
                    
                    logger.info(f"\n     📱 Sending switch command to device:")
                    logger.info(f"        Device UUID: {device_uuid}")
                    logger.info(f"        Target Playlist: {playlist_id}")
                    
                    # Create PlaybackControlRequest
                    from src.schemas.signage import PlaybackControlRequest, PlaybackCommand, PlaybackParameters
                    
                    # Create playback parameters
                    playback_params = PlaybackParameters()
                    
                    # Create control request to start new playlist
                    control_request = PlaybackControlRequest(
                        device_ids=[device_uuid],
                        command=PlaybackCommand.START,
                        video_list_id=UUID(playlist_id),
                        parameters=playback_params
                    )
                    
                    # Send the command (SignagePlaybackService will query discovery service)
                    result = await playback_service.control_playback(control_request)
                    logger.info(f"        ✅ Command result: {json.dumps(result, indent=10)}")
                
                except ValueError as e:
                    logger.error(f"Invalid device UUID {device_uuid_str}: {e}")
                except Exception as e:
                    logger.error(f"Error switching playlist for device {device_uuid_str}: {e}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse action_config: {e}")
        except Exception as e:
            logger.error(f"Error executing signage action: {e}", exc_info=True)


# Global subscriber instance
_subscriber: InstantDetectionSubscriber = None


async def start_subscriber():
    """Start the global subscriber"""
    global _subscriber
    if _subscriber is None:
        _subscriber = InstantDetectionSubscriber()
    await _subscriber.start()


async def stop_subscriber():
    """Stop the global subscriber"""
    global _subscriber
    if _subscriber:
        await _subscriber.stop()
