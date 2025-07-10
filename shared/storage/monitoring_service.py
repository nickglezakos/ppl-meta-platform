#!/usr/bin/env python3
"""
PPL Meta Platform - Storage Monitoring Service

This service provides real-time storage monitoring with Prometheus metrics,
alerting, and automated health checks for Docker volumes.

Author: PPL Meta Platform Team
Version: 1.0.0
Date: 2025-07-10
"""

import argparse
import asyncio
import json
import logging
import os

# Import our volume manager
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import aiohttp
from aiohttp import web
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

sys.path.append(str(Path(__file__).parent))
from volume_manager import VolumeManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StorageMonitoringService:
    """Real-time storage monitoring service with Prometheus metrics."""

    def __init__(self, config_file: str = "volume_config.yml"):
        """Initialize the monitoring service."""
        self.config_file = config_file
        self.volume_manager = VolumeManager(config_file)
        self.registry = CollectorRegistry()
        self.setup_metrics()
        self.app = web.Application()
        self.setup_routes()

    def setup_metrics(self):
        """Set up Prometheus metrics."""
        # Volume size metrics
        self.volume_size_bytes = Gauge(
            "ppl_volume_size_bytes",
            "Size of Docker volume in bytes",
            ["volume_name", "service"],
            registry=self.registry,
        )

        self.volume_used_percent = Gauge(
            "ppl_volume_used_percent",
            "Percentage of volume space used",
            ["volume_name", "service"],
            registry=self.registry,
        )

        self.volume_available_bytes = Gauge(
            "ppl_volume_available_bytes",
            "Available space in volume in bytes",
            ["volume_name", "service"],
            registry=self.registry,
        )

        # Volume operations metrics
        self.volume_backup_total = Counter(
            "ppl_volume_backup_total",
            "Total number of volume backups performed",
            ["volume_name", "status"],
            registry=self.registry,
        )

        self.volume_backup_duration_seconds = Histogram(
            "ppl_volume_backup_duration_seconds",
            "Time taken to backup volume",
            ["volume_name"],
            registry=self.registry,
        )

        self.volume_backup_size_bytes = Gauge(
            "ppl_volume_backup_size_bytes",
            "Size of latest backup in bytes",
            ["volume_name"],
            registry=self.registry,
        )

        # Alert metrics
        self.volume_alerts_total = Gauge(
            "ppl_volume_alerts_total",
            "Number of active volume alerts",
            registry=self.registry,
        )

        self.volume_alert_status = Gauge(
            "ppl_volume_alert_status",
            "Alert status for volume (1=alert, 0=ok)",
            ["volume_name", "alert_type"],
            registry=self.registry,
        )

        # System metrics
        self.storage_total_volumes = Gauge(
            "ppl_storage_total_volumes",
            "Total number of Docker volumes",
            registry=self.registry,
        )

        self.storage_total_size_bytes = Gauge(
            "ppl_storage_total_size_bytes",
            "Total size of all volumes in bytes",
            registry=self.registry,
        )

        # Service info
        self.service_info = Info(
            "ppl_storage_monitoring_service",
            "Information about the storage monitoring service",
            registry=self.registry,
        )

        self.service_info.info(
            {
                "version": "1.0.0",
                "python_version": sys.version,
                "config_file": self.config_file,
            }
        )

    def setup_routes(self):
        """Set up HTTP routes."""
        self.app.router.add_get("/metrics", self.metrics_handler)
        self.app.router.add_get("/health", self.health_handler)
        self.app.router.add_get("/status", self.status_handler)
        self.app.router.add_get("/volumes", self.volumes_handler)
        self.app.router.add_get("/alerts", self.alerts_handler)
        self.app.router.add_post("/backup/{volume_name}", self.backup_handler)

    async def metrics_handler(self, request):
        """Serve Prometheus metrics."""
        # Update metrics before serving
        await self.update_metrics()

        metrics_data = generate_latest(self.registry)
        return web.Response(
            text=metrics_data.decode("utf-8"), content_type=CONTENT_TYPE_LATEST
        )

    async def health_handler(self, request):
        """Health check endpoint."""
        try:
            # Quick health check
            volumes = self.volume_manager.list_volumes()
            return web.json_response(
                {
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "volumes_count": len(volumes),
                }
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return web.json_response(
                {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
                status=500,
            )

    async def status_handler(self, request):
        """Detailed status endpoint."""
        try:
            monitoring_data = self.volume_manager.monitor_volumes()
            return web.json_response(monitoring_data)
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return web.json_response(
                {"error": str(e), "timestamp": datetime.now().isoformat()}, status=500
            )

    async def volumes_handler(self, request):
        """List volumes with usage information."""
        try:
            volumes = self.volume_manager.list_volumes()
            volume_data = []

            for volume in volumes:
                usage = self.volume_manager.get_volume_usage(volume["Name"])
                volume_info = {
                    "name": volume["Name"],
                    "driver": volume.get("Driver", "unknown"),
                    "mount_point": volume.get("Mountpoint", "unknown"),
                    "usage": usage,
                }
                volume_data.append(volume_info)

            return web.json_response(
                {
                    "volumes": volume_data,
                    "total_count": len(volume_data),
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Failed to get volumes: {e}")
            return web.json_response(
                {"error": str(e), "timestamp": datetime.now().isoformat()}, status=500
            )

    async def alerts_handler(self, request):
        """Get current alerts."""
        try:
            monitoring_data = self.volume_manager.monitor_volumes()
            return web.json_response(
                {
                    "alerts": monitoring_data.get("alerts", []),
                    "alert_count": len(monitoring_data.get("alerts", [])),
                    "timestamp": datetime.now().isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return web.json_response(
                {"error": str(e), "timestamp": datetime.now().isoformat()}, status=500
            )

    async def backup_handler(self, request):
        """Trigger backup for a specific volume."""
        try:
            volume_name = request.match_info["volume_name"]

            # Get backup name from query parameters
            backup_name = request.query.get("name")

            # Perform backup
            start_time = time.time()
            success = self.volume_manager.backup_volume(volume_name, backup_name)
            duration = time.time() - start_time

            # Update metrics
            status = "success" if success else "failed"
            self.volume_backup_total.labels(
                volume_name=volume_name, status=status
            ).inc()
            self.volume_backup_duration_seconds.labels(volume_name=volume_name).observe(
                duration
            )

            if success:
                return web.json_response(
                    {
                        "status": "success",
                        "volume_name": volume_name,
                        "backup_name": backup_name,
                        "duration_seconds": duration,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            else:
                return web.json_response(
                    {
                        "status": "failed",
                        "volume_name": volume_name,
                        "error": "Backup operation failed",
                        "duration_seconds": duration,
                        "timestamp": datetime.now().isoformat(),
                    },
                    status=500,
                )

        except Exception as e:
            logger.error(f"Backup handler failed: {e}")
            return web.json_response(
                {"error": str(e), "timestamp": datetime.now().isoformat()}, status=500
            )

    async def update_metrics(self):
        """Update Prometheus metrics with current data."""
        try:
            monitoring_data = self.volume_manager.monitor_volumes()

            # Clear previous alert metrics
            self.volume_alert_status._metrics.clear()

            # Update volume metrics
            total_size = 0
            volume_config = self.volume_manager.config.get("volumes", {})

            for volume_data in monitoring_data.get("volumes", []):
                volume_name = volume_data["volume_name"]
                service_name = volume_config.get(volume_name, {}).get(
                    "service", "unknown"
                )

                # Size metrics
                size_bytes = volume_data.get("size_bytes", 0)
                used_percent = volume_data.get("used_percent", 0)
                available_bytes = volume_data.get("available_bytes", 0)

                self.volume_size_bytes.labels(
                    volume_name=volume_name, service=service_name
                ).set(size_bytes)

                self.volume_used_percent.labels(
                    volume_name=volume_name, service=service_name
                ).set(used_percent)

                self.volume_available_bytes.labels(
                    volume_name=volume_name, service=service_name
                ).set(available_bytes)

                total_size += size_bytes

            # Update alert metrics
            alerts = monitoring_data.get("alerts", [])
            self.volume_alerts_total.set(len(alerts))

            for alert in alerts:
                volume_name = alert.get("volume", "unknown")
                alert_type = alert.get("type", "unknown")
                self.volume_alert_status.labels(
                    volume_name=volume_name, alert_type=alert_type
                ).set(1)

            # Update system metrics
            self.storage_total_volumes.set(monitoring_data.get("total_volumes", 0))
            self.storage_total_size_bytes.set(total_size)

            # Update backup size metrics
            backups = self.volume_manager.list_backups()
            backup_sizes = {}

            for backup in backups:
                volume_name = backup.get("volume_name", "unknown")
                if volume_name not in backup_sizes:
                    backup_sizes[volume_name] = backup.get("file_size", 0)
                else:
                    # Keep the largest backup size for each volume
                    backup_sizes[volume_name] = max(
                        backup_sizes[volume_name], backup.get("file_size", 0)
                    )

            for volume_name, size in backup_sizes.items():
                self.volume_backup_size_bytes.labels(volume_name=volume_name).set(size)

        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")

    async def monitoring_loop(self, interval: int = 300):
        """Continuous monitoring loop."""
        logger.info(f"Starting monitoring loop with {interval}s interval")

        while True:
            try:
                await self.update_metrics()
                logger.debug("Metrics updated successfully")
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")

            await asyncio.sleep(interval)

    async def start_monitoring(self, interval: int = 300):
        """Start the monitoring loop as a background task."""
        self.monitoring_task = asyncio.create_task(self.monitoring_loop(interval))

    async def stop_monitoring(self):
        """Stop the monitoring loop."""
        if hasattr(self, "monitoring_task"):
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

    async def startup(self):
        """Service startup handler."""
        logger.info("Starting storage monitoring service")
        config = self.volume_manager.config.get("monitoring", {})
        interval = config.get("check_interval", 300)
        await self.start_monitoring(interval)

    async def cleanup(self):
        """Service cleanup handler."""
        logger.info("Stopping storage monitoring service")
        await self.stop_monitoring()

    def run(self, host="0.0.0.0", port=9100):
        """Run the monitoring service."""
        self.app.on_startup.append(lambda app: self.startup())
        self.app.on_cleanup.append(lambda app: self.cleanup())

        logger.info(f"Starting storage monitoring service on {host}:{port}")
        web.run_app(self.app, host=host, port=port)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PPL Meta Platform Storage Monitoring Service"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=9100, help="Port to bind to")
    parser.add_argument(
        "--config", default="volume_config.yml", help="Configuration file"
    )
    parser.add_argument("--log-level", default="INFO", help="Log level")

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    # Create and run service
    service = StorageMonitoringService(args.config)
    service.run(args.host, args.port)


if __name__ == "__main__":
    main()
