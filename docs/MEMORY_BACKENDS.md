# Orka Memory Backends

Orka supports multiple memory backends for storing orchestration events, agent outputs, and system state. You can choose between Redis and Kafka based on your infrastructure and requirements.

## Overview

The memory system in Orka serves several purposes:
- **Event Logging**: Records all agent activities and system events
- **Data Persistence**: Stores data for reliability and debugging
- **Agent Communication**: Enables agents to access past context and outputs
- **Fork/Join Coordination**: Manages parallel execution branches
- **Audit Trail**: Provides complete workflow history

## Supported Backends

### Redis (Default)
- **Best for**: Traditional deployments, single-node setups, quick prototyping
- **Features**: Full feature support including fork/join coordination, hash/set operations
- **Persistence**: Redis streams and data structures
- **Scalability**: Single Redis instance or Redis Cluster

### Kafka
- **Best for**: Event-driven architectures, microservices, high-throughput scenarios
- **Features**: Event streaming, basic coordination (in-memory fork/join)
- **Persistence**: Kafka topics with configurable retention
- **Scalability**: Native Kafka clustering and partitioning

## Configuration

### Environment Variables

Set the memory backend using environment variables:

```bash
# For Redis (default)
export ORKA_MEMORY_BACKEND=redis
export REDIS_URL=redis://localhost:6380/0

# For Kafka
export ORKA_MEMORY_BACKEND=kafka
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_TOPIC_PREFIX=orka-memory
```

### Redis Configuration

```bash
# Basic Redis setup
export ORKA_MEMORY_BACKEND=redis
export REDIS_URL=redis://localhost:6380/0

# Redis with authentication
export REDIS_URL=redis://:password@localhost:6380/0

# Redis Cluster
export REDIS_URL=redis://node1:6380,node2:6380,node3:6380/0
```

### Kafka Configuration

```bash
# Basic Kafka setup
export ORKA_MEMORY_BACKEND=kafka
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_TOPIC_PREFIX=orka-memory

# Kafka with multiple brokers
export KAFKA_BOOTSTRAP_SERVERS=broker1:9092,broker2:9092,broker3:9092

# Custom topic prefix
export KAFKA_TOPIC_PREFIX=my-app-events
```

## YAML Configuration

You can also specify memory configuration in your orchestrator YAML:

### Redis Example
```yaml
orchestrator:
  id: "my-orchestrator"
  strategy: "parallel"
  memory:
    store_type: "redis"
    url: "redis://localhost:6380/0"
  agents:
    - "agent1"
    - "agent2"
```

### Kafka Example
```yaml
orchestrator:
  id: "my-orchestrator"
  strategy: "parallel"
  memory:
    store_type: "kafka"
    bootstrap_servers: "localhost:9092"
    topic_prefix: "orka-memory"
  agents:
    - "agent1"
    - "agent2"
```

## Backend Comparison

| Feature | Redis | Kafka |
|---------|-------|-------|
| Event Logging | ✅ Redis Streams | ✅ Kafka Topics |
| Hash Operations | ✅ Native Redis | ✅ In-Memory |
| Set Operations | ✅ Native Redis | ✅ In-Memory |
| Fork/Join Coordination | ✅ Distributed | ⚠️ In-Memory Only |
| Tail Operations | ✅ XREVRANGE | ⚠️ Local Buffer |
| Persistence | ✅ Redis RDB/AOF | ✅ Kafka Log Segments |
| Scalability | ✅ Redis Cluster | ✅ Kafka Partitions |
| Event Replay | ⚠️ Limited | ✅ Full History |
| Memory Usage | ⚠️ All in RAM | ✅ Disk + RAM |

## Installation Requirements

### Redis Backend
```bash
pip install redis[async]>=5.0.0
```

### Kafka Backend
```bash
pip install kafka-python>=2.0.2
```

## Docker Setup

### Redis with Docker
```yaml
version: '3.8'
services:
  redis:
    image: redis:7.2-alpine
    ports:
      - "6380:6380"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  orka:
    build: .
    environment:
      - ORKA_MEMORY_BACKEND=redis
      - REDIS_URL=redis://redis:6380/0
    depends_on:
      - redis

volumes:
  redis_data:
```

### Kafka with Docker
```yaml
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  orka:
    build: .
    environment:
      - ORKA_MEMORY_BACKEND=kafka
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - KAFKA_TOPIC_PREFIX=orka-memory
    depends_on:
      - kafka
```

## Usage Examples

### Programmatic Configuration

```python
from orka.memory_logger import create_memory_logger

# Redis backend
redis_memory = create_memory_logger(
    backend="redis",
    redis_url="redis://localhost:6380/0"
)

# Kafka backend
kafka_memory = create_memory_logger(
    backend="kafka",
    bootstrap_servers="localhost:9092",
    topic_prefix="my-events"
)
```

### Orchestrator Integration

```python
from orka.orchestrator import Orchestrator
import os

# Set environment variable
os.environ["ORKA_MEMORY_BACKEND"] = "kafka"
os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"

# Initialize orchestrator (will automatically use Kafka)
orchestrator = Orchestrator("config.yml")
result = await orchestrator.run("input data")
```

## Limitations and Considerations

### Kafka Backend Limitations
1. **Fork/Join Coordination**: Uses in-memory storage, not distributed
2. **Hash/Set Operations**: Stored locally, lost on restart
3. **Tail Operations**: Limited to local memory buffer
4. **Cross-Instance**: Not suitable for multi-instance deployments without shared state

### Redis Backend Limitations
1. **Memory Usage**: All data stored in RAM
2. **Event Replay**: Limited retention compared to Kafka
3. **Horizontal Scaling**: Requires Redis Cluster setup

## Migration Between Backends

### Redis to Kafka
1. Export existing Redis data using `save_to_file()`
2. Configure Kafka backend
3. Restart orchestrator
4. Optionally replay events from exported file

### Kafka to Redis
1. Configure Redis backend
2. Restart orchestrator
3. Historical Kafka events remain in topics for reference

## Monitoring and Debugging

### Redis Monitoring
```bash
# Monitor Redis commands
redis-cli monitor

# Check stream length
redis-cli xlen orka:memory

# View recent events
redis-cli xrevrange orka:memory + - count 10
```

### Kafka Monitoring
```bash
# List topics
kafka-topics --bootstrap-server localhost:9092 --list

# Check topic details
kafka-topics --bootstrap-server localhost:9092 --describe --topic orka-memory-events

# Consume events
kafka-console-consumer --bootstrap-server localhost:9092 --topic orka-memory-events --from-beginning
```

## Best Practices

1. **Choose the Right Backend**:
   - Use Redis for simpler deployments and full feature support
   - Use Kafka for event-driven architectures and high throughput

2. **Configuration Management**:
   - Use environment variables for production deployments
   - Use YAML configuration for development and testing

3. **Monitoring**:
   - Monitor memory usage and event throughput
   - Set up appropriate retention policies

4. **Testing**:
   - Test both backends in your development environment
   - Use the fake Redis client for unit tests

5. **Production Deployment**:
   - Use Redis Cluster or Kafka clusters for high availability
   - Configure appropriate backup and retention policies 