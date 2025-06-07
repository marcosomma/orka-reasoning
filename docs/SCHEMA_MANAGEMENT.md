# OrKa Schema Management

## 🎯 Overview

OrKa has transitioned from raw JSON blobs to proper schema-based message serialization using **Confluent Schema Registry**. This provides strong type safety, schema evolution, and prevents the technical debt associated with unstructured data.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   OrKa Memory   │───▶│  Schema Registry │───▶│  Kafka Topics   │
│    Producer     │    │   (Port 8081)    │    │   (Avro/Proto)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Schema Evolution │
                       │ & Compatibility  │
                       └──────────────────┘
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements-schema.txt
```

### 2. Start Schema Registry

```bash
# Start Kafka with Schema Registry
docker-compose --profile kafka up -d

# Verify Schema Registry is running
curl http://localhost:8081/subjects
```

### 3. Basic Usage

```python
from orka.memory.schema_manager import create_schema_manager, SchemaFormat

# Initialize schema manager
schema_manager = create_schema_manager(
    registry_url='http://localhost:8081',
    format=SchemaFormat.AVRO  # or SchemaFormat.PROTOBUF
)

# Register schemas
schema_manager.register_schema('orka-memory-topic-value', 'memory_entry')

# Use in your code
serializer = schema_manager.get_serializer('orka-memory-topic')
deserializer = schema_manager.get_deserializer('orka-memory-topic')
```

## 📊 Available Schemas

### Avro Schema (`orka/schemas/avro/memory_entry.avsc`)

```json
{
  "type": "record",
  "name": "MemoryEntry",
  "namespace": "orka.memory",
  "fields": [
    {"name": "id", "type": "string"},
    {"name": "content", "type": "string"},
    {"name": "metadata", "type": {
      "type": "record",
      "name": "MemoryMetadata",
      "fields": [
        {"name": "source", "type": "string"},
        {"name": "confidence", "type": "double"},
        {"name": "timestamp", "type": "double"},
        {"name": "agent_id", "type": "string"},
        {"name": "tags", "type": {"type": "array", "items": "string"}},
        // ... more fields
      ]
    }},
    {"name": "similarity", "type": ["null", "double"]},
    {"name": "ts", "type": "long"},
    {"name": "match_type", "type": {
      "type": "enum",
      "symbols": ["exact", "semantic", "fuzzy", "stream", "hybrid"]
    }},
    {"name": "stream_key", "type": "string"}
  ]
}
```

### Protobuf Schema (`orka/schemas/protobuf/memory_entry.proto`)

```protobuf
syntax = "proto3";
package orka.memory;

message MemoryEntry {
  string id = 1;
  string content = 2;
  MemoryMetadata metadata = 3;
  optional double similarity = 4;
  int64 ts = 5;
  MatchType match_type = 6;
  string stream_key = 7;
}

message MemoryMetadata {
  string source = 1;
  double confidence = 2;
  repeated string tags = 8;
  // ... more fields
}

enum MatchType {
  SEMANTIC = 0;
  EXACT = 1;
  FUZZY = 2;
  STREAM = 3;
  HYBRID = 4;
}
```

## 🔄 Migration from JSON

### Automated Migration

```bash
# Analyze your existing JSON messages
python scripts/migrate_to_schemas.py --analyze logs/orka_trace_*.json --generate-code --create-plan

# This generates:
# - migration_code.py (code templates)
# - migration_plan.md (step-by-step plan)
```

### Manual Migration Steps

1. **Install Schema Dependencies**
   ```bash
   pip install confluent-kafka[avro] confluent-kafka[protobuf]
   ```

2. **Update Producers**
   ```python
   # OLD: Raw JSON
   producer.produce(topic, value=json.dumps(memory_obj).encode())
   
   # NEW: Schema-based
   from orka.memory.schema_manager import create_schema_manager
   schema_manager = create_schema_manager()
   serializer = schema_manager.get_serializer(topic)
   
   producer.produce(
       topic=topic,
       value=serializer(memory_obj, SerializationContext(topic, MessageField.VALUE))
   )
   ```

3. **Update Consumers**
   ```python
   # OLD: Raw JSON
   memory_obj = json.loads(message.value().decode())
   
   # NEW: Schema-based
   deserializer = schema_manager.get_deserializer(topic)
   memory_obj = deserializer(message.value(), SerializationContext(topic, MessageField.VALUE))
   ```

## 🛠️ Schema Registry Management

### Available Endpoints

| Service | URL | Description |
|---------|-----|-------------|
| Schema Registry | `http://localhost:8081` | Main registry API |
| Schema Registry UI | `http://localhost:8082` | Web interface for schemas |

