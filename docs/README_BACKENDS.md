# OrKa Backend Selection Guide

OrKa supports multiple memory backends: **RedisStack** (default), **Redis** (legacy), **Kafka** (hybrid), and **Dual** (both). Choose the right backend for your use case.

## 🎯 **Backend Comparison**

| Backend | Performance | Use Case | Vector Search | Setup Complexity |
|---------|-------------|----------|---------------|------------------|
| **RedisStack** | ⚡ 100x faster | Production AI workloads | ✅ HNSW indexing | 🟢 Simple |
| **Redis** | 🔄 Standard | Development, legacy | ❌ Basic search | 🟢 Simple |
| **Kafka** | 🚀 Hybrid | Enterprise, audit trails | ✅ Via RedisStack | 🟡 Moderate |
| **Dual** | 🔄 Variable | Testing, migration | ✅ Via RedisStack | 🔴 Complex |

## 🚀 Quick Start Options

### Option 1: Environment Variable (Recommended)
```bash
# Start with RedisStack backend (default - recommended)
python -m orka.orka_start

# Start with Kafka backend (hybrid: Kafka events + RedisStack memory)
ORKA_MEMORY_BACKEND=kafka python -m orka.orka_start

# Start with dual backend (both Redis and Kafka)
ORKA_MEMORY_BACKEND=dual python -m orka.orka_start

# Force basic Redis (legacy/development only)
ORKA_FORCE_BASIC_REDIS=true python -m orka.orka_start
```

### Option 2: Helper Scripts
```bash
# Start with basic Redis backend (legacy/development)
python orka/start_redis_only.py

# Start with Kafka backend (hybrid with RedisStack)
python -m orka.start_kafka
```

### Option 3: Docker Scripts (Alternative)
```bash
# Windows
orka\docker\start-redis.bat
orka\docker\start-kafka.bat

# Linux/macOS
./orka/docker/start-redis.sh
./orka/docker/start-kafka.sh
```

## 📍 Service Endpoints

### RedisStack Backend (Default)
- **Orka API**: http://localhost:8000
- **RedisStack**: localhost:6379 (Redis + vector search modules)

### Basic Redis Backend (Legacy)
- **Orka API**: http://localhost:8000
- **Redis**: localhost:6379 (basic Redis only)

### Kafka Backend (Hybrid with RedisStack)
- **Orka API**: http://localhost:8001
- **Kafka (Events)**: localhost:9092
- **RedisStack (Memory)**: localhost:6379  
- **Zookeeper**: localhost:2181

### Dual Backend
- **Orka API**: http://localhost:8002
- **Redis**: localhost:6379
- **Kafka**: localhost:9092
- **Zookeeper**: localhost:2181

## 🔧 Environment Variables

### All Backends
- `ORKA_MEMORY_BACKEND`: Choose backend type (`redisstack`, `redis`, `kafka`, `dual`)
- `ORKA_FORCE_BASIC_REDIS`: Force basic Redis mode (`true`/`false`)

### RedisStack/Redis-Specific
- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379/0`)

### Kafka-Specific
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka brokers (default: `localhost:9092`)
- `KAFKA_TOPIC_PREFIX`: Topic name prefix (default: `orka-memory`)

## 🛠️ Management Commands

### Check Running Services
```bash
# List running containers
docker ps

# Check specific backend services
docker-compose --profile redis ps
docker-compose --profile kafka ps
docker-compose --profile dual ps
```

### View Logs
```bash
# Orka application logs (shown in terminal)
# Docker container logs
docker-compose logs -f redis
docker-compose logs -f kafka
docker-compose logs -f zookeeper
```

### Stop Services
```bash
# Stop by pressing Ctrl+C in the terminal where orka_start is running
# Or manually stop containers:
docker-compose --profile redis down
docker-compose --profile kafka down
docker-compose --profile dual down
```

## 🔄 Switching Between Backends

### Runtime Switch (Dual Backend)
When using dual backend, you can switch between Redis and Kafka at runtime by changing the `ORKA_MEMORY_BACKEND` environment variable in your application configuration.

### Complete Switch
1. Stop current services (Ctrl+C)
2. Start with different backend:
   ```bash
   ORKA_MEMORY_BACKEND=kafka python -m orka.orka_start
   ```

## 🐛 Troubleshooting

### Common Issues

**Backend won't start:**
```bash
# Check Docker is running
docker --version

# Check for port conflicts
netstat -an | grep 6379  # Redis
netstat -an | grep 9092  # Kafka
```

**Services not ready:**
- Redis: Usually ready in 5-10 seconds
- Kafka: Can take 15-30 seconds to initialize
- Check logs: `docker-compose logs <service-name>`

**Wrong backend selected:**
- Check environment variable: `echo $ORKA_MEMORY_BACKEND`
- Verify correct ports are being used (see endpoints above)

### Debug Commands
```bash
# Test Redis connection
docker-compose exec redis redis-cli ping

# Test Kafka connection  
docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --list

# View Orka memory logs
# Redis: docker-compose exec redis redis-cli monitor
# Kafka: docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:29092 --topic orka-memory-events --from-beginning
```

## 🎯 Use Cases

### RedisStack Backend (Recommended)
- **Best for**: Production AI workloads, vector search applications, intelligent memory
- **Features**: 100x faster vector search, HNSW indexing, semantic similarity, automatic fallback to basic Redis
- **Limitations**: Requires RedisStack installation (or falls back gracefully)

### Basic Redis Backend (Legacy)
- **Best for**: Development, legacy systems, simple deployments without vector search
- **Features**: Fast in-memory operations, simple setup, proven reliability
- **Limitations**: No vector search, basic text matching only

### Kafka Backend (Hybrid with RedisStack)
- **Best for**: Enterprise systems, audit trails, distributed architectures with AI capabilities
- **Features**: Kafka for persistent event streaming + RedisStack for intelligent memory operations and vector search
- **Limitations**: More complex setup, requires both Kafka and RedisStack infrastructure

### Dual Backend
- **Best for**: Testing, migration scenarios, comparing performance
- **Features**: Can switch between backends without restart
- **Limitations**: Uses resources for both systems

## 📚 Examples

### Basic Usage
```python
# Your OrKa workflow code remains the same regardless of backend
from orka.orchestrator import Orchestrator

orchestrator = Orchestrator("config.yml")
result = await orchestrator.run("input data")
```

### Backend-Specific Configuration
```python
import os

# Force Kafka backend in code
os.environ["ORKA_MEMORY_BACKEND"] = "kafka"
os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"

from orka.orchestrator import Orchestrator
orchestrator = Orchestrator("config.yml")
```

### Programmatic Backend Selection
```python
from orka.memory_logger import create_memory_logger

# RedisStack (default - recommended)
memory = create_memory_logger("redisstack", redis_url="redis://localhost:6379")

# Basic Redis (legacy)
import os
os.environ["ORKA_FORCE_BASIC_REDIS"] = "true"
memory = create_memory_logger("redis", redis_url="redis://localhost:6379")

# Kafka (hybrid with RedisStack)
memory = create_memory_logger("kafka", bootstrap_servers="localhost:9092", redis_url="redis://localhost:6379")
``` 