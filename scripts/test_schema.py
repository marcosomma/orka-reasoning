import os

from orka.memory.schema_manager import SchemaFormat, create_schema_manager

# Set environment variables
os.environ["KAFKA_SCHEMA_REGISTRY_URL"] = "http://localhost:8081"
os.environ["KAFKA_USE_SCHEMA_REGISTRY"] = "true"
os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"

# Initialize schema manager
schema_manager = create_schema_manager(
    registry_url="http://localhost:8081",
    format=SchemaFormat.AVRO,
)

# Register schema
try:
    schema_id = schema_manager.register_schema("orka-memory-topic-value", "memory_entry")
    print(f"Successfully registered schema with ID: {schema_id}")
except Exception as e:
    print(f"Error registering schema: {e}")
