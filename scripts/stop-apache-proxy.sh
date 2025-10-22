#!/bin/bash
# Stop PPL Meta Mini with Apache Proxy

echo "🛑 Stopping PPL Meta Mini with Apache Proxy..."

# Stop Apache
echo "Stopping Apache..."
sudo brew services stop httpd

# Stop PPL Meta Mini
echo "Stopping PPL Meta Mini..."
pkill -f "python.*main.py"

# Verify services are stopped
sleep 2

if ! pgrep -f "python.*main.py" > /dev/null; then
    echo "✅ PPL Meta Mini stopped"
else
    echo "⚠️ Some Python processes may still be running"
fi

if ! brew services list | grep httpd | grep started > /dev/null; then
    echo "✅ Apache stopped"
else
    echo "⚠️ Apache may still be running"
fi

echo "✅ All services stopped"