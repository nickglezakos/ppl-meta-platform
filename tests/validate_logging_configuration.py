#!/usr/bin/env python3
"""
Validation script for standardized logging across all PPL Meta services.

This script verifies that each service can properly use the shared logging module
and that logging configurations are consistent.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def check_service_logging_config(service_path, service_name):
    """Check if a service has proper logging configuration."""
    print(f"\n🔍 Checking {service_name}...")

    config_file = os.path.join(service_path, "src", "config.py")
    env_file = os.path.join(service_path, ".env.example")
    requirements_file = os.path.join(service_path, "requirements.txt")

    # Check for config.py
    if not os.path.exists(config_file):
        print(f"  ❌ Missing config.py file")
        return False

    # Check for LOG_LEVEL and LOG_FORMAT in config
    with open(config_file, "r") as f:
        config_content = f.read()

    has_log_level = "LOG_LEVEL" in config_content
    has_log_format = "LOG_FORMAT" in config_content

    print(f"  {'✅' if has_log_level else '❌'} LOG_LEVEL configuration")
    print(f"  {'✅' if has_log_format else '❌'} LOG_FORMAT configuration")

    # Check .env.example
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            env_content = f.read()
        has_env_log_level = "LOG_LEVEL=" in env_content
        has_env_log_format = "LOG_FORMAT=" in env_content
        print(f"  {'✅' if has_env_log_level else '❌'} LOG_LEVEL in .env.example")
        print(f"  {'✅' if has_env_log_format else '❌'} LOG_FORMAT in .env.example")
    else:
        print(f"  ❌ Missing .env.example file")
        has_env_log_level = has_env_log_format = False

    # Check requirements.txt for structlog
    if os.path.exists(requirements_file):
        with open(requirements_file, "r") as f:
            requirements_content = f.read()
        has_structlog = "structlog" in requirements_content
        print(f"  {'✅' if has_structlog else '❌'} structlog dependency")
    else:
        print(f"  ❌ Missing requirements.txt file")
        has_structlog = False

    # Overall status
    all_good = (
        has_log_level
        and has_log_format
        and has_env_log_level
        and has_env_log_format
        and has_structlog
    )
    print(f"  {'✅' if all_good else '❌'} Overall logging configuration")

    return all_good


def check_shared_logging_module():
    """Check if the shared logging module exists and is properly structured."""
    print("\n🔍 Checking shared logging module...")

    shared_path = os.path.join(os.path.dirname(__file__), "shared", "logging")

    # Check directory structure
    if not os.path.exists(shared_path):
        print("  ❌ Shared logging directory missing")
        return False

    init_file = os.path.join(shared_path, "__init__.py")
    logger_file = os.path.join(shared_path, "structured_logger.py")
    requirements_file = os.path.join(shared_path, "requirements.txt")

    files_exist = [
        ("__init__.py", os.path.exists(init_file)),
        ("structured_logger.py", os.path.exists(logger_file)),
        ("requirements.txt", os.path.exists(requirements_file)),
    ]

    for file_name, exists in files_exist:
        print(f"  {'✅' if exists else '❌'} {file_name}")

    all_files_exist = all(exists for _, exists in files_exist)

    # Check if structured_logger has key functions
    if os.path.exists(logger_file):
        with open(logger_file, "r") as f:
            logger_content = f.read()

        required_functions = [
            "setup_logging",
            "get_logger",
            "log_request",
            "log_response",
            "log_error",
            "log_database_operation",
            "log_external_api_call",
        ]

        for func in required_functions:
            has_func = f"def {func}" in logger_content
            print(f"  {'✅' if has_func else '❌'} {func} function")
            all_files_exist &= has_func

    print(f"  {'✅' if all_files_exist else '❌'} Overall shared logging module")
    return all_files_exist


def check_documentation():
    """Check if logging documentation exists."""
    print("\n🔍 Checking documentation...")

    docs = [
        ("STANDARDIZED_LOGGING_GUIDE.md", "Logging guide"),
        ("test_standardized_logging.py", "Test script"),
    ]

    all_docs_exist = True
    for doc_file, description in docs:
        doc_path = os.path.join(os.path.dirname(__file__), doc_file)
        exists = os.path.exists(doc_path)
        print(f"  {'✅' if exists else '❌'} {description}: {doc_file}")
        all_docs_exist &= exists

    return all_docs_exist


def main():
    """Run the validation checks."""
    print("=" * 60)
    print("PPL Meta Platform - Logging Configuration Validation")
    print("=" * 60)

    base_path = os.path.dirname(__file__)

    # Services to check
    services = [
        ("ppl-meta-gateway", "Gateway Service"),
        ("ppl-meta-node", "Node Service"),
        ("ppl-meta-media", "Media Service"),
        ("ppl-meta-orchestrator", "Orchestrator Service"),
    ]

    # Check shared logging module
    shared_ok = check_shared_logging_module()

    # Check each service
    services_ok = []
    for service_dir, service_name in services:
        service_path = os.path.join(base_path, service_dir)
        if os.path.exists(service_path):
            service_ok = check_service_logging_config(service_path, service_name)
            services_ok.append(service_ok)
        else:
            print(f"\n🔍 Checking {service_name}...")
            print(f"  ❌ Service directory not found: {service_path}")
            services_ok.append(False)

    # Check documentation
    docs_ok = check_documentation()

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    print(f"Shared logging module: {'✅ PASS' if shared_ok else '❌ FAIL'}")

    for i, (service_dir, service_name) in enumerate(services):
        status = "✅ PASS" if services_ok[i] else "❌ FAIL"
        print(f"{service_name}: {status}")

    print(f"Documentation: {'✅ PASS' if docs_ok else '❌ FAIL'}")

    all_pass = shared_ok and all(services_ok) and docs_ok

    print(
        f"\nOverall status: {'✅ ALL CHECKS PASSED' if all_pass else '❌ SOME CHECKS FAILED'}"
    )

    if all_pass:
        print("\n🎉 Standardized logging is properly configured across all services!")
        print("\nNext steps:")
        print("1. Test logging with: python test_standardized_logging.py")
        print("2. Deploy services and verify log output")
        print("3. Set up log aggregation (ELK/Loki) for production")
    else:
        print(
            "\n❌ Some issues need to be resolved before logging is fully standardized."
        )
        print("Please fix the failing checks and run this script again.")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
