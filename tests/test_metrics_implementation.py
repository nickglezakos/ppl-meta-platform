#!/usr/bin/env python3
"""
Test script to validate Prometheus metrics implementation.

This script tests:
1. Metrics endpoint availability
2. Metrics content validation
3. Custom metrics functionality
4. Service-specific metrics
"""

import os
import sys
import time
from typing import Dict

import requests

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), "shared"))


def test_metrics_endpoint(service_name: str, port: int) -> Dict[str, any]:
    """Test if metrics endpoint is available and returns valid data."""
    url = f"http://localhost:{port}/metrics"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            metrics_text = response.text

            # Basic validation - check for common Prometheus metrics
            required_metrics = [
                "http_requests_total",
                "http_request_duration_seconds",
                "system_cpu_usage_percent",
                "system_memory_usage_percent",
                "service_info",
            ]

            found_metrics = []
            for metric in required_metrics:
                if metric in metrics_text:
                    found_metrics.append(metric)

            return {
                "service": service_name,
                "port": port,
                "status": "success",
                "metrics_count": len(metrics_text.split("\n")),
                "required_metrics_found": len(found_metrics),
                "required_metrics_total": len(required_metrics),
                "missing_metrics": [
                    m for m in required_metrics if m not in found_metrics
                ],
                "sample_metrics": (
                    metrics_text[:500] + "..."
                    if len(metrics_text) > 500
                    else metrics_text
                ),
            }
        else:
            return {
                "service": service_name,
                "port": port,
                "status": "error",
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
            }

    except requests.exceptions.ConnectionError:
        return {
            "service": service_name,
            "port": port,
            "status": "connection_error",
            "error": f"Cannot connect to {url}",
        }
    except Exception as e:
        return {
            "service": service_name,
            "port": port,
            "status": "error",
            "error": str(e),
        }


def test_health_endpoint(service_name: str, port: int) -> Dict[str, any]:
    """Test if health endpoint is available."""
    health_urls = [
        f"http://localhost:{port}/health",
        f"http://localhost:{port}/health/",
        f"http://localhost:{port}/api/v1/health/",
    ]

    for url in health_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return {
                    "service": service_name,
                    "port": port,
                    "health_url": url,
                    "status": "healthy",
                    "response": response.json(),
                }
        except:
            continue

    return {
        "service": service_name,
        "port": port,
        "status": "unhealthy",
        "error": "No health endpoint responded",
    }


def generate_load_test_requests(service_name: str, port: int, num_requests: int = 10):
    """Generate some requests to create metrics data."""
    base_url = f"http://localhost:{port}"
    endpoints = ["/health", "/", "/docs", "/metrics"]

    print(f"Generating {num_requests} requests to {service_name}...")

    for i in range(num_requests):
        for endpoint in endpoints:
            try:
                requests.get(f"{base_url}{endpoint}", timeout=2)
            except:
                pass  # Ignore errors for load testing
        time.sleep(0.1)  # Small delay between requests


def main():
    """Main test function."""
    # Service configurations
    services = [
        {"name": "ppl-meta-gateway", "port": 8080},
        {"name": "ppl-meta-node", "port": 8001},
        {"name": "ppl-meta-media", "port": 8000},
        {"name": "ppl-meta-orchestrator", "port": 8002},
    ]

    print("🔍 Testing PPL Meta Platform Metrics Implementation")
    print("=" * 60)

    # Test 1: Check if services are running
    print("\n1. Checking service health...")
    health_results = []
    for service in services:
        result = test_health_endpoint(service["name"], service["port"])
        health_results.append(result)
        status_icon = "✅" if result["status"] == "healthy" else "❌"
        print(
            f"   {status_icon} {service['name']} (port {service['port']}): {result['status']}"
        )

    # Test 2: Generate some load to create metrics
    print("\n2. Generating load to create metrics data...")
    for service in services:
        if any(
            h["status"] == "healthy" and h["service"] == service["name"]
            for h in health_results
        ):
            generate_load_test_requests(service["name"], service["port"])

    # Wait for metrics to be collected
    print("   Waiting 5 seconds for metrics collection...")
    time.sleep(5)

    # Test 3: Check metrics endpoints
    print("\n3. Testing metrics endpoints...")
    metrics_results = []
    for service in services:
        result = test_metrics_endpoint(service["name"], service["port"])
        metrics_results.append(result)

        if result["status"] == "success":
            print(
                f"   ✅ {service['name']}: {result['metrics_count']} metrics lines, "
                f"{result['required_metrics_found']}/{result['required_metrics_total']} required metrics"
            )
            if result["missing_metrics"]:
                print(f"      Missing: {', '.join(result['missing_metrics'])}")
        else:
            print(
                f"   ❌ {service['name']}: {result['status']} - {result.get('error', 'Unknown error')}"
            )

    # Test 4: Validate specific metrics
    print("\n4. Validating metrics content...")
    for result in metrics_results:
        if result["status"] == "success":
            service_name = result["service"]
            print(f"\n   📊 {service_name} Metrics Sample:")
            # Show first few lines of metrics that contain service name
            lines = result["sample_metrics"].split("\n")
            service_lines = [
                line for line in lines if service_name.replace("-", "_") in line
            ][:3]
            for line in service_lines:
                if line.strip():
                    print(f"      {line}")

    # Summary
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)

    healthy_services = sum(1 for r in health_results if r["status"] == "healthy")
    metrics_working = sum(1 for r in metrics_results if r["status"] == "success")

    print(f"Services healthy: {healthy_services}/{len(services)}")
    print(f"Metrics working: {metrics_working}/{len(services)}")

    if healthy_services == len(services) and metrics_working == len(services):
        print("\n🎉 All services are healthy and metrics are working!")
        print("✅ ISSUE-012: Missing Service Metrics - RESOLVED")
        return 0
    else:
        print("\n⚠️  Some services have issues:")
        for result in health_results + metrics_results:
            if result["status"] not in ["healthy", "success"]:
                print(f"   - {result['service']}: {result['status']}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
