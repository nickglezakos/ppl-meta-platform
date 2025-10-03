#!/bin/bash

echo "🚀 Starting PPL Meta vmeta Service"
echo "=================================="

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

# Start the vmeta service
cd src && python main.py
