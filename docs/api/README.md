# API Documentation

## 📋 Overview

This directory contains API specifications and documentation for all PPL Meta Platform services.

## 📁 Available Documentation

### **Service API Documentation**

- `cameras_docs.html` - Camera service API documentation with endpoints, schemas, and examples
- `media_docs.html` - Media service API documentation with file handling and processing endpoints

## 🚀 API Overview

### **Camera Service API**

The Camera Service provides endpoints for:

- Camera registration and management
- Live streaming control
- Snapshot capture
- Camera status monitoring
- Configuration management

**Base URL**: `http://localhost:8005`
**Documentation**: [cameras_docs.html](cameras_docs.html)

### **Media Service API**

The Media Service provides endpoints for:

- Media file upload and download
- Image and video processing
- File metadata management
- Storage management
- Content delivery

**Base URL**: `http://localhost:8000`
**Documentation**: [media_docs.html](media_docs.html)

## 📡 Service Integration

### **Authentication**

All services use token-based authentication:

```http
Authorization: Bearer <service-token>
```

### **Common Response Format**

```json
{
  "status": "success|error",
  "data": {},
  "message": "Description",
  "timestamp": "2025-08-22T10:00:00Z"
}
```

### **Error Handling**

Standard HTTP status codes are used:

- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error

## 🔍 API Testing

### **Health Check Endpoints**

All services provide health check endpoints:

```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "camera-service",
  "version": "2.5.0",
  "timestamp": "2025-08-22T10:00:00Z"
}
```

### **Testing Tools**

Recommended tools for API testing:

- **Postman** - Interactive API testing
- **curl** - Command line testing
- **httpie** - User-friendly HTTP client
- **Swagger UI** - Interactive API documentation

## 📊 Performance Considerations

### **Rate Limiting**

Services implement rate limiting:

- **Camera Service**: 100 requests/minute per client
- **Media Service**: 50 file operations/minute per client

### **Pagination**

List endpoints support pagination:

```http
GET /api/cameras?page=1&limit=20
```

### **Filtering and Sorting**

Query parameters for filtering:

```http
GET /api/media?type=image&sort=created_at&order=desc
```

## 🛡️ Security

### **API Security Headers**

All responses include security headers:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`

### **CORS Configuration**

Cross-Origin Resource Sharing (CORS) is configured for:

- Frontend applications
- Development environments
- Authorized third-party integrations

### **Input Validation**

All endpoints implement:

- Request schema validation
- Input sanitization
- Parameter type checking
- File upload validation

## 📞 Related Documentation

- **Architecture**: See `../architecture/` for service design
- **Development**: See `../development/` for implementation guides
- **Deployment**: See `../deployment/` for service configuration

## 🔄 API Versioning

### **Version Strategy**

APIs follow semantic versioning:

- **Major Version**: Breaking changes
- **Minor Version**: New features, backward compatible
- **Patch Version**: Bug fixes

### **Version Headers**

API version is specified in headers:

```http
API-Version: 2.5.0
Accept: application/json
```

### **Deprecation Policy**

- Advance notice for deprecated endpoints
- Minimum 6-month support for deprecated features
- Clear migration paths for new versions

## 📚 OpenAPI Specifications

### **Automatic Generation**

API documentation is automatically generated from:

- FastAPI service definitions
- Pydantic model schemas
- Endpoint annotations

### **Interactive Documentation**

Each service provides interactive docs:

- **Camera Service**: `http://localhost:8005/docs`
- **Media Service**: `http://localhost:8000/docs`

**Last Updated**: August 2025
**Maintained by**: PPL Meta API Team
