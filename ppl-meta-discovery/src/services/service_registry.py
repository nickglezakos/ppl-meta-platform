"""Service registry for backend services."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
from fastapi import HTTPException
from models import (
    DiscoveryQuery,
    HeartbeatRequest,
    RegistrationRequest,
    RegistrationResponse,
    ServiceInfo,
    ServiceList,
    ServiceStatus,
)

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Registry for managing backend services."""

    def __init__(self, heartbeat_timeout: int = 90):
        """Initialize the service registry.

        Args:
            heartbeat_timeout: Seconds after which service is stale
        """
        self._services: Dict[str, ServiceInfo] = {}
        self._heartbeat_timeout = heartbeat_timeout
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the service registry background tasks."""
        logger.info("Starting service registry")
        self._cleanup_task = asyncio.create_task(self._cleanup_stale_services())

    async def stop(self):
        """Stop the service registry background tasks."""
        logger.info("Stopping service registry")
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def register_service(
        self, request: RegistrationRequest
    ) -> RegistrationResponse:
        """Register a new service or update existing one.

        Args:
            request: Service registration request

        Returns:
            Registration response with service ID
        """
        # Generate deterministic UUID based on service name
        # This ensures the same service always gets the same UUID across restarts
        service_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, request.name))

        # Check if service with same name already exists
        existing_service = self._find_service_by_name(request.name)
        if existing_service:
            logger.info(f"Updating existing service: {request.name}")
            service_id = existing_service.service_id

        # Extract Tailscale IP from metadata if present (Phase 2: VPN-aware)
        tailscale_ip = request.metadata.get("tailscale_ip") if request.metadata else None

        # Create service info
        service_info = ServiceInfo(
            service_id=service_id,
            name=request.name,
            service_type=request.service_type,
            version=request.version,
            host=request.host,
            port=request.port,
            health_endpoint=request.health_endpoint,
            tailscale_ip=tailscale_ip,
            tailscale_port=request.port if tailscale_ip else None,
            capabilities=request.capabilities,
            metadata=request.metadata,
            status=ServiceStatus.REGISTERING,
            registered_at=datetime.utcnow(),
            last_seen=datetime.utcnow(),
        )

        # Store the service
        self._services[service_id] = service_info

        # Perform initial health check
        health_status = await self._check_service_health(service_info)
        service_info.status = health_status

        logger.info(
            f"Registered service {request.name} "
            f"({service_id}) with status {health_status}"
        )

        return RegistrationResponse(
            success=True,
            service_id=service_id,
            message=f"Service {request.name} registered successfully",
            heartbeat_interval=30,
        )

    async def update_heartbeat(self, request: HeartbeatRequest) -> Dict[str, str]:
        """Update service heartbeat.

        Args:
            request: Heartbeat request

        Returns:
            Status message

        Raises:
            HTTPException: If service not found
        """
        if not request.service_id:
            raise HTTPException(
                status_code=400, detail="service_id is required for service heartbeat"
            )

        service = self._services.get(request.service_id)
        if not service:
            raise HTTPException(
                status_code=404, detail=f"Service {request.service_id} not found"
            )

        # Update service information
        old_last_seen = service.last_seen
        service.last_seen = datetime.utcnow()
        service.heartbeat_count += 1
        service.status = request.status

        # Update metadata if provided
        if request.metadata:
            # Extract Tailscale IP from heartbeat metadata (Phase 2)
            if "tailscale_ip" in request.metadata:
                service.tailscale_ip = request.metadata["tailscale_ip"]
                service.tailscale_port = service.tailscale_port or service.port
            service.metadata.update(request.metadata)

        logger.info(
            f"💓 Updated heartbeat for service {service.name} ({request.service_id}): "
            f"old_last_seen={old_last_seen}, new_last_seen={service.last_seen}, "
            f"heartbeat_count={service.heartbeat_count}, status={service.status}"
        )

        return {"status": "heartbeat updated"}

    async def deregister_service(self, service_id: str) -> Dict[str, str]:
        """Deregister a service.

        Args:
            service_id: ID of service to deregister

        Returns:
            Status message

        Raises:
            HTTPException: If service not found
        """
        service = self._services.get(service_id)
        if not service:
            raise HTTPException(
                status_code=404, detail=f"Service {service_id} not found"
            )

        service.status = ServiceStatus.DEREGISTERING

        # Remove after short delay to allow for cleanup
        await asyncio.sleep(1)
        del self._services[service_id]

        logger.info(f"Deregistered service {service.name} ({service_id})")

        return {"status": "service deregistered"}

    def get_service(self, service_id: str) -> Optional[ServiceInfo]:
        """Get service by ID.

        Args:
            service_id: Service ID

        Returns:
            Service info if found, None otherwise
        """
        return self._services.get(service_id)

    def list_services(self, query: Optional[DiscoveryQuery] = None) -> ServiceList:
        """List services with optional filtering.

        Args:
            query: Optional discovery query for filtering

        Returns:
            Filtered list of services
        """
        services = list(self._services.values())

        # Apply filters if query provided
        if query:
            if query.service_type:
                services = [s for s in services if s.service_type == query.service_type]

            if query.service_name:
                services = [
                    s for s in services if query.service_name.lower() in s.name.lower()
                ]

            if query.status:
                services = [s for s in services if s.status == query.status]

            if query.capabilities:
                services = [
                    s
                    for s in services
                    if all(cap in s.capabilities for cap in query.capabilities)
                ]

        healthy_count = sum(1 for s in services if s.status == ServiceStatus.HEALTHY)

        return ServiceList(
            services=services,
            total_count=len(services),
            healthy_count=healthy_count,
        )

    def get_services_by_type(self, service_type: str) -> List[ServiceInfo]:
        """Get all services of a specific type.

        Args:
            service_type: Type of services to retrieve

        Returns:
            List of services of the specified type
        """
        return [
            service
            for service in self._services.values()
            if service.service_type == service_type
        ]

    def get_healthy_services(self) -> List[ServiceInfo]:
        """Get all healthy services.

        Returns:
            List of healthy services
        """
        return [
            service
            for service in self._services.values()
            if service.status == ServiceStatus.HEALTHY
        ]

    async def get_vpn_peers(
        self, matrix_group_id: Optional[str] = None
    ) -> List[ServiceInfo]:
        """Get VPN-addressable peers, optionally filtered by matrix group.
        
        Returns services that have a tailscale_ip set, meaning they
        are reachable via the VPN mesh.
        """
        results = []
        for svc in self._services.values():
            if svc.tailscale_ip and svc.status == ServiceStatus.HEALTHY:
                # Optionally filter by matrix group
                if matrix_group_id:
                    svc_matrix = svc.metadata.get("matrix_group_id", "")
                    if svc_matrix != matrix_group_id:
                        continue
                results.append(svc)
        # Sort by name for consistent output
        results.sort(key=lambda s: s.name)
        return results

    async def health_check_all(self) -> Dict[str, ServiceStatus]:
        """Perform health check on all registered services.

        Returns:
            Dictionary mapping service IDs to their health status
        """
        health_results = {}

        tasks = []
        for service_id, service in self._services.items():
            task = self._check_service_health_with_id(service_id, service)
            tasks.append(task)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, (service_id, _) in enumerate(self._services.items()):
                result = results[i]
                if isinstance(result, Exception):
                    health_results[service_id] = ServiceStatus.UNHEALTHY
                else:
                    health_results[service_id] = result

        return health_results

    def _find_service_by_name(self, name: str) -> Optional[ServiceInfo]:
        """Find service by name.

        Args:
            name: Service name to search for

        Returns:
            Service info if found, None otherwise
        """
        for service in self._services.values():
            if service.name == name:
                return service
        return None

    async def _check_service_health(self, service: ServiceInfo) -> ServiceStatus:
        """Check health of a single service.

        Args:
            service: Service to check

        Returns:
            Health status
        """
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(service.health_url) as response:
                    if response.status == 200:
                        return ServiceStatus.HEALTHY
                    else:
                        logger.warning(
                            f"Service {service.name} health check failed: "
                            f"HTTP {response.status}"
                        )
                        return ServiceStatus.UNHEALTHY
        except Exception as e:
            logger.warning(f"Service {service.name} health check failed: {e}")
            return ServiceStatus.UNHEALTHY

    async def _check_service_health_with_id(
        self, service_id: str, service: ServiceInfo
    ) -> ServiceStatus:
        """Check health of a service and update its status.

        Args:
            service_id: Service ID
            service: Service to check

        Returns:
            Health status
        """
        status = await self._check_service_health(service)
        service.status = status
        return status

    async def _cleanup_stale_services(self):
        """Background task to cleanup stale services."""
        logger.info("Starting service cleanup task")

        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                current_time = datetime.utcnow()
                stale_services = []

                for service_id, service in self._services.items():
                    time_since_last_seen = (
                        current_time - service.last_seen
                    ).total_seconds()

                    if time_since_last_seen > self._heartbeat_timeout:
                        stale_services.append((service_id, service))
                        logger.warning(
                            f"Service {service.name} ({service_id}) is stale "
                            f"(last seen {time_since_last_seen:.0f}s ago)"
                        )

                # Remove stale services
                for service_id, service in stale_services:
                    # Mark as unhealthy first
                    service.status = ServiceStatus.UNHEALTHY

                    # Try to perform final health check
                    try:
                        health_status = await self._check_service_health(service)
                        if health_status == ServiceStatus.HEALTHY:
                            # Service is actually healthy, update last_seen
                            service.last_seen = current_time
                            service.status = ServiceStatus.HEALTHY
                            logger.info(
                                f"Service {service.name} ({service_id}) recovered"
                            )
                            continue
                    except Exception:
                        pass

                    # Remove the stale service
                    try:
                        del self._services[service_id]
                        logger.info(
                            f"Removed stale service {service.name} ({service_id})"
                        )
                    except KeyError:
                        pass  # Service already removed

                # Log registry status
                if len(self._services) > 0:
                    healthy_count = len(
                        [
                            s
                            for s in self._services.values()
                            if s.status == ServiceStatus.HEALTHY
                        ]
                    )
                    logger.debug(
                        f"Service registry status: {len(self._services)} total, "
                        f"{healthy_count} healthy"
                    )

            except asyncio.CancelledError:
                logger.info("Service cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in service cleanup task: {e}")
                # Continue running despite errors

    async def force_cleanup_service(self, service_id: str) -> bool:
        """Force cleanup of a specific service.

        Args:
            service_id: ID of service to cleanup

        Returns:
            True if service was removed, False if not found
        """
        if service_id in self._services:
            service = self._services[service_id]
            del self._services[service_id]
            logger.info(f"Force removed service {service.name} ({service_id})")
            return True
        return False

    async def cleanup_by_status(self, status: ServiceStatus) -> int:
        """Remove all services with a specific status.

        Args:
            status: Status of services to remove

        Returns:
            Number of services removed
        """
        services_to_remove = [
            (service_id, service)
            for service_id, service in self._services.items()
            if service.status == status
        ]

        count = 0
        for service_id, service in services_to_remove:
            try:
                del self._services[service_id]
                logger.info(f"Removed {status} service {service.name} ({service_id})")
                count += 1
            except KeyError:
                pass

        return count

    async def batch_health_check(self) -> Dict[str, Dict]:
        """Perform batch health check and cleanup.

        Returns:
            Dictionary with health check results and cleanup actions
        """
        logger.info("Starting batch health check")

        results = {
            "checked": 0,
            "healthy": 0,
            "unhealthy": 0,
            "removed": 0,
            "services": {},
        }

        current_time = datetime.utcnow()
        services_to_check = list(self._services.items())

        for service_id, service in services_to_check:
            results["checked"] += 1

            try:
                # Check if service is too stale
                time_since_last_seen = (
                    current_time - service.last_seen
                ).total_seconds()

                if time_since_last_seen > self._heartbeat_timeout * 2:
                    # Remove very stale services immediately
                    del self._services[service_id]
                    results["removed"] += 1
                    results["services"][service_id] = {
                        "name": service.name,
                        "action": "removed_stale",
                        "last_seen_ago": time_since_last_seen,
                    }
                    continue

                # Perform health check
                health_status = await self._check_service_health(service)
                service.status = health_status

                if health_status == ServiceStatus.HEALTHY:
                    service.last_seen = current_time
                    results["healthy"] += 1
                    results["services"][service_id] = {
                        "name": service.name,
                        "action": "healthy",
                        "status": "healthy",
                    }
                else:
                    results["unhealthy"] += 1
                    results["services"][service_id] = {
                        "name": service.name,
                        "action": "marked_unhealthy",
                        "status": "unhealthy",
                    }

            except Exception as e:
                logger.error(f"Health check failed for {service.name}: {e}")
                service.status = ServiceStatus.UNHEALTHY
                results["unhealthy"] += 1
                results["services"][service_id] = {
                    "name": service.name,
                    "action": "health_check_failed",
                    "error": str(e),
                }

        logger.info(
            f"Batch health check complete: {results['checked']} checked, "
            f"{results['healthy']} healthy, {results['unhealthy']} unhealthy, "
            f"{results['removed']} removed"
        )

        return results
