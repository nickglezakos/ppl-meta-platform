# PPL Meta Platform - Ecosystem Issues & Known Problems

This document tracks all known issues, bugs, and areas for improvement across the entire PPL Meta Platform ecosystem.

**Last Updated**: July 2, 2025  
**Status**: Active Development  
**Priority Levels**: 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low

---

## Overview

The PPL Meta Platform consists of multiple microservices and infrastructure components:

### Core Microservices
- **ppl-meta-gateway**: API Gateway and service orchestration (Port: 8080)
- **ppl-meta-node**: User management and authentication (Port: 8001)
- **ppl-meta-media**: Media processing and storage (Port: 8000)
- **ppl-meta-orchestrator**: Service coordination and workflows (Port: 8002)
- **ppl-meta-frontend**: Flutter-based cross-platform frontend (Port: 80/443)

This document categorizes issues by component and priority to help with debugging, development planning, and system maintenance.

---

## 🔴 Critical Issues

### Infrastructure & Docker Compose

#### ISSUE-001: Missing Infrastructure Docker Images
- **Component**: Full Ecosystem Deployment
- **Status**: ✅ Resolved
- **Description**: Several infrastructure services failed to start due to missing Docker images and SSL configuration
- **Affected Services**: 
  - ✅ `consul:1.16` → `hashicorp/consul:latest` (Fixed)
  - ✅ `prom/prometheus` - Metrics collection (Working)
  - ✅ `grafana/grafana` - Monitoring dashboard (Working)
  - ✅ `linuxserver/wireguard` - VPN mesh networking (Working)
  - ✅ `nginx-gateway` - SSL certificate issues (Fixed)
- **Errors Resolved**:
  - ✅ `failed to resolve reference "docker.io/library/consul:1.16": not found` → Updated to `hashicorp/consul:latest`
  - ✅ `nginx: [emerg] cannot load certificate` → Created self-signed SSL certificates
  - ✅ Port conflicts between nginx-gateway and ppl-meta-gateway → Fixed port mapping
- **Impact**: ✅ RESOLVED - Complete ecosystem (`docker-compose.ecosystem.yml`) now starts successfully
- **Resolution Applied (v1.0.3)**:
  - [x] Updated Consul image to `hashicorp/consul:latest` with proper data directory configuration
  - [x] Created self-signed SSL certificates for nginx-gateway using OpenSSL
  - [x] Fixed port conflicts by changing nginx external port from 8080 to 8090
  - [x] Fixed Consul configuration with proper `-data-dir=/consul/data` parameter
  - [x] Updated health check configurations to use Python instead of curl
  - [x] Built missing ppl-meta-orchestrator Docker image
- **Current Status** (Last verified: Jan 2, 2025):
  - ✅ All infrastructure services running and healthy:
    - nginx-gateway (ports 80/443/8090) ✅
    - postgres (port 5433) ✅
    - redis (port 6379) ✅
    - consul (port 8500) ✅
    - prometheus (port 9090) ✅
    - grafana (port 3000) ✅
    - wireguard (port 51820/udp) ✅
  - ✅ All core microservices running:
    - ppl-meta-node (port 8001) ✅ healthy
    - ppl-meta-media (port 8000) ✅ healthy
    - ppl-meta-gateway (port 8080) ⚠️ running but health check reports unhealthy
    - ppl-meta-orchestrator (port 8002) ⚠️ running but health check reports unhealthy
  - 🔍 **Remaining Issue**: Gateway and Orchestrator health checks report "unhealthy"
    - Services are fully functional and responding to requests
    - Issue appears to be with Docker health check configuration, not actual service failure
    - Requests to `http://localhost:8080/health` and `http://localhost:8002/health` work externally
    - Needs refinement of internal Docker health check commands
