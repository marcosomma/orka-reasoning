# OrKa Backend Selection Guide

OrKa now supports multiple memory backends: **Redis**, **Kafka**, and **Dual** (both). You can choose which backend to use when starting OrKa.

## 🚀 Quick Start Options

### Option 1: Environment Variable (Recommended)
```bash
# Start with Redis backend (default)
python -m orka.orka_start

# Start with Kafka backend
ORKA_MEMORY_BACKEND=kafka python -m orka.orka_start

# Start with dual backend (both Redis and Kafka)
ORKA_MEMORY_BACKEND=dual python -m orka.orka_start
```

### Option 2: Helper Scripts
```bash
# Start with Redis backend
python -m orka.start_redis

# Start with Kafka backend  
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

### Redis Backend
- **Orka API**: http://localhost:8000
- **Redis**: localhost:6379

### Kafka Backend
- **Orka API**: http://localhost:8001
- **Kafka**: localhost:9092
- **Zookeeper**: localhost:2181

### Dual Backend
- **Orka API**: http://localhost:8002
- **Redis**: localhost:6379
- **Kafka**: localhost:9092
- **Zookeeper**: localhost:2181

## 🔧 Environment Variables

### All Backends
- `ORKA_MEMORY_BACKEND`: Choose backend type (`redis`, `kafka`, `dual`)

### Redis-Specific
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

### Redis Backend
- **Best for**: Development, single-node deployments, quick prototyping
- **Features**: Fast in-memory operations, simple setup
- **Limitations**: Single point of failure, memory-bound storage

### Kafka Backend  
- **Best for**: Production, distributed systems, high-throughput scenarios
- **Features**: Persistent event log, horizontal scaling, fault tolerance
- **Limitations**: More complex setup, higher resource usage

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

# Redis
memory = create_memory_logger("redis", redis_url="redis://localhost:6379")

# Kafka  
memory = create_memory_logger("kafka", bootstrap_servers="localhost:9092")
``` 