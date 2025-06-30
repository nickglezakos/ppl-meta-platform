# PPL Meta Platform

Complete infrastructure workspace for the PPL Meta Platform - a hybrid microservices architecture with cloud-to-edge capabilities.

## 🏗️ Workspace Structure

```
ppl-meta-code/
├── services/                    # All microservices
│   ├── gateway/                # API Gateway service
│   ├── user-management/        # User authentication & management
│   ├── media/                  # Media processing & storage
│   ├── orchestrator/           # Business logic coordination
│   └── vision/                 # Machine vision services
├── infrastructure/             # Infrastructure components
│   ├── nginx/                  # Reverse proxy configuration
│   ├── database/               # Database schemas and migrations
│   ├── monitoring/             # Prometheus, Grafana configs
│   └── vpn/                    # WireGuard VPN configuration
├── shared/                     # Shared libraries and utilities
│   ├── config/                 # Common configuration
│   ├── auth/                   # Authentication utilities
│   ├── logging/                # Logging utilities
│   └── utils/                  # Common utilities
├── docs/                       # Documentation
├── tools/                      # Development and deployment tools
├── environments/               # Environment-specific configurations
└── docker-compose.yml         # Main orchestration file
```

## 🚀 Quick Start

```bash
# Setup the workspace
npm run setup

# Start development environment
npm run dev

# Or manually with Docker
docker-compose up -d
```

## 📚 Documentation

- [Architecture Overview](docs/architecture/overview.md)
- [API Documentation](docs/api/README.md)
- [Deployment Guide](docs/deployment/README.md)
- [Development Guide](docs/development/README.md)

## 🔧 Development

Each service is independently developable but shares common utilities and configurations through the `shared/` directory.

## 🌐 Service URLs

- Main Gateway: https://localhost
- API Gateway: http://localhost:8080
- User Management: http://localhost:8001
- Media Service: http://localhost:8000
- Orchestrator: http://localhost:8002
- Monitoring: http://localhost:3000 (Grafana)
- Service Discovery: http://localhost:8500 (Consul)
