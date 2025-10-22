#!/bin/bash
# Start PPL Meta Mini with Apache Proxy

echo "🚀 Starting PPL Meta Mini with Apache Proxy..."

# Check if Apache is installed
if ! command -v httpd &> /dev/null; then
    echo "❌ Apache not found. Install with: brew install httpd"
    exit 1
fi

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
if curl -s http://localhost:8080/ppl-health > /dev/null; then
    echo "✅ Apache proxy is working"
    echo "🎉 Setup complete!"
    echo ""
    echo "Available endpoints:"
    echo "  - Landing Page: http://localhost:8080/"
    echo "  - API Docs (Proxy): http://localhost:8080/ppl-docs"
    echo "  - API Docs (Direct): http://localhost:8004/docs"
    echo "  - Health (Proxy): http://localhost:8080/ppl-health"
    echo "  - Health (Direct): http://localhost:8004/health"
    echo ""
    echo "To stop services:"
    echo "  sudo brew services stop httpd"
    echo "  kill $PPL_PID"
else
    echo "❌ Apache proxy not working"
    echo "Check Apache configuration and logs"
    echo "You may need to configure Apache first (see APACHE_MACOS_SETUP.md)"
fi