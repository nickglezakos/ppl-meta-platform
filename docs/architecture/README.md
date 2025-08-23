# Architecture Documentation

## 📋 Overview

This directory contains technical architecture documents and system design specifications for the PPL Meta Platform.

## 📁 Directory Structure

### **Microservices** (`microservices/`)

Complete microservices architecture documentation:

- `ENHANCED_MICROSERVICES_ARCHITECTURE.md` - Comprehensive microservices architecture with service categorization, overlap prevention, and deployment strategies

### **Network Discovery** (`network-discovery/`)

Network discovery system architecture and implementation:

- `MICROSERVICES_NETWORK_DISCOVERY_ARCHITECTURE.md` - Core network discovery system architecture
- `NETWORK_DISCOVERY_IMPLEMENTATION_PLAN.md` - Detailed implementation planning document
- `NETWORK_DISCOVERY_IMPLEMENTATION_COMPLETE.md` - Completed implementation details and outcomes
- `PPL_META_NETWORK_DISCOVERY.md` - Foundational network discovery documentation

## 🎯 Key Architectural Principles

### Service Organization

- **Frontend Services**: Flutter web, desktop, and mobile applications
- **Backend Services**: Core platform microservices (Node, Gateway, Media, etc.)
- **Edge Services**: Raspberry Pi and edge device optimized services

### Network Discovery Architecture

- **Backend Discovery Service**: Centralized network discovery coordination
- **Edge VPN Service**: Edge device VPN client functionality
- **Frontend Discovery Enhancement**: Enhanced user interface for network management

### Communication Patterns

- **Service-to-Service**: Internal microservice communication via APIs
- **Frontend-to-Backend**: RESTful APIs with real-time updates
- **Edge-to-Platform**: Secure VPN tunneling and API communication

## 🚀 Implementation Status

### Completed

- ✅ Enhanced Microservices Architecture
- ✅ Network Discovery Implementation
- ✅ Service categorization and overlap prevention
- ✅ Communication pattern definitions

### In Progress

- 🔄 Backend Discovery Service development
- 🔄 Edge VPN Service implementation
- 🔄 Frontend discovery enhancement

### Planned

- 📋 Public services architecture (SaaS components)
- 📋 Scalability optimization
- 📋 Performance monitoring integration

## 📞 Related Documentation

- **Development**: See `../development/` for implementation guides
- **Deployment**: See `../deployment/` for deployment configurations
- **API**: See `../api/` for service interface specifications

## 🔄 Maintenance

This documentation is updated as part of the development process. Major architectural changes require:

1. Architecture review and approval
2. Documentation updates
3. Implementation guide updates
4. Deployment procedure updates

**Last Updated**: August 2025
**Maintained by**: PPL Meta Architecture Team
