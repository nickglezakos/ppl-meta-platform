#!/bin/bash
echo "📹 Camera Service Logs - Last 50 lines with instant detection context"
echo "=================================================================="

# Find camera service process
PID=$(ps aux | grep "ppl-meta-cameras.*uvicorn" | grep -v grep | awk '{print $2}' | head -1)

if [ -z "$PID" ]; then
    echo "❌ Camera service not running"
    exit 1
fi

echo "Camera service PID: $PID"
echo ""
echo "Looking for instant detection logs..."
echo ""

# Since logs go to stdout/stderr mixed with other services, let's try to filter
# We'll check if there are any log files
if [ -d "/Users/nickgklezakos/Documents/ppl-meta-code/logs" ]; then
    echo "Checking logs directory..."
    ls -la /Users/nickgklezakos/Documents/ppl-meta-code/logs/ | grep camera
fi

echo ""
echo "💡 To see live camera logs, run:"
echo "   cd ppl-meta-cameras && source venv/bin/activate && PYTHONPATH=\$PWD uvicorn src.main:app --host 0.0.0.0 --port 8005 --reload"
