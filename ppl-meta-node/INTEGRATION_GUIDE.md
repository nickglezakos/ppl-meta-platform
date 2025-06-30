# PPL Meta Platform - Infrastructure Integration Guide

## 🎯 Overview

Your PPL Meta Platform infrastructure is now set up according to the hybrid microservices deployment described in your infrastructure documentation. Here's what we've built and how to integrate it with your other microservices.

## 🏗️ What's Been Built

### 1. Nginx API Gateway (Cloud-Hosted Entry Point)
- **Location**: `nginx/` directory
- **Configuration**: `nginx/nginx.conf` and `nginx/conf.d/default.conf`
- **Features**: SSL termination, rate limiting, service routing
- **Access**: https://localhost (HTTPS) and http://localhost (HTTP redirect)

### 2. Complete Docker Infrastructure
- **File**: `docker-compose.infrastructure.yml`
- **Services**: All microservices, database, monitoring, VPN
- **Networks**: Isolated networks for security
- **Volumes**: Persistent storage for data

### 3. Service Discovery & Communication
- **File**: `src/microservice_config.py` (enhanced)
- **Features**: Consul integration, internal service auth
- **Capabilities**: Service-to-service communication

### 4. Mesh VPN for Edge Devices
- **Service**: WireGuard VPN server
- **Purpose**: Secure communication with edge devices
- **Configuration**: `wireguard/wg0.conf.template`

### 5. Monitoring & Observability
- **Prometheus**: Metrics collection
- **Grafana**: Dashboards and visualization
- **Consul**: Service discovery UI

## 🔄 Integration with Your Existing Microservices

### Step 1: Move Your Other Microservices

You mentioned having all microservices under `ppl-meta-code` directory. Here's how to integrate them:

```bash
# Example structure you should aim for:
ppl-meta-code/
├── ppl-meta-node/          # User Management (current project)
├── ppl-meta-media/         # Media processing service
├── ppl-meta-orchestrator/  # Business logic orchestrator
├── ppl-meta-gateway/       # API Gateway service
├── ppl-meta-vision/        # Machine vision service
└── docker-compose.ecosystem.yml  # All services together
```

### Step 2: Update Service Configurations

For each microservice, ensure they have:

1. **Health endpoints**: `/health` or `/api/v1/health`
2. **Environment variables**: For service discovery
3. **Docker configuration**: Proper networking
4. **Service registration**: With Consul

### Step 3: Extend Docker Compose

Create a master `docker-compose.ecosystem.yml` that includes all your services:

```yaml
# Include the infrastructure we built
include:
  - path: ppl-meta-node/docker-compose.infrastructure.yml

services:
  # Add your other microservices here
  ppl-meta-vision:
    build: ./ppl-meta-vision
    ports:
      - "8003:8003"
    networks:
      - ppl-network
      - ppl-internal
    # ... other configuration
```

## 🌐 Nginx Routing Configuration

The Nginx configuration is already set up for your core services. To add new microservices:

1. **Add upstream**: In `nginx/nginx.conf`
   ```nginx
   upstream ppl_vision {
       server ppl-meta-vision:8003;
       keepalive 32;
   }
   ```

2. **Add location**: In `nginx/conf.d/default.conf`
   ```nginx
   location /vision/ {
       proxy_pass http://ppl_vision/;
       # ... proxy settings
   }
   ```

## 🔌 Edge Device Integration

### For IoT/Hardware Services

1. **Install WireGuard** on your edge devices
2. **Get client config**: From the WireGuard container
3. **Connect to VPN**: Your devices get IPs like 10.13.13.10, 10.13.13.11, etc.
4. **Access from cloud**: Services can reach edge devices via VPN IPs

### Example Edge Device Communication

```python
# In your microservices
from src.microservice_config import mesh_vpn

# Access IoT controller
iot_url = mesh_vpn.get_edge_device_url("iot-controller", 8000)
response = httpx.get(f"{iot_url}/api/sensors")

# Access camera system
camera_url = mesh_vpn.get_edge_device_url("camera-system", 8001)
response = httpx.post(f"{camera_url}/api/capture")
```

## 📊 Service Discovery Pattern

Each microservice should register itself:

```python
# In your microservice startup
from src.microservice_config import service_discovery

# Register service
await service_discovery.register_service({
    "name": "ppl-meta-vision",
    "address": "0.0.0.0",
    "port": 8003,
    "health_check": "/health"
})
```

## 🚀 Deployment Workflow

### Development
1. **Start infrastructure**: `./start-infrastructure.sh`
2. **Develop services**: Individual `uvicorn` or Docker containers
3. **Test integration**: Via Nginx gateway

### Production
1. **Update environment**: Production secrets and certificates
2. **Deploy to cloud**: Use the Docker Compose setup
3. **Configure DNS**: Point your domain to the server
4. **Set up edge devices**: Install WireGuard clients

## 🔧 Next Steps

### Immediate Actions
1. **Copy `.env.template` to `.env`** and configure
2. **Update secrets**: Change all default passwords
3. **Test the setup**: Run `./start-infrastructure.sh`

### Integration Tasks
1. **Move other microservices** to the ecosystem
2. **Update their configurations** for service discovery
3. **Add Nginx routing** for new services
4. **Set up edge devices** with WireGuard

### Production Preparation
1. **Get proper SSL certificates** (Let's Encrypt or commercial)
2. **Set up monitoring alerts** in Grafana
3. **Configure backup systems** for databases
4. **Set up CI/CD pipelines** for deployments

## 🆘 Support During Integration

### Testing Service Communication

```bash
# Test internal service discovery
docker exec -it ppl-meta-node python -c "
from src.microservice_config import service_discovery
print(service_discovery.get_service_url('media'))
"

# Test VPN connectivity
docker exec -it ppl-wireguard wg show
```

### Monitoring Integration

- **Logs**: `docker-compose logs -f [service-name]`
- **Metrics**: http://localhost:9090 (Prometheus)
- **Dashboards**: http://localhost:3000 (Grafana)
- **Service Discovery**: http://localhost:8500 (Consul)

### Common Integration Issues

1. **Port conflicts**: Check service ports don't overlap
2. **Network isolation**: Ensure services are on correct networks
3. **Environment variables**: Verify all services have required env vars
4. **Health checks**: Make sure health endpoints return 200 OK

## 📋 Checklist for Complete Integration

- [ ] Infrastructure started successfully
- [ ] All core services responding to health checks
- [ ] Nginx routing working for existing services
- [ ] Environment variables configured
- [ ] SSL certificates in place
- [ ] Other microservices moved to ecosystem
- [ ] Service discovery working
- [ ] Edge devices connected via VPN
- [ ] Monitoring dashboards configured
- [ ] Backup systems in place

Your infrastructure is now ready to support the complete PPL Meta Platform ecosystem with secure cloud-to-edge communication!
