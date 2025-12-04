"""Services API routes for PPL Meta Discovery Service."""

import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from models import (
    DiscoveryQuery,
    HeartbeatRequest,
    RegistrationRequest,
    RegistrationResponse,
    ServiceInfo,
    ServiceList,
)
from services.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/services", tags=["services"])


def get_service_registry() -> ServiceRegistry:
    """Dependency to get service registry instance."""
    # This will be properly injected in main.py
    from src.main import app

    return app.state.service_registry


@router.post("/register", response_model=RegistrationResponse)
async def register_service(
    request: RegistrationRequest,
    service_registry: ServiceRegistry = Depends(get_service_registry),
) -> RegistrationResponse:
    """Register a new backend service."""
    return await service_registry.register_service(request)


@router.post("/heartbeat")
async def service_heartbeat(
    request: HeartbeatRequest,
    service_registry: ServiceRegistry = Depends(get_service_registry),
) -> Dict[str, str]:
    """Update service heartbeat."""
    try:
        logger.info(f"📨 Received heartbeat request: service_id={request.service_id}, status={request.status}")
        result = await service_registry.update_heartbeat(request)
        logger.debug(f"✅ Heartbeat processed successfully for {request.service_id}")
        return result
    except Exception as e:
        logger.error(f"❌ Heartbeat failed for {request.service_id}: {e}", exc_info=True)
        raise


@router.delete("/deregister/{service_id}")
async def deregister_service(
    service_id: str,
    service_registry: ServiceRegistry = Depends(get_service_registry),
) -> Dict[str, str]:
    """Deregister a service."""
    return await service_registry.deregister_service(service_id)


@router.get("/", response_model=ServiceList)
async def list_services(
    service_type: str = Query(None, description="Filter by service type"),
    service_name: str = Query(None, description="Filter by service name"),
    status: str = Query(None, description="Filter by status"),
    capabilities: List[str] = Query(None, description="Required capabilities"),
    service_registry: ServiceRegistry = Depends(get_service_registry),
) -> ServiceList:
    """List all registered services with optional filtering."""

    # Build discovery query
    query = DiscoveryQuery()
    if service_type:
        query.service_type = service_type
    if service_name:
        query.service_name = service_name
    if status:
        query.status = status
    if capabilities:
        query.capabilities = capabilities

    return service_registry.list_services(query)


@router.get("/{service_id}", response_model=ServiceInfo)
async def get_service(
    service_id: str,
    service_registry: ServiceRegistry = Depends(get_service_registry),
) -> ServiceInfo:
    """Get specific service by ID."""
    service = service_registry.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service {service_id} not found")
    return service


@router.get("/health/check")
async def health_check_all_services(
    service_registry: ServiceRegistry = Depends(get_service_registry),
) -> Dict[str, str]:
    """Perform health check on all registered services."""
    health_results = await service_registry.health_check_all()
    return {service_id: status.value for service_id, status in health_results.items()}
