#!/bin/bash

# Orka Redis Backend Startup Script
# This script starts Orka with Redis as the memory backend

set -e  # Exit on any error

echo "🚀 Starting Orka with Redis Backend..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Stop any existing services
echo "🛑 Stopping any existing Redis services..."
docker-compose --profile redis down 2>/dev/null || true

# Build and start Redis services
echo "🔧 Building and starting Redis services..."
docker-compose --profile redis up --build -d

# Wait for services to be ready
echo "⏳ Waiting for Redis to be ready..."
sleep 5

# Check if Redis is responding
echo "🔍 Testing Redis connection..."
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is ready!"
else
    echo "❌ Redis connection failed"
    exit 1
fi

# Show running services
echo "📋 Services Status:"
docker-compose --profile redis ps

echo ""
echo "✅ Orka Redis Backend is now running!"
echo ""
echo "📍 Service Endpoints:"
echo "   • Orka API: http://localhost:8000"
echo "   • Redis:    localhost:6379"
echo ""
echo "🛠️  Management Commands:"
echo "   • View logs:     docker-compose --profile redis logs -f"
echo "   • Stop services: docker-compose --profile redis down"
echo "   • Redis CLI:     docker-compose exec redis redis-cli"
echo ""
echo "🔧 Environment Variables:"
echo "   • ORKA_MEMORY_BACKEND=redis"
echo "   • REDIS_URL=redis://redis:6379/0"
echo "" 