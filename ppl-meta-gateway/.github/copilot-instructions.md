# Copilot Instructions for PPL Meta Gateway

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Project Context
This is a Python FastAPI-based API Gateway microservice that serves as the central entry point for the PPL Meta microservices ecosystem. The gateway handles:

1. **Request Routing**: Routes incoming requests to appropriate microservices (ppl-meta-node, ppl-meta-media, etc.)
2. **Authentication & Authorization**: Validates JWT tokens and manages user permissions
3. **Load Balancing**: Distributes load across multiple service instances
4. **Service Discovery**: Dynamically discovers and routes to available services
5. **Nginx Configuration**: Manages dynamic nginx configuration updates
6. **Mesh VPN Integration**: Supports secure communication with edge/local services via mesh VPN

## Architecture Guidelines
- Follow microservices patterns with clear separation of concerns
- Use FastAPI for high-performance async operations
- Implement proper error handling and logging
- Support both cloud and edge deployments
- Maintain compatibility with existing ppl-meta-node and ppl-meta-media services

## Code Style
- Use Python 3.9+ features
- Follow PEP 8 guidelines
- Use type hints throughout
- Implement comprehensive error handling
- Add detailed docstrings for all public methods
- Use Pydantic models for request/response validation

## Dependencies
- FastAPI for the web framework
- Uvicorn for ASGI server
- Pydantic for data validation
- Httpx for async HTTP client operations
- Python-jose for JWT handling
- Redis for caching and service discovery
- Nginx python bindings for configuration management
