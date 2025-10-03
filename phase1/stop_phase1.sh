#!/bin/bash

echo "🛑 Stopping PPL Meta Phase 1 system..."

# Kill any running Phase 1 processes
pkill -f "phase1_integration.py" 2>/dev/null || true
pkill -f "uvicorn.*phase1_integration" 2>/dev/null || true

echo "✅ Phase 1 system stopped"
