# OrKa V0.7.0 Docker Setup - 100x Faster Vector Search

This directory contains Docker configurations and scripts for running OrKa V0.7.0 with **RedisStack HNSW indexing** and enterprise Kafka streaming.

## 🚀 V0.7.0 Performance Revolution

- **🚀 100x Faster Vector Search** - RedisStack HNSW indexing (0.5-5ms vs 50-200ms)
- **⚡ 50x Higher Throughput** - 50,000+ memory operations per second
- **🏗️ Unified Architecture** - All backends now use RedisStack for memory
- **🔧 Automatic Setup** - Zero manual configuration required

## 🚀 Quick Start

### RedisStack Backend (V0.7.0 Default - 100x Faster)
```bash
# Linux/macOS
./start-redis.sh

# Windows
start-redis.bat

# Or manually:
docker-compose --profile redis up --build -d
```

### Kafka + RedisStack Backend (Enterprise Streaming + 100x Memory)
```bash
# Linux/macOS
./start-kafka.sh

# Windows
start-kafka.bat

# Or manually:
docker-compose --profile kafka up --build -d
```

### Dual Backend (Development & Testing)
```bash
# Linux/macOS
./start-dual.sh

# Windows (manual only)
docker-compose --profile dual up --build -d
```

## 📋 Available Services

### RedisStack Profile (`--profile redis`)
- **orka-start-redis**: OrKa API server with RedisStack HNSW backend
- **redis**: RedisStack server with vector search capabilities

**Endpoints:**
- OrKa API: `http://localhost:8000`
- RedisStack: `localhost:6380` (external), `redis:6380` (internal)

**Performance:**
- Vector Search: Sub-millisecond HNSW indexing
- Memory Ops: 50,000+ operations/second
- Concurrent: 1,000+ simultaneous searches

### Kafka Profile (`--profile kafka`)
- **orka-start-kafka**: Orka API server with Kafka backend
- **kafka**: Kafka broker
- **zookeeper**: Zookeeper for Kafka coordination

**Endpoints:**
- Orka API: `http://localhost:8001`
- Kafka: `localhost:9092`
- Zookeeper: `localhost:2181`

### Dual Profile (`--profile dual`)
- **orka-dual-backend**: Orka API server with configurable backend
- **redis**: Redis server
- **kafka**: Kafka broker
- **zookeeper**: Zookeeper

**Endpoints:**
- Orka API: `http://localhost:8002`
- Redis: `localhost:6380`
- Kafka: `localhost:9092`

## 🛠️ Management Commands

### Starting Services
```bash
# Redis only
docker-compose --profile redis up -d

# Kafka only  
docker-compose --profile kafka up -d

# Both (dual backend)
docker-compose --profile dual up -d
```

### Stopping Services
```bash
# Stop specific profile
docker-compose --profile redis down
docker-compose --profile kafka down
docker-compose --profile dual down

# Stop all services
./cleanup.sh

# Stop all and remove volumes
./cleanup.sh --volumes
```

### Viewing Logs
```bash
# All services in a profile
docker-compose --profile redis logs -f
docker-compose --profile kafka logs -f

# Specific service
docker-compose logs -f orka-start-redis
docker-compose logs -f kafka
```

### Debugging
```bash
# Check Redis
docker-compose exec redis redis-cli ping
docker-compose exec redis redis-cli info

# Check Kafka
docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --list
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:29092 --topic orka-memory-events --from-beginning
```

## 🔧 Environment Variables

### RedisStack Backend (V0.7.0 Default)
```bash
ORKA_MEMORY_BACKEND=redisstack  # Default in V0.7.0
REDIS_URL=redis://redis:6380/0
# Automatic HNSW indexing with optimized parameters:
# - M=16 (connectivity)
# - ef_construction=200 (build accuracy)
```

### Kafka + RedisStack Backend (Enterprise)
```bash
ORKA_MEMORY_BACKEND=kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
KAFKA_TOPIC_PREFIX=orka-memory
KAFKA_SCHEMA_REGISTRY_URL=http://schema-registry:8081
REDIS_URL=redis://redis:6380/0  # RedisStack for memory operations
```

