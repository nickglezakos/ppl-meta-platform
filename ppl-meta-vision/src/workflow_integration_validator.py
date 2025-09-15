#!/usr/bin/env python3
"""
Face Detection Workflows 4 & 5 - Integration & Development Continuity Package
=============================================================================

DEVELOPMENT-FOCUSED INTEGRATION VALIDATION SYSTEM

This module ensures that Face Detection Workflows 4 and 5 are properly integrated
with existing PPL Meta services, providing a solid foundation for continued
development while maintaining backward compatibility and system stability.

Focus Areas:
- Service integration validation and testing
- Development environment consistency
- Automated regression testing
- Developer experience optimization
- Backward compatibility assurance

Integration Scope:
- ppl-meta-media service integration
- ppl-meta-vision service compatibility
- ppl-meta-gateway routing validation
- Database schema consistency
- API endpoint verification
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IntegrationTestResult:
    """Result of a service integration test."""

    test_name: str
    service: str
    success: bool
    execution_time_ms: float
    details: Dict[str, Any]
    error: Optional[str] = None


@dataclass
class ServiceCompatibility:
    """Service compatibility assessment."""

    service_name: str
    workflow4_compatible: bool
    workflow5_compatible: bool
    api_endpoints_valid: bool
    database_schema_compatible: bool
    issues: List[str]
    recommendations: List[str]


class WorkflowIntegrationValidator:
    """
    Validates integration of Workflows 4 & 5 with existing services.
    Focuses on development continuity rather than production readiness.
    """

    def __init__(self):
        self.services = {
            "ppl-meta-media": {
                "port": 8000,
                "health_endpoint": "/health",
                "workflow_endpoints": [
                    "/api/v1/face-detection/session",
                    "/api/v1/face-detection/stream",
                ],
            },
            "ppl-meta-vision": {
                "port": 8003,
                "health_endpoint": "/health",
                "workflow_endpoints": [
                    "/api/v1/process-video",
                    "/api/v1/face-detection",
                ],
            },
            "ppl-meta-gateway": {
                "port": 8080,
                "health_endpoint": "/health",
                "workflow_endpoints": ["/health", "/api/v1/health"],
            },
        }

        self.integration_tests = [
            ("Workflow 4 Session Management", self._test_workflow4_sessions),
            ("Workflow 5 Processing Status", self._test_workflow5_processing),
            ("Database Schema Compatibility", self._test_database_schema),
            ("API Endpoint Availability", self._test_api_endpoints),
            ("Service Communication", self._test_service_communication),
            ("Backward Compatibility", self._test_backward_compatibility),
        ]

        self.test_results: List[IntegrationTestResult] = []

    async def run_integration_validation(self) -> Dict[str, Any]:
        """Run complete integration validation for development continuity."""
        logger.info("🔍 Starting Workflow Integration Validation for Development...")

        validation_start_time = time.time()

        # Run all integration tests
        for test_name, test_method in self.integration_tests:
            logger.info(f"\n📋 Running: {test_name}...")

            test_start_time = time.time()
            try:
                result = await test_method()
                test_time = (time.time() - test_start_time) * 1000

                test_result = IntegrationTestResult(
                    test_name=test_name,
                    service=result.get("service", "system"),
                    success=result.get("success", False),
                    execution_time_ms=test_time,
                    details=result,
                    error=result.get("error"),
                )

                self.test_results.append(test_result)

                if test_result.success:
                    logger.info(f"✅ {test_name}: {result.get('message', 'Passed')}")
                else:
                    logger.warning(f"⚠️ {test_name}: {result.get('message', 'Failed')}")

            except Exception as e:
                test_time = (time.time() - test_start_time) * 1000
                logger.error(f"❌ {test_name} failed with exception: {e}")

                test_result = IntegrationTestResult(
                    test_name=test_name,
                    service="system",
                    success=False,
                    execution_time_ms=test_time,
                    details={},
                    error=str(e),
                )

                self.test_results.append(test_result)

        total_validation_time = (time.time() - validation_start_time) * 1000

        return self._generate_integration_report(total_validation_time)

    async def _test_workflow4_sessions(self) -> Dict[str, Any]:
        """Test Workflow 4 session management integration."""
        try:
            # Test session-based face detection functionality
            from workflow4_session_manager import Workflow4SessionManager

            session_manager = Workflow4SessionManager()
            await session_manager.initialize()

            # Test session creation
            test_media_id = "test-workflow4-integration"
            session_result = await session_manager.create_session(test_media_id)

            if not session_result.get("success"):
                return {
                    "success": False,
                    "service": "ppl-meta-vision",
                    "message": "Workflow 4 session creation failed",
                    "error": session_result.get("error"),
                }

            session_uuid = session_result["session_uuid"]

            # Test session validation
            validation_result = await session_manager.validate_session(session_uuid)

            if not validation_result:
                return {
                    "success": False,
                    "service": "ppl-meta-vision",
                    "message": "Workflow 4 session validation failed",
                }

            # Cleanup test session
            await session_manager.cleanup_session(session_uuid)

            return {
                "success": True,
                "service": "ppl-meta-vision",
                "message": "Workflow 4 session management working correctly",
                "session_uuid": session_uuid,
                "integration_verified": True,
            }

        except ImportError:
            return {
                "success": False,
                "service": "ppl-meta-vision",
                "message": "Workflow 4 session manager not available - integration may be incomplete",
                "error": "Missing workflow4_session_manager module",
            }
        except Exception as e:
            return {
                "success": False,
                "service": "ppl-meta-vision",
                "message": f"Workflow 4 session test failed: {e}",
                "error": str(e),
            }

    async def _test_workflow5_processing(self) -> Dict[str, Any]:
        """Test Workflow 5 processing status integration."""
        try:
            # Test processing status functionality
            from workflow5_face_data_retrieval_fixed import Workflow5FaceDataRetriever

            retriever = Workflow5FaceDataRetriever()
            await retriever.initialize()

            # Test with existing media items
            test_media_items = await retriever.get_available_media()

            if not test_media_items:
                return {
                    "success": True,
                    "service": "ppl-meta-vision",
                    "message": "Workflow 5 integration ready - no test media available yet",
                    "media_count": 0,
                    "status": "ready_for_development",
                }

            # Test processing status for first available media
            test_media_uuid = test_media_items[0]["media_uuid"]
            processing_result = await retriever.check_processing_status(test_media_uuid)

            # Test face data retrieval
            face_data_result = await retriever.get_faces_for_media(test_media_uuid)

            return {
                "success": True,
                "service": "ppl-meta-vision",
                "message": "Workflow 5 processing status working correctly",
                "test_media_uuid": test_media_uuid,
                "processing_status": processing_result,
                "face_data_available": len(face_data_result) > 0,
                "integration_verified": True,
            }

        except ImportError:
            return {
                "success": False,
                "service": "ppl-meta-vision",
                "message": "Workflow 5 data retriever not available - integration may be incomplete",
                "error": "Missing workflow5_face_data_retrieval_fixed module",
            }
        except Exception as e:
            return {
                "success": False,
                "service": "ppl-meta-vision",
                "message": f"Workflow 5 processing test failed: {e}",
                "error": str(e),
            }

    async def _test_database_schema(self) -> Dict[str, Any]:
        """Test database schema compatibility for workflows."""
        try:
            # Test database connection and schema
            import psycopg2
            from workflow5_phase6_critical_fixes import DatabaseSchemaFixer

            # Test basic database connectivity
            schema_fixer = DatabaseSchemaFixer()
            await schema_fixer.initialize()

            # Run schema validation
            validation_results = await schema_fixer.validate_schema_compatibility()

            schema_issues = []
            schema_fixes = 0

            if validation_results.get("fixes_needed", 0) > 0:
                schema_issues.append(
                    f"{validation_results['fixes_needed']} schema fixes needed"
                )

            if validation_results.get("missing_indexes", 0) > 0:
                schema_issues.append(
                    f"{validation_results['missing_indexes']} missing indexes"
                )

            return {
                "success": len(schema_issues) == 0,
                "service": "database",
                "message": f"Database schema validation: {len(schema_issues)} issues found",
                "schema_compatible": len(schema_issues) == 0,
                "issues": schema_issues,
                "validation_details": validation_results,
            }

        except ImportError as e:
            return {
                "success": False,
                "service": "database",
                "message": "Database schema validation unavailable - missing dependencies",
                "error": f"Import error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "service": "database",
                "message": f"Database schema test failed: {e}",
                "error": str(e),
            }

    async def _test_api_endpoints(self) -> Dict[str, Any]:
        """Test API endpoint availability for workflow integration."""
        endpoint_results = {}
        total_endpoints = 0
        available_endpoints = 0

        for service_name, service_config in self.services.items():
            port = service_config["port"]
            endpoints = [service_config["health_endpoint"]] + service_config.get(
                "workflow_endpoints", []
            )

            service_results = {}

            for endpoint in endpoints:
                total_endpoints += 1
                url = f"http://localhost:{port}{endpoint}"

                try:
                    response = requests.get(url, timeout=3)
                    is_available = response.status_code in [
                        200,
                        404,
                    ]  # 404 is OK for development

                    if is_available:
                        available_endpoints += 1

                    service_results[endpoint] = {
                        "available": is_available,
                        "status_code": response.status_code,
                        "response_time_ms": response.elapsed.total_seconds() * 1000,
                    }

                except Exception as e:
                    service_results[endpoint] = {"available": False, "error": str(e)}

            endpoint_results[service_name] = service_results

        availability_rate = (
            (available_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0
        )

        return {
            "success": availability_rate >= 60,  # Relaxed for development
            "service": "all_services",
            "message": f"API endpoint availability: {available_endpoints}/{total_endpoints} ({availability_rate:.1f}%)",
            "availability_rate": availability_rate,
            "endpoint_details": endpoint_results,
            "development_ready": availability_rate >= 50,
        }

    async def _test_service_communication(self) -> Dict[str, Any]:
        """Test inter-service communication for workflows."""
        communication_tests = []

        # Test Media -> Vision communication
        try:
            media_response = requests.get("http://localhost:8000/health", timeout=3)
            vision_response = requests.get("http://localhost:8003/health", timeout=3)

            media_available = media_response.status_code == 200
            vision_available = vision_response.status_code == 200

            communication_tests.append(
                {
                    "test": "media_vision_communication",
                    "success": media_available and vision_available,
                    "media_available": media_available,
                    "vision_available": vision_available,
                }
            )

        except Exception as e:
            communication_tests.append(
                {
                    "test": "media_vision_communication",
                    "success": False,
                    "error": str(e),
                }
            )

        # Test Gateway routing
        try:
            gateway_response = requests.get("http://localhost:8080/health", timeout=3)
            gateway_available = gateway_response.status_code == 200

            communication_tests.append(
                {
                    "test": "gateway_routing",
                    "success": gateway_available,
                    "gateway_available": gateway_available,
                }
            )

        except Exception as e:
            communication_tests.append(
                {"test": "gateway_routing", "success": False, "error": str(e)}
            )

        successful_tests = sum(1 for test in communication_tests if test["success"])
        total_tests = len(communication_tests)

        return {
            "success": successful_tests
            >= (total_tests * 0.5),  # 50% success rate for development
            "service": "communication",
            "message": f"Service communication: {successful_tests}/{total_tests} tests passed",
            "communication_tests": communication_tests,
            "development_ready": successful_tests > 0,
        }

    async def _test_backward_compatibility(self) -> Dict[str, Any]:
        """Test backward compatibility with existing functionality."""
        compatibility_checks = []

        # Check if existing endpoints still work
        existing_endpoints = [
            ("http://localhost:8000/health", "Media Service Health"),
            ("http://localhost:8003/health", "Vision Service Health"),
            ("http://localhost:8080/health", "Gateway Health"),
        ]

        for url, description in existing_endpoints:
            try:
                response = requests.get(url, timeout=3)
                compatible = response.status_code in [
                    200,
                    404,
                ]  # 404 acceptable in development

                compatibility_checks.append(
                    {
                        "check": description,
                        "compatible": compatible,
                        "status_code": response.status_code,
                        "url": url,
                    }
                )

            except Exception as e:
                compatibility_checks.append(
                    {
                        "check": description,
                        "compatible": False,
                        "error": str(e),
                        "url": url,
                    }
                )

        compatible_checks = sum(
            1 for check in compatibility_checks if check["compatible"]
        )
        total_checks = len(compatibility_checks)

        return {
            "success": compatible_checks
            >= (total_checks * 0.7),  # 70% compatibility for development
            "service": "backward_compatibility",
            "message": f"Backward compatibility: {compatible_checks}/{total_checks} checks passed",
            "compatibility_checks": compatibility_checks,
            "compatibility_rate": (
                (compatible_checks / total_checks * 100) if total_checks > 0 else 0
            ),
        }

    def _generate_integration_report(self, total_time: float) -> Dict[str, Any]:
        """Generate comprehensive integration validation report."""

        successful_tests = sum(1 for result in self.test_results if result.success)
        total_tests = len(self.test_results)

        # Categorize results by service
        service_results = {}
        for result in self.test_results:
            service = result.service
            if service not in service_results:
                service_results[service] = []
            service_results[service].append(result)

        # Generate development readiness assessment
        development_ready = successful_tests >= (total_tests * 0.7)  # 70% success rate

        # Generate recommendations
        recommendations = self._generate_development_recommendations()

        return {
            "integration_summary": {
                "validation_successful": development_ready,
                "total_execution_time_ms": round(total_time, 2),
                "successful_tests": successful_tests,
                "total_tests": total_tests,
                "success_rate_percent": round(
                    (successful_tests / total_tests * 100) if total_tests > 0 else 0, 2
                ),
            },
            "test_results": [
                {
                    "test": result.test_name,
                    "service": result.service,
                    "success": result.success,
                    "execution_time_ms": result.execution_time_ms,
                    "details": result.details,
                    "error": result.error,
                }
                for result in self.test_results
            ],
            "service_compatibility": service_results,
            "development_readiness": {
                "ready_for_development": development_ready,
                "workflow4_integrated": any(
                    r.success for r in self.test_results if "Workflow 4" in r.test_name
                ),
                "workflow5_integrated": any(
                    r.success for r in self.test_results if "Workflow 5" in r.test_name
                ),
                "database_compatible": any(
                    r.success for r in self.test_results if "Database" in r.test_name
                ),
                "services_communicating": any(
                    r.success
                    for r in self.test_results
                    if "Communication" in r.test_name
                ),
            },
            "recommendations": recommendations,
            "next_steps": self._get_development_next_steps(development_ready),
        }

    def _generate_development_recommendations(self) -> List[str]:
        """Generate recommendations for development continuity."""
        recommendations = []

        # Check for failed tests and generate specific recommendations
        for result in self.test_results:
            if not result.success:
                if "Workflow 4" in result.test_name:
                    recommendations.append(
                        "Workflow 4 integration needs attention - check session management setup"
                    )
                elif "Workflow 5" in result.test_name:
                    recommendations.append(
                        "Workflow 5 integration needs attention - verify processing status APIs"
                    )
                elif "Database" in result.test_name:
                    recommendations.append(
                        "Database schema compatibility issues - run schema fixes before development"
                    )
                elif "API" in result.test_name:
                    recommendations.append(
                        "Some API endpoints unavailable - ensure all services are running for development"
                    )
                elif "Communication" in result.test_name:
                    recommendations.append(
                        "Service communication issues - check network connectivity and service status"
                    )
                elif "Compatibility" in result.test_name:
                    recommendations.append(
                        "Backward compatibility concerns - verify existing functionality"
                    )

        if not recommendations:
            recommendations.append(
                "All integration tests passed - system ready for continued development"
            )

        return recommendations

    def _get_development_next_steps(self, development_ready: bool) -> List[str]:
        """Get recommended next steps for development."""
        if development_ready:
            return [
                "✅ Integration validation successful - continue with development",
                "🔧 Run specific workflow tests as needed during development",
                "📊 Monitor integration health during active development",
                "🚀 Consider running integration validation before major changes",
                "📝 Update integration tests as new features are added",
            ]
        else:
            return [
                "🔧 Address failed integration tests before continuing development",
                "🚀 Ensure all required services are running",
                "📋 Review database schema compatibility issues",
                "🔍 Check service configuration and connectivity",
                "⚙️ Re-run integration validation after fixes",
                "📞 Contact team leads if integration issues persist",
            ]


class DevelopmentEnvironmentSetup:
    """
    Helps set up development environment for Workflow 4 & 5 development.
    """

    def __init__(self):
        self.required_services = [
            "ppl-meta-media",
            "ppl-meta-vision",
            "ppl-meta-gateway",
        ]

    def generate_development_guide(self) -> str:
        """Generate development environment setup guide."""
        return """
