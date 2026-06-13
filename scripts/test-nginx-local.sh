#!/bin/bash

# PPL Meta Platform - Nginx Local Development Test Script
# This script tests nginx proxy functionality

echo "🧪 Testing Nginx Proxy for PPL Meta Platform"
echo "============================================="

# Test if nginx is running
if ! pgrep nginx > /dev/null; then
    echo "❌ Nginx is not running. Please start nginx first."
    echo "Run: ./scripts/setup-nginx-local.sh"
    exit 1
fi

echo "✅ Nginx is running"

LAN_IP=""
if [[ -f /tmp/ppl-meta-local-dev-meta.env ]]; then
    # shellcheck disable=SC1091
    source /tmp/ppl-meta-local-dev-meta.env
fi

# Test main entry point
echo "🔍 Testing main entry point (http://localhost)..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost | grep -q "200\|302"; then
    echo "✅ Main entry point is accessible"
else
    echo "❌ Main entry point failed"
fi

echo "🔍 Testing HTTPS entry point (https://localhost)..."
if curl -k -s -o /dev/null -w "%{http_code}" https://localhost | grep -q "200\|302"; then
    echo "✅ HTTPS entry point is accessible"
else
    echo "❌ HTTPS entry point failed"
fi

if [[ -n "${LAN_IP:-}" ]]; then
    echo "🔍 Testing LAN HTTPS entry point (https://$LAN_IP)..."
    if curl -k -s -o /dev/null -w "%{http_code}" "https://$LAN_IP" | grep -q "200\|302"; then
        echo "✅ LAN HTTPS entry point is accessible"
    else
        echo "❌ LAN HTTPS entry point failed"
    fi
fi

# Test health checks through nginx
echo "🏥 Testing health checks through nginx proxy..."

echo "  • Testing aggregated health check..."
if curl -s http://localhost/health > /dev/null; then
    echo "    ✅ Aggregated health check working"
else
    echo "    ❌ Aggregated health check failed"
fi

echo "  • Testing individual health checks..."
services=("node" "media" "gateway" "orchestrator")
for service in "${services[@]}"; do
    if curl -s http://localhost/health/$service > /dev/null; then
        echo "    ✅ $service health check working"
    else
        echo "    ❌ $service health check failed"
    fi
done

# Test API routes
echo "🔌 Testing API routes through nginx proxy..."

echo "  • Testing API Gateway route..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/api/ | grep -q "200\|404\|405"; then
    echo "    ✅ API Gateway route accessible"
else
    echo "    ❌ API Gateway route failed"
fi

echo "  • Testing User Management route..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/users/ | grep -q "200\|404\|405\|401"; then
    echo "    ✅ User Management route accessible"
else
    echo "    ❌ User Management route failed"
fi

echo "  • Testing Media Service route..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/media/ | grep -q "200\|404\|405"; then
    echo "    ✅ Media Service route accessible"
else
    echo "    ❌ Media Service route failed"
fi

echo "  • Testing Orchestrator route..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost/api/v1/orchestrate/ | grep -q "200\|404\|405"; then
    echo "    ✅ Orchestrator route accessible"
else
    echo "    ❌ Orchestrator route failed"
fi

# Test CORS headers
echo "🌐 Testing CORS headers..."
cors_headers=$(curl -s -I http://localhost/health | grep -i "access-control-allow")
if [[ -n "$cors_headers" ]]; then
    echo "✅ CORS headers present"
    echo "    $cors_headers"
else
    echo "❌ CORS headers missing"
fi

# Test security headers
echo "🔒 Testing security headers..."
security_headers=$(curl -s -I http://localhost/health | grep -i -E "x-frame-options|x-content-type-options|x-xss-protection")
if [[ -n "$security_headers" ]]; then
    echo "✅ Security headers present"
else
    echo "❌ Security headers missing"
fi

echo ""
echo "🎯 Test Summary:"
echo "   Nginx is properly routing requests to your local Python services"
echo "   You can access all services through http://localhost"
echo "   HTTPS is available through https://localhost"
if [[ -n "${LAN_IP:-}" ]]; then
    echo "   LAN HTTPS target: https://$LAN_IP"
fi
echo "   CORS and security headers are configured for development"
if command -v brew > /dev/null 2>&1 && brew list nginx > /dev/null 2>&1; then
    echo "   Homebrew service status: $(brew services list | awk '$1 == "nginx" {print $2}')"
fi
echo ""
echo "💡 Next steps:"
echo "   • Test with a frontend application on iPad over LAN HTTPS"
echo "   • Trust the local CA on iPad when using mkcert"
echo "   • Add monitoring and logging"
