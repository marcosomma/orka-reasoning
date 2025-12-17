# OrKa Backend Selection Guide

OrKa supports Redis-based memory backends: **RedisStack** (recommended) and **Redis** (basic). Choose the right backend for your use case.

## 🎯 **Backend Comparison**

| Backend | Performance | Use Case | Vector Search | Setup Complexity |
|---------|-------------|----------|---------------|------------------|
| **RedisStack** | ⚡ 100x faster | Latency-sensitive workloads | ✅ HNSW indexing | 🟢 Simple |
| **Redis** | 🔄 Standard | Development, legacy | ❌ Basic search | 🟢 Simple |

## 🚀 Quick Start Options

### Option 1: Environment Variable (Recommended)
```bash
# Start with RedisStack backend (default - recommended)
python -m orka.orka_start

# Force basic Redis (legacy/development only)
ORKA_FORCE_BASIC_REDIS=true python -m orka.orka_start
```

### Option 2: Docker Scripts
```bash
# Windows
orka\docker\start-redis.bat

# Linux/macOS
./orka/docker/start-redis.sh
```

## 📊 **Performance Benchmarks**

### Vector Search Performance
```
RedisStack HNSW:  1.2ms avg query time (100x faster)
Redis Basic:      120ms avg query time
```

### Memory Operations
```
RedisStack:  10,000 ops/sec
Redis:       8,000 ops/sec
```

## 🔧 **Configuration**

### RedisStack (Recommended)
```bash
# Environment variables
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6380/0

# Start OrKa
python -m orka.orka_start
```

**Features:**
- ✅ HNSW vector indexing for 100x faster semantic search
- ✅ Advanced memory decay and compression
- ✅ Near real-time memory analytics (deployment-dependent)
- ✅ Automatic index optimization

### Redis (Basic)
```bash
# Environment variables
export ORKA_MEMORY_BACKEND=redis
export REDIS_URL=redis://localhost:6379/0

# Start OrKa
python -m orka.orka_start
```

**Features:**
- ✅ Fast in-memory storage
- ✅ Basic memory operations
- ❌ No vector search capabilities
- ❌ Limited semantic search

## 🐳 **Docker Configuration**

### RedisStack Setup
```yaml
version: '3.8'
services:
  redis-stack:
    image: redis/redis-stack:latest
    ports:
      - "6380:6380"
    volumes:
      - redis_data:/data
    environment:
      - REDIS_ARGS=--save 60 1000

volumes:
  redis_data:
```

### Basic Redis Setup
```yaml
version: '3.8'
services:
  redis:
    image: redis:latest
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

## 🔍 **Backend Selection Guide**

### Choose **RedisStack** if:
- ✅ You need semantic/vector search
- ✅ Guidance for building production-grade AI applications (validate for your environment)
- ✅ Want 100x faster query performance
- ✅ Need advanced memory features

### Choose **Redis** if:
- ✅ Simple development setup
- ✅ Legacy system compatibility
- ✅ No vector search requirements
- ✅ Minimal resource usage

## 🛠️ **Advanced Configuration**

### Memory Decay Settings
```bash
# Enable intelligent memory decay
export ORKA_MEMORY_DECAY_ENABLED=true
export ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2
export ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168
export ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES=30
```

### Performance Tuning
```bash
# Redis connection pooling
export REDIS_MAX_CONNECTIONS=100
export REDIS_CONNECTION_TIMEOUT=5

# Memory optimization
export ORKA_MEMORY_COMPRESSION_ENABLED=true
export ORKA_MEMORY_BATCH_SIZE=1000
```

## 🔧 **Troubleshooting**

### Common Issues

**"FT.CREATE unknown command"**
- **Cause:** Using basic Redis instead of RedisStack
- **Solution:** Switch to RedisStack or use `ORKA_FORCE_BASIC_REDIS=true`

**Slow vector search performance**
- **Cause:** HNSW index not created or optimized
- **Solution:** Check index status with `redis-cli FT._LIST`

**Connection refused errors**
- **Cause:** Redis/RedisStack not running
- **Solution:** Start Redis with `docker run -p 6380:6380 redis/redis-stack`

### Health Checks
```bash
# Check Redis connection
redis-cli ping

# Check RedisStack features
redis-cli FT._LIST

# Monitor OrKa memory
orka memory watch
```

## 📈 **Migration Guide**

### From Basic Redis to RedisStack
```bash
# 1. Stop current Redis
docker stop redis

# 2. Start RedisStack
docker run -d -p 6380:6380 redis/redis-stack

# 3. Update environment
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6380/0

# 4. Restart OrKa
python -m orka.orka_start
```

## 🎯 **Best Practices**

Guidance: RedisStack is recommended for latency-sensitive workloads; evaluate trade-offs and test for your specific environment.
2. **Development:** RedisStack recommended, Redis acceptable for simple testing
3. **Monitoring:** Use `orka memory watch` to monitor performance
4. **Backup:** Configure Redis persistence with `--save` options
5. **Security:** Use Redis AUTH and network isolation in deployments

## 📚 **Additional Resources**

- [Memory System Guide](MEMORY_SYSTEM_GUIDE.md)
- [YAML Configuration](YAML_CONFIGURATION.md)
- [Troubleshooting Guide](troubleshooting.md)
- [Performance Tuning](best-practices.md)