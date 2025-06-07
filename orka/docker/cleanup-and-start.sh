#!/bin/bash

echo "🧹 Starting comprehensive Docker cleanup..."

# Stop all running containers
echo "Stopping all running containers..."
docker stop $(docker ps -q) 2>/dev/null || echo "No running containers to stop"

# Remove all containers (including stopped ones)
echo "Removing all containers..."
docker rm $(docker ps -aq) 2>/dev/null || echo "No containers to remove"

# Remove all images
echo "Removing unused images..."
docker image prune -a -f

# Remove all volumes
echo "Removing unused volumes..."
docker volume prune -f

# Remove all networks
echo "Removing unused networks..."
docker network prune -f

# Remove everything else
echo "Running system-wide cleanup..."
docker system prune -a -f --volumes

# Specifically clean up docker-compose related resources
echo "Cleaning up docker-compose resources..."
docker-compose -f docker-compose.yml down --remove-orphans --volumes --rmi all 2>/dev/null || echo "No compose services to clean"

echo "✅ Cleanup completed!"

# Start the services
echo "🚀 Starting services..."

# Check which profile to use
PROFILE=${1:-redis}

case $PROFILE in
  redis)
    echo "Starting Redis profile..."
    docker-compose --profile redis up -d --remove-orphans
    ;;
  kafka)
    echo "Starting Kafka profile..."
    docker-compose --profile kafka up -d --remove-orphans
    ;;
  dual)
    echo "Starting dual backend profile..."
    docker-compose --profile dual up -d --remove-orphans
    ;;
  *)
    echo "Usage: $0 [redis|kafka|dual]"
    echo "Defaulting to redis profile..."
    docker-compose --profile redis up -d --remove-orphans
    ;;
esac

echo "✅ Services started!"
echo "📊 Running containers:"
docker ps 