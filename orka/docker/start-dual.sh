#!/bin/bash

# Orka Dual Backend Startup Script
# This script starts Orka with both Redis and Kafka backends for testing

set -e  # Exit on any error

echo "🚀 Starting Orka with Dual Backend (Redis + Kafka)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Stop any existing services
echo "🛑 Stopping any existing services..."
docker-compose --profile dual down 2>/dev/null || true

# Build and start all services
echo "🔧 Building and starting all services..."
docker-compose --profile dual up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to initialize..."
sleep 15

# Check Redis
echo "🔍 Testing Redis connection..."
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is ready!"
else
    echo "❌ Redis connection failed"
    exit 1
fi

# Check Kafka
echo "🔍 Testing Kafka connection..."
sleep 5
if docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --list > /dev/null 2>&1; then
    echo "✅ Kafka is ready!"
else
    echo "❌ Kafka connection failed, trying again..."
    sleep 10
    if docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --list > /dev/null 2>&1; then
        echo "✅ Kafka is now ready!"
    else
        echo "❌ Kafka connection still failing"
        exit 1
    fi
fi

# Create initial Orka topics
echo "📝 Creating Orka topics..."
docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --create --topic orka-memory-events --partitions 3 --replication-factor 1 --if-not-exists 2>/dev/null || true

# Show running services
echo "📋 Services Status:"
docker-compose --profile dual ps

echo ""
echo "✅ Orka Dual Backend is now running!"
echo ""
echo "📍 Service Endpoints:"
echo "   • Orka API (Dual): http://localhost:8002"
echo "   • Redis:           localhost:6379"
echo "   • Kafka:           localhost:9092"
echo "   • Zookeeper:       localhost:2181"
echo ""
echo "🛠️  Management Commands:"
echo "   • View logs:        docker-compose --profile dual logs -f"
echo "   • Stop services:    docker-compose --profile dual down"
echo "   • Redis CLI:        docker-compose exec redis redis-cli"
echo "   • List topics:      docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --list"
echo ""
echo "🔧 Environment Variables (Default):"
echo "   • ORKA_MEMORY_BACKEND=redis (can be changed to kafka)"
echo "   • REDIS_URL=redis://redis:6379/0"
echo "   • KAFKA_BOOTSTRAP_SERVERS=kafka:29092"
echo "   • KAFKA_TOPIC_PREFIX=orka-memory"
echo ""
echo "💡 Switch backend by setting ORKA_MEMORY_BACKEND environment variable"
echo "" 