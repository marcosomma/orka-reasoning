#!/bin/bash

# Orka Cleanup Script
# This script stops all Orka services and optionally cleans up volumes

set -e  # Exit on any error

echo "🧹 Orka Cleanup Utility"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Function to stop services by profile
stop_profile() {
    local profile=$1
    local service_name=$2
    
    echo "🛑 Stopping $service_name services..."
    if docker-compose --profile $profile ps -q | grep -q .; then
        docker-compose --profile $profile down
        echo "✅ $service_name services stopped"
    else
        echo "ℹ️  No running $service_name services found"
    fi
}

# Check command line arguments
CLEAN_VOLUMES=false
if [[ "$1" == "--volumes" || "$1" == "-v" ]]; then
    CLEAN_VOLUMES=true
fi

# Stop all profile-based services
stop_profile "redis" "Redis"
stop_profile "kafka" "Kafka" 
stop_profile "dual" "Dual Backend"

# Stop any remaining containers
echo "🛑 Stopping any remaining Orka containers..."
docker-compose down 2>/dev/null || true

# Remove orphaned containers
echo "🗑️  Removing orphaned containers..."
docker-compose down --remove-orphans 2>/dev/null || true

# Clean up volumes if requested
if [[ "$CLEAN_VOLUMES" == true ]]; then
    echo "🗂️  Removing volumes..."
    docker-compose down -v 2>/dev/null || true
    
    # Remove specific Orka volumes
    docker volume rm orka-docker_redis_data 2>/dev/null || true
    echo "✅ Volumes cleaned up"
fi

# Clean up unused networks
echo "🌐 Cleaning up networks..."
docker network prune -f 2>/dev/null || true

echo ""
echo "✅ Cleanup completed!"
echo ""

if [[ "$CLEAN_VOLUMES" == false ]]; then
    echo "💡 To also remove persistent data volumes, run:"
    echo "   ./cleanup.sh --volumes"
    echo ""
fi

echo "📋 Current Docker status:"
echo "   • Running containers: $(docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E '(orka|redis|kafka|zookeeper)' | wc -l || echo '0')"
echo "   • Orka volumes:       $(docker volume ls --format 'table {{.Name}}' | grep -E '(orka|redis)' | wc -l || echo '0')"
echo "   • Orka networks:      $(docker network ls --format 'table {{.Name}}' | grep -E '(orka|redis|kafka)' | wc -l || echo '0')"
echo "" 