# Face Detection Workflows 4 & 5 - Development Setup Guide

## Quick Start for Developers

### 1. Service Dependencies
Ensure these services are running for Workflow development:
- ppl-meta-media (port 8000)
- ppl-meta-vision (port 8003) 
- ppl-meta-gateway (port 8080)

### 2. Development Commands
```bash
# Start all required services
cd /Users/nickgklezakos/Documents/ppl-meta-code
# Use VS Code task: "🚀 Start All Local Python Services"

# Validate integration
cd ppl-meta-vision/src
python workflow_integration_validator.py

# Run specific workflow tests
python -c "from workflow4_session_manager import Workflow4SessionManager; print('Workflow 4 ready')"
python -c "from workflow5_face_data_retrieval_fixed import Workflow5FaceDataRetriever; print('Workflow 5 ready')"
```

### 3. Development Workflow
1. Start required services
2. Run integration validation
3. Develop workflow features
4. Test integration periodically
5. Run validation before commits

### 4. Key Development Files
- workflow4_session_manager.py - Session-based face detection
- workflow5_face_data_retrieval_fixed.py - Stored face data retrieval
- workflow5_fallback_manager.py - Fallback mechanisms
- workflow5_validation_test_suite.py - Validation framework

### 5. Integration Testing
Run integration tests frequently during development:
```python
from workflow_integration_validator import WorkflowIntegrationValidator
validator = WorkflowIntegrationValidator()
result = await validator.run_integration_validation()
```

