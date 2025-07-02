# PPL Meta Platform - Ecosystem Issues & Known Problems

This document tracks all known issues, bugs, and areas for improvement across the entire PPL Meta Platform ecosystem.

**Last Updated**: June 30, 2025  
**Status**: Active Development  
**Priority Levels**: 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low

---

## Overview

The PPL Meta Platform consists of multiple microservices and infrastructure components. This document categorizes issues by component and priority to help with debugging, development planning, and system maintenance.

---

## 🔴 Critical Issues

### Infrastructure & Docker Compose

#### ISSUE-001: Missing Infrastructure Docker Images
- **Component**: Full Ecosystem Deployment
- **Status**: Unresolved
- **Description**: Several infrastructure services fail to start due to missing Docker images
- **Affected Services**: 
  - `consul:1.16` - Service discovery
  - `prom/prometheus` - Metrics collection
  - `grafana/grafana` - Monitoring dashboard
  - `linuxserver/wireguard` - VPN mesh networking
- **Error**: `failed to resolve reference "docker.io/library/consul:1.16": not found`
- **Impact**: Complete ecosystem (`docker-compose.ecosystem.yml`) fails to start
- **Workaround**: Use `docker-compose.minimal.yml` with core services only
- **Resolution**: 
  - [ ] Find alternative image sources or versions
  - [ ] Build custom images for unavailable services
  - [ ] Create conditional service definitions

#### ISSUE-002: Service Configuration Port Mismatches
- **Component**: Service Discovery & Load Balancing
- **Status**: Unresolved
- **Description**: Port configurations are inconsistent between documentation and actual service configurations
- **Details**:
  - Documentation states Node service on port 8000, but actual configuration uses 8001
  - Media service port conflicts between different compose files
- **Impact**: Service-to-service communication failures
- **Resolution**:
  - [ ] Standardize port assignments across all configurations
  - [ ] Update documentation to match actual ports
  - [ ] Verify all service URL environment variables

### Service Startup Issues

#### ISSUE-003: Node Service Container Restart Loop
- **Component**: ppl-meta-node
- **Status**: Unresolved
- **Description**: Node service container continuously restarts when deployed via Docker
- **Error Pattern**: `Restarting (1) X seconds ago`
- **Likely Causes**:
  - Database connection issues
  - Missing environment variables
  - Python module import errors
  - Configuration validation failures
- **Impact**: Node service unavailable in Docker deployments
- **Investigation Needed**:
  - [ ] Check container logs for specific error messages
  - [ ] Verify database connectivity from container
  - [ ] Validate environment variable loading
  - [ ] Test import paths in Docker context

#### ISSUE-004: Media Service Container Failures
- **Component**: ppl-meta-media
- **Status**: Unresolved
- **Description**: Media service fails to start consistently in Docker environment
- **Symptoms**: Container exits or restarts frequently
- **Impact**: Media processing functionality unavailable
- **Investigation Needed**:
  - [ ] Analyze container startup logs
  - [ ] Check dependency installation in Docker image
  - [ ] Verify database schema and connectivity
  - [ ] Test file system permissions for media storage

---

## 🟠 High Priority Issues

### Configuration & Environment

#### ISSUE-005: Environment Variable Inconsistencies
- **Component**: All Services
- **Status**: Partially Resolved
- **Description**: Environment variables are not consistently defined across services
- **Problems**:
  - Missing default values for optional variables
  - Inconsistent naming conventions
  - Some variables required but not documented
- **Impact**: Services fail to start or operate incorrectly
- **Progress**:
  - [x] Fixed SECRET_KEY loading in gateway
  - [ ] Standardize MAIL_* variables across services
  - [ ] Add validation for required environment variables
  - [ ] Create environment variable templates

#### ISSUE-006: Database Connection String Variations
- **Component**: ppl-meta-node, ppl-meta-media
- **Status**: Unresolved
- **Description**: Different services use different database connection formats
- **Details**:
  - URL encoding issues with special characters in passwords
  - Different database names for different services
  - Port mismatches between compose files (5432 vs 5433)
- **Impact**: Database connectivity issues
- **Resolution**:
  - [ ] Standardize connection string format
  - [ ] Use consistent database credentials across services
  - [ ] Implement connection string validation

### Service Dependencies

#### ISSUE-007: Import Path Problems in Docker Context
- **Component**: ppl-meta-gateway
- **Status**: Resolved
- **Description**: Python import paths fail when running in Docker containers
- **Error**: `ModuleNotFoundError: No module named 'src.config'`
- **Solution Applied**: Fixed import statements to use relative paths
- **Status**: ✅ Resolved - imports now work correctly in Docker

#### ISSUE-008: Missing Python Dependencies
- **Component**: ppl-meta-gateway
- **Status**: Resolved
- **Description**: Missing `psutil` dependency causing service failures
- **Solution Applied**: Added `psutil>=5.9.0` to requirements.txt
- **Status**: ✅ Resolved - dependency installed and working

---

## 🟡 Medium Priority Issues

### Performance & Optimization

