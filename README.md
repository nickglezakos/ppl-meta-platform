# PPL Meta Platform - Unified Monorepo

A comprehensive microservices platform for people detection, recognition, and management using computer vision and AI technologies.

## 🔐 Security Features (v1.2.0-security)

**LATEST RELEASE**: [v1.2.0-security](https://github.com/nickglezakos/ppl-meta-platform/releases/tag/v1.2.0-security) - Comprehensive secrets management system

### 🛡️ Security Highlights

- **Zero Hardcoded Secrets**: All passwords, keys, and credentials are securely generated and managed
- **Cryptographic Security**: 256-bit secure random generation for all secrets
- **Docker Secrets Integration**: Production-ready deployment with Docker secrets
- **Secret Rotation**: Automated secret rotation capabilities with backup
- **Encryption at Rest**: Optional AES-256 encryption for secret storage
- **External Key Management**: Integration with Vault, AWS, and Azure key management

### 🔑 Quick Security Setup

```bash
# Development environment
./setup-secrets.sh

# Production environment
python secrets/manage_secrets.py generate --encrypted
python secrets/manage_secrets.py create-docker
docker-compose -f docker-compose.secrets.yml up -d
```

## 🏗️ Architecture Overview

This monorepo contains all services and infrastructure for the PPL Meta platform:

```text
ppl-meta-code/
├── services/
│   ├── gateway/         # API Gateway & Routing
│   ├── media/          # Media Processing Service
│   ├── user-management/ # User Management Service (ppl-meta-node)
│   ├── orchestrator/   # Service Orchestration
│   └── vision/         # Computer Vision & AI
├── infrastructure/
│   ├── database/       # Database configurations
│   ├── monitoring/     # Monitoring & logging
│   ├── nginx/         # Reverse proxy configs
│   └── vpn/           # VPN & security
├── secrets/            # 🔐 Secrets Management System
│   ├── manage_secrets.py # CLI for secret management
│   └── requirements.txt  # Dependencies
├── shared/
│   ├── auth/          # Shared authentication
│   ├── config/        # Common configurations
│   └── utils/         # Shared utilities
└── docs/              # Documentation
```

## 🚀 Services

### Core Services

| Service | Description | Technology | Port | Status |
|---------|-------------|------------|------|--------|
| **Gateway** | API Gateway & Load Balancer | Python/FastAPI | 8000 | 🟡 Development |
| **User Management** | Authentication & User APIs | Python/FastAPI | 8001 | ✅ Active |
| **Media** | Video/Image Processing | Python/FastAPI | 8002 | ✅ Active |
| **Orchestrator** | Service Coordination | Python/FastAPI | 8003 | 🟡 Development |
| **Vision** | AI/ML Computer Vision | Python/TensorFlow | 8004 | 🔄 Planning |

### Infrastructure Services

| Component | Description | Technology |
|-----------|-------------|------------|
| **Database** | PostgreSQL with Redis | Docker |
| **Monitoring** | Prometheus + Grafana | Docker |
| **Nginx** | Reverse Proxy | Docker |
| **VPN** | WireGuard VPN | Docker |

## 🛠️ Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git

### Setup Development Environment

1. **Clone & Setup**
   ```bash
   git clone https://github.com/nickglezakos/ppl-meta-platform.git
   cd ppl-meta-platform
   ```

2. **Start Infrastructure**
   ```bash
   docker-compose -f docker-compose.ecosystem.yml up -d
   ```

3. **Setup Individual Services**
   ```bash
   # User Management Service
   cd ppl-meta-node
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python src/main.py
   
   # Media Service
   cd ../ppl-meta-media
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python src/main.py
   ```

## 📋 Development Guidelines

### Git Workflow
- **Main Branch**: `main` - Production-ready code
- **Development**: `develop` - Integration branch
- **Features**: `feature/service-name/feature-description`
- **Hotfixes**: `hotfix/issue-description`

### Service Development
1. Each service should be independently deployable
2. Use consistent Python version (3.11+) across all services
3. Follow FastAPI patterns for new services
4. Include comprehensive tests
5. Document API endpoints

### Environment Management
- Use `.env` files for service-specific configuration
- Shared configuration in `shared/config/`
- Never commit secrets or credentials

## 🐳 Docker Development

### Full Stack Development
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f [service-name]

# Rebuild specific service
docker-compose build [service-name]
```

### Individual Service Development
```bash
# Run service in development mode
cd [service-directory]
docker-compose up --build
```

## 📊 Monitoring & Health Checks

- **Health Checks**: `/health` endpoint on each service
- **Metrics**: Prometheus metrics at `/metrics`
- **Documentation**: Swagger UI at `/docs` for each API service

## 🔐 Security

- JWT-based authentication
- Role-based access control (RBAC)
- API rate limiting
- VPN access for production environments

## 📚 Documentation

**📖 Complete Documentation**: [docs/README.md](./docs/README.md)

### Quick Links
- **[Current Development Issues](./docs/current/)** - Active development and issues
- **[User Testing Issues](./docs/current/user-testing/PPL_META_PLATFORM_USER_TESTING_ISSUES.md)** - Bug reports and user feedback
- **[Vision Service Development](./docs/current/vision-service/PPL_META_VISION_SERVICE_ISSUES.md)** - New microservice planning
- **[Technical Documentation](./docs/technical/)** - API specs, database design, infrastructure
- **[User Guides](./docs/guides/)** - Setup and usage guides

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For questions and support:
- **Issues**: GitHub Issues
- **Email**: nick.glezakos@gmail.com
- **Documentation**: See `docs/` directory

## 📄 License

[License information to be added]

---

**Built with ❤️ by the PPL Meta Team**
