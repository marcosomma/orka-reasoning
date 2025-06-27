@echo off
REM Orka Kafka + Redis Hybrid Backend Startup Script (Windows)
REM This script starts Orka with Kafka for event streaming and Redis for memory operations

echo 🚀 Starting Orka with Kafka + Redis Hybrid Backend...
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REM Stop any existing services
echo 🛑 Stopping any existing services...
docker-compose --profile kafka down >nul 2>&1

REM Build and start hybrid services (Kafka + Redis)
echo 🔧 Building and starting Kafka + Redis services...
docker-compose --profile kafka up --build -d

REM Wait for services to be ready
echo ⏳ Waiting for Redis to be ready...
timeout /t 5 >nul

REM Check if Redis is responding
echo 🔍 Testing Redis connection...
docker-compose exec redis redis-cli ping >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Redis is ready!
) else (
    echo ❌ Redis connection failed
    exit /b 1
)

echo ⏳ Waiting for Zookeeper to be ready...
timeout /t 10 >nul

echo ⏳ Waiting for Kafka to be ready...
timeout /t 15 >nul

REM Check if Kafka is responding
echo 🔍 Testing Kafka connection...
docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --list >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Kafka is ready!
) else (
    echo ❌ Kafka connection failed, trying again...
    timeout /t 10 >nul
    docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --list >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ Kafka is now ready!
    ) else (
        echo ❌ Kafka connection still failing
        echo 📋 Checking service logs for diagnostics...
        docker-compose --profile kafka logs kafka
        exit /b 1
    )
)

REM Create initial Orka topics
echo 📝 Creating Orka topics...
docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --create --topic orka-memory-events --partitions 3 --replication-factor 1 --if-not-exists >nul 2>&1

REM Show running services
echo 📋 Services Status:
docker-compose --profile kafka ps

echo.
echo ✅ Orka Kafka + Redis Hybrid Backend is now running!
echo.
echo 📍 Service Endpoints:
echo    • Orka API:         http://localhost:8001
echo    • Kafka (Events):   localhost:9092
echo    • Redis (Memory):   localhost:6379
echo    • Zookeeper:        localhost:2181
echo.
echo 🛠️  Management Commands:
echo    • View logs:        docker-compose --profile kafka logs -f
echo    • Stop services:    docker-compose --profile kafka down
echo    • List topics:      docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --list
echo    • View messages:    docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:29092 --topic orka-memory-events --from-beginning
echo    • Redis CLI:        docker-compose exec redis redis-cli
echo.
echo 🔧 Environment Variables:
echo    • ORKA_MEMORY_BACKEND=kafka
echo    • KAFKA_BOOTSTRAP_SERVERS=kafka:29092
echo    • KAFKA_TOPIC_PREFIX=orka-memory
echo    • REDIS_URL=redis://redis:6379/0
echo. 