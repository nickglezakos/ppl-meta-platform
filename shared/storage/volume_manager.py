#!/usr/bin/env python3
"""
PPL Meta Platform - Volume Management System

This module provides comprehensive Docker volume management including:
- Automated backup and restore operations
- Storage monitoring and alerting
- Permission management and troubleshooting
- Volume health checks and optimization

Author: PPL Meta Platform Team
Version: 1.0.0
Date: 2025-07-10
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("volume_manager.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class VolumeManager:
    """Comprehensive Docker volume management system."""

    def __init__(self, config_file: str = "volume_config.yml"):
        """Initialize the volume manager with configuration."""
        self.config_file = config_file
        self.config = self._load_config()
        self.backup_dir = Path(self.config.get("backup_directory", "./backups"))
        self.backup_dir.mkdir(exist_ok=True)

    def _load_config(self) -> Dict:
        """Load configuration from JSON file."""
        config_path = Path(self.config_file)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # Create default configuration
            default_config = {
                "backup_directory": "./backups",
                "retention_days": 30,
                "compression": True,
                "volumes": {
                    "postgres_data": {
                        "service": "postgres",
                        "critical": True,
                        "backup_frequency": "daily",
                        "retention_days": 90,
                    },
                    "redis_data": {
                        "service": "redis",
                        "critical": True,
                        "backup_frequency": "daily",
                        "retention_days": 30,
                    },
                    "media-storage": {
                        "service": "ppl-meta-media",
                        "critical": True,
                        "backup_frequency": "daily",
                        "retention_days": 60,
                    },
                    "user-data": {
                        "service": "ppl-meta-node",
                        "critical": True,
                        "backup_frequency": "daily",
                        "retention_days": 60,
                    },
                    "orchestrator-data": {
                        "service": "ppl-meta-orchestrator",
                        "critical": True,
                        "backup_frequency": "daily",
                        "retention_days": 60,
                    },
                    "consul_data": {
                        "service": "consul",
                        "critical": False,
                        "backup_frequency": "weekly",
                        "retention_days": 30,
                    },
                    "prometheus_data": {
                        "service": "prometheus",
                        "critical": False,
                        "backup_frequency": "weekly",
                        "retention_days": 14,
                    },
                    "grafana_data": {
                        "service": "grafana",
                        "critical": False,
                        "backup_frequency": "weekly",
                        "retention_days": 30,
                    },
                },
                "monitoring": {
                    "enabled": True,
                    "check_interval": 300,  # 5 minutes
                    "alert_thresholds": {
                        "disk_usage_percent": 85,
                        "growth_rate_mb_per_day": 1000,
                    },
                },
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2)
            return default_config

    def list_volumes(self) -> List[Dict]:
        """List all Docker volumes with metadata."""
        try:
            result = subprocess.run(
                ["docker", "volume", "ls", "--format", "json"],
                capture_output=True,
                text=True,
                check=True,
            )
            volumes = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    volume_data = json.loads(line)
                    # Get volume details
                    inspect_result = subprocess.run(
                        ["docker", "volume", "inspect", volume_data["Name"]],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    volume_details = json.loads(inspect_result.stdout)[0]
                    volume_data.update(volume_details)
                    volumes.append(volume_data)
            return volumes
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list volumes: {e}")
            return []

    def get_volume_usage(self, volume_name: str) -> Dict:
        """Get volume usage statistics."""
        try:
            # Get volume mount point
            inspect_result = subprocess.run(
                ["docker", "volume", "inspect", volume_name],
                capture_output=True,
                text=True,
                check=True,
            )
            volume_info = json.loads(inspect_result.stdout)[0]
            mount_point = volume_info["Mountpoint"]

            # Get disk usage
            usage_result = subprocess.run(
                ["du", "-sb", mount_point], capture_output=True, text=True, check=True
            )
            size_bytes = int(usage_result.stdout.split()[0])

            # Get available space
            statvfs_result = subprocess.run(
                ["df", "-B1", mount_point], capture_output=True, text=True, check=True
            )
            df_lines = statvfs_result.stdout.strip().split("\n")
            if len(df_lines) > 1:
                df_parts = df_lines[1].split()
                total_bytes = int(df_parts[1])
                available_bytes = int(df_parts[3])
                used_percent = (total_bytes - available_bytes) / total_bytes * 100
            else:
                total_bytes = available_bytes = used_percent = 0

            return {
                "volume_name": volume_name,
                "mount_point": mount_point,
                "size_bytes": size_bytes,
                "size_mb": size_bytes / (1024 * 1024),
                "size_gb": size_bytes / (1024 * 1024 * 1024),
                "total_bytes": total_bytes,
                "available_bytes": available_bytes,
                "used_percent": used_percent,
                "timestamp": datetime.now().isoformat(),
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get usage for volume {volume_name}: {e}")
            return {}

    def backup_volume(
        self, volume_name: str, backup_name: Optional[str] = None
    ) -> bool:
        """Create a backup of a Docker volume."""
        try:
            if backup_name is None:
                backup_name = (
                    f"{volume_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )

            backup_path = self.backup_dir / f"{backup_name}.tar.gz"

            logger.info(f"Creating backup of volume '{volume_name}' to '{backup_path}'")

            # Create backup using docker run with volume mount
            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{volume_name}:/source:ro",
                "-v",
                f"{self.backup_dir.absolute()}:/backup",
                "alpine:latest",
                "tar",
                "czf",
                f"/backup/{backup_name}.tar.gz",
                "-C",
                "/source",
                ".",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Verify backup file exists and has content
            if backup_path.exists() and backup_path.stat().st_size > 0:
                logger.info(f"Backup completed successfully: {backup_path}")

                # Create metadata file
                metadata = {
                    "volume_name": volume_name,
                    "backup_name": backup_name,
                    "backup_path": str(backup_path),
                    "creation_time": datetime.now().isoformat(),
                    "file_size": backup_path.stat().st_size,
                    "volume_usage": self.get_volume_usage(volume_name),
                }

                metadata_path = self.backup_dir / f"{backup_name}.json"
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)

                return True
            else:
                logger.error(f"Backup file not created or empty: {backup_path}")
                return False

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to backup volume {volume_name}: {e}")
            return False

    def restore_volume(self, volume_name: str, backup_name: str) -> bool:
        """Restore a Docker volume from backup."""
        try:
            backup_path = self.backup_dir / f"{backup_name}.tar.gz"

            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False

            logger.info(f"Restoring volume '{volume_name}' from backup '{backup_path}'")

            # Create volume if it doesn't exist
            subprocess.run(["docker", "volume", "create", volume_name], check=False)

            # Restore backup using docker run
            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{volume_name}:/target",
                "-v",
                f"{self.backup_dir.absolute()}:/backup",
                "alpine:latest",
                "sh",
                "-c",
                f"cd /target && tar xzf /backup/{backup_name}.tar.gz",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(
                f"Volume '{volume_name}' restored successfully from '{backup_path}'"
            )
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restore volume {volume_name}: {e}")
            return False

    def list_backups(self) -> List[Dict]:
        """List all available backups with metadata."""
        backups = []

        for backup_file in self.backup_dir.glob("*.tar.gz"):
            backup_name = backup_file.stem
            metadata_file = self.backup_dir / f"{backup_name}.json"

            backup_info = {
                "backup_name": backup_name,
                "backup_path": str(backup_file),
                "file_size": backup_file.stat().st_size,
                "creation_time": datetime.fromtimestamp(
                    backup_file.stat().st_ctime
                ).isoformat(),
            }

            if metadata_file.exists():
                try:
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)
                    backup_info.update(metadata)
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {backup_name}: {e}")

            backups.append(backup_info)

        return sorted(backups, key=lambda x: x["creation_time"], reverse=True)

    def cleanup_old_backups(self, retention_days: Optional[int] = None) -> int:
        """Remove old backups based on retention policy."""
        if retention_days is None:
            retention_days = self.config.get("retention_days", 30)

        cutoff_date = datetime.now() - timedelta(days=retention_days)
        removed_count = 0

        for backup_file in self.backup_dir.glob("*.tar.gz"):
            file_time = datetime.fromtimestamp(backup_file.stat().st_ctime)

            if file_time < cutoff_date:
                try:
                    backup_name = backup_file.stem
                    metadata_file = self.backup_dir / f"{backup_name}.json"

                    backup_file.unlink()
                    if metadata_file.exists():
                        metadata_file.unlink()

                    logger.info(f"Removed old backup: {backup_file}")
                    removed_count += 1

                except Exception as e:
                    logger.error(f"Failed to remove backup {backup_file}: {e}")

        return removed_count

    def fix_permissions(
        self, volume_name: str, uid: int = 1000, gid: int = 1000
    ) -> bool:
        """Fix permissions on a Docker volume."""
        try:
            logger.info(
                f"Fixing permissions for volume '{volume_name}' (uid={uid}, gid={gid})"
            )

            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{volume_name}:/target",
                "alpine:latest",
                "chown",
                "-R",
                f"{uid}:{gid}",
                "/target",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"Permissions fixed for volume '{volume_name}'")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fix permissions for volume {volume_name}: {e}")
            return False

    def monitor_volumes(self) -> Dict:
        """Monitor all volumes and return status report."""
        volumes = self.list_volumes()
        volume_stats = []
        alerts = []

        for volume in volumes:
            volume_name = volume["Name"]
            usage_data = self.get_volume_usage(volume_name)

            if usage_data:
                volume_stats.append(usage_data)

                # Check alert thresholds
                thresholds = self.config.get("monitoring", {}).get(
                    "alert_thresholds", {}
                )

                if usage_data.get("used_percent", 0) > thresholds.get(
                    "disk_usage_percent", 85
                ):
                    alerts.append(
                        {
                            "type": "high_disk_usage",
                            "volume": volume_name,
                            "value": usage_data["used_percent"],
                            "threshold": thresholds["disk_usage_percent"],
                            "message": f"Volume {volume_name} is {usage_data['used_percent']:.1f}% full",
                        }
                    )

        return {
            "timestamp": datetime.now().isoformat(),
            "volumes": volume_stats,
            "alerts": alerts,
            "total_volumes": len(volumes),
            "total_size_gb": sum(v.get("size_gb", 0) for v in volume_stats),
        }

    def generate_metrics(self) -> str:
        """Generate Prometheus metrics for volume monitoring."""
        monitoring_data = self.monitor_volumes()
        metrics = []

        # Add header
        metrics.append("# HELP ppl_volume_size_bytes Size of Docker volume in bytes")
        metrics.append("# TYPE ppl_volume_size_bytes gauge")

        for volume in monitoring_data["volumes"]:
            volume_name = volume["volume_name"]
            size_bytes = volume.get("size_bytes", 0)
            metrics.append(
                f'ppl_volume_size_bytes{{volume="{volume_name}"}} {size_bytes}'
            )

        metrics.append("# HELP ppl_volume_used_percent Percentage of volume space used")
        metrics.append("# TYPE ppl_volume_used_percent gauge")

        for volume in monitoring_data["volumes"]:
            volume_name = volume["volume_name"]
            used_percent = volume.get("used_percent", 0)
            metrics.append(
                f'ppl_volume_used_percent{{volume="{volume_name}"}} {used_percent}'
            )

        metrics.append("# HELP ppl_volume_alerts_total Number of volume alerts")
        metrics.append("# TYPE ppl_volume_alerts_total counter")
        metrics.append(f"ppl_volume_alerts_total {len(monitoring_data['alerts'])}")

        return "\n".join(metrics)


def main():
    """Main CLI interface for volume management."""
    parser = argparse.ArgumentParser(description="PPL Meta Platform Volume Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser("list", help="List Docker volumes")
    list_parser.add_argument(
        "--usage", action="store_true", help="Include usage statistics"
    )

    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Backup a volume")
    backup_parser.add_argument("volume", help="Volume name to backup")
    backup_parser.add_argument("--name", help="Custom backup name")

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore a volume")
    restore_parser.add_argument("volume", help="Volume name to restore")
    restore_parser.add_argument("backup", help="Backup name to restore from")

    # List backups command
    backups_parser = subparsers.add_parser("backups", help="List available backups")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove old backups")
    cleanup_parser.add_argument("--days", type=int, help="Retention days")

    # Fix permissions command
    perms_parser = subparsers.add_parser(
        "fix-permissions", help="Fix volume permissions"
    )
    perms_parser.add_argument("volume", help="Volume name")
    perms_parser.add_argument("--uid", type=int, default=1000, help="User ID")
    perms_parser.add_argument("--gid", type=int, default=1000, help="Group ID")

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor volume status")
    monitor_parser.add_argument(
        "--continuous", action="store_true", help="Continuous monitoring"
    )
    monitor_parser.add_argument(
        "--interval", type=int, default=300, help="Check interval in seconds"
    )

    # Metrics command
    metrics_parser = subparsers.add_parser(
        "metrics", help="Generate Prometheus metrics"
    )

    # Backup all command
    backup_all_parser = subparsers.add_parser(
        "backup-all", help="Backup all configured volumes"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    vm = VolumeManager()

    if args.command == "list":
        volumes = vm.list_volumes()
        print(f"Found {len(volumes)} Docker volumes:")
        for volume in volumes:
            print(f"  - {volume['Name']}")
            if args.usage:
                usage = vm.get_volume_usage(volume["Name"])
                if usage:
                    print(f"    Size: {usage['size_gb']:.2f} GB")
                    print(f"    Usage: {usage['used_percent']:.1f}%")

    elif args.command == "backup":
        success = vm.backup_volume(args.volume, args.name)
        if success:
            print(f"✅ Successfully backed up volume '{args.volume}'")
        else:
            print(f"❌ Failed to backup volume '{args.volume}'")
            sys.exit(1)

    elif args.command == "restore":
        success = vm.restore_volume(args.volume, args.backup)
        if success:
            print(
                f"✅ Successfully restored volume '{args.volume}' from backup '{args.backup}'"
            )
        else:
            print(f"❌ Failed to restore volume '{args.volume}'")
            sys.exit(1)

    elif args.command == "backups":
        backups = vm.list_backups()
        print(f"Found {len(backups)} backups:")
        for backup in backups:
            size_mb = backup["file_size"] / (1024 * 1024)
            print(
                f"  - {backup['backup_name']} ({size_mb:.1f} MB) - {backup['creation_time']}"
            )

    elif args.command == "cleanup":
        removed = vm.cleanup_old_backups(args.days)
        print(f"✅ Removed {removed} old backup(s)")

    elif args.command == "fix-permissions":
        success = vm.fix_permissions(args.volume, args.uid, args.gid)
        if success:
            print(f"✅ Fixed permissions for volume '{args.volume}'")
        else:
            print(f"❌ Failed to fix permissions for volume '{args.volume}'")
            sys.exit(1)

    elif args.command == "monitor":
        if args.continuous:
            print(f"Starting continuous monitoring (interval: {args.interval}s)")
            while True:
                report = vm.monitor_volumes()
                print(f"\n[{report['timestamp']}] Volume Status:")
                print(f"  Total volumes: {report['total_volumes']}")
                print(f"  Total size: {report['total_size_gb']:.2f} GB")

                if report["alerts"]:
                    print(f"  🚨 {len(report['alerts'])} alert(s):")
                    for alert in report["alerts"]:
                        print(f"    - {alert['message']}")
                else:
                    print("  ✅ No alerts")

                time.sleep(args.interval)
        else:
            report = vm.monitor_volumes()
            print(json.dumps(report, indent=2))

    elif args.command == "metrics":
        metrics = vm.generate_metrics()
        print(metrics)

    elif args.command == "backup-all":
        volumes = vm.config.get("volumes", {})
        success_count = 0

        for volume_name in volumes.keys():
            print(f"Backing up volume '{volume_name}'...")
            if vm.backup_volume(volume_name):
                success_count += 1
                print(f"  ✅ Success")
            else:
                print(f"  ❌ Failed")

        print(
            f"\nCompleted: {success_count}/{len(volumes)} volumes backed up successfully"
        )


if __name__ == "__main__":
    main()
