# Deployment Documentation

## � Overview

This directory contains deployment guides, procedures, and configuration files for the PPL Meta Platform.

## 📁 Directory Structure

### **Docker Configurations** (`docker/`)

Container deployment configurations:

- `docker-compose.ecosystem.yml` - Complete ecosystem deployment with all services
- `docker-compose.minimal.yml` - Minimal deployment configuration for testing
- `docker-compose.secrets.yml` - Secret management and security configuration
- `docker-compose.service-discovery-test.yml` - Service discovery testing environment

### **Nginx Configurations** (`nginx/`)

Reverse proxy and load balancing configurations:

- `nginx-local-dev.conf` - Local development nginx configuration with service routing

### **General Deployment Documentation**

- `PORT_CONFLICT_ANALYSIS_AND_SOLUTIONS.md` - Port conflict resolution and management guide

### Deployment Types

- **Local Development** - Setting up local development environment *(Coming Soon)*
- **Docker Deployment** - Containerized deployment guide *(Coming Soon)*
- **Cloud Deployment** - Cloud platform deployment *(Coming Soon)*

## 🎯 Quick Deployment

### For Local Development
```bash
# Start all services locally
🚀 Start All Local Python Services
```

### For Production
```bash
# Docker deployment
docker-compose -f docker-compose.minimal.yml up -d
```

---

*Deployment documentation for PPL Meta Platform v2.2.0*
