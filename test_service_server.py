#!/usr/bin/env python3
"""
Simple test service to validate service discovery
"""

import asyncio
import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.service_discovery import ServiceDiscoveryClient

app = FastAPI(title="Test Service Discovery", version="1.0.0")

# Global service discovery client
service_discovery_client = None


@app.on_event("startup")
async def startup_event():
    """Register with service discovery on startup."""
    global service_discovery_client

    try:
        service_discovery_client = ServiceDiscoveryClient(
            consul_enabled=True, consul_host="localhost", consul_port=8500
        )

        # Register this test service
        success = await service_discovery_client.register_service(
            service_name="test-discovery-service",
            host="127.0.0.1",
            port=8888,
            health_endpoint="/health",
            tags=["test", "discovery"],
            metadata={"version": "1.0.0", "environment": "test"},
        )

        if success:
            print("✅ Test service registered with Consul successfully!")
        else:
            print("❌ Failed to register test service with Consul")

        # Start health monitoring
        await service_discovery_client.start_health_monitoring()
        print("✅ Health monitoring started")

    except Exception as e:
        print(f"❌ Startup error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Deregister from service discovery on shutdown."""
    global service_discovery_client

    if service_discovery_client:
        try:
            await service_discovery_client.deregister_service(
                "test-discovery-service", "127.0.0.1", 8888
            )
            print("✅ Test service deregistered from Consul")
        except Exception as e:
            print(f"❌ Shutdown error: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint for Consul."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "test-discovery-service",
            "version": "1.0.0",
        },
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Test Service Discovery",
        "status": "running",
        "consul_enabled": (
            service_discovery_client.consul_enabled
            if service_discovery_client
            else False
        ),
    }


@app.get("/discover/{service_name}")
async def discover_service(service_name: str):
    """Test service discovery by looking up another service."""
    global service_discovery_client

    if not service_discovery_client:
        return {"error": "Service discovery not initialized"}

    try:
        service_url = await service_discovery_client.get_service_url(service_name)
        if service_url:
            return {
                "service_name": service_name,
                "service_url": service_url,
                "status": "found",
            }
        else:
            return {
                "service_name": service_name,
                "service_url": None,
                "status": "not_found",
            }
    except Exception as e:
        return {"service_name": service_name, "error": str(e), "status": "error"}


if __name__ == "__main__":
    print("🚀 Starting Test Service Discovery Server on port 8888")
    print("📍 Health endpoint: http://localhost:8888/health")
    print("🔍 Discovery endpoint: http://localhost:8888/discover/{service_name}")
    print("⭐ Root: http://localhost:8888/")

    uvicorn.run(app, host="127.0.0.1", port=8888, log_level="info")
