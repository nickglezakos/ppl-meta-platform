"""
Service Discovery for API Gateway
"""
from typing import Dict, List, Optional
import structlog

logger = structlog.get_logger()


class ServiceRegistry:
    """Service registry for managing microservice endpoints."""
    
    def __init__(self):
        self.services: Dict[str, Dict] = {}
        logger.info("Service registry initialized")
    
    async def register_service(
        self, 
        service_name: str, 
        host: str, 
        port: int, 
        health_endpoint: str = "/health"
    ) -> None:
        """Register a service with the registry."""
        self.services[service_name] = {
            "host": host,
            "port": port,
            "health_endpoint": health_endpoint,
            "url": f"http://{host}:{port}"
        }
        logger.info(
            "Service registered",
            service=service_name,
            host=host,
            port=port
        )
    
    async def deregister_service(self, service_name: str) -> None:
        """Deregister a service from the registry."""
        if service_name in self.services:
            del self.services[service_name]
            logger.info("Service deregistered", service=service_name)
    
    async def get_service(self, service_name: str) -> Optional[Dict]:
        """Get service information by name."""
        return self.services.get(service_name)
    
    async def list_services(self) -> List[str]:
        """List all registered service names."""
        return list(self.services.keys())
    
    async def health_check_service(self, service_name: str) -> bool:
        """Check if a service is healthy."""
        # Basic implementation - can be enhanced with actual health checks
        service = await self.get_service(service_name)
        return service is not None


# Global service registry instance
service_registry = ServiceRegistry()