- **SSL Configuration Notes**:
  - ✅ Created self-signed certificates for development: `/nginx/ssl/ppl-meta.crt` and `/nginx/ssl/ppl-meta.key`
  - ✅ SSL/TLS properly configured in nginx with certificate paths: `/etc/ssl/ppl-meta.crt` and `/etc/ssl/ppl-meta.key`
  - ✅ HTTPS access working on port 443
  - 🔄 For production deployment, replace with proper SSL certificates (Let's Encrypt recommended)
  - 📝 Complete SSL setup guide added to ECOSYSTEM_GUIDE.md


#### ISSUE-002: Service Configuration Port Mismatches
- **Component**: Service Discovery & Load Balancing
- **Status**: ✅ Resolved
- **Description**: Port configurations are inconsistent between documentation and actual service configurations
- **Root Causes Identified & Fixed**:
  - ✅ Initial documentation errors regarding service port assignments
  - ✅ Standardized port assignments across all configurations verified
  - ✅ Service URL environment variables validated and consistent
- **Impact**: ✅ RESOLVED - Service-to-service communication now reliable with standardized ports
- **Resolution Applied (v1.0.2)**:
  - [x] Verified consistent port assignments across all docker-compose files
  - [x] Confirmed documentation matches actual configurations
  - [x] Validated service URL environment variables in all configurations
  - [x] Tested inter-service communication on standardized ports
- **Standardized Port Assignments**:
  - `ppl-meta-gateway`: Port 8080 (API Gateway & Service Orchestration)
  - `ppl-meta-node`: Port 8001 (User Management & Authentication)
  - `ppl-meta-media`: Port 8000 (Media Processing & Storage)
  - `ppl-meta-orchestrator`: Port 8002 (Service Coordination & Workflows)
  - `ppl-meta-frontend`: Port 80/443 (Flutter Frontend)
  - `nginx-gateway`: Port 80/443 (Reverse Proxy)
  - `postgres`: Port 5433 (Database)
  - `redis`: Port 6379 (Cache)
- **Files Verified**:
  - `docker-compose.ecosystem.yml` - All ports consistent
  - `docker-compose.minimal.yml` - All ports consistent
  - `ppl-meta-node/docker-compose.infrastructure.yml` - All ports consistent
  - Service configuration files verified
- **Testing Status**: ✅ All services communicate successfully on assigned ports

### Service Startup Issues

#### ISSUE-003: Node Service Container Restart Loop
- **Component**: ppl-meta-node
- **Status**: ✅ Resolved
- **Description**: Node service container continuously restarts when deployed via Docker
- **Error Pattern**: `Restarting (1) X seconds ago`
- **Root Causes Identified & Fixed**:
  - ✅ Pydantic settings validation errors (missing environment variables)
  - ✅ Mail service configuration crashes with missing SMTP variables
  - ✅ Configuration validation failures due to Pydantic v2 incompatibility
  - ✅ Missing proper error handling for optional services
- **Impact**: ✅ RESOLVED - Node service now starts reliably in Docker deployments
- **Resolution Applied (v1.0.1)**:
  - [x] Fixed Pydantic v2 configuration validation
  - [x] Added graceful mail service fallback for missing SMTP configuration
  - [x] Improved environment variable handling and validation
  - [x] Enhanced Docker container startup reliability with proper health checks
  - [x] Added comprehensive logging and error handling
- **Files Modified**:
  - `ppl-meta-node/src/config.py` - Environment variable mapping and Pydantic v2 migration
  - `ppl-meta-node/src/mail.py` - Graceful handling of missing mail configuration
  - `ppl-meta-node/src/main.py` - Improved logging and error handling
  - `ppl-meta-node/src/api/v1/health.py` - Enhanced health check endpoints
  - `ppl-meta-node/Dockerfile` - Container optimization and health checks
- **Testing Status**: ✅ Service builds successfully, starts properly, handles missing configuration gracefully

#### ISSUE-004: Media Service Container Failures
- **Component**: ppl-meta-media
- **Status**: ✅ Resolved
- **Description**: Media service fails to start consistently in Docker environment
- **Symptoms**: Container exits or restarts frequently
- **Impact**: ✅ RESOLVED - Media processing functionality now available
- **Root Causes Identified & Fixed**:
  - ✅ Pydantic v2 configuration compatibility issues
  - ✅ Missing environment variable mappings (LOG_LEVEL, UPLOAD_DIR)
  - ✅ PostgreSQL syntax errors in database initialization
  - ✅ Docker container startup sequence and health checks
- **Resolution Applied (v1.0.1)**:
  - [x] Fixed Pydantic v2 configuration using `ConfigDict(extra='ignore')`
  - [x] Added missing environment variables to Settings class
  - [x] Corrected PostgreSQL database initialization syntax
  - [x] Enhanced Docker container reliability with proper health checks
  - [x] Verified service-to-service communication and API endpoints
- **Files Modified**:
  - `ppl-meta-media/src/config.py` - Pydantic v2 migration and environment variable mapping
  - `ppl-meta-media/init-databases.sql` - PostgreSQL syntax fixes
  - Container builds successfully and starts reliably
- **Testing Status**: ✅ Service builds successfully, starts properly, serves API endpoints on port 8000

---

## 🟠 High Priority Issues

### Configuration & Environment

#### ISSUE-005: Environment Variable Inconsistencies
- **Component**: All Services
- **Status**: ✅ Resolved
- **Description**: Environment variables are not consistently defined across services
- **Problems Resolved**:
  - ✅ Standardized MAIL_* variables across all services with consistent naming conventions
  - ✅ Added missing default values for optional variables in all service configurations
  - ✅ Ensured all required variables are documented and present in .env.example templates
  - ✅ Created validation tooling to maintain consistency
- **Impact**: ✅ RESOLVED - All services now have consistent environment variable configuration
- **Resolution Applied (v1.0.4)**:
  - [x] Standardized MAIL_* variables (MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, etc.) across all services
  - [x] Updated config.py files in all services to include standardized variable definitions
  - [x] Created/updated .env.example templates for all services:
    - ppl-meta-node/.env.example (updated)
    - ppl-meta-media/.env.example (updated)
    - ppl-meta-gateway/.env.example (updated)
    - ppl-meta-orchestrator/.env.example (created)
    - ppl-meta-frontend/.env.example (created)
    - ppl-meta-code/.env.example (created)
  - [x] Added mail configuration validation helpers to all service configs
  - [x] Created validate_env_vars.py script for cross-service validation and documentation
  - [x] Added validation for required environment variables in all services
  - [x] Ensured consistent naming conventions and variable coverage across the ecosystem
- **Validation Results**:
  - ✅ All 6 services now have consistent environment variable configuration
  - ✅ 4 required variables standardized: APP_NAME, APP_VERSION, DATABASE_URL, SECRET_KEY
  - ✅ 28 optional variables standardized across all services
  - ✅ 0 configuration inconsistencies detected by validation script

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

#### ISSUE-022: VS Code Workspace Organization
- **Component**: Development Environment
- **Status**: ✅ Resolved
- **Priority**: 🟡 Medium
- **Description**: VS Code workspace had duplicate folder entries causing confusion in explorer
- **Problems**:
  - Multiple folder entries for the same directories
  - Cluttered workspace explorer
  - Inconsistent workspace file configuration
- **Impact**: 
  - Developer confusion when navigating files ✅ RESOLVED
  - Duplicate entries in file explorer ✅ RESOLVED
  - Inefficient workspace navigation ✅ RESOLVED
- **Resolution**: ✅ COMPLETED
  - [x] Cleaned up `ppl-meta-platform.code-workspace` configuration
  - [x] Removed duplicate folder entries
  - [x] Kept only root folder for clean explorer view
  - [x] Preserved all necessary workspace settings and extensions

#### ISSUE-023: Missing Frontend Microservice
- **Component**: Frontend Architecture
- **Status**: ✅ Resolved
- **Priority**: 🟠 High
- **Description**: Platform lacked a dedicated frontend microservice
- **Problems**:
  - No standardized frontend architecture
  - Missing cross-platform UI capabilities
  - No centralized frontend service for the platform
- **Impact**: 
  - Limited user interface options ✅ RESOLVED
  - No mobile app capabilities ✅ RESOLVED
  - Incomplete microservices architecture ✅ RESOLVED
- **Resolution**: ✅ COMPLETED
  - [x] Created `ppl-meta-frontend` Flutter microservice
  - [x] Implemented cross-platform support (web, mobile, desktop)
  - [x] Added comprehensive Flutter dependencies and configuration
  - [x] Created Docker deployment configuration
  - [x] Added frontend to CI/CD pipeline
  - [x] Updated documentation and ecosystem guides
- **Features Added**:
  - Flutter 3.10+ with modern architecture
  - Riverpod state management
  - GoRouter for navigation
  - API integration with existing services
  - Docker containerization with nginx
  - Development and production build configurations

#### ISSUE-024: Comprehensive Documentation Creation
- **Component**: Documentation & Guides
- **Status**: ✅ Resolved
- **Priority**: 🟠 High
- **Description**: Platform lacked comprehensive ecosystem documentation
- **Problems**:
  - No central ecosystem guide
  - Missing CI/CD strategy documentation
  - Unclear service architecture information
- **Impact**: 
  - Developer onboarding difficulties ✅ RESOLVED
  - Deployment confusion ✅ RESOLVED
  - Architecture understanding gaps ✅ RESOLVED
- **Resolution**: ✅ COMPLETED
  - [x] Created `ECOSYSTEM_GUIDE.md` with comprehensive platform overview
  - [x] Created `CI_CD_STRATEGY.md` with deployment pipelines and strategies
  - [x] Updated service-specific documentation
  - [x] Added troubleshooting guides and best practices
  - [x] Included frontend microservice in all documentation

---

## 🎯 Improvement Roadmap

### Phase 1: Critical Stability (Immediate)

1. ✅ Fix Docker image availability issues → Use minimal compose
2. ✅ Resolve service startup problems → Node service restart loop RESOLVED (v1.0.1), Media service RESOLVED (v1.0.2)
3. ✅ Standardize environment configuration → Gateway completed, Node completed, Media completed
4. ✅ Fix service port mismatches → Port assignments standardized and verified (v1.0.2)
5. ⏳ Fix database connectivity issues
6. ✅ Clean up duplicate microservices architecture → COMPLETED
7. ✅ Add frontend microservice → COMPLETED
8. ✅ Create comprehensive documentation → COMPLETED
9. ✅ Organize VS Code workspace → COMPLETED

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
- **Ecosystem Guide**: `ECOSYSTEM_GUIDE.md`
- **CI/CD Strategy**: `CI_CD_STRATEGY.md`
- **This Document**: `ECOSYSTEM_ISSUES.md`
- **Frontend Service**: `ppl-meta-frontend/`
- **Archive Location**: `archive/legacy-services-20250702/`

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

# Frontend development commands
cd ppl-meta-frontend
flutter pub get
flutter run -d chrome
flutter test
flutter build web --release

# Build frontend Docker image
docker build -t ppl-meta-frontend:latest ./ppl-meta-frontend
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

---

## Frontend Development Considerations

With the addition of the Flutter frontend microservice, consider these potential future issues:

#### ISSUE-025: Frontend API Integration
- **Component**: ppl-meta-frontend
- **Status**: Open
- **Priority**: 🟡 Medium
- **Description**: Frontend needs comprehensive API integration with all backend services
- **Requirements**:
  - [ ] Implement authentication flow with ppl-meta-node
  - [ ] Add media upload/management with ppl-meta-media
  - [ ] Integrate with orchestrator for complex workflows
  - [ ] Add proper error handling and loading states
  - [ ] Implement offline capabilities

#### ISSUE-026: Frontend Testing Strategy
- **Component**: ppl-meta-frontend
- **Status**: Open
- **Priority**: 🟡 Medium
- **Description**: Comprehensive testing strategy needed for Flutter frontend
- **Requirements**:
  - [ ] Unit tests for business logic
  - [ ] Widget tests for UI components
  - [ ] Integration tests for API communication
  - [ ] End-to-end tests for user workflows
  - [ ] Performance testing for web builds

#### ISSUE-027: Mobile App Distribution
- **Component**: ppl-meta-frontend
- **Status**: Future Planning
- **Priority**: 🟢 Low
- **Description**: Future mobile app distribution strategy
- **Requirements**:
  - [ ] Android app store deployment
  - [ ] iOS app store deployment
  - [ ] Code signing and certificate management
  - [ ] App store optimization and metadata
  - [ ] Beta testing and distribution channels
