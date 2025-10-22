# Apache Integration Options for PPL Meta Mini Service

## Overview

There are two main approaches to integrate PPL Meta Mini with Apache:

### Option A: Apache Reverse Proxy (Recommended)
- Keep Uvicorn/FastAPI running internally
- Apache serves as reverse proxy to forward requests
- Best for development and production deployment
- Easier to implement and maintain

### Option B: Apache + mod_wsgi
- Replace Uvicorn with Apache using mod_wsgi
- Direct Apache serving of FastAPI application
- More complex setup but potentially better performance
- Requires WSGI adapter for FastAPI

---

## Option A: Apache Reverse Proxy Configuration

### Benefits
- ✅ Keep existing Uvicorn setup unchanged
- ✅ SSL termination at Apache level
- ✅ Load balancing capabilities
- ✅ Static file serving by Apache
- ✅ Easy to configure and debug
- ✅ Can run multiple FastAPI instances

### Apache Virtual Host Configuration

Create `/etc/apache2/sites-available/ppl-meta-mini.conf`:

```apache
<VirtualHost *:80>
    ServerName ppl-meta-mini.local
    DocumentRoot /var/www/html
    
    # Reverse proxy to FastAPI service
    ProxyPreserveHost On
    ProxyRequests Off
    
    # Main API endpoints
    ProxyPass /api/v1/ http://localhost:8004/api/v1/
    ProxyPassReverse /api/v1/ http://localhost:8004/api/v1/
    
    # Health check endpoint
    ProxyPass /health http://localhost:8004/health
    ProxyPassReverse /health http://localhost:8004/health
    
    # Swagger UI (optional for production)
    ProxyPass /docs http://localhost:8004/docs
    ProxyPassReverse /docs http://localhost:8004/docs
    
    # OpenAPI schema
    ProxyPass /openapi.json http://localhost:8004/openapi.json
    ProxyPassReverse /openapi.json http://localhost:8004/openapi.json
    
    # Optional: Serve static files directly from Apache
    Alias /static /path/to/static/files
    <Directory "/path/to/static/files">
        Require all granted
    </Directory>
    
    # Logging
    ErrorLog ${APACHE_LOG_DIR}/ppl-meta-mini_error.log
    CustomLog ${APACHE_LOG_DIR}/ppl-meta-mini_access.log combined
</VirtualHost>
```

### SSL Configuration (HTTPS)

Create `/etc/apache2/sites-available/ppl-meta-mini-ssl.conf`:

```apache
<VirtualHost *:443>
    ServerName ppl-meta-mini.local
    DocumentRoot /var/www/html
    
    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /path/to/your/certificate.crt
    SSLCertificateKeyFile /path/to/your/private.key
    
    # Reverse proxy configuration (same as HTTP)
    ProxyPreserveHost On
    ProxyRequests Off
    
    # Forward original protocol headers
    ProxyPassReverse /api/v1/ http://localhost:8004/api/v1/
    ProxyPass /api/v1/ http://localhost:8004/api/v1/
    ProxyPassReverse /health http://localhost:8004/health
    ProxyPass /health http://localhost:8004/health
    
    # Set headers for FastAPI to know about HTTPS
    ProxyPassReverse / http://localhost:8004/
    ProxyPass / http://localhost:8004/
    
    Header always set X-Forwarded-Proto "https"
    Header always set X-Forwarded-Port "443"
    
    ErrorLog ${APACHE_LOG_DIR}/ppl-meta-mini_ssl_error.log
    CustomLog ${APACHE_LOG_DIR}/ppl-meta-mini_ssl_access.log combined
</VirtualHost>
```

### Setup Commands for Option A

```bash
# Enable required Apache modules
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod headers
sudo a2enmod ssl

# Enable the site
sudo a2ensite ppl-meta-mini.conf
sudo a2ensite ppl-meta-mini-ssl.conf  # if using SSL

# Test configuration
sudo apache2ctl configtest

# Restart Apache
sudo systemctl restart apache2

# Add to /etc/hosts for local testing
echo "127.0.0.1 ppl-meta-mini.local" | sudo tee -a /etc/hosts
```

---

## Option B: Apache + mod_wsgi Configuration

### Benefits
- ✅ Direct Apache serving (no additional process)
- ✅ Better integration with Apache features
- ✅ Potentially better performance for high load
- ✅ Single process management

### Challenges
- ❌ More complex setup
- ❌ FastAPI async features may be limited
- ❌ Harder to debug
- ❌ Requires WSGI adapter

### Required Dependencies

