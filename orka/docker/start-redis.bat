@echo off
REM Orka Redis Backend Startup Script (Windows)
REM This script starts Orka with Redis as the memory backend

echo 🚀 Starting Orka with Redis Backend...
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REM Stop any existing services
echo 🛑 Stopping any existing Redis services...
docker-compose --profile redis down >nul 2>&1

REM Build and start Redis services
echo 🔧 Building and starting Redis services...
docker-compose --profile redis up --build -d

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

REM Show running services
echo 📋 Services Status:
docker-compose --profile redis ps

echo.
echo ✅ Orka Redis Backend is now running!
echo.
echo 📍 Service Endpoints:
echo    • Orka API: http://localhost:8000
echo    • Redis:    localhost:6380
echo.
echo 🛠️  Management Commands:
echo    • View logs:     docker-compose --profile redis logs -f
echo    • Stop services: docker-compose --profile redis down
echo    • Redis CLI:     docker-compose exec redis redis-cli
echo.
echo 🔧 Environment Variables:
echo    • ORKA_MEMORY_BACKEND=redis
echo    • REDIS_URL=redis://redis:6380/0
echo. 