#### ISSUE-009: Docker Image Size Optimization
- **Component**: All Services
- **Status**: Open
- **Description**: Docker images are larger than necessary
- **Current Sizes**:
  - ppl-meta-gateway: 627MB
  - ppl-meta-node: 996MB
  - ppl-meta-media: 731MB
- **Optimization Opportunities**:
  - [ ] Use multi-stage builds
  - [ ] Switch to Alpine base images
  - [ ] Remove unnecessary packages and files
  - [ ] Implement .dockerignore files

#### ISSUE-010: Health Check Timeout Issues
- **Component**: All Services
- **Status**: Open
- **Description**: Health check endpoints sometimes timeout during startup
- **Impact**: Docker reports services as unhealthy even when they're starting normally
- **Resolution**:
  - [ ] Increase health check timeout values
  - [ ] Implement proper startup probes
  - [ ] Add health check retry logic

### Monitoring & Logging

#### ISSUE-011: Inconsistent Logging Configuration
- **Component**: All Services
- **Status**: Open
- **Description**: Logging levels and formats vary between services
- **Problems**:
  - Different log formats make aggregation difficult
  - Log levels not consistently configurable
  - Some services log to stdout, others to files
- **Resolution**:
  - [ ] Standardize logging configuration across services
  - [ ] Implement structured logging (JSON format)
  - [ ] Add log level environment variable support

#### ISSUE-012: Missing Service Metrics
- **Component**: All Services
- **Status**: Open
- **Description**: Limited metrics collection for monitoring
- **Missing Metrics**:
  - Request/response times
  - Error rates
  - Resource utilization
  - Custom business metrics
- **Resolution**:
  - [ ] Implement Prometheus metrics endpoints
  - [ ] Add custom metrics for business logic
  - [ ] Create Grafana dashboards

---

## 🟢 Low Priority Issues

### Documentation & Development Experience

#### ISSUE-013: Deprecated Docker Compose Version Warnings
- **Component**: Docker Compose Files
- **Status**: Open
- **Description**: All compose files show version deprecation warnings
- **Warning**: `the attribute 'version' is obsolete, it will be ignored`
- **Impact**: Cosmetic warnings in console output
- **Resolution**:
  - [ ] Remove version declarations from all compose files
  - [ ] Update compose file format to current standard

#### ISSUE-014: VS Code Tasks Need Refinement
- **Component**: Development Environment
- **Status**: Open
- **Description**: VS Code tasks could be more comprehensive
- **Improvements Needed**:
  - [ ] Add task for building Docker images
  - [ ] Create combined start/stop tasks
  - [ ] Add health check verification tasks
  - [ ] Implement log viewing tasks

### Security & Best Practices

#### ISSUE-015: Hardcoded Secrets in Configuration
- **Component**: All Services
- **Status**: Open
- **Description**: Some secrets are hardcoded in configuration files
- **Security Concerns**:
  - Database passwords in plain text
  - Default SECRET_KEY values
  - SMTP credentials exposure
- **Resolution**:
  - [ ] Implement proper secrets management
  - [ ] Use Docker secrets or external key management
  - [ ] Add secret rotation capabilities

#### ISSUE-016: Missing Input Validation
- **Component**: All Services
- **Status**: Open
- **Description**: Limited input validation on API endpoints
- **Risks**:
  - Potential injection attacks
  - Data corruption from invalid inputs
  - Poor error handling
- **Resolution**:
  - [ ] Implement comprehensive input validation
  - [ ] Add request/response schema validation
  - [ ] Improve error handling and responses

---

## 🔧 Infrastructure Improvements

### Service Discovery & Communication

#### ISSUE-017: Service Discovery Implementation
- **Component**: Service Communication
- **Status**: Open
- **Description**: Services use hardcoded URLs for inter-service communication
- **Problems**:
  - No dynamic service discovery
  - Hardcoded service URLs
  - No load balancing between service instances
- **Resolution**:
  - [ ] Implement Consul-based service discovery
  - [ ] Add service registration/deregistration
  - [ ] Implement client-side load balancing

#### ISSUE-018: Missing API Gateway Features
- **Component**: ppl-meta-gateway
- **Status**: Open
- **Description**: Gateway lacks advanced routing and middleware features
- **Missing Features**:
  - Rate limiting implementation
  - Request/response transformation
  - Circuit breaker pattern
  - Request tracing
- **Resolution**:
  - [ ] Implement advanced middleware
  - [ ] Add circuit breaker functionality
  - [ ] Implement distributed tracing

### Database & Storage

#### ISSUE-019: Database Migration Strategy
- **Component**: Database Management
- **Status**: Open
- **Description**: No automated database migration system
- **Problems**:
  - Manual schema updates required
  - No version control for database changes
  - Risk of schema drift between environments
- **Resolution**:
  - [ ] Implement Alembic migrations for all services
  - [ ] Add migration validation and rollback
  - [ ] Create automated migration testing