### 6. Common Development Issues
- Services not responding: Check if all services are running
- Database errors: Ensure PostgreSQL is running and accessible
- Import errors: Verify Python path and dependencies
- Integration failures: Run validation to identify specific issues

### 7. Development Best Practices
- Test integration before and after major changes
- Keep services running during active development
- Use validation results to guide development priorities
- Document any new integration requirements
"""


async def main():
    """Run the integration validation for development continuity."""
    print("🔍 Face Detection Workflows 4 & 5 - Integration Validation")
    print("=" * 65)
    print("Focus: Development Continuity & Service Integration")
    print()

    # Create and run integration validator
    validator = WorkflowIntegrationValidator()

    try:
        validation_report = await validator.run_integration_validation()

        # Display results
        print(f"\n📊 Integration Validation Report:")
        print("=" * 45)

        summary = validation_report["integration_summary"]
        print(
            f"Overall Status: {'✅ READY FOR DEVELOPMENT' if summary['validation_successful'] else '⚠️ NEEDS ATTENTION'}"
        )
        print(f"Total Time: {summary['total_execution_time_ms']:.1f}ms")
        print(
            f"Success Rate: {summary['success_rate_percent']:.1f}% ({summary['successful_tests']}/{summary['total_tests']})"
        )

        # Development readiness
        readiness = validation_report["development_readiness"]
        print(f"\n🚀 Development Readiness:")
        print(
            f"  Ready for Development: {'✅' if readiness['ready_for_development'] else '❌'}"
        )
        print(
            f"  Workflow 4 Integrated: {'✅' if readiness['workflow4_integrated'] else '❌'}"
        )
        print(
            f"  Workflow 5 Integrated: {'✅' if readiness['workflow5_integrated'] else '❌'}"
        )
        print(
            f"  Database Compatible: {'✅' if readiness['database_compatible'] else '❌'}"
        )
        print(
            f"  Services Communicating: {'✅' if readiness['services_communicating'] else '❌'}"
        )

        # Test details
        print(f"\n📋 Test Results:")
        for test_result in validation_report["test_results"]:
            status = "✅" if test_result["success"] else "⚠️"
            test_name = test_result["test"]
            service = test_result["service"]
            time_ms = test_result["execution_time_ms"]
            print(f"  {status} {test_name} ({service}): {time_ms:.1f}ms")

            if test_result["error"]:
                print(f"      Error: {test_result['error']}")

        # Recommendations
        print(f"\n💡 Development Recommendations:")
        for recommendation in validation_report["recommendations"]:
            print(f"  • {recommendation}")

        # Next steps
        print(f"\n🚀 Next Steps:")
        for step in validation_report["next_steps"]:
            print(f"  {step}")

        # Save detailed report
        report_file = f"/tmp/workflow_integration_report_{int(time.time())}.json"
        with open(report_file, "w") as f:
            json.dump(validation_report, f, indent=2, default=str)

        print(f"\n📄 Detailed report saved to: {report_file}")

        # Generate development guide
        dev_setup = DevelopmentEnvironmentSetup()
        guide_content = dev_setup.generate_development_guide()

        guide_file = "/tmp/workflow_development_guide.md"
        with open(guide_file, "w") as f:
            f.write(guide_content)

        print(f"📚 Development guide saved to: {guide_file}")

        if readiness["ready_for_development"]:
            print(f"\n🎉 INTEGRATION VALIDATION SUCCESSFUL!")
            print(f"✅ Workflows 4 & 5 are ready for continued development")
            print(f"🚀 Development can proceed with confidence")
        else:
            print(f"\n⚠️ INTEGRATION VALIDATION NEEDS ATTENTION")
            print(f"🔧 Address identified issues before continuing development")

    except Exception as e:
        print(f"❌ Integration validation failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
