"""
Shared Migration Utilities for PPL Meta Platform

This module provides utilities for managing database migrations across all services.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


class MigrationManager:
    """Manages database migrations for PPL Meta Platform services."""

    SERVICES = {
        "ppl-meta-node": {"path": "ppl-meta-node", "database": "ppl_db", "port": 5433},
        "ppl-meta-media": {
            "path": "ppl-meta-media",
            "database": "ppl_media_db",
            "port": 5433,
        },
        "ppl-meta-gateway": {
            "path": "ppl-meta-gateway",
            "database": "ppl_gateway_db",
            "port": 5433,
        },
        "ppl-meta-orchestrator": {
            "path": "ppl-meta-orchestrator",
            "database": "ppl_orchestrator_db",
            "port": 5433,
        },
    }

    def __init__(self, root_path: Optional[str] = None):
        """Initialize the migration manager.

        Args:
            root_path: Path to the root of the project. If None, auto-detect.
        """
        if root_path is None:
            # Auto-detect root path
            current = Path(__file__).parent
            while current.parent != current:
                if (current / "ppl-meta-node").exists():
                    root_path = str(current)
                    break
                current = current.parent

        self.root_path = Path(root_path) if root_path else Path.cwd()

    def get_service_path(self, service_name: str) -> Path:
        """Get the full path to a service directory."""
        if service_name not in self.SERVICES:
            raise ValueError(f"Unknown service: {service_name}")

        return self.root_path / self.SERVICES[service_name]["path"]

    def service_has_alembic(self, service_name: str) -> bool:
        """Check if a service has Alembic migrations set up."""
        service_path = self.get_service_path(service_name)
        return (service_path / "alembic.ini").exists()

    def init_alembic(self, service_name: str) -> bool:
        """Initialize Alembic for a service.

        Args:
            service_name: Name of the service to initialize

        Returns:
            True if successful, False otherwise
        """
        service_path = self.get_service_path(service_name)

        if self.service_has_alembic(service_name):
            print(f"✅ {service_name} already has Alembic initialized")
            return True

        try:
            # Change to service directory and run alembic init
            result = subprocess.run(
                ["alembic", "init", "migrations"],
                cwd=service_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"✅ Initialized Alembic for {service_name}")
                return True
            else:
                print(
                    f"❌ Failed to initialize Alembic for {service_name}: {result.stderr}"
                )
                return False

        except subprocess.CalledProcessError as e:
            print(f"❌ Error initializing Alembic for {service_name}: {e}")
            return False

    def create_migration(
        self, service_name: str, message: str, auto: bool = True
    ) -> bool:
        """Create a new migration for a service.

        Args:
            service_name: Name of the service
            message: Migration message
            auto: Whether to auto-generate the migration

        Returns:
            True if successful, False otherwise
        """
        service_path = self.get_service_path(service_name)

        if not self.service_has_alembic(service_name):
            print(f"❌ {service_name} does not have Alembic initialized")
            return False

        try:
            cmd = ["alembic", "revision", "-m", message]
            if auto:
                cmd.append("--autogenerate")

            result = subprocess.run(
                cmd, cwd=service_path, capture_output=True, text=True
            )

            if result.returncode == 0:
                print(f"✅ Created migration for {service_name}: {message}")
                return True
            else:
                print(
                    f"❌ Failed to create migration for {service_name}: {result.stderr}"
                )
                return False

        except subprocess.CalledProcessError as e:
            print(f"❌ Error creating migration for {service_name}: {e}")
            return False

    def run_migrations(self, service_name: str, target: str = "head") -> bool:
        """Run migrations for a service.

        Args:
            service_name: Name of the service
            target: Migration target (default: head)

        Returns:
            True if successful, False otherwise
        """
        service_path = self.get_service_path(service_name)

        if not self.service_has_alembic(service_name):
            print(f"❌ {service_name} does not have Alembic initialized")
            return False

        try:
            result = subprocess.run(
                ["alembic", "upgrade", target],
                cwd=service_path,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"✅ Ran migrations for {service_name}")
                return True
            else:
                print(
                    f"❌ Failed to run migrations for {service_name}: {result.stderr}"
                )
                return False

        except subprocess.CalledProcessError as e:
            print(f"❌ Error running migrations for {service_name}: {e}")
            return False

    def get_migration_status(self, service_name: str) -> Dict:
        """Get migration status for a service.

        Args:
            service_name: Name of the service

        Returns:
            Dictionary with migration status information
        """
        service_path = self.get_service_path(service_name)
        status = {
            "service": service_name,
            "has_alembic": self.service_has_alembic(service_name),
            "current_revision": None,
            "available_migrations": [],
            "pending_migrations": [],
        }

        if not status["has_alembic"]:
            return status

        try:
            # Get current revision
            result = subprocess.run(
                ["alembic", "current"], cwd=service_path, capture_output=True, text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                status["current_revision"] = result.stdout.strip()

            # Get migration history
            result = subprocess.run(
                ["alembic", "history"], cwd=service_path, capture_output=True, text=True
            )

            if result.returncode == 0:
                # Parse migration history (simplified)
                for line in result.stdout.split("\n"):
                    if line.strip() and not line.startswith("Rev:"):
                        status["available_migrations"].append(line.strip())

        except subprocess.CalledProcessError:
            pass  # Ignore errors for now

        return status

    def status_all_services(self) -> List[Dict]:
        """Get migration status for all services.

        Returns:
            List of status dictionaries for each service
        """
        statuses = []
        for service_name in self.SERVICES.keys():
            statuses.append(self.get_migration_status(service_name))
        return statuses

    def init_all_services(self) -> bool:
        """Initialize Alembic for all services.

        Returns:
            True if all services were initialized successfully
        """
        success = True
        for service_name in self.SERVICES.keys():
            if not self.init_alembic(service_name):
                success = False
        return success


def main():
    """CLI interface for migration management."""
    if len(sys.argv) < 2:
        print("Usage: python migration_manager.py <command> [args...]")
        print("Commands:")
        print("  status - Show migration status for all services")
        print("  init [service] - Initialize Alembic for service(s)")
        print("  create <service> <message> - Create new migration")
        print("  migrate [service] - Run migrations for service(s)")
        return

    manager = MigrationManager()
    command = sys.argv[1]

    if command == "status":
        statuses = manager.status_all_services()
        print("\n📊 Migration Status Report")
        print("=" * 50)
        for status in statuses:
            print(f"\n🔧 {status['service']}")
            print(f"   Alembic: {'✅' if status['has_alembic'] else '❌'}")
            print(f"   Current: {status['current_revision'] or 'No migrations'}")

    elif command == "init":
        if len(sys.argv) > 2:
            service = sys.argv[2]
            manager.init_alembic(service)
        else:
            manager.init_all_services()

    elif command == "create":
        if len(sys.argv) < 4:
            print("Usage: create <service> <message>")
            return
        service = sys.argv[2]
        message = sys.argv[3]
        manager.create_migration(service, message)

    elif command == "migrate":
        if len(sys.argv) > 2:
            service = sys.argv[2]
            manager.run_migrations(service)
        else:
            for service in manager.SERVICES.keys():
                manager.run_migrations(service)
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
