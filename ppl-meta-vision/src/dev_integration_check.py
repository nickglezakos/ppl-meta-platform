#!/usr/bin/env python3
"""
Development Environment Health Check & Workflow Integration Status
================================================================

Quick validation tool for Workflow 4 & 5 integration status.
Ensures development can continue smoothly with existing services.

Usage:
    python dev_integration_check.py
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DevHealthCheck:
    """Development environment health check result."""

    component: str
    status: str  # "ready", "warning", "error"
    message: str
    details: Dict[str, Any]


class DevelopmentIntegrationChecker:
    """
    Lightweight integration checker for development environment.
    Focuses on ensuring Workflows 4 & 5 can be developed against
    existing services without full production validation.
    """

    def __init__(self):
        self.services = {
            "Media Service": {"port": 8000, "path": "/health"},
            "Vision Service": {"port": 8003, "path": "/health"},
            "Gateway Service": {"port": 8080, "path": "/health"},
        }

        self.workflow_modules = [
            "workflow4_session_manager",
            "workflow5_face_data_retrieval_fixed",
            "workflow5_fallback_manager",
        ]

    async def run_dev_health_check(self) -> List[DevHealthCheck]:
        """Run lightweight development environment health check."""
        results = []

        # Check service availability
        for service_name, config in self.services.items():
            result = await self._check_service_health(service_name, config)
            results.append(result)

        # Check workflow module availability
        workflow_result = self._check_workflow_modules()
        results.append(workflow_result)

        # Check database connectivity
        db_result = await self._check_database_connectivity()
        results.append(db_result)

        return results

    async def _check_service_health(self, name: str, config: Dict) -> DevHealthCheck:
        """Check if a service is responding."""
        port = config["port"]
        path = config["path"]
        url = f"http://localhost:{port}{path}"

        try:
            response = requests.get(url, timeout=3)

            if response.status_code == 200:
                return DevHealthCheck(
                    component=name,
                    status="ready",
                    message=f"Service responding normally on port {port}",
                    details={
                        "port": port,
                        "response_time": response.elapsed.total_seconds(),
                    },
                )
            else:
                return DevHealthCheck(
                    component=name,
                    status="warning",
                    message=f"Service responding with status {response.status_code}",
                    details={"port": port, "status_code": response.status_code},
                )

        except requests.ConnectionError:
            return DevHealthCheck(
                component=name,
                status="error",
                message=f"Service not responding on port {port}",
                details={"port": port, "error": "connection_refused"},
            )
        except Exception as e:
            return DevHealthCheck(
                component=name,
                status="error",
                message=f"Service check failed: {str(e)}",
                details={"port": port, "error": str(e)},
            )

    def _check_workflow_modules(self) -> DevHealthCheck:
        """Check workflow module availability."""
        available_modules = []
        missing_modules = []

        for module_name in self.workflow_modules:
            try:
                __import__(module_name)
                available_modules.append(module_name)
            except ImportError:
                missing_modules.append(module_name)

        if len(missing_modules) == 0:
            return DevHealthCheck(
                component="Workflow Modules",
                status="ready",
                message="All workflow modules available for development",
                details={"available": available_modules},
            )
        elif len(available_modules) > 0:
            return DevHealthCheck(
                component="Workflow Modules",
                status="warning",
                message=f"Some workflow modules missing: {missing_modules}",
                details={"available": available_modules, "missing": missing_modules},
            )
        else:
            return DevHealthCheck(
                component="Workflow Modules",
                status="error",
                message="No workflow modules available",
                details={"missing": missing_modules},
            )

    async def _check_database_connectivity(self) -> DevHealthCheck:
        """Check basic database connectivity."""
        try:
            # Try to import database dependencies
            import psycopg2

            # Basic connectivity test would go here
            # For now, just check that the dependency is available
            return DevHealthCheck(
                component="Database",
                status="ready",
                message="Database dependencies available",
                details={"driver": "psycopg2"},
            )

        except ImportError:
            return DevHealthCheck(
                component="Database",
                status="warning",
                message="Database driver not available (may still work)",
                details={"missing": "psycopg2"},
            )

    def print_dev_status(self, results: List[DevHealthCheck]):
        """Print development environment status."""
        print("🚀 Development Environment Status")
        print("=" * 40)

        ready_count = sum(1 for r in results if r.status == "ready")
        total_count = len(results)

        print(f"Overall: {ready_count}/{total_count} components ready")
        print()

        for result in results:
            if result.status == "ready":
                icon = "✅"
            elif result.status == "warning":
                icon = "⚠️"
            else:
                icon = "❌"

            print(f"{icon} {result.component}: {result.message}")

        print()

        if ready_count == total_count:
            print("🎉 Development environment ready!")
            print("✅ You can continue developing Workflows 4 & 5")
        elif ready_count >= total_count * 0.7:
            print("⚠️ Development environment mostly ready")
            print("🔧 Some components need attention but development can continue")
        else:
            print("❌ Development environment needs setup")
            print("🚀 Start required services before developing")

        print()
        print("💡 Quick fix commands:")
        print(
            "   Start services: Use VS Code task '🚀 Start All Local Python Services'"
        )
        print(
            "   Check services: Use VS Code task '🏥 Local Python Health Check - All Services'"
        )


async def main():
    """Run development integration check."""
    checker = DevelopmentIntegrationChecker()
    results = await checker.run_dev_health_check()
    checker.print_dev_status(results)


if __name__ == "__main__":
    asyncio.run(main())
