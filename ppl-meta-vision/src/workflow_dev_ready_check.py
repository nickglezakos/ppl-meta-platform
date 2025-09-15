#!/usr/bin/env python3
"""
Workflow Integration Status - Development Ready Validation
=========================================================

Validates that Workflows 4 & 5 are properly integrated for development,
focusing on code availability and basic setup rather than live services.

This script works even when services are not running, making it perfect
for development environment validation.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class WorkflowDevelopmentValidator:
    """Validates workflow development readiness."""

    def __init__(self):
        self.vision_src_path = Path(__file__).parent
        self.project_root = self.vision_src_path.parent.parent

        # Critical workflow files for development
        self.workflow_files = {
            "Workflow 4 Core": [
                "workflow4_session_manager.py",
                "workflow4_validation_complete.py",
                "workflow4_comprehensive_integration_test.py",
            ],
            "Workflow 5 Core": [
                "workflow5_face_data_retrieval_fixed.py",
                "workflow5_fallback_manager.py",
                "workflow5_validation_test_suite.py",
            ],
            "Phase 6 Production": [
                "workflow5_phase6_critical_fixes.py",
                "workflow5_production_deployment_pipeline.py",
                "workflow5_production_monitoring_alerting.py",
            ],
            "Integration Tools": [
                "workflow_integration_validator.py",
                "dev_integration_check.py",
            ],
        }

        # Service directories to check
        self.service_dirs = {
            "Media Service": "ppl-meta-media",
            "Vision Service": "ppl-meta-vision",
            "Gateway Service": "ppl-meta-gateway",
            "Orchestrator Service": "ppl-meta-orchestrator",
        }

    def validate_development_environment(self) -> Dict[str, any]:
        """Validate complete development environment."""
        results = {
            "workflow_files": self._check_workflow_files(),
            "service_structure": self._check_service_structure(),
            "python_environment": self._check_python_environment(),
            "development_tools": self._check_development_tools(),
            "documentation": self._check_documentation(),
        }

        # Calculate overall readiness
        ready_components = sum(
            1 for r in results.values() if r.get("status") == "ready"
        )
        total_components = len(results)

        results["overall"] = {
            "ready_components": ready_components,
            "total_components": total_components,
            "readiness_percent": (ready_components / total_components * 100),
            "development_ready": ready_components >= 4,  # Need at least 80% ready
        }

        return results

    def _check_workflow_files(self) -> Dict[str, any]:
        """Check availability of workflow implementation files."""
        file_status = {}
        missing_files = []
        available_files = []

        for category, files in self.workflow_files.items():
            category_files = {"available": [], "missing": []}

            for filename in files:
                file_path = self.vision_src_path / filename
                if file_path.exists():
                    category_files["available"].append(filename)
                    available_files.append(filename)
                else:
                    category_files["missing"].append(filename)
                    missing_files.append(filename)

            file_status[category] = category_files

        total_files = sum(len(files) for files in self.workflow_files.values())
        available_count = len(available_files)

        return {
            "status": "ready" if available_count >= total_files * 0.8 else "warning",
            "available_count": available_count,
            "total_count": total_files,
            "availability_percent": (available_count / total_files * 100),
            "file_status": file_status,
            "missing_critical": len(missing_files) > 0,
        }

    def _check_service_structure(self) -> Dict[str, any]:
        """Check service directory structure."""
        service_status = {}
        available_services = []

        for service_name, service_dir in self.service_dirs.items():
            service_path = self.project_root / service_dir

            if service_path.exists() and service_path.is_dir():
                # Check for main.py or src directory
                has_main = (service_path / "main.py").exists()
                has_src = (service_path / "src").exists() and (
                    service_path / "src" / "main.py"
                ).exists()

                service_status[service_name] = {
                    "available": True,
                    "path": str(service_path),
                    "has_main": has_main,
                    "has_src": has_src,
                    "runnable": has_main or has_src,
                }

                if has_main or has_src:
                    available_services.append(service_name)
            else:
                service_status[service_name] = {
                    "available": False,
                    "path": str(service_path),
                }

        return {
            "status": "ready" if len(available_services) >= 3 else "warning",
            "available_services": available_services,
            "total_services": len(self.service_dirs),
            "service_details": service_status,
        }

    def _check_python_environment(self) -> Dict[str, any]:
        """Check Python environment and dependencies."""
        python_info = {
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "executable": sys.executable,
            "path": sys.path[:3],  # First few paths
        }

        # Check for key dependencies
        dependencies = {}
        required_deps = ["asyncio", "json", "pathlib", "typing"]
        optional_deps = ["psycopg2", "requests", "aiohttp"]

        for dep in required_deps:
            try:
                __import__(dep)
                dependencies[dep] = "available"
            except ImportError:
                dependencies[dep] = "missing"

        for dep in optional_deps:
            try:
                __import__(dep)
                dependencies[dep] = "available"
            except ImportError:
                dependencies[dep] = "optional_missing"

        required_available = sum(
            1 for dep in required_deps if dependencies[dep] == "available"
        )

        return {
            "status": (
                "ready" if required_available == len(required_deps) else "warning"
            ),
            "python_info": python_info,
            "dependencies": dependencies,
            "required_available": required_available,
            "total_required": len(required_deps),
        }

    def _check_development_tools(self) -> Dict[str, any]:
        """Check development and testing tools."""
        tools = {}

        # Check for VS Code workspace file
        workspace_file = self.project_root / "ppl-meta-platform.code-workspace"
        tools["vscode_workspace"] = workspace_file.exists()

        # Check for development scripts
        dev_scripts = ["dev_integration_check.py", "workflow_integration_validator.py"]

        available_scripts = []
        for script in dev_scripts:
            if (self.vision_src_path / script).exists():
                available_scripts.append(script)

        tools["dev_scripts"] = {
            "available": available_scripts,
            "total": len(dev_scripts),
        }

        # Check for documentation
        docs = [
            "WORKFLOW_DEVELOPMENT_INTEGRATION_GUIDE.md",
            "FACE_DETECTION_WORKFLOW_5_DEVELOPMENT_PHASES.md",
        ]

        available_docs = []
        for doc in docs:
            if (self.project_root / doc).exists():
                available_docs.append(doc)

        tools["documentation"] = {"available": available_docs, "total": len(docs)}

        tool_score = (
            (1 if tools["vscode_workspace"] else 0)
            + (len(available_scripts) / len(dev_scripts))
            + (len(available_docs) / len(docs))
        ) / 3

        return {
            "status": "ready" if tool_score >= 0.7 else "warning",
            "tool_details": tools,
            "tool_score": tool_score,
        }

    def _check_documentation(self) -> Dict[str, any]:
        """Check development documentation availability."""
        docs = {
            "Integration Guide": "WORKFLOW_DEVELOPMENT_INTEGRATION_GUIDE.md",
            "Development Phases": "FACE_DETECTION_WORKFLOW_5_DEVELOPMENT_PHASES.md",
            "README": "README.md",
        }

        doc_status = {}
        available_docs = 0

        for doc_name, filename in docs.items():
            doc_path = self.project_root / filename
            if doc_path.exists():
                doc_status[doc_name] = {
                    "available": True,
                    "path": str(doc_path),
                    "size": doc_path.stat().st_size,
                }
                available_docs += 1
            else:
                doc_status[doc_name] = {"available": False, "path": str(doc_path)}

        return {
            "status": "ready" if available_docs >= 2 else "warning",
            "available_docs": available_docs,
            "total_docs": len(docs),
            "doc_details": doc_status,
        }

    def print_development_status(self, results: Dict[str, any]):
        """Print formatted development status report."""
        overall = results["overall"]

        print("🚀 Workflow 4 & 5 Development Integration Status")
        print("=" * 55)
        print()

        # Overall status
        if overall["development_ready"]:
            print("✅ DEVELOPMENT READY")
            print("🎯 Workflows 4 & 5 are integrated and ready for development")
        else:
            print("⚠️ DEVELOPMENT NEEDS SETUP")
            print("🔧 Some components need attention before development")

        print()
        print(
            f"Overall Readiness: {overall['readiness_percent']:.1f}% ({overall['ready_components']}/{overall['total_components']} components ready)"
        )
        print()

        # Component details
        components = [
            ("Workflow Files", results["workflow_files"]),
            ("Service Structure", results["service_structure"]),
            ("Python Environment", results["python_environment"]),
            ("Development Tools", results["development_tools"]),
            ("Documentation", results["documentation"]),
        ]

        for name, component in components:
            status_icon = "✅" if component["status"] == "ready" else "⚠️"
            print(f"{status_icon} {name}: {component['status'].upper()}")

            # Add specific details for each component
            if name == "Workflow Files":
                print(
                    f"   Available: {component['available_count']}/{component['total_count']} files ({component['availability_percent']:.1f}%)"
                )
            elif name == "Service Structure":
                print(
                    f"   Services: {len(component['available_services'])}/{component['total_services']} available"
                )
            elif name == "Python Environment":
                print(
                    f"   Dependencies: {component['required_available']}/{component['total_required']} required available"
                )
            elif name == "Development Tools":
                print(f"   Tool Score: {component['tool_score']:.1f}/1.0")
            elif name == "Documentation":
                print(
                    f"   Docs: {component['available_docs']}/{component['total_docs']} available"
                )

        print()

        # Development guidance
        if overall["development_ready"]:
            print("🎉 Development Environment Ready!")
            print()
            print("✅ Next Steps:")
            print(
                "   1. Start services: Use VS Code task '🚀 Start All Local Python Services'"
            )
            print("   2. Run integration check: python dev_integration_check.py")
            print("   3. Begin development: Import and use workflow modules")
            print("   4. Test changes: Run workflow validation tests")
            print()
            print("📚 Development Resources:")
            print("   • Integration Guide: WORKFLOW_DEVELOPMENT_INTEGRATION_GUIDE.md")
            print(
                "   • Phase Documentation: FACE_DETECTION_WORKFLOW_5_DEVELOPMENT_PHASES.md"
            )
            print("   • Health Check: python dev_integration_check.py")
            print("   • Full Validation: python workflow_integration_validator.py")
        else:
            print("🔧 Setup Required:")

            # Specific setup guidance
            if results["workflow_files"]["status"] != "ready":
                print("   • Missing workflow files - check implementation completeness")

            if results["service_structure"]["status"] != "ready":
                print("   • Service structure incomplete - verify service directories")

            if results["python_environment"]["status"] != "ready":
                print("   • Python dependencies missing - install required packages")

            print()
            print("💡 Quick Setup:")
            print("   1. Ensure you're in the correct directory")
            print("   2. Check for missing workflow implementation files")
            print("   3. Verify service directory structure")
            print("   4. Install any missing Python dependencies")


def main():
    """Run development validation."""
    validator = WorkflowDevelopmentValidator()
    results = validator.validate_development_environment()
    validator.print_development_status(results)

    # Return appropriate exit code
    if results["overall"]["development_ready"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
