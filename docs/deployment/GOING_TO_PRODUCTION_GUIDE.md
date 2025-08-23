# PPL Meta Platform - Going to Production Guide

## 🚀 Production Readiness Checklist

This document outlines the essential configurations and changes required when transitioning the PPL Meta Platform from development to production environment.

---

## 📊 **CRITICAL: Distributed Tracing & Monitoring**

### Issue: OpenTelemetry/Jaeger Configuration

**Current Development State**: Distributed tracing is **DISABLED** in Gateway service  
**Production Requirement**: Enable distributed tracing with proper Jaeger infrastructure

#### Current Configuration (Development)

```python
# ppl-meta-gateway/src/config.py
tracing_enabled: bool = False  # ⚠️ DISABLED for development
jaeger_endpoint: str = "http://localhost:14268/api/traces"
jaeger_agent_host: str = "localhost"
jaeger_agent_port: int = 6831
```

#### Production Changes Required

1. **Deploy Jaeger Infrastructure**

   ```bash
   # Option 1: Docker Compose (recommended for production)
   docker run -d --name jaeger \
     -p 16686:16686 \
     -p 14268:14268 \
     -p 14250:14250 \
     -p 6831:6831/udp \
     -p 6832:6832/udp \
     jaegertracing/all-in-one:latest
   
   # Option 2: Kubernetes deployment
   kubectl apply -f https://github.com/jaegertracing/jaeger-operator/releases/download/v1.29.0/jaeger-operator.yaml
   ```

2. **Enable Tracing in Gateway Configuration**
   ```python
   # ppl-meta-gateway/src/config.py
   tracing_enabled: bool = True  # ✅ ENABLE for production
   jaeger_endpoint: str = "http://jaeger-collector:14268/api/traces"  # Update for production endpoint
   jaeger_agent_host: str = "jaeger-agent"  # Update for production host
   jaeger_agent_port: int = 6831
   tracing_sampling_rate: float = 0.1  # Adjust sampling rate for production (1.0 = 100%, 0.1 = 10%)
   ```

3. **Restart Gateway Service** after configuration changes

#### Benefits of Production Tracing
- **Request Flow Visibility**: Track requests across all microservices
- **Performance Monitoring**: Identify bottlenecks and slow operations
- **Error Debugging**: Trace error propagation through service calls
- **SLA Monitoring**: Monitor response times and service availability

---

## 🗄️ **CRITICAL: Caching Configuration**

### Issue: All Caching Layers Disabled
**Current Development State**: Caching is **DISABLED** at multiple levels for development
**Production Requirement**: Enable caching for performance optimization

#### Current Configuration (Development)

**1. Nginx Proxy Caching - DISABLED**
```nginx
# nginx-local-dev.conf
proxy_cache off;                    # ⚠️ DISABLED
proxy_buffering off;                # ⚠️ DISABLED
add_header Cache-Control "no-cache, no-store, must-revalidate" always;  # ⚠️ FORCE NO CACHE
```

**2. API Response Caching - DISABLED**
```nginx
# All API requests forced through Gateway without caching
location /api/ {
    proxy_pass http://gateway_service;
    # No caching headers for API responses
}
```

#### Production Changes Required

**1. Enable Nginx Caching with Proper Configuration**
```nginx
# nginx-production.conf
# Enable proxy caching
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=1g inactive=60m use_temp_path=off;

server {
    # Static assets caching (aggressive)
    location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        proxy_cache api_cache;
        proxy_cache_valid 200 1y;
    }
    
    # API response caching (conservative)
    location /api/v1/media/analytics {
        proxy_pass http://gateway_service;
        proxy_cache api_cache;
        proxy_cache_valid 200 5m;  # Cache analytics for 5 minutes
        proxy_cache_key "$scheme$request_method$host$request_uri";
        add_header X-Cache-Status $upstream_cache_status;
    }
    
    # Media file caching (moderate)
    location /api/v1/media/download/ {
        proxy_pass http://gateway_service;
        proxy_cache api_cache;
        proxy_cache_valid 200 1h;  # Cache media downloads for 1 hour
    }
    
    # Authentication endpoints - NO CACHING
    location ~ /api/v1/users/(login|logout|register) {
        proxy_pass http://gateway_service;
        proxy_cache off;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}
```

**2. Application-Level Caching Strategy**
```python
# Add to Gateway service configuration
class Settings(BaseSettings):
    # Redis caching configuration
    redis_enabled: bool = True
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Cache TTL settings
    analytics_cache_ttl: int = 300  # 5 minutes
    media_metadata_cache_ttl: int = 3600  # 1 hour
    user_profile_cache_ttl: int = 1800  # 30 minutes
```

**3. Database Query Caching**
```python
# Example: Add Redis caching to analytics endpoint
@api_router.get("/media/analytics")
async def get_media_analytics(request: Request):
    cache_key = f"analytics:{user_id}"
    
    # Try cache first
    cached_result = await redis_client.get(cache_key)
    if cached_result:
        return json.loads(cached_result)
    
    # Calculate analytics
    analytics = await calculate_user_analytics(user_id)
    
    # Cache result
    await redis_client.setex(cache_key, 300, json.dumps(analytics))
    
    return analytics
```

