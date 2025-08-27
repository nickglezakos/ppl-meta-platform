"""
Platform Service - Core platform instance management

Handles:
- Platform instance identity and initialization
- Hardware fingerprinting for license binding
- Platform metadata management
- Integration with discovery service

GitHub Issue: #44
"""

import asyncio
import hashlib
import json
import logging
import os
import platform
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

try:
    import cpuinfo
    import psutil
except ImportError:
    psutil = None
    cpuinfo = None

from models.platform_models import ActivationStatus, LicenseType, PlatformInstance

logger = logging.getLogger(__name__)


class PlatformService:
    """Platform instance management service"""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize platform service"""
        self.data_dir = Path(data_dir or "data")
        self.data_dir.mkdir(exist_ok=True)

        self.db_path = self.data_dir / "platform.db"
        self._instance: Optional[PlatformInstance] = None
        self._background_tasks = []

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Create platform_instances table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS platform_instances (
                    instance_id TEXT PRIMARY KEY,
                    license_key TEXT,
                    owner_email TEXT,
                    installation_date TEXT,
                    activation_date TEXT,
                    platform_version TEXT DEFAULT '1.0.0',
                    hardware_fingerprint TEXT,
                    activation_status TEXT DEFAULT 'pending',
                    license_type TEXT,
                    expires_date TEXT,
                    last_validation TEXT,
                    validation_count INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}'
                )
            """
            )

            conn.commit()
            conn.close()
            logger.info("✅ Platform database initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize platform database: {e}")
            raise

    async def ensure_platform_instance(self) -> PlatformInstance:
        """Ensure platform instance exists, create if needed"""
        if self._instance:
            return self._instance

        # Try to load existing instance
        self._instance = await self._load_platform_instance()

        if not self._instance:
            # Create new platform instance
            self._instance = await self._create_platform_instance()

        return self._instance

    async def _load_platform_instance(self) -> Optional[PlatformInstance]:
        """Load platform instance from database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM platform_instances 
                ORDER BY installation_date DESC 
                LIMIT 1
            """
            )

            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            # Parse row data
            (
                instance_id,
                license_key,
                owner_email,
                installation_date,
                activation_date,
                platform_version,
                hardware_fingerprint,
                activation_status,
                license_type,
                expires_date,
                last_validation,
                validation_count,
                metadata,
            ) = row

            return PlatformInstance(
                instance_id=UUID(instance_id),
                license_key=license_key,
                owner_email=owner_email,
                installation_date=datetime.fromisoformat(installation_date),
                activation_date=(
                    datetime.fromisoformat(activation_date) if activation_date else None
                ),
                platform_version=platform_version,
                hardware_fingerprint=hardware_fingerprint,
                activation_status=ActivationStatus(activation_status),
                license_type=LicenseType(license_type) if license_type else None,
                expires_date=(
                    datetime.fromisoformat(expires_date) if expires_date else None
                ),
                last_validation=(
                    datetime.fromisoformat(last_validation) if last_validation else None
                ),
                validation_count=validation_count,
                metadata=json.loads(metadata) if metadata else {},
            )

        except Exception as e:
            logger.error(f"❌ Failed to load platform instance: {e}")
            return None

    async def _create_platform_instance(self) -> PlatformInstance:
        """Create new platform instance"""
        try:
            # Generate hardware fingerprint
            hardware_fingerprint = await self._generate_hardware_fingerprint()

            # Create platform instance
            instance = PlatformInstance(
                instance_id=uuid4(),
                installation_date=datetime.now(),
                platform_version="1.0.0",
                hardware_fingerprint=hardware_fingerprint,
                activation_status=ActivationStatus.PENDING,
                metadata={
                    "system_info": await self._get_system_info(),
                    "created_by": "ppl-meta-bootcore",
                },
            )

            # Save to database
            await self._save_platform_instance(instance)

            logger.info(f"✅ Created new platform instance: {instance.instance_id}")
            return instance

        except Exception as e:
            logger.error(f"❌ Failed to create platform instance: {e}")
            raise

    async def _save_platform_instance(self, instance: PlatformInstance):
        """Save platform instance to database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO platform_instances (
                    instance_id, license_key, owner_email, installation_date,
                    activation_date, platform_version, hardware_fingerprint,
                    activation_status, license_type, expires_date,
                    last_validation, validation_count, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(instance.instance_id),
                    instance.license_key,
                    instance.owner_email,
                    instance.installation_date.isoformat(),
                    (
                        instance.activation_date.isoformat()
                        if instance.activation_date
                        else None
                    ),
                    instance.platform_version,
                    instance.hardware_fingerprint,
                    instance.activation_status.value,
                    instance.license_type.value if instance.license_type else None,
                    (
                        instance.expires_date.isoformat()
                        if instance.expires_date
                        else None
                    ),
                    (
                        instance.last_validation.isoformat()
                        if instance.last_validation
                        else None
                    ),
                    instance.validation_count,
                    json.dumps(instance.metadata),
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"❌ Failed to save platform instance: {e}")
            raise

    async def _generate_hardware_fingerprint(self) -> str:
        """Generate hardware fingerprint for license binding"""
        try:
            fingerprint_data = []

            # System information
            fingerprint_data.append(platform.system())
            fingerprint_data.append(platform.machine())
            fingerprint_data.append(platform.processor())

            if psutil:
                # CPU information
                try:
                    fingerprint_data.append(str(psutil.cpu_count()))
                    fingerprint_data.append(
                        str(psutil.cpu_freq().max if psutil.cpu_freq() else "unknown")
                    )
                except:
                    pass

                # Memory information
                try:
                    memory = psutil.virtual_memory()
                    fingerprint_data.append(str(memory.total))
                except:
                    pass

                # Disk information
                try:
                    disk = psutil.disk_usage("/")
                    fingerprint_data.append(str(disk.total))
                except:
                    pass

            if cpuinfo:
                # CPU brand
                try:
                    cpu_info = cpuinfo.get_cpu_info()
                    fingerprint_data.append(cpu_info.get("brand_raw", "unknown"))
                except:
                    pass

            # Network interfaces (MAC addresses)
            if psutil:
                try:
                    for interface, addrs in psutil.net_if_addrs().items():
                        for addr in addrs:
                            if addr.family == psutil.AF_LINK and addr.address:
                                fingerprint_data.append(addr.address)
                except:
                    pass

            # Create fingerprint hash
            fingerprint_string = "|".join(fingerprint_data)
            fingerprint_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()

            return fingerprint_hash[:32]  # Use first 32 characters

        except Exception as e:
            logger.error(f"❌ Failed to generate hardware fingerprint: {e}")
            # Fallback to basic system fingerprint
            fallback_data = (
                f"{platform.system()}|{platform.machine()}|{datetime.now().date()}"
            )
            return hashlib.sha256(fallback_data.encode()).hexdigest()[:32]

    async def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }

        if psutil:
            try:
                info.update(
                    {
                        "cpu_count": psutil.cpu_count(),
                        "memory_gb": round(
                            psutil.virtual_memory().total / (1024**3), 2
                        ),
                        "disk_gb": round(psutil.disk_usage("/").total / (1024**3), 2),
                    }
                )
            except:
                pass

        return info

    async def update_platform_instance(self, **kwargs) -> PlatformInstance:
        """Update platform instance"""
        if not self._instance:
            await self.ensure_platform_instance()

        # Update fields
        for key, value in kwargs.items():
            if hasattr(self._instance, key):
                setattr(self._instance, key, value)

        # Save to database
        await self._save_platform_instance(self._instance)

        return self._instance

    def get_instance_id(self) -> Optional[str]:
        """Get platform instance ID"""
        return str(self._instance.instance_id) if self._instance else None

    def get_hardware_fingerprint(self) -> Optional[str]:
        """Get hardware fingerprint"""
        return self._instance.hardware_fingerprint if self._instance else None

    async def health_check(self) -> str:
        """Health check for platform service"""
        try:
            if not self._instance:
                await self.ensure_platform_instance()

            # Check database connectivity
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()

            return "healthy"

        except Exception as e:
            logger.error(f"❌ Platform service health check failed: {e}")
            return "unhealthy"

    async def start_background_tasks(self):
        """Start background maintenance tasks"""
        # Add any background tasks here
        pass

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
        logger.info("✅ Platform service cleanup complete")
