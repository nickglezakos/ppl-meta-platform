# PPL Meta Mini Apache Integration - macOS Setup

## Quick Setup Guide for macOS

### Option A: Apache Reverse Proxy (Recommended)

This setup keeps your existing PPL Meta Mini service running on port 8004 and uses Apache as a reverse proxy.

## Prerequisites

```bash
# Install Apache on macOS using Homebrew
brew install httpd

# Start Apache service
sudo brew services start httpd

# Or manually start Apache
sudo /opt/homebrew/bin/httpd -D FOREGROUND
```

## Configuration Files

### 1. Apache Configuration

Edit `/opt/homebrew/etc/httpd/httpd.conf` or create a custom config:

```apache
# Basic Apache Configuration
Listen 80
Listen 443

ServerRoot "/opt/homebrew"
PidFile /opt/homebrew/var/run/httpd.pid

# Modules
LoadModule rewrite_module lib/httpd/modules/mod_rewrite.so
LoadModule proxy_module lib/httpd/modules/mod_proxy.so
LoadModule proxy_http_module lib/httpd/modules/mod_proxy_http.so
LoadModule headers_module lib/httpd/modules/mod_headers.so
LoadModule ssl_module lib/httpd/modules/mod_ssl.so

# Include virtual hosts
Include /opt/homebrew/etc/httpd/extra/httpd-vhosts.conf
```

### 2. Virtual Host Configuration

Create `/opt/homebrew/etc/httpd/extra/ppl-meta-mini.conf`:

```apache
# PPL Meta Mini Virtual Host
<VirtualHost *:80>
    ServerName ppl-meta-mini.local
    ServerAlias www.ppl-meta-mini.local
    
    # Document root (for static files if needed)
    DocumentRoot "/opt/homebrew/var/www"
    
    # Enable proxy module
    ProxyPreserveHost On
    ProxyRequests Off
    
    # API endpoints proxy
    ProxyPass /api/v1/ http://localhost:8004/api/v1/
    ProxyPassReverse /api/v1/ http://localhost:8004/api/v1/
    
    # Health check
    ProxyPass /health http://localhost:8004/health
    ProxyPassReverse /health http://localhost:8004/health
    
    # Swagger UI (optional for development)
    ProxyPass /docs http://localhost:8004/docs
    ProxyPassReverse /docs http://localhost:8004/docs
    
    # OpenAPI schema
    ProxyPass /openapi.json http://localhost:8004/openapi.json
    ProxyPassReverse /openapi.json http://localhost:8004/openapi.json
    
    # Root redirect to docs (optional)
    RedirectMatch ^/$ /docs
    
    # Headers for better integration
    ProxyPassReverse / http://localhost:8004/
    Header always set X-Forwarded-Proto "http"
    Header always set X-Forwarded-Host "ppl-meta-mini.local"
    
    # Logging
    ErrorLog "/opt/homebrew/var/log/httpd/ppl-meta-mini_error.log"
    CustomLog "/opt/homebrew/var/log/httpd/ppl-meta-mini_access.log" combined
</VirtualHost>

# HTTPS Virtual Host (if SSL needed)
<VirtualHost *:443>
    ServerName ppl-meta-mini.local
    ServerAlias www.ppl-meta-mini.local
    
    DocumentRoot "/opt/homebrew/var/www"
    
    # SSL Configuration (self-signed for development)
    SSLEngine on
    SSLCertificateFile "/opt/homebrew/etc/httpd/ssl/ppl-meta-mini.crt"
    SSLCertificateKeyFile "/opt/homebrew/etc/httpd/ssl/ppl-meta-mini.key"
    
    # Proxy configuration (same as HTTP)
    ProxyPreserveHost On
    ProxyRequests Off
    
    ProxyPass /api/v1/ http://localhost:8004/api/v1/
    ProxyPassReverse /api/v1/ http://localhost:8004/api/v1/
    ProxyPass /health http://localhost:8004/health
    ProxyPassReverse /health http://localhost:8004/health
    ProxyPass /docs http://localhost:8004/docs
    ProxyPassReverse /docs http://localhost:8004/docs
    ProxyPass /openapi.json http://localhost:8004/openapi.json
    ProxyPassReverse /openapi.json http://localhost:8004/openapi.json
    
    # HTTPS headers
    Header always set X-Forwarded-Proto "https"
    Header always set X-Forwarded-Host "ppl-meta-mini.local"
    Header always set X-Forwarded-Port "443"
    
    ErrorLog "/opt/homebrew/var/log/httpd/ppl-meta-mini_ssl_error.log"
    CustomLog "/opt/homebrew/var/log/httpd/ppl-meta-mini_ssl_access.log" combined
</VirtualHost>
```

### 3. Include the configuration

Add to `/opt/homebrew/etc/httpd/extra/httpd-vhosts.conf`:

