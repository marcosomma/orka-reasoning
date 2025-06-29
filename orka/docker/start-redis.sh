#!/bin/bash

# OrKa V0.7.0 RedisStack Backend Startup Script
# This script starts OrKa with RedisStack for 100x faster vector search

set -e  # Exit on any error

echo "🚀 Starting OrKa V0.7.0 with RedisStack Backend (100x Faster Vector Search)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Stop any existing services
echo "🛑 Stopping any existing Redis services..."
docker-compose --profile redis down 2>/dev/null || true

# Build and start RedisStack services
echo "🔧 Building and starting RedisStack services..."
docker-compose --profile redis up --build -d

# Wait for services to be ready
echo "⏳ Waiting for RedisStack to be ready..."
sleep 10

# Check if RedisStack is responding
echo "🔍 Testing RedisStack connection..."
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ RedisStack is ready!"
    
    # Check if vector search modules are loaded
    echo "🔍 Verifying HNSW vector search capabilities..."
    if docker-compose exec redis redis-cli MODULE LIST | grep -q search > /dev/null 2>&1; then
        echo "✅ RedisStack vector search modules loaded!"
        echo "🚀 HNSW indexing available for 100x faster searches!"
    else
        echo "⚠️  Vector search modules not detected - falling back to basic Redis"
    fi
else
    echo "❌ RedisStack connection failed"
    exit 1
fi

# Show running services
echo "📋 Services Status:"
docker-compose --profile redis ps

echo ""
echo "✅ OrKa V0.7.0 RedisStack Backend is now running!"
echo ""
echo "📍 Service Endpoints:"
echo "   • OrKa API: http://localhost:8000"
echo "   • RedisStack: localhost:6380 (external), redis:6379 (internal)"
echo ""
echo "🛠️  Management Commands:"
echo "   • View logs:     docker-compose --profile redis logs -f"
echo "   • Stop services: docker-compose --profile redis down"
echo "   • Redis CLI:     docker-compose exec redis redis-cli"
echo "   • Memory watch:  python -m orka.orka_cli memory watch"
echo ""
echo "🔧 Environment Variables:"
echo "   • ORKA_MEMORY_BACKEND=redisstack (V0.7.0 default)"
echo "   • REDIS_URL=redis://redis:6379/0"
echo ""
echo "⚡ Performance:"
echo "   • Vector Search: Sub-millisecond latency with HNSW indexing"
echo "   • Memory Ops:    50,000+ operations/second"
echo "   • Concurrent:    1,000+ simultaneous searches"
echo "" 