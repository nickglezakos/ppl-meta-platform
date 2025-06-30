# PPL Meta Platform Infrastructure

This repository implements a hybrid microservices deployment with Nginx Gateway and Mesh VPN, designed for scalable cloud-to-edge computing.

## 🏗️ Architecture Overview

The PPL Meta Platform follows a hybrid microservices architecture with:

- **Cloud-Hosted Nginx API Gateway**: Central entry point handling authentication and routing
- **User Management Service**: Authentication, authorization, and user operations
- **Media Service**: File processing, storage, and streaming
- **Orchestrator Service**: Business logic and workflow coordination
- **Gateway Service**: API routing and service discovery
- **Mesh VPN**: Secure communication with edge devices

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenSSL (for SSL certificates)
- Git

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd ppl-meta-node
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.template .env

# Edit .env with your settings
nano .env
```

**Important**: Update these in `.env`:
- `SECRET_KEY`: Generate a secure secret key
- `MAIL_*`: Configure your email settings
- `DOMAIN_NAME`: Your actual domain name
- All default passwords

### 3. Start Infrastructure

```bash
# Make startup script executable
chmod +x start-infrastructure.sh

# Start all services
./start-infrastructure.sh
```

### 4. Access Services

- **Main Gateway**: https://localhost
- **API Documentation**: http://localhost/api/docs
- **User Management**: http://localhost/users/
- **Media Service**: http://localhost/media/
- **Monitoring (Prometheus)**: http://localhost:9090
- **Dashboard (Grafana)**: http://localhost:3000 (admin/admin)
- **Service Discovery (Consul)**: http://localhost:8500

## 📋 Service Details

### Core Services

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| Nginx Gateway | 80/443 | Reverse proxy, SSL termination | `/health` |
| PPL Gateway | 8080 | API routing, service discovery | `/health` |
| User Management | 8001 | Authentication, user ops | `/api/v1/health` |
| Media Service | 8000 | File processing, storage | `/health` |
| Orchestrator | 8002 | Business logic, workflows | `/api/v1/health` |

### Infrastructure Services

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5433 | Primary database |
| Redis | 6379 | Caching, sessions |
| Consul | 8500 | Service discovery |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Monitoring dashboard |
| WireGuard | 51820/udp | VPN for edge devices |

## 🔧 Development

### Building Individual Services

```bash
# User Management Service
docker build -t ppl-meta-node .

# Build and run locally
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

### Viewing Logs

```bash
# All services
docker-compose -f docker-compose.infrastructure.yml logs -f

# Specific service
docker-compose -f docker-compose.infrastructure.yml logs -f ppl-meta-node

# Nginx access logs
tail -f nginx/logs/access.log
```

### Service Management

```bash
# Stop all services
docker-compose -f docker-compose.infrastructure.yml down

# Restart specific service
docker-compose -f docker-compose.infrastructure.yml restart ppl-meta-node

# Update and restart
docker-compose -f docker-compose.infrastructure.yml up -d --build ppl-meta-node
```

## 🌐 Mesh VPN Configuration

### Server Setup (Already Configured)

The WireGuard VPN server is automatically configured in Docker Compose.

### Edge Device Configuration

1. **Generate client config**: Access the WireGuard container
   ```bash
   docker exec -it ppl-wireguard cat /config/peer1/peer1.conf
   ```

2. **Install on edge device**: Copy the config to your edge device and start WireGuard

3. **Update device mapping**: Edit `src/microservice_config.py` to add your device IPs

### Edge Device Integration

```python
# Access edge device from microservices
from src.microservice_config import mesh_vpn

# Get edge device URL
device_url = mesh_vpn.get_edge_device_url("iot-controller", 8000)

# Make request to edge device
response = httpx.get(f"{device_url}/api/status")
```

## 📊 Monitoring & Observability

### Prometheus Metrics

- Service health and performance metrics
- Request rates and response times
- Resource utilization
- Custom application metrics

### Grafana Dashboards

Default dashboards for:
- Service overview
- Request/response metrics
- Database performance
- Infrastructure health

### Log Aggregation

Logs are collected in:
- `nginx/logs/` - Nginx access and error logs
- `logs/` - Application logs
- Docker logs via `docker-compose logs`

## 🔐 Security

### SSL/TLS

- Self-signed certificates for development (auto-generated)
- For production: Replace certificates in `nginx/ssl/`

### Service Authentication

- Internal service-to-service auth via `X-Service-Secret` header
- JWT tokens for user authentication
- Rate limiting on API endpoints

### VPN Security

- WireGuard for secure edge device communication
- Isolated networks for internal service communication
- Firewall rules in Docker networks

## 🚀 Production Deployment

### Cloud Deployment

1. **Update configurations**:
   - Use proper SSL certificates
   - Configure production database
   - Set up proper secrets management
   - Configure monitoring alerts

2. **Infrastructure as Code**:
   - Use Terraform or CloudFormation
   - Set up CI/CD pipelines
   - Configure auto-scaling

3. **Security hardening**:
   - Enable firewall rules
   - Set up VPN access controls
   - Configure monitoring and alerting

### Edge Device Deployment

1. **VPN Setup**: Configure WireGuard on edge devices
2. **Service Discovery**: Register edge services with Consul
3. **Monitoring**: Set up monitoring agents on edge devices

## 🛠️ Troubleshooting

### Common Issues

**Services not starting**:
```bash
# Check service status
docker-compose -f docker-compose.infrastructure.yml ps

# Check logs
docker-compose -f docker-compose.infrastructure.yml logs [service-name]
```

**Database connection issues**:
```bash
# Check database is running
docker exec -it ppl-postgres pg_isready -U nickadmin

# Connect to database
docker exec -it ppl-postgres psql -U nickadmin -d ppl_db
```

**SSL certificate issues**:
```bash
# Regenerate self-signed certificates
rm nginx/ssl/*
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout nginx/ssl/ppl-meta.key \
    -out nginx/ssl/ppl-meta.crt \
    -subj "/C=US/ST=State/L=City/O=PPL Meta/CN=localhost"
```

**VPN connectivity issues**:
```bash
# Check WireGuard status
docker exec -it ppl-wireguard wg show

# Check VPN logs
docker logs ppl-wireguard
```

### Health Checks

```bash
# Test all service health endpoints
curl http://localhost/health
curl http://localhost:8001/api/v1/health
curl http://localhost:8000/health
curl http://localhost:8080/health
```

## 📚 API Documentation

- **Main API Docs**: http://localhost/api/docs
- **User Management**: http://localhost:8001/docs
- **OpenAPI Specs**: Available at `/openapi.json` for each service

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the troubleshooting section above
- Review logs for error messages
- Check service health endpoints
- Open an issue in the repository
