# PPL Meta Platform Documentation

## 📋 Documentation Structure & Lifecycle

This directory contains comprehensive documentation for the PPL Meta Platform, organized according to a **document lifecycle workflow** that aligns with our development process.

## 🔄 Document Lifecycle Process

### **Stage 1: Planning** (`planning/`)
All new feature ideas, issue plans, and requirements start here:

- **Purpose**: Initial planning and requirements gathering
- **Naming**: `ISSUE-[number]-[description]-PLAN.md`
- **Template**: `templates/PLANNING_TEMPLATE.md`
- **No subdirectories**: Flat structure for easy management

### **Stage 2: Active Development** (`current/`)
Documents move here when implementation begins:

- **Purpose**: Track active development and implementation progress
- **Naming**: `ISSUE-[number]-[description]-ACTIVE.md`
- **Template**: `templates/IMPLEMENTATION_TEMPLATE.md`
- **No subdirectories**: Flat structure for current work focus

### **Stage 3: Reference Documentation** (Category Directories)
Completed work moves to appropriate category for long-term reference:

- `architecture/` - System design and technical architecture
- `development/` - Implementation guides and development processes
- `deployment/` - Deployment procedures and configurations
- `api/` - Service interfaces and API documentation
- `troubleshooting/` - Issue resolution and debugging guides
- `research/` - Experimental work and research findings

## 🛠️ Quick Start

### Create New Planning Document
```bash
./scripts/docs-lifecycle.sh create 123 "feature-name"
```

### Start Active Development
```bash
./scripts/docs-lifecycle.sh activate 123 "feature-name"
```

### Complete Implementation
```bash
./scripts/docs-lifecycle.sh complete ISSUE-123-feature-name-ACTIVE.md architecture
```

### Check Status
```bash
./scripts/docs-lifecycle.sh status
```

## 📁 Directory Structure

### **Planning** (`planning/`)
New ideas and feature planning:

- All planning documents start here
- Use `PLANNING_TEMPLATE.md` for new documents
- Move to `current/` when implementation begins

### **Current Active Work** (`current/`)
Currently active implementations:

- Documents for work in progress
- Regular status updates required
- Move to appropriate category when complete

### **Architecture** (`architecture/`)
System design and technical architecture:

#### Microservices (`architecture/microservices/`)
- `ENHANCED_MICROSERVICES_ARCHITECTURE.md` - Complete microservices architecture

#### Network Discovery (`architecture/network-discovery/`)
- `MICROSERVICES_NETWORK_DISCOVERY_ARCHITECTURE.md` - Network discovery system
- `NETWORK_DISCOVERY_IMPLEMENTATION_PLAN.md` - Implementation planning
- `NETWORK_DISCOVERY_IMPLEMENTATION_COMPLETE.md` - Completed implementation
- `PPL_META_NETWORK_DISCOVERY.md` - Core network discovery documentation

### **Development** (`development/`)
Implementation guides and development processes:

- `CONTINUOUS_DEVELOPMENT_CONTINUOUS_INTEGRATION.md` - Complete CI/CD strategy
- `RELEASE_NOTES_v2.*.md` - Release notes and changelog

#### Implementation Guides (`development/implementation-guides/`)
- Camera and Flutter implementation guides
- VPN integration documentation
- RTSP frontend integration
- OpenCV integration examples

#### Testing (`development/testing/`)
- Testing procedures and frameworks
- Camera test documentation and results

### **Deployment** (`deployment/`)
Deployment procedures and configurations:

#### Docker (`deployment/docker/`)
- `docker-compose.ecosystem.yml` - Complete ecosystem deployment
- `docker-compose.minimal.yml` - Minimal deployment configuration
- `docker-compose.secrets.yml` - Secret management configuration
- `docker-compose.service-discovery-test.yml` - Service discovery testing

#### Nginx (`deployment/nginx/`)
- `nginx-local-dev.conf` - Local development nginx configuration