```bash
# Install mod_wsgi for Python
sudo apt-get install libapache2-mod-wsgi-py3
# or
pip install mod_wsgi

# Enable module
sudo a2enmod wsgi
```

### WSGI Application File

Create `/path/to/ppl-meta-mini/wsgi.py`:

```python
#!/usr/bin/env python3
"""
WSGI entry point for PPL Meta Mini FastAPI application
"""
import sys
import os

# Add the source directory to Python path
sys.path.insert(0, '/path/to/ppl-meta-mini/src')

# Set environment variables if needed
os.environ.setdefault('PYTHONPATH', '/path/to/ppl-meta-mini/src')

from main import app

# FastAPI WSGI application
application = app
```

### Apache Virtual Host for mod_wsgi

Create `/etc/apache2/sites-available/ppl-meta-mini-wsgi.conf`:

```apache
<VirtualHost *:80>
    ServerName ppl-meta-mini.local
    DocumentRoot /var/www/html
    
    # WSGI Configuration
    WSGIDaemonProcess ppl-meta-mini python-path=/path/to/ppl-meta-mini/src
    WSGIProcessGroup ppl-meta-mini
    WSGIScriptAlias / /path/to/ppl-meta-mini/wsgi.py
    
    <Directory /path/to/ppl-meta-mini>
        WSGIApplicationGroup %{GLOBAL}
        Require all granted
    </Directory>
    
    # Static files (if any)
    Alias /static /path/to/static/files
    <Directory "/path/to/static/files">
        Require all granted
    </Directory>
    
    ErrorLog ${APACHE_LOG_DIR}/ppl-meta-mini_wsgi_error.log
    CustomLog ${APACHE_LOG_DIR}/ppl-meta-mini_wsgi_access.log combined
</VirtualHost>
```

---

## Comparison and Recommendations

### Option A: Reverse Proxy (Recommended)

**Pros:**
- Easier setup and maintenance
- Keep existing development workflow
- Better debugging capabilities
- Can use Uvicorn's reload features in development
- Async FastAPI features work perfectly
- Can run multiple instances for load balancing

**Cons:**
- Additional process to manage
- Slightly more resource usage

**Best for:** Development, staging, and production environments

### Option B: mod_wsgi

**Pros:**
- Single process management
- Tight Apache integration
- Potentially better performance for sync operations

**Cons:**
- Complex setup
- May lose some FastAPI async benefits
- Harder to debug
- Less flexible for development

**Best for:** High-performance production environments with sync workloads

---

## Implementation Steps

### For Option A (Reverse Proxy)

1. **Keep PPL Meta Mini running as is:**
   ```bash
   cd /path/to/ppl-meta-mini/src
   python main.py
   ```

2. **Configure Apache virtual host**
3. **Test the proxy setup**
4. **Add SSL if needed**

### For Option B (mod_wsgi)

1. **Create WSGI adapter**
2. **Install mod_wsgi**
3. **Configure Apache virtual host**
4. **Stop Uvicorn service**
5. **Test WSGI setup**

---

## Production Considerations

### Load Balancing (Option A)
```apache
# Multiple FastAPI instances
ProxyPass /api/v1/ balancer://ppl-meta-cluster/
ProxyPassReverse /api/v1/ balancer://ppl-meta-cluster/

<Proxy balancer://ppl-meta-cluster>
    BalancerMember http://localhost:8004
    BalancerMember http://localhost:8005
    BalancerMember http://localhost:8006
    ProxySet lbmethod=byrequests
</Proxy>
```

### Security Headers
```apache
# Security headers
Header always set X-Content-Type-Options "nosniff"
Header always set X-Frame-Options "DENY"
Header always set X-XSS-Protection "1; mode=block"
Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
```

### Rate Limiting
```apache
# Enable mod_evasive for basic rate limiting
LoadModule evasive24_module modules/mod_evasive24.so

<IfModule mod_evasive24.c>
    DOSHashTableSize    2048
    DOSPageCount        10
    DOSPageInterval     1
    DOSSiteCount        50
    DOSSiteInterval     1
    DOSBlockingPeriod   300
</IfModule>
```

---

## Recommendation

**For PPL Meta Mini, I recommend Option A (Reverse Proxy)** because:

1. **Maintains async capabilities** - FastAPI's async features work perfectly
2. **Easier development** - Keep existing workflow unchanged
3. **Better debugging** - Can easily check both Apache and FastAPI logs
4. **Flexibility** - Can easily scale to multiple instances
5. **SSL termination** - Handle HTTPS at Apache level
6. **Static file serving** - Apache can serve documentation/static files efficiently

Would you like me to create the specific configuration files for your setup?