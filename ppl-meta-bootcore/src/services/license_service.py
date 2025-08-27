"""
License Service - License validation and management

Handles:
- License key validation and activation
- License status monitoring
- Feature flags based on license type
- Online validation with offline grace periods

GitHub Issue: #44
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from models.platform_models import (
    ActivationStatus,
    LicenseActivationRequest,
    LicenseActivationResponse,
    LicenseInfo,
    LicenseStatusResponse,
    LicenseType,
)

logger = logging.getLogger(__name__)


class LicenseService:
    """License validation and management service"""

    def __init__(self, platform_service, data_dir: Optional[str] = None):
        """Initialize license service"""
        self.platform_service = platform_service
        self.data_dir = Path(data_dir or "data")
        self.data_dir.mkdir(exist_ok=True)

        self.db_path = self.data_dir / "licenses.db"
        self._current_license: Optional[LicenseInfo] = None
        self._background_tasks = []

        # Initialize database
        self._init_database()

        # License validation settings
        self.offline_grace_days = 30
        self.validation_interval_hours = 24

    def _init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Create licenses table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS licenses (
                    license_key TEXT PRIMARY KEY,
                    license_type TEXT NOT NULL,
                    issued_date TEXT NOT NULL,
                    expires_date TEXT,
                    max_users INTEGER DEFAULT 1,
                    features_enabled TEXT DEFAULT '[]',
                    activation_limit INTEGER DEFAULT 1,
                    current_activations INTEGER DEFAULT 0,
                    customer_id TEXT,
                    purchase_order TEXT,
                    is_active INTEGER DEFAULT 1,
                    last_validation TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """
            )

            # Create activation history table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS activation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    license_key TEXT NOT NULL,
                    instance_id TEXT NOT NULL,
                    activation_date TEXT NOT NULL,
                    hardware_fingerprint TEXT,
                    activation_type TEXT DEFAULT 'activate',
                    metadata TEXT DEFAULT '{}'
                )
            """
            )

            conn.commit()
            conn.close()
            logger.info("✅ License database initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize license database: {e}")
            raise

    async def activate_license(
        self, request: LicenseActivationRequest
    ) -> LicenseActivationResponse:
        """Activate a license key"""
        try:
            # Validate license key format
            if not self._validate_license_key_format(request.license_key):
                return LicenseActivationResponse(
                    success=False,
                    instance_id=UUID("00000000-0000-0000-0000-000000000000"),
                    activation_status=ActivationStatus.INVALID,
                    message="Invalid license key format",
                )

            # For demo purposes, create a license based on key pattern
            license_info = await self._create_demo_license(request.license_key)

            if not license_info:
                return LicenseActivationResponse(
                    success=False,
                    instance_id=UUID("00000000-0000-0000-0000-000000000000"),
                    activation_status=ActivationStatus.INVALID,
                    message="License key not found or invalid",
                )

            # Get platform instance
            platform_instance = await self.platform_service.ensure_platform_instance()

            # Update platform instance with license info
            await self.platform_service.update_platform_instance(
                license_key=request.license_key,
                owner_email=request.owner_email,
                activation_date=datetime.now(),
                activation_status=ActivationStatus.ACTIVE,
                license_type=license_info.license_type,
                expires_date=license_info.expires_date,
                last_validation=datetime.now(),
            )

            # Save license info
            await self._save_license(license_info)
            self._current_license = license_info

            # Record activation
            await self._record_activation(
                license_info.license_key,
                platform_instance.instance_id,
                platform_instance.hardware_fingerprint,
            )

            logger.info(f"✅ License activated: {request.license_key[:8]}...")

            return LicenseActivationResponse(
                success=True,
                instance_id=platform_instance.instance_id,
                activation_status=ActivationStatus.ACTIVE,
                license_type=license_info.license_type,
                expires_date=license_info.expires_date,
                features_enabled=license_info.features_enabled,
                max_users=license_info.max_users,
                message="License activated successfully",
                next_validation=datetime.now()
                + timedelta(hours=self.validation_interval_hours),
            )

        except Exception as e:
            logger.error(f"❌ License activation failed: {e}")
            return LicenseActivationResponse(
                success=False,
                instance_id=UUID("00000000-0000-0000-0000-000000000000"),
                activation_status=ActivationStatus.INVALID,
                message=f"Activation failed: {str(e)}",
            )

    def _validate_license_key_format(self, license_key: str) -> bool:
        """Validate license key format"""
        # Basic format validation
        return (
            len(license_key) >= 10
            and len(license_key) <= 50
            and license_key.replace("-", "").replace("_", "").isalnum()
        )

    async def _create_demo_license(self, license_key: str) -> Optional[LicenseInfo]:
        """Create demo license based on key pattern (for development)"""
        try:
            # Demo license patterns
            if license_key.upper().startswith("TRIAL-"):
                license_type = LicenseType.TRIAL
                expires_date = datetime.now() + timedelta(days=30)
                max_users = 1
                features = ["basic_features", "single_camera"]

            elif license_key.upper().startswith("PRO-"):
                license_type = LicenseType.PROFESSIONAL
                expires_date = datetime.now() + timedelta(days=365)
                max_users = 5
                features = ["advanced_features", "multi_camera", "cloud_storage"]

            elif license_key.upper().startswith("ENT-"):
                license_type = LicenseType.ENTERPRISE
                expires_date = None  # No expiration
                max_users = 50
                features = [
                    "all_features",
                    "unlimited_cameras",
                    "cloud_storage",
                    "api_access",
                    "analytics",
                ]

            elif license_key.upper().startswith("DEV-"):
                license_type = LicenseType.DEVELOPER
                expires_date = datetime.now() + timedelta(days=365)
                max_users = 3
                features = ["development_features", "api_access", "debugging"]

            else:
                # Default trial license for any other format
                license_type = LicenseType.TRIAL
                expires_date = datetime.now() + timedelta(days=7)
                max_users = 1
                features = ["basic_features"]

            return LicenseInfo(
                license_key=license_key,
                license_type=license_type,
                issued_date=datetime.now(),
                expires_date=expires_date,
                max_users=max_users,
                features_enabled=features,
                activation_limit=1,
                current_activations=1,
                is_active=True,
                metadata={"demo_license": True, "created_by": "ppl-meta-bootcore"},
            )

        except Exception as e:
            logger.error(f"❌ Failed to create demo license: {e}")
            return None

    async def _save_license(self, license_info: LicenseInfo):
        """Save license to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO licenses (
                    license_key, license_type, issued_date, expires_date,
                    max_users, features_enabled, activation_limit,
                    current_activations, customer_id, purchase_order,
                    is_active, last_validation, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    license_info.license_key,
                    license_info.license_type.value,
                    license_info.issued_date.isoformat(),
                    (
                        license_info.expires_date.isoformat()
                        if license_info.expires_date
                        else None
                    ),
                    license_info.max_users,
                    json.dumps(license_info.features_enabled),
                    license_info.activation_limit,
                    license_info.current_activations,
                    str(license_info.customer_id) if license_info.customer_id else None,
                    license_info.purchase_order,
                    1 if license_info.is_active else 0,
                    datetime.now().isoformat(),
                    json.dumps(license_info.metadata),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"❌ Failed to save license: {e}")
            raise

    async def _record_activation(
        self, license_key: str, instance_id: UUID, hardware_fingerprint: str
    ):
        """Record license activation"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO activation_history (
                    license_key, instance_id, activation_date, 
                    hardware_fingerprint, activation_type, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    license_key,
                    str(instance_id),
                    datetime.now().isoformat(),
                    hardware_fingerprint,
                    "activate",
                    json.dumps({"source": "ppl-meta-bootcore"}),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"❌ Failed to record activation: {e}")

    async def get_license_status(self) -> LicenseStatusResponse:
        """Get current license status"""
        try:
            platform_instance = await self.platform_service.ensure_platform_instance()

            if not platform_instance.license_key:
                return LicenseStatusResponse(
                    license_active=False,
                    activation_status=ActivationStatus.PENDING,
                    current_users=0,
                    max_users=1,
                )

            # Load current license if not cached
            if not self._current_license:
                self._current_license = await self._load_license(
                    platform_instance.license_key
                )

            if not self._current_license:
                return LicenseStatusResponse(
                    license_active=False,
                    activation_status=ActivationStatus.INVALID,
                    current_users=0,
                    max_users=1,
                )

            # Check expiration
            is_expired = (
                self._current_license.expires_date
                and datetime.now() > self._current_license.expires_date
            )

            days_remaining = None
            if self._current_license.expires_date:
                delta = self._current_license.expires_date - datetime.now()
                days_remaining = max(0, delta.days)

            return LicenseStatusResponse(
                license_active=self._current_license.is_active and not is_expired,
                license_type=self._current_license.license_type,
                activation_status=platform_instance.activation_status,
                expires_date=self._current_license.expires_date,
                days_remaining=days_remaining,
                features_enabled=self._current_license.features_enabled,
                max_users=self._current_license.max_users,
                current_users=0,  # TODO: Get from user service
                last_validation=platform_instance.last_validation,
                next_validation=self._get_next_validation_time(),
            )

        except Exception as e:
            logger.error(f"❌ Failed to get license status: {e}")
            return LicenseStatusResponse(
                license_active=False,
                activation_status=ActivationStatus.INVALID,
                current_users=0,
                max_users=1,
            )

    async def _load_license(self, license_key: str) -> Optional[LicenseInfo]:
        """Load license from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM licenses WHERE license_key = ?
            """,
                (license_key,),
            )

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            # Parse row data
            (
                license_key,
                license_type,
                issued_date,
                expires_date,
                max_users,
                features_enabled,
                activation_limit,
                current_activations,
                customer_id,
                purchase_order,
                is_active,
                last_validation,
                metadata,
            ) = row

            return LicenseInfo(
                license_key=license_key,
                license_type=LicenseType(license_type),
                issued_date=datetime.fromisoformat(issued_date),
                expires_date=(
                    datetime.fromisoformat(expires_date) if expires_date else None
                ),
                max_users=max_users,
                features_enabled=json.loads(features_enabled),
                activation_limit=activation_limit,
                current_activations=current_activations,
                customer_id=UUID(customer_id) if customer_id else None,
                purchase_order=purchase_order,
                is_active=bool(is_active),
                metadata=json.loads(metadata) if metadata else {},
            )

        except Exception as e:
            logger.error(f"❌ Failed to load license: {e}")
            return None

    def _get_next_validation_time(self) -> Optional[datetime]:
        """Get next validation time"""
        return datetime.now() + timedelta(hours=self.validation_interval_hours)

    def get_license_status(self) -> str:
        """Get simple license status string"""
        try:
            if self._current_license and self._current_license.is_active:
                if self._current_license.expires_date:
                    if datetime.now() > self._current_license.expires_date:
                        return "expired"
                    return "active"
                return "active"
            return "inactive"
        except:
            return "unknown"

    def is_license_active(self) -> bool:
        """Check if license is active"""
        return self.get_license_status() == "active"

    async def health_check(self) -> str:
        """Health check for license service"""
        try:
            # Check database connectivity
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()

            return "healthy"

        except Exception as e:
            logger.error(f"❌ License service health check failed: {e}")
            return "unhealthy"

    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        # Background license validation task
        task = asyncio.create_task(self._background_license_validation())
        self._background_tasks.append(task)

    async def _background_license_validation(self):
        """Background task for periodic license validation"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour

                # TODO: Implement online validation
                logger.debug("🔄 Background license validation check")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Background license validation error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry

    async def cleanup(self):
        """Cleanup resources"""
        # Cancel background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._background_tasks.clear()
        logger.info("✅ License service cleanup complete")