### **API Documentation** (`api/`)
Service interfaces and API specifications:

- `cameras_docs.html` - Camera service API documentation
- `media_docs.html` - Media service API documentation

### **Troubleshooting** (`troubleshooting/`)
Issue resolution and debugging guides:

- `KNOWN_ISSUES.md` - Platform known issues
- Network discovery issue documentation
- Problem resolution guides

### **Research** (`research/`)
Experimental work and research findings:

- Proof of concept documentation
- Technology evaluation
- Performance research

### **Templates** (`templates/`)
Document templates for the lifecycle process:

- `PLANNING_TEMPLATE.md` - For new feature planning
- `IMPLEMENTATION_TEMPLATE.md` - For active development
- `REFERENCE_TEMPLATE.md` - For completed implementations

## 🚀 Workflow Integration

### Document Lifecycle Management
Use the provided script for easy document management:

```bash
# Create new planning document
./scripts/docs-lifecycle.sh create 124 "mobile-app-enhancement"

# Activate for development
./scripts/docs-lifecycle.sh activate 124 "mobile-app-enhancement"

# Complete and move to final category
./scripts/docs-lifecycle.sh complete ISSUE-124-mobile-app-enhancement-ACTIVE.md development

# Check current status
./scripts/docs-lifecycle.sh status

# List documents in specific stage
./scripts/docs-lifecycle.sh list planning
./scripts/docs-lifecycle.sh list current
```

### GitHub Integration
- Link documents to GitHub issues using issue numbers
- Reference documents in pull requests
- Use project boards to track document progress
- Integrate with milestone planning

### Development Process Integration
1. **New Feature**: Create planning document
2. **Start Development**: Activate document, move to current
3. **Implementation**: Update progress regularly
4. **Completion**: Move to appropriate reference category
5. **Maintenance**: Update reference docs as needed

## 📊 Legacy Documentation

The following directories contain legacy documentation that follows the previous organization:

- `archive/` - Historical documentation and resolved issues
- `current/` - Previously active working documents (now reorganized)
- `guides/` - Legacy user and deployment guides
- `technical/` - Legacy technical documentation
- `notebooks/` - Jupyter notebooks and research
- `Release Notes/` - Legacy release notes

These will be gradually integrated into the new lifecycle process as they are updated or referenced.

## 🔍 Finding Documentation

### By Development Stage
- **Planning**: Check `planning/` directory
- **Active Work**: Check `current/` directory
- **Completed**: Check appropriate category directories

### By Category
- **System Design**: `architecture/`
- **Implementation**: `development/`
- **Operations**: `deployment/`
- **APIs**: `api/`
- **Problems**: `troubleshooting/`
- **Experiments**: `research/`

### By Topic
- **Network Discovery**: `architecture/network-discovery/`
- **Microservices**: `architecture/microservices/`
- **Testing**: `development/testing/`
- **Docker**: `deployment/docker/`
- **Camera Integration**: Search implementation guides

## 📞 Getting Help

### Process Questions
- Review `DOCUMENT_LIFECYCLE.md` for detailed process information
- Check templates in `templates/` directory
- Use the lifecycle script: `./scripts/docs-lifecycle.sh --help`

### Technical Documentation
- Architecture questions: See `architecture/` directory
- Implementation help: See `development/` directory
- Deployment issues: See `deployment/` and `troubleshooting/`
- API integration: See `api/` directory

### Contributing to Documentation
1. Create new documents using the planning template
2. Follow the naming conventions
3. Update progress regularly for active documents
4. Move completed work to appropriate categories
5. Keep the lifecycle tracking document updated

---

**Documentation Process**: All documents follow the lifecycle: planning → current → category
**Management Tool**: `scripts/docs-lifecycle.sh`
**Process Owner**: Nick Klezakos
**Last Updated**: August 22, 2025

*This documentation structure supports efficient development workflow while maintaining comprehensive reference materials for the PPL Meta Platform.*
