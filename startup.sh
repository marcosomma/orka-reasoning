#!/bin/bash
# OrKa Cloud Run Startup Script - OpenAI-Only Architecture
# Launches Redis and OrKa server (no local LLM needed)

set -e

echo "========================================="
echo "OrKa Cloud Run Startup (OpenAI-Only)"
echo "========================================="

# Function to check if a service is ready
check_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    echo "Waiting for $service to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            echo "$service is ready!"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "ERROR: $service failed to start after $max_attempts attempts"
    return 1
}

# Function to cleanup old logs
cleanup_old_logs() {
    local retention_hours=${ORKA_LOG_RETENTION_HOURS:-24}
    echo "Cleaning up logs older than $retention_hours hours..."
    find /logs -type f -name "*.json" -mmin +$((retention_hours * 60)) -delete 2>/dev/null || true
    find /logs -type f -name "*.log" -mmin +$((retention_hours * 60)) -delete 2>/dev/null || true
}

# 1. Start Redis server directly
echo "Starting Redis server..."
redis-server /etc/redis/redis.conf &
REDIS_PID=$!
sleep 3

# Check Redis
if ! redis-cli -p 6380 ping > /dev/null 2>&1; then
    echo "ERROR: Redis failed to start"
    exit 1
fi
echo "Redis started successfully (PID: $REDIS_PID)"

# 2. Clean up old logs
cleanup_old_logs

# 3. Start OrKa server
echo "Starting OrKa server on port ${ORKA_PORT}..."
echo "Using OpenAI agents (users provide OPENAI_API_KEY in requests)"
cd /app
exec python3 -m orka.server

# Note: exec replaces the shell process with the Python process
# This ensures proper signal handling and graceful shutdown