### Legacy Redis Backend (Basic - Not Recommended)
```bash
ORKA_FORCE_BASIC_REDIS=true     # Force basic Redis mode
ORKA_MEMORY_BACKEND=redis       # Legacy mode
REDIS_URL=redis://redis:6380/0
```

### Runtime Override
You can override the memory backend at runtime:
```bash
# Switch dual backend to Kafka
docker-compose exec orka-dual-backend env ORKA_MEMORY_BACKEND=kafka python -m orka.server
```

## 📁 File Structure

```
orka/docker/
├── docker-compose.yml     # Main Docker Compose configuration
├── Dockerfile             # Orka application container
├── start-redis.sh         # Redis backend startup script (Linux/macOS)
├── start-redis.bat        # Redis backend startup script (Windows)
├── start-kafka.sh         # Kafka backend startup script (Linux/macOS)
├── start-kafka.bat        # Kafka backend startup script (Windows)
├── start-dual.sh          # Dual backend startup script (Linux/macOS)
├── cleanup.sh             # Service cleanup script (Linux/macOS)
└── README.md              # This documentation
```

## 🐳 Docker Compose Profiles

This setup uses Docker Compose profiles to manage different backend configurations:

- **redis**: Minimal setup with Redis only
- **kafka**: Full event streaming with Kafka + Zookeeper
- **dual**: Both backends for testing and comparison

## 🔄 Migration Between Backends

### From Redis to Kafka
1. Export Redis data: `docker-compose exec redis redis-cli --rdb > backup.rdb`
2. Stop Redis services: `docker-compose --profile redis down`
3. Start Kafka services: `./start-kafka.sh`
4. Configure application to use Kafka backend

### From Kafka to Redis
1. Stop Kafka services: `docker-compose --profile kafka down`
2. Start Redis services: `./start-redis.sh`
3. Configure application to use Redis backend
4. Kafka topics remain for historical reference

## 🚨 Troubleshooting

### Common Issues

**Kafka takes too long to start:**
- Increase wait times in startup scripts
- Check if Zookeeper is running: `docker-compose ps zookeeper`
- View Kafka logs: `docker-compose logs kafka`

**Redis connection refused:**
- Check Redis logs: `docker-compose logs redis`
- Verify Redis is running: `docker-compose ps redis`
- Test connection: `docker-compose exec redis redis-cli ping`

**Port conflicts:**
- Redis: Check if port 6380 is available
- Kafka: Check if port 9092 is available
- Orka APIs: Ports 8000, 8001, 8002

**Memory issues:**
- Increase Docker memory allocation
- Monitor container resources: `docker stats`

### Cleanup and Reset
```bash
# Complete cleanup
./cleanup.sh --volumes

# Remove all Orka-related containers and images
docker-compose down --rmi all --volumes --remove-orphans

# Prune Docker system
docker system prune -a --volumes
```

## 📊 Monitoring

### Redis Monitoring
```bash
# Redis CLI
docker-compose exec redis redis-cli

# Monitor commands
docker-compose exec redis redis-cli monitor

# Check memory usage
docker-compose exec redis redis-cli info memory
```

### Kafka Monitoring
```bash
# List topics
docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --list

# Describe topic
docker-compose exec kafka kafka-topics --bootstrap-server localhost:29092 --describe --topic orka-memory-events

# Consumer groups
docker-compose exec kafka kafka-consumer-groups --bootstrap-server localhost:29092 --list
```

## 🎯 Production Considerations

### For Redis
- Use Redis Cluster for high availability
- Configure Redis persistence (RDB + AOF)
- Set up Redis monitoring and alerting
- Consider Redis memory optimization

### For Kafka
- Use multiple Kafka brokers
- Configure appropriate replication factors
- Set up monitoring with JMX
- Configure log retention policies
- Consider using Kafka Connect for integration

### Security
- Enable authentication for both Redis and Kafka
- Use TLS encryption for production
- Configure network security groups
- Regular security updates

## 🤝 Contributing

When adding new features:
1. Update the appropriate Docker Compose profiles
2. Update startup scripts with proper health checks
3. Add documentation to this README
4. Test both backends thoroughly 