#### ISSUE-020: Storage Volume Management
- **Component**: Docker Volumes
- **Status**: Open
- **Description**: Storage volumes not optimally configured
- **Issues**:
  - No backup strategy for volumes
  - Volume permissions issues
  - Limited storage monitoring
- **Resolution**:
  - [ ] Implement volume backup strategy
  - [ ] Fix permission issues
  - [ ] Add storage monitoring

#### ISSUE-021: Duplicate Microservices Architecture
- **Component**: Repository Structure
- **Status**: ✅ Resolved
- **Priority**: 🟡 Medium
- **Description**: Duplicate microservices code existed in two locations
- **Duplicate Locations**:
  - **Active**: Root-level directories (`/ppl-meta-gateway/`, `/ppl-meta-node/`, etc.) ✅
  - **Legacy**: Monorepo structure (`/ppl-meta-code/services/gateway/`, `/ppl-meta-code/services/user-management/`, etc.) ❌ REMOVED
- **Impact**: 
  - Code maintenance confusion ✅ RESOLVED
  - Potential deployment to wrong codebase ✅ RESOLVED
  - Increased repository size ✅ RESOLVED
  - Developer confusion about active codebase ✅ RESOLVED
- **Root Cause**: Evolution from monorepo to individual microservices without cleanup
- **Resolution**: ✅ COMPLETED
  - [x] Audit code differences between duplicate locations → No differences found
  - [x] Confirm root-level services are the active/current versions → Confirmed
  - [x] Archive legacy `/ppl-meta-code/services/` directory → Archived to `/archive/legacy-services-20250702/`
  - [x] Remove legacy `/ppl-meta-code/services/` directory → Removed
  - [x] Update legacy docker-compose.yml → Marked as deprecated with clear instructions
  - [x] Archive obsolete migration scripts → Moved to archive
  - [x] Update documentation to clarify active service locations → Updated
- **Archive Location**: `/archive/legacy-services-20250702/`

---

## 🎯 Improvement Roadmap

### Phase 1: Critical Stability (Immediate)

1. ✅ Fix Docker image availability issues → Use minimal compose
2. ⏳ Resolve service startup problems
3. ⏳ Standardize environment configuration
4. ⏳ Fix database connectivity issues
5. ✅ Clean up duplicate microservices architecture → COMPLETED

### Phase 2: Core Functionality (Short-term)
1. ⏳ Implement proper health checks
2. ⏳ Add comprehensive logging
3. ⏳ Fix service-to-service communication
4. ⏳ Implement basic monitoring

### Phase 3: Production Readiness (Medium-term)
1. ⏳ Add security hardening
2. ⏳ Implement service discovery
3. ⏳ Add backup and recovery
4. ⏳ Performance optimization

### Phase 4: Advanced Features (Long-term)
1. ⏳ Advanced monitoring and alerting
2. ⏳ Auto-scaling capabilities
3. ⏳ Multi-environment deployment
4. ⏳ CI/CD pipeline integration

---

## 🚨 Emergency Contacts & Resources

### Key Files for Issue Resolution
- **Main Compose**: `docker-compose.ecosystem.yml`
- **Minimal Compose**: `docker-compose.minimal.yml`
- **Infrastructure**: `ppl-meta-node/docker-compose.infrastructure.yml`
- **Documentation**: `ECOSYSTEM_GUIDE.md`
- **This Document**: `ECOSYSTEM_ISSUES.md`

### Common Debugging Commands
```bash
# Check service status
docker-compose -f docker-compose.minimal.yml ps

# View service logs
docker logs ppl-meta-gateway --tail 50

# Check environment variables
docker exec ppl-meta-gateway env | grep SECRET_KEY

# Test service connectivity
curl http://localhost:8080/health

# Clean up containers and networks
docker-compose down && docker system prune -f
```

### Development Commands
```bash
# Start minimal ecosystem
SECRET_KEY="super-secure-jwt-secret-key-for-ppl-meta-gateway-production-2024" \
docker-compose -f docker-compose.minimal.yml up -d

# Stop all services
docker-compose -f docker-compose.minimal.yml down

# Rebuild specific service
docker build -t ppl-meta-gateway:latest ./ppl-meta-gateway
```

---

## 📝 Issue Reporting Template

When reporting new issues, please use this template:

```markdown
## ISSUE-XXX: [Brief Description]
- **Component**: [Service/Component Name]
- **Priority**: [🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low]
- **Status**: [Open | In Progress | Resolved | Closed]
- **Reporter**: [Your Name]
- **Date**: [Date Reported]

### Description
[Detailed description of the issue]

### Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Expected Behavior
[What should happen]

### Actual Behavior
[What actually happens]

### Environment
- OS: [Operating System]
- Docker Version: [Version]
- Python Version: [Version]
- Service Version: [Version]

### Logs/Error Messages
```
[Paste relevant logs or error messages]
```

### Proposed Solution
[If you have ideas for fixing the issue]

### Related Issues
[Link to related issues]
```

---

This document will be updated as issues are resolved and new ones are discovered. For urgent issues, please prioritize based on the impact on core functionality and user experience.
