# User Management Service

Handles user authentication, authorization, and user operations for the PPL Meta Platform.

## Features

- User registration and authentication
- JWT token management
- Role-based access control
- Password reset functionality
- Email verification
- User action logging

## API Endpoints

- `/api/v1/users/` - User management
- `/api/v1/auth/` - Authentication
- `/api/v1/health` - Health check

## Development

```bash
cd services/user-management
uvicorn src.main:app --reload --port 8001
```