### Common Operations

```bash
# List all subjects
curl http://localhost:8081/subjects

# Get schema for a subject
curl http://localhost:8081/subjects/orka-memory-topic-value/versions/latest

# Register a new schema
curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"schema": "..."}' \
  http://localhost:8081/subjects/orka-memory-topic-value/versions

# Check compatibility
curl -X POST -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  --data '{"schema": "..."}' \
  http://localhost:8081/compatibility/subjects/orka-memory-topic-value/versions/latest
```

## 🔄 Schema Evolution

### Backward Compatible Changes ✅

- Adding optional fields with defaults
- Adding new enum values (at the end)
- Removing fields (with proper handling)

### Breaking Changes ❌

- Removing required fields
- Changing field types
- Reordering fields (Protobuf)
- Changing enum values

### Evolution Example

```python
# Version 1: Original schema
{
  "name": "MemoryEntry",
  "fields": [
    {"name": "id", "type": "string"},
    {"name": "content", "type": "string"}
  ]
}

# Version 2: Added optional field (backward compatible)
{
  "name": "MemoryEntry", 
  "fields": [
    {"name": "id", "type": "string"},
    {"name": "content", "type": "string"},
    {"name": "confidence", "type": ["null", "double"], "default": null}
  ]
}
```

## 📊 Monitoring & Debugging

### Real-time Logs

```bash
# Schema Registry logs
docker logs -f docker-schema-registry-1

# Kafka logs with schema info
docker logs -f docker-kafka-1 | grep -i schema

# All services
docker-compose logs -f schema-registry kafka
```

### Schema Registry UI

Visit `http://localhost:8082` to:
- Browse registered schemas
- View schema evolution history
- Test schema compatibility
- Manage schema subjects

### Troubleshooting

| Problem | Solution |
|---------|----------|
| Schema not found | Check registration: `curl http://localhost:8081/subjects` |
| Serialization error | Validate data against schema |
| Compatibility error | Review schema evolution rules |
| Registry unreachable | Verify Docker services: `docker ps` |

## 🎛️ Configuration

### Environment Variables

```bash
# Schema Registry URL
KAFKA_SCHEMA_REGISTRY_URL=http://schema-registry:8081

# Schema format preference  
ORKA_SCHEMA_FORMAT=avro  # or protobuf

# Schema compatibility level
SCHEMA_REGISTRY_COMPATIBILITY_LEVEL=BACKWARD
```

### Docker Compose Configuration

```yaml
services:
  schema-registry:
    image: confluentinc/cp-schema-registry:latest
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:29092
      SCHEMA_REGISTRY_LISTENERS: http://0.0.0.0:8081
```

## 🏎️ Performance Considerations

### Avro vs Protobuf

| Feature | Avro | Protobuf |
|---------|------|----------|
| **Size** | Smaller (no field tags) | Slightly larger |
| **Speed** | Fast | Very fast |
| **Schema Evolution** | Excellent | Good |
| **Language Support** | Good | Excellent |
| **Best For** | Data pipelines | Microservices |

### Recommendations

- **Use Avro** for data-heavy applications with frequent schema changes
- **Use Protobuf** for high-performance APIs and cross-language compatibility
- **Enable compression** at Kafka level for additional space savings
- **Cache serializers/deserializers** to avoid schema registry lookups

## 🔒 Security

### Schema Registry Security

```yaml
# Add to docker-compose.yml for production
environment:
  SCHEMA_REGISTRY_AUTHENTICATION_METHOD: BASIC
  SCHEMA_REGISTRY_AUTHENTICATION_REALM: SchemaRegistry
  SCHEMA_REGISTRY_AUTHENTICATION_ROLES: admin,user
```

### Access Control

- Implement role-based access to schema subjects
- Use HTTPS for schema registry in production
- Restrict schema modification permissions
- Monitor schema changes and access patterns

## 📚 Additional Resources

- [Confluent Schema Registry Documentation](https://docs.confluent.io/platform/current/schema-registry/)
- [Avro Specification](https://avro.apache.org/docs/current/spec.html)
- [Protocol Buffers Documentation](https://developers.google.com/protocol-buffers)
- [Schema Evolution Best Practices](https://docs.confluent.io/platform/current/schema-registry/avro.html#schema-evolution)

---

**Next Steps**: After implementing schema management, consider adding:
- Schema validation in CI/CD pipelines
- Automated schema testing
- Data lineage tracking
- Schema governance policies 