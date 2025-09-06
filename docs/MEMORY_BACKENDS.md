# Orka Memory Backends

Orka supports Redis-based memory backends for storing orchestration events, agent outputs, and system state. Choose between RedisStack (recommended) and basic Redis based on your performance requirements.

## Overview

The memory system in Orka serves several purposes:
- **Event Logging**: Records all agent activities and system events
- **Data Persistence**: Stores data for reliability and debugging
- **Agent Communication**: Enables agents to access past context and outputs
- **Fork/Join Coordination**: Manages parallel execution branches
- **Audit Trail**: Provides complete workflow history

## Supported Backends

### RedisStack (Recommended)
- **Best for**: Production AI workloads, high-performance applications
- **Features**: HNSW vector indexing, 100x faster search, advanced memory management
- **Performance**: Sub-millisecond search, 50,000+ operations/second
- **Scalability**: Single RedisStack instance or Redis Cluster

### Redis (Legacy)
- **Best for**: Development, single-node deployments, quick prototyping
- **Features**: Fast in-memory operations, simple setup, full feature support
- **Persistence**: Redis streams and data structures
- **Scalability**: Single Redis instance or Redis Cluster

## Configuration

### Environment Variables

Set the memory backend using environment variables:

```bash
# For RedisStack (default - recommended)
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6380/0

# For basic Redis
export ORKA_MEMORY_BACKEND=redis
export REDIS_URL=redis://localhost:6380/0
```

### RedisStack Configuration

```bash
# Basic RedisStack setup
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6380/0

# RedisStack with authentication
export REDIS_URL=redis://:password@localhost:6380/0

# Redis Cluster
export REDIS_URL=redis://node1:6380,node2:6380,node3:6380/0
```

### Basic Redis Configuration

```bash
# Force basic Redis mode
export ORKA_MEMORY_BACKEND=redis
export ORKA_FORCE_BASIC_REDIS=true
export REDIS_URL=redis://localhost:6380/0
```

## Backend Comparison

| Feature | Basic Redis | RedisStack |
|---------|-------------|------------|
| Event Logging | ✅ Redis Streams | ✅ Redis Streams |
| Hash Operations | ✅ Native Redis | ✅ Native Redis |
| Set Operations | ✅ Native Redis | ✅ Native Redis |
| Vector Search | ❌ Not Available | ✅ HNSW Indexing |
| Search Performance | Standard | 100x Faster |
| Memory Efficiency | Standard | 60% Reduction |
| Concurrent Operations | Standard | 1000+ Simultaneous |
| Setup Complexity | Simple | Simple |

## Installation

### RedisStack Backend (Recommended)
```bash
# Using Docker (recommended)
docker run -d -p 6380:6379 redis/redis-stack-server:latest

# Or install natively
# Windows: Download from https://redis.io/download
# macOS: brew install redis-stack
# Ubuntu: sudo apt install redis-stack-server
```

### Basic Redis Backend
```bash
# Using Docker
docker run -d -p 6380:6379 redis:latest

# Or install natively
# macOS: brew install redis
# Ubuntu: sudo apt install redis-server
```

## Docker Setup Examples

### RedisStack with Docker
```yaml
version: '3.8'
services:
  redis:
    image: redis/redis-stack-server:7.2.0-v6
    ports:
      - "6380:6379"
    volumes:
      - redis_data:/data
    command: >
      redis-stack-server 
      --appendonly yes 
      --maxmemory 2gb 
      --maxmemory-policy allkeys-lru

  orka:
    build: .
    environment:
      - ORKA_MEMORY_BACKEND=redisstack
      - REDIS_URL=redis://redis:6380/0
    depends_on:
      - redis

volumes:
  redis_data:
```

### Basic Redis with Docker
```yaml
version: '3.8'
services:
  redis:
    image: redis:latest
    ports:
      - "6380:6379"
    command: redis-server --appendonly yes

  orka:
    build: .
    environment:
      - ORKA_MEMORY_BACKEND=redis
      - REDIS_URL=redis://redis:6380/0
    depends_on:
      - redis
```

## Usage Examples

### Programmatic Configuration

```python
from orka.memory_logger import create_memory_logger

# RedisStack backend (recommended)
redisstack_memory = create_memory_logger(
    backend="redisstack",
    redis_url="redis://localhost:6380/0"
)

# Basic Redis backend
redis_memory = create_memory_logger(
    backend="redis",
    redis_url="redis://localhost:6380/0"
)
```

### Orchestrator Integration

```python
from orka.orchestrator import Orchestrator
import os

# Set environment variable
os.environ["ORKA_MEMORY_BACKEND"] = "redisstack"
os.environ["REDIS_URL"] = "redis://localhost:6380/0"

# Initialize orchestrator (will automatically use RedisStack)
orchestrator = Orchestrator("config.yml")
result = await orchestrator.run("input data")
```

## Performance Characteristics

### RedisStack Performance
- **Vector Search**: Sub-millisecond latency with HNSW indexing
- **Write Throughput**: 50,000+ memories/second sustained
- **Search Latency**: <5ms for complex hybrid queries
- **Memory Efficiency**: ~60% reduction in storage overhead
- **Concurrent Users**: 1000+ simultaneous search operations

### Basic Redis Performance
- **Write Throughput**: 10,000+ memories/second sustained
- **Read Latency**: <50ms average search latency
- **Memory Efficiency**: Standard Redis performance
- **Scalability**: Horizontal scaling with Redis Cluster support

## Migration Guide

### From Basic Redis to RedisStack
1. Stop your Orka application
2. Start RedisStack instead of basic Redis
3. Update environment variable: `ORKA_MEMORY_BACKEND=redisstack`
4. Restart Orka - existing data will be preserved

### Configuration Migration
```bash
# Old configuration
export ORKA_MEMORY_BACKEND=redis

# New configuration
export ORKA_MEMORY_BACKEND=redisstack
```

## Monitoring

### Redis Monitoring
```bash
# Connect to Redis CLI
redis-cli -p 6380

# Check Redis info
redis-cli -p 6380 info

# Monitor Redis operations
redis-cli -p 6380 monitor

# Check memory usage
redis-cli -p 6380 info memory
```

### RedisStack Monitoring
```bash
# Check loaded modules
redis-cli -p 6380 MODULE LIST

# Check vector index info
redis-cli -p 6380 FT.INFO orka_enhanced_memory

# Monitor search operations
redis-cli -p 6380 FT.SEARCH orka_enhanced_memory "*"
```

## Best Practices

1. **Backend Selection**:
   - Use RedisStack for production AI workloads requiring fast search
   - Use basic Redis for simple applications or development

2. **Memory Management**:
   - Configure appropriate memory limits and eviction policies
   - Enable persistence (AOF/RDB) for data durability

3. **Performance Optimization**:
   - Use RedisStack HNSW indexing for vector search workloads
   - Configure memory decay rules to manage data lifecycle

4. **Monitoring**:
   - Monitor Redis memory usage and performance metrics
   - Set up alerts for memory usage and connection issues

5. **Production Deployment**:
   - Use Redis Cluster for high availability
   - Configure appropriate backup and retention policies
   - Use RedisStack for maximum performance benefits