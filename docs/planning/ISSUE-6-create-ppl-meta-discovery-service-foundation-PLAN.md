# Create PPL Meta Discovery Service Foundation - Planning Document

**Status**: Planning  
**Issue**: [#ISSUE_NUMBER](https://github.com/nickglezakos/ppl-meta-platform/issues/ISSUE_NUMBER)  
**Project**: [PPL Meta Platform](https://github.com/users/nickglezakos/projects/1)  
**Created**: 2025-08-27  
**Last Updated**: 2025-08-27  
**Project**: https://github.com/users/nickglezakos/projects/1
Location**: planning/ → current/ → [final_category]/

---

## � GitHub Issue Sync Status

> **Last Synced**: 2025-08-27 - [STATUS]  
> **Sync Notes**: [Any notes about what changed during last sync]

### Quick Copy-Paste for GitHub Issue:

```markdown
# Create PPL Meta Discovery Service Foundation

## 📋 Problem Statement

The PPL Meta platform currently lacks a centralized network discovery service, leading to scattered discovery logic across mobile apps and backend services. This creates reliability issues across the 16 documented network scenarios (local WiFi, hotspot, Tailscale VPN, OpenVPN, corporate networks) and makes it difficult to maintain consistent service discovery behavior.

## 🎯 Objectives

- [ ] Create centralized `ppl-meta-discovery` service (Port 8006) as the foundation for network discovery
- [ ] Implement service registry for backend microservices with health monitoring  
- [ ] Establish edge device registry for mobile cameras and Raspberry Pi devices
- [ ] Provide unified discovery API endpoints for all platform services and clients

## 🏗️ Implementation Plan

### Phase 1: Foundation Setup (3-4 days)
- [x] Create `ppl-meta-discovery` directory structure with FastAPI foundation
- [x] Set up basic service with health endpoint on port 8006
- [x] Implement core service registry data structures and storage
- [x] Add basic REST API endpoints for service registration and discovery
- [ ] Create Docker configuration and deployment scripts

### Phase 2: Core Implementation (4-5 days)  
- [ ] Implement service registry with automatic health monitoring
- [ ] Add edge device registry for mobile cameras and Raspberry Pi devices
- [ ] Create multicast announcement system (224.1.1.1:12345)
- [ ] Implement discovery API endpoints with complete platform topology
- [ ] Add service deregistration and cleanup logic

### Phase 3: Integration & Polish (2-3 days)
- [ ] Update all existing backend services to register with discovery service
- [ ] Add discovery service to VS Code tasks and deployment workflows
- [ ] Implement comprehensive error handling and logging
- [ ] Add configuration management for different environments
- [ ] Create basic monitoring and health check integration

## 🎯 Success Criteria

- [ ] Discovery service successfully registers and tracks all 6 existing backend services
- [ ] Service provides REST API endpoints for service discovery and registration  
- [ ] Foundation supports all documented network scenarios without client-side complexity
- [ ] Service integrates with existing VS Code tasks and deployment workflows

## 📅 Timeline

**Target Completion**: 2025-09-06 (10 days)
- Foundation Setup: 2025-08-30
- Core Implementation: 2025-09-04  
- Integration Complete: 2025-09-06

## 🔧 Technical Details

- **Service**: `ppl-meta-discovery` (Port 8006)
- **Technology**: Python/FastAPI (consistent with existing backend services)
- **Integration**: Registry for all 6 backend services + edge devices
- **Foundation**: Supports all 16 documented network discovery scenarios
```

---

## �🔗 Project Integration

- **GitHub Issue**: [#ISSUE_NUMBER](https://github.com/nickglezakos/ppl-meta-platform/issues/ISSUE_NUMBER)
- **Project Board**: [Project Card](https://github.com/users/nickglezakos/projects/1) - Move to "📋 Planned"
- **Repository**: [ppl-meta-platform](https://github.com/nickglezakos/ppl-meta-platform)
- **Related PRs**: _Will be added during development_
- **Dependencies**: _List any blocking issues_

## 📋 Issue Overview

### Problem Statement

The PPL Meta platform currently lacks a centralized network discovery service, leading to scattered discovery logic across mobile apps and backend services. This creates reliability issues across the 16 documented network scenarios (local WiFi, hotspot, Tailscale VPN, OpenVPN, corporate networks) and makes it difficult to maintain consistent service discovery behavior. The existing architecture requires each client to implement complex discovery algorithms, resulting in code duplication and inconsistent behavior across different network configurations.

### Objectives

- [ ] Create centralized `ppl-meta-discovery` service (Port 8006) as the foundation for network discovery
- [ ] Implement service registry for backend microservices with health monitoring
- [ ] Establish edge device registry for mobile cameras and Raspberry Pi devices
- [ ] Provide unified discovery API endpoints for all platform services and clients

### Success Criteria

- [ ] Discovery service successfully registers and tracks all 6 existing backend services
- [ ] Service provides REST API endpoints for service discovery and registration
- [ ] Foundation supports all documented network scenarios without client-side complexity
- [ ] Service integrates with existing VS Code tasks and deployment workflows

## 🎯 Proposed Solution

### High-Level Approach

Create a new microservice `ppl-meta-discovery` that serves as the central coordination point for all network discovery operations. This service will implement a dual registry system: one for backend platform services and another for edge devices (mobile cameras, Raspberry Pi). The service will provide REST API endpoints for registration, discovery, and health monitoring while supporting all 16 documented network scenarios through flexible discovery methods.

### Technical Strategy

- **Architecture Changes**: Add new discovery service as 7th backend microservice, modify existing services to register with discovery service
- **New Components**: Discovery service with FastAPI, service registry module, edge device registry, multicast announcements, discovery API endpoints
- **Modified Components**: All existing backend services (node, gateway, media, orchestrator, vision, cameras) to include discovery registration
- **Integration Points**: Service registry integrates with existing health check endpoints, discovery APIs consumed by mobile apps and frontend clients

### Alternative Approaches Considered

1. **Distributed Discovery**: Keep discovery logic in each service/client
   - *Rejected*: Leads to code duplication and inconsistent behavior across network scenarios
2. **Gateway-Based Discovery**: Extend existing gateway service with discovery capabilities  
   - *Rejected*: Would overload gateway service and create tight coupling with discovery logic

## 🏗️ Implementation Plan

### Phase 1: Foundation Setup

**Estimated Duration**: 3-4 days

- [ ] Create `ppl-meta-discovery` directory structure with FastAPI foundation
- [ ] Set up basic service with health endpoint on port 8006  
- [ ] Implement core service registry data structures and storage
- [ ] Add basic REST API endpoints for service registration and discovery
- [ ] Create Docker configuration and deployment scripts

### Phase 2: Core Implementation

**Estimated Duration**: 4-5 days

- [ ] Implement service registry with automatic health monitoring
- [ ] Add edge device registry for mobile cameras and Raspberry Pi devices
- [ ] Create multicast announcement system (224.1.1.1:12345)
- [ ] Implement discovery API endpoints with complete platform topology
- [ ] Add service deregistration and cleanup logic

### Phase 3: Integration & Polish

**Estimated Duration**: 2-3 days

- [ ] Update all existing backend services to register with discovery service
- [ ] Add discovery service to VS Code tasks and deployment workflows
- [ ] Implement comprehensive error handling and logging
- [ ] Add configuration management for different environments
- [ ] Create basic monitoring and health check integration

## 🧪 Testing Strategy

### Unit Testing

- [ ] Test coverage requirements: 85%+ for core discovery logic
- [ ] Critical paths identified: service registration, health monitoring, discovery API endpoints
- [ ] Mock strategies defined: Mock backend services, edge devices, network interfaces for isolated testing

### Integration Testing

- [ ] Integration test scenarios defined: Discovery service + existing backend services registration workflow
- [ ] End-to-end test cases planned: Complete service discovery flow from mobile app through discovery service to backend services
- [ ] Performance benchmarks established: <100ms discovery response time, support for 50+ concurrent registrations

### Manual Testing

- [ ] User acceptance criteria defined: Discovery service accessible via REST API, successful registration of all 6 backend services
- [ ] Edge case scenarios identified: Service crashes, network disconnections, duplicate registrations, port conflicts
- [ ] Platform testing planned: Test across Docker, local development, and deployment scenarios

## 📚 Documentation Requirements

### Technical Documentation

- [ ] API documentation updates: OpenAPI/Swagger spec for discovery service endpoints
- [ ] Architecture diagrams: Updated microservices architecture including discovery service integration
- [ ] Database schema changes: Service registry and edge device registry data models  
- [ ] Configuration changes: Environment variables, port configuration, deployment settings

### User Documentation

- [ ] Developer guide updates: How to register services with discovery service
- [ ] Integration tutorials: Connecting mobile apps and frontend clients to discovery service
- [ ] Troubleshooting guide: Common discovery service issues and network diagnostics
- [ ] Migration guides: Updating existing services to use centralized discovery

## ⚠️ Risks and Mitigation

### Technical Risks

- **Port Conflict Risk**: Port 8006 may conflict with existing services in some environments
  - _Mitigation_: Implement flexible port configuration with environment variables and auto-detection
- **Service Discovery Circular Dependency**: Discovery service needs to be discoverable itself
  - _Mitigation_: Use well-known port 8006 and multicast announcements for discovery service location

### Project Risks

- **Integration Complexity**: Updating all 6 existing services to register with discovery service
  - _Mitigation_: Implement backward compatibility and gradual rollout approach
- **Performance Impact**: Additional network calls for service registration and discovery
  - _Mitigation_: Implement local caching and efficient registry data structures

## 🔄 Dependencies

### Blocking Dependencies

- [ ] None - This is a foundation service that other services will depend on
- [ ] Docker configuration and deployment infrastructure must be available

### Related Work

- [ ] ISSUE-007: Create Discovery API Endpoints (will build on this foundation)
- [ ] ISSUE-009: Integrate with Existing Services (will use this foundation)
- [ ] Network Discovery Documentation: All 16 scenarios documented in `PPL_META_NETWORK_DISCOVERY.md`

## 📅 Timeline

**Target Start Date**: 2025-08-27  
**Target Completion Date**: 2025-09-06 (10 days)  
**Key Milestones**:

- [ ] Foundation Setup Complete: 2025-08-30 - Basic FastAPI service with health endpoint and directory structure
- [ ] Core Implementation Complete: 2025-09-04 - Service registry, edge registry, and discovery APIs functional  
- [ ] Integration & Testing Complete: 2025-09-06 - All backend services integrated, VS Code tasks updated, ready for production

## 🎯 Definition of Done

This planning phase is complete when:

- [ ] All sections above are filled out with specific details
- [ ] Technical approach has been reviewed and approved
- [ ] Implementation plan has been validated for feasibility
- [ ] Timeline has been agreed upon by stakeholders
- [ ] All dependencies have been identified and addressed
- [ ] GitHub issue has been updated with planning details
- [ ] Project card has been moved to "🔄 In Progress" when ready

## 📝 Notes

**Service Architecture Details:**
- Port: 8006 (follows existing pattern: node=8001, gateway=8080, etc.)
- Technology: Python/FastAPI (consistent with other backend services)
- Registry Storage: In-memory with periodic persistence (Redis integration in future)
- Discovery Methods: REST API + Multicast announcements

**Network Scenario Support Foundation:**
- Service registry supports all 16 documented network discovery scenarios
- Foundation enables mobile apps to use single discovery endpoint instead of complex client-side logic
- Edge device registry prepares for future Raspberry Pi and mobile camera integration

**Integration Points:**
- All existing backend services will register on startup
- VS Code tasks will include discovery service in startup/shutdown workflows  
- Mobile apps will query discovery service for complete platform topology
- Future services (Tailscale integration, OpenVPN support) will build on this foundation

---

**Next Steps**:

1. Complete planning details above ✅
2. Get stakeholder review and approval 
3. Move to current/ phase with: `./scripts/docs-lifecycle-enhanced.sh activate 6 "create-ppl-meta-discovery-service-foundation"`
4. Update GitHub Project card to "🔄 In Progress"
