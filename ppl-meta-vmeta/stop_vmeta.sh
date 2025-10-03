#!/bin/bash

echo "🛑 Stopping PPL Meta vmeta Service"
echo "================================="

pkill -f "python.*main.py.*vmeta" || echo "vmeta service was not running"
echo "✅ vmeta service stopped"
