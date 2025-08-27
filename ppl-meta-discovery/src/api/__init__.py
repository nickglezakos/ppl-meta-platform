"""API package for PPL Meta Discovery Service."""

from .health import router as health_router
from .services import router as services_router
from .devices import router as devices_router

__all__ = [
    "health_router",
    "services_router", 
    "devices_router",
]
