
# PPL Meta Node - User Management Service

## Overview

PPL Meta Node is a FastAPI-based microservice responsible for user management, authentication, and authorization within the PPL Meta platform. It operates as a separate service from PPL Meta Media and provides secure user operations and inter-service authentication.

## Key Features

- ✅ **User Registration & Authentication**
- ✅ **JWT Token Management** 
- ✅ **Email Verification**
- ✅ **Password Reset**
- ✅ **Role-Based Access Control (RBAC)**
- ✅ **Inter-Service Authentication**
- ✅ **API Versioning** (`/api/v1/`)
- ✅ **Health Monitoring**
- ✅ **Docker Support**
- ✅ **PostgreSQL Database**

## Architecture

### Service Configuration
- **Port**: 8001 (to avoid conflict with PPL Meta Media on 8000)
- **Database**: PostgreSQL (shared with PPL Media or separate instance)
- **Authentication**: JWT with inter-service token validation
- **API Versioning**: `/api/v1/` with backward compatibility

## API Endpoints

### Authentication & User Management (v1)
- `POST /api/v1/users/register` - Register new user
- `POST /api/v1/users/login` - User login
- `POST /api/v1/users/logout` - User logout
- `GET /api/v1/users/verify-email` - Email verification
- `POST /api/v1/users/forgot-password` - Password reset request
- `POST /api/v1/users/reset-password` - Password reset confirmation
- `POST /api/v1/users/update-password` - Update password

### Inter-Service Authentication
- `POST /api/v1/users/validate-token` - Validate JWT token (service-to-service)
- `GET /api/v1/users/user-info/{user_id}` - Get user info (service-to-service)
- `GET /api/v1/users/user-permissions/{user_id}` - Get user permissions (service-to-service)

### Health & Monitoring
- `GET /api/v1/health/` - Basic health check
- `GET /api/v1/health/detailed` - Detailed health with system metrics
- `GET /api/v1/health/ready` - Kubernetes readiness probe
- `GET /api/v1/health/live` - Kubernetes liveness probe

## Configuration

### Environment Variables (.env)
```bash
# Application Settings
PORT=8001
HOST=0.0.0.0
DEBUG=False

# Database
DATABASE_URL=postgresql://nickadmin:Kodikos%4023@localhost/ppl_db

# Security
SECRET_KEY=your-secret-key
SERVICE_SECRET=shared-service-secret-key

# Service Communication
PPL_MEDIA_SERVICE_URL=http://localhost:8000
```

## Deployment

### Docker Deployment (Recommended)
```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d
```

### Development Mode
```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
python -m src.main
```

## Integration with PPL Meta Media

### Service Communication
Both services communicate via HTTP APIs with JWT token validation for security.

### Shared Network
Both services should run on the same Docker network for seamless communication.

## API Documentation

### Swagger UI
Available at: `http://localhost:8001/docs`

**PPL Meta Node** - Secure, Scalable User Management for the PPL Meta Platform