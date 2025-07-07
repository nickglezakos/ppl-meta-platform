#!/usr/bin/env python3
"""
Test script for standardized logging configuration.

This script tests the shared logging module across all services
to ensure consistent behavior and formatting.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from shared.logging import (
    LogFormat,
    LogLevel,
    get_logger,
    log_database_operation,
    log_error,
    log_external_api_call,
    log_request,
    log_response,
    setup_logging,
)


def test_console_logging():
    """Test console logging format."""
    print("=" * 60)
    print("Testing Console Logging Format")
    print("=" * 60)

    # Setup console logging
    logger = setup_logging(
        service_name="test-service-console",
        log_level=LogLevel.INFO,
        log_format=LogFormat.CONSOLE,
    )

    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    # Test structured data
    logger.info("User login attempt", user_id="12345", ip_address="192.168.1.1")

    # Test helper functions
    log_request(logger, "req-123", "GET", "/api/users", user_id="12345")
    log_response(logger, "req-123", 200, 45.2)

    try:
        raise ValueError("Test exception")
    except Exception as e:
        log_error(logger, e, {"context": "test_function"})

    log_database_operation(logger, "SELECT", "users", duration_ms=12.5, affected_rows=5)
    log_external_api_call(logger, "auth-service", "/validate", "POST", 200, 150.0)

    print("\n")


def test_json_logging():
    """Test JSON logging format."""
    print("=" * 60)
    print("Testing JSON Logging Format")
    print("=" * 60)

    # Create temporary log file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
        log_file = f.name

    try:
        # Setup JSON logging with file output
        logger = setup_logging(
            service_name="test-service-json",
            log_level=LogLevel.INFO,
            log_format=LogFormat.JSON,
            log_file=log_file,
        )

        # Test different log levels
        logger.info("Testing JSON format", test_data={"key": "value", "number": 123})
        logger.warning("This is a warning", alert_level="medium")
        logger.error("Error occurred", error_code=500, module="authentication")

        # Test helper functions
        log_request(logger, "req-456", "POST", "/api/auth/login", user_id="67890")
        log_response(logger, "req-456", 201, 89.7)

        log_database_operation(
            logger, "INSERT", "user_sessions", duration_ms=25.3, affected_rows=1
        )

        # Read and validate JSON log file
        print("Log file contents:")
        with open(log_file, "r") as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        log_entry = json.loads(line.strip())
                        print(
                            f"Line {line_num}: Valid JSON - {log_entry.get('message', 'No message')}"
                        )

                        # Validate required fields
                        required_fields = [
                            "timestamp",
                            "level",
                            "logger",
                            "message",
                            "service",
                        ]
                        missing_fields = [
                            field for field in required_fields if field not in log_entry
                        ]
                        if missing_fields:
                            print(f"  WARNING: Missing fields: {missing_fields}")
                        else:
                            print(f"  ✓ All required fields present")

                    except json.JSONDecodeError as e:
                        print(f"Line {line_num}: Invalid JSON - {e}")

    finally:
        # Cleanup
        if os.path.exists(log_file):
            os.unlink(log_file)

    print("\n")


def test_service_configurations():
    """Test logging configurations for each service."""
    print("=" * 60)
    print("Testing Service-Specific Configurations")
    print("=" * 60)

    services = [
        {"name": "ppl-meta-gateway", "log_level": "INFO", "log_format": "json"},
        {"name": "ppl-meta-node", "log_level": "DEBUG", "log_format": "console"},
        {"name": "ppl-meta-media", "log_level": "WARNING", "log_format": "json"},
        {"name": "ppl-meta-orchestrator", "log_level": "INFO", "log_format": "console"},
    ]

    for service_config in services:
        print(f"Testing {service_config['name']}...")

        # Set environment variables to simulate service environment
        os.environ["APP_NAME"] = service_config["name"]
        os.environ["APP_VERSION"] = "1.0.0-test"
        os.environ["ENVIRONMENT"] = "testing"

        logger = setup_logging(
            service_name=service_config["name"],
            log_level=service_config["log_level"],
            log_format=service_config["log_format"],
            extra_context={"deployment": "test", "region": "us-east-1"},
        )

        logger.info(
            "Service logging test",
            test_case="service_configuration",
            expected_level=service_config["log_level"],
            expected_format=service_config["log_format"],
        )

        print(f"  ✓ {service_config['name']} logging configured successfully")

    print("\n")


def test_log_levels():
    """Test different log level configurations."""
    print("=" * 60)
    print("Testing Log Level Filtering")
    print("=" * 60)

    # Test with WARNING level
    print("Setting log level to WARNING...")
    logger = setup_logging(
        service_name="test-service-levels",
        log_level=LogLevel.WARNING,
        log_format=LogFormat.CONSOLE,
    )

    print("Attempting to log at different levels:")
    logger.debug("This DEBUG message should NOT appear")
    logger.info("This INFO message should NOT appear")
    logger.warning("This WARNING message SHOULD appear")
    logger.error("This ERROR message SHOULD appear")
    logger.critical("This CRITICAL message SHOULD appear")

    print("\n")


def main():
    """Run all logging tests."""
    print("PPL Meta Platform - Standardized Logging Test Suite")
    print("=" * 60)
    print()

    test_console_logging()
    test_json_logging()
    test_service_configurations()
    test_log_levels()

    print("=" * 60)
    print("Logging tests completed!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Verify that logs appear consistently across all services")
    print("2. Check that JSON logs are properly structured for log aggregation")
    print("3. Confirm that log levels are respected in all environments")
    print("4. Test log file rotation and cleanup in production")


if __name__ == "__main__":
    main()
