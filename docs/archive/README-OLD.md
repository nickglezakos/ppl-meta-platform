# PPL Meta Platform Documentation

## � Documentation Structure

This directory contains comprehensive documentation for the PPL Meta Platform, organized according to the monorepo structure defined in the CI/CD strategy.

### 🏗️ Architecture Documentation (`architecture/`)

Technical architecture documents and system design specifications:

#### **Microservices** (`architecture/microservices/`)
- `ENHANCED_MICROSERVICES_ARCHITECTURE.md` - Complete microservices architecture with service categorization

#### **Network Discovery** (`architecture/network-discovery/`)
- `MICROSERVICES_NETWORK_DISCOVERY_ARCHITECTURE.md` - Network discovery system architecture
- `NETWORK_DISCOVERY_IMPLEMENTATION_PLAN.md` - Implementation planning document
- `NETWORK_DISCOVERY_IMPLEMENTATION_COMPLETE.md` - Completed implementation details
- `PPL_META_NETWORK_DISCOVERY.md` - Core network discovery documentation

### 🚀 Deployment Documentation (`deployment/`)

Deployment guides, procedures, and configuration files:

#### **Docker** (`deployment/docker/`)
- `docker-compose.ecosystem.yml` - Complete ecosystem deployment
- `docker-compose.minimal.yml` - Minimal deployment configuration
- `docker-compose.secrets.yml` - Secret management configuration
- `docker-compose.service-discovery-test.yml` - Service discovery testing

#### **Nginx** (`deployment/nginx/`)
- `nginx-local-dev.conf` - Local development nginx configuration

#### **General Deployment**
- `PORT_CONFLICT_ANALYSIS_AND_SOLUTIONS.md` - Port conflict resolution guide

### 🛠️ Development Documentation (`development/`)

Development standards, guidelines, and processes:

#### **Core Development Process**
- `CONTINUOUS_DEVELOPMENT_CONTINUOUS_INTEGRATION.md` - Complete CI/CD strategy
- `RELEASE_NOTES_v2.*.md` - Release notes and changelog

#### **Implementation Guides** (`development/implementation-guides/`)
- `CAM-FLUTTER-*` - Camera and Flutter implementation guides
- `ENHANCED_SNAPSHOT_RESOLUTION_IMPLEMENTATION.md` - Snapshot resolution enhancement
- `VPN_INTEGRATION_COMPLETE.md` - VPN integration implementation
- `RTSP_FRONTEND_INTEGRATION_COMPLETE.md` - RTSP frontend integration
- `OPENCV_INTEGRATION_EXAMPLE.md` - OpenCV integration examples

#### **Testing** (`development/testing/`)
- `CAM-FLUTTER-004-PHASE-1-TESTING-GUIDE.md` - Camera testing procedures

##### **Camera Tests** (`development/testing/cam-tests/`)
- `CAM-TEST-001-RESULTS.md` - Camera test results
- `CAM-TEST-002-*` - Comprehensive camera lifecycle tests
- `CAM-TEST-003-*` - Streaming and snapshot tests

#### **Issue Documentation**
- `MOBILE_NETWORK_DISCOVERY_ISSUE.md` - Mobile network discovery issues
- `PLATFORM_NETWORK_DISCOVERY_ISSUE.md` - Platform network discovery issues

### 📡 API Documentation (`api/`)

API specifications and documentation:

- `cameras_docs.html` - Camera service API documentation
- `media_docs.html` - Media service API documentation

## 📁 Legacy Structure

The following directories contain legacy documentation that will be gradually integrated:

- `archive/` - Archived documentation
- `current/` - Current working documents
- `planning/` - Planning and roadmap documents
- `templates/` - Document templates
- `notebooks/` - Jupyter notebooks and research
- `Release Notes/` - Legacy release notes

## 🔄 Document Maintenance

### Update Requirements

- **New Features**: Documentation required before merge
- **API Changes**: Automatic documentation generation and validation
- **Architecture Changes**: Update relevant architecture documents
- **Bug Fixes**: Update troubleshooting guides as needed

### Document Categories

- **Architecture**: System design and technical specifications
- **Deployment**: Installation, configuration, and operations
- **Development**: Coding standards, testing, and implementation guides
- **API**: Service interfaces and integration guides

## 🚀 Quick Navigation

### For Developers

- Start with `development/CONTINUOUS_DEVELOPMENT_CONTINUOUS_INTEGRATION.md`
- Review `architecture/microservices/ENHANCED_MICROSERVICES_ARCHITECTURE.md`
- Check relevant implementation guides in `development/implementation-guides/`

### For DevOps/Deployment

- Review `deployment/docker/` for containerized deployments
- Check `deployment/PORT_CONFLICT_ANALYSIS_AND_SOLUTIONS.md` for troubleshooting
- Use `deployment/nginx/` for proxy configuration

### For API Integration

- Start with `api/` directory for service API documentation
- Review `architecture/` for service interaction patterns
- Check `development/testing/` for integration examples

## 📞 Maintenance and Updates

This documentation structure follows the monorepo strategy outlined in the CI/CD documentation. All documents should be kept current with the codebase and updated as part of the development process.

For questions or suggestions regarding documentation structure, please refer to the CI/CD strategy document or create an issue in the project repository.

### 📡 API Documentation (`api/`)

API specifications and documentation:
- `cameras_docs.html` - Camera service API documentation
- `media_docs.html` - Media service API documentation

### 🏗️ Technical Documentation

- **[API Specifications](technical/api/)** - All service API documentation
- **[Database Design](technical/database/)** - Schema and data model docs
- **[Frontend Architecture](technical/frontend/)** - Flutter app documentation
- **[Infrastructure](technical/infrastructure/)** - Deployment and DevOps docs

### 📖 Guides

- **[User Guides](guides/user/)** - End-user documentation
- **[Developer Guides](guides/developer/)** - Development setup and standards
- **[Deployment Guides](guides/deployment/)** - Deployment procedures

### 📚 Archive

- **[Historical Issues](archive/)** - Resolved issues and version history
- **[Release Notes](archive/versions/)** - Version-specific documentation

## 🎯 Quick Links

### Development

- [Current User Testing Issues](current/user-testing/PPL_META_PLATFORM_USER_TESTING_ISSUES.md)
- [Vision Service Development Plan](current/vision-service/PPL_META_VISION_SERVICE_ISSUES.md)
- [Development Setup Guide](guides/developer/setup-development.md)

### Technical Reference

- [API Documentation](technical/api/)
- [Database Schema](technical/database/)
- [Frontend Architecture](technical/frontend/)

### Deployment

- [Local Setup](guides/deployment/local-setup.md)
- [Docker Deployment](guides/deployment/docker-deployment.md)
- [Production Deployment](guides/deployment/production-deployment.md)

## 📋 Document Status Legend

- 🔄 **PLANNING** - In planning phase
- 🚧 **IN PROGRESS** - Currently being worked on
- 🧪 **TESTING** - Under testing/review
- ✅ **RESOLVED** - Completed/resolved
- 📁 **ARCHIVED** - Moved to archive

## 🗂️ Navigation Tips

- Use the directory structure to find specific documentation types
- Check the `current/` directory for active development issues
- Refer to `technical/` for detailed specifications
- Use `guides/` for step-by-step instructions
- Check `archive/` for historical context

---

*Last updated: July 19, 2025*
*Documentation structure follows PPL Meta Platform v2.2.0 conventions*