#### Production Caching Strategy
- **Static Assets**: 1 year cache with immutable headers
- **Media Files**: 1 hour cache for downloads, no cache for uploads
- **Analytics Data**: 5-minute cache (frequent updates expected)
- **User Profiles**: 30-minute cache (occasional updates)
- **Authentication**: No caching (security requirement)

---

## 🔒 **Security & Configuration**

### Environment Variables
```bash
# Production environment variables
SECRET_KEY=<strong-production-secret-256-bits>
DATABASE_URL=postgresql://prod_user:secure_pass@db-server:5432/ppl_meta_prod
REDIS_URL=redis://redis-server:6379/0

# Jaeger configuration
JAEGER_ENDPOINT=http://jaeger-collector:14268/api/traces
JAEGER_AGENT_HOST=jaeger-agent
JAEGER_SAMPLING_RATE=0.1

# Email configuration (if not already set)
SMTP_SERVER=smtp.production-provider.com
SMTP_PORT=587
SMTP_USERNAME=noreply@yourdomain.com
SMTP_PASSWORD=<secure-smtp-password>
```

### SSL/TLS Configuration
```nginx
# nginx-production.conf
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/ssl/certificate.crt;
    ssl_certificate_key /path/to/ssl/private.key;
    
    # SSL security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
}
```

---

## 📈 **Performance Optimization**

### Database Optimization
- **Connection Pooling**: Configure proper connection pool sizes
- **Indexing**: Ensure all frequently queried fields are indexed
- **Query Optimization**: Review and optimize slow queries

### Service Scaling
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  gateway:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

---

## 🏥 **Monitoring & Health Checks**

### Production Health Monitoring
```python
# Enhanced health check endpoints
@api_router.get("/health/detailed")
async def detailed_health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "services": {
            "database": await check_database_health(),
            "redis": await check_redis_health(),
            "jaeger": await check_jaeger_health(),
        },
        "metrics": {
            "active_connections": get_active_connections(),
            "memory_usage": get_memory_usage(),
            "cache_hit_ratio": get_cache_hit_ratio(),
        }
    }
```

### Logging Configuration
```python
# Production logging settings
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "production": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/ppl-meta/app.log",
            "maxBytes": 100 * 1024 * 1024,  # 100MB
            "backupCount": 5,
            "formatter": "production",
        },
    },
    "root": {
        "level": "INFO",  # Change from DEBUG to INFO for production
        "handlers": ["file"],
    },
}
```

---

## ✅ **Pre-Production Checklist**

### Infrastructure
- [ ] Jaeger tracing infrastructure deployed and accessible
- [ ] Redis caching server deployed and configured
- [ ] SSL certificates installed and configured
- [ ] Production database with proper backup strategy
- [ ] Load balancer configured (if applicable)

### Configuration Changes
- [ ] `tracing_enabled: bool = True` in Gateway configuration
- [ ] Nginx caching enabled with appropriate TTL settings
- [ ] Production environment variables set
- [ ] Database connection pooling configured
- [ ] Log levels adjusted to INFO/WARN for production

### Security
- [ ] All default passwords changed
- [ ] SSL/TLS properly configured
- [ ] Security headers implemented
- [ ] API rate limiting configured
- [ ] Input validation and sanitization verified

### Performance
- [ ] Load testing completed
- [ ] Database queries optimized
- [ ] Caching strategy tested and validated
- [ ] CDN configured for static assets (if applicable)

### Monitoring
- [ ] Health check endpoints tested
- [ ] Log aggregation configured
- [ ] Alerting rules configured
- [ ] Backup and recovery procedures tested
- [ ] Disaster recovery plan documented

---

## 🚨 **Critical Warnings**

### ⚠️ **DO NOT DEPLOY WITHOUT:**
1. **Jaeger Infrastructure**: Enabling tracing without Jaeger will cause connection errors
2. **Cache Invalidation Strategy**: Ensure cache keys are properly invalidated on data updates
3. **SSL Certificates**: Never deploy HTTP-only in production
4. **Database Backups**: Implement automated backup strategy before going live
5. **Monitoring**: Deploy with comprehensive monitoring from day one

### 🔄 **Post-Deployment Verification**
1. Test all critical user flows (registration, login, media upload)
2. Verify Jaeger traces are being collected
3. Confirm caching is working (check response headers)
4. Monitor performance metrics for first 24 hours
5. Validate SSL certificate and security headers

---

## 📞 **Emergency Rollback Plan**

If issues arise after enabling production configurations:

### Quick Rollback Commands
```bash
# Disable tracing immediately
# In ppl-meta-gateway/src/config.py:
tracing_enabled: bool = False

# Disable caching immediately
# In nginx configuration:
proxy_cache off;
proxy_buffering off;

# Restart services
docker-compose restart gateway nginx
```

### Monitoring During Rollback
- Watch error rates in application logs
- Monitor response times
- Check database connection pools
- Verify user experience is restored

---

**Document Version**: 1.0  
**Last Updated**: July 16, 2025  
**Next Review**: Before production deployment