```apache
# Include PPL Meta Mini configuration
Include /opt/homebrew/etc/httpd/extra/ppl-meta-mini.conf
```

## Setup Commands

```bash
# 1. Create SSL directory (if using HTTPS)
sudo mkdir -p /opt/homebrew/etc/httpd/ssl

# 2. Generate self-signed certificate for development
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /opt/homebrew/etc/httpd/ssl/ppl-meta-mini.key \
    -out /opt/homebrew/etc/httpd/ssl/ppl-meta-mini.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=ppl-meta-mini.local"

# 3. Add domain to hosts file
echo "127.0.0.1 ppl-meta-mini.local" | sudo tee -a /etc/hosts

# 4. Test Apache configuration
sudo /opt/homebrew/bin/httpd -t

# 5. Start Apache
sudo brew services start httpd

# 6. Start PPL Meta Mini service
cd /Users/nickgklezakos/Documents/ppl-meta-code/autonomous/ppl-meta-mini/src
python main.py &
```

## Testing the Setup

```bash
# Test direct PPL Meta Mini service
curl http://localhost:8004/health

# Test through Apache proxy
curl http://ppl-meta-mini.local/health

# Test HTTPS (if configured)
curl -k https://ppl-meta-mini.local/health

# Test API endpoints
curl http://ppl-meta-mini.local/api/v1/health

# Access Swagger UI
open http://ppl-meta-mini.local/docs
```

## Automation Script

Create `/Users/nickgklezakos/Documents/ppl-meta-code/scripts/start-apache-proxy.sh`:

```bash
#!/bin/bash
# Start PPL Meta Mini with Apache Proxy

echo "🚀 Starting PPL Meta Mini with Apache Proxy..."

# Start PPL Meta Mini service
echo "Starting PPL Meta Mini service..."
cd /Users/nickgklezakos/Documents/ppl-meta-code/autonomous/ppl-meta-mini/src
python main.py &
PPL_PID=$!
echo "PPL Meta Mini started with PID: $PPL_PID"

# Wait for service to start
sleep 3

# Test if service is running
if curl -s http://localhost:8004/health > /dev/null; then
    echo "✅ PPL Meta Mini service is running"
else
    echo "❌ PPL Meta Mini service failed to start"
    exit 1
fi

# Start Apache
echo "Starting Apache..."
sudo brew services start httpd

# Wait for Apache
sleep 2

# Test Apache proxy
if curl -s http://ppl-meta-mini.local/health > /dev/null; then
    echo "✅ Apache proxy is working"
    echo "🎉 Setup complete!"
    echo ""
    echo "Available endpoints:"
    echo "  - Direct: http://localhost:8004/docs"
    echo "  - Proxy:  http://ppl-meta-mini.local/docs"
    echo ""
    echo "To stop services:"
    echo "  sudo brew services stop httpd"
    echo "  kill $PPL_PID"
else
    echo "❌ Apache proxy not working"
    echo "Check Apache configuration and logs"
fi
```

Make it executable:
```bash
chmod +x /Users/nickgklezakos/Documents/ppl-meta-code/scripts/start-apache-proxy.sh
```

## Stop Script

Create `/Users/nickgklezakos/Documents/ppl-meta-code/scripts/stop-apache-proxy.sh`:

```bash
#!/bin/bash
# Stop PPL Meta Mini with Apache Proxy

echo "🛑 Stopping PPL Meta Mini with Apache Proxy..."

# Stop Apache
echo "Stopping Apache..."
sudo brew services stop httpd

# Stop PPL Meta Mini
echo "Stopping PPL Meta Mini..."
pkill -f "python.*main.py"

echo "✅ All services stopped"
```

Make it executable:
```bash
chmod +x /Users/nickgklezakos/Documents/ppl-meta-code/scripts/stop-apache-proxy.sh
```

## Benefits of This Setup

1. **Professional URLs**: Access via `http://ppl-meta-mini.local` instead of `localhost:8004`
2. **SSL Support**: HTTPS termination at Apache level
3. **Static Files**: Apache can serve documentation and static content efficiently
4. **Load Balancing**: Easy to add multiple PPL Meta Mini instances
5. **Security**: Apache handles security headers and SSL
6. **Logging**: Centralized logging through Apache
7. **Production Ready**: Easy transition to production deployment

## Troubleshooting

```bash
# Check Apache status
brew services list | grep httpd

# Check Apache configuration
sudo /opt/homebrew/bin/httpd -t

# Check Apache logs
tail -f /opt/homebrew/var/log/httpd/error_log
tail -f /opt/homebrew/var/log/httpd/ppl-meta-mini_error.log

# Check if ports are in use
lsof -i :80
lsof -i :8004

# Test connectivity
curl -v http://ppl-meta-mini.local/health
```

This setup gives you a professional, production-ready deployment while maintaining your existing FastAPI development workflow!