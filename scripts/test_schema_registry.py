import json
import os
import time

from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.serialization import MessageField, SerializationContext

from orka.memory.schema_manager import SchemaFormat, create_schema_manager


def test_schema_registry():
    print("🔧 Testing Schema Registry Integration")

    # 1. Set environment variables
    os.environ["KAFKA_SCHEMA_REGISTRY_URL"] = "http://localhost:8081"
    os.environ["KAFKA_USE_SCHEMA_REGISTRY"] = "true"
    os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"

    try:
        # 2. Test Schema Registry connection
        print("\n1. Testing Schema Registry connection...")
        registry_client = SchemaRegistryClient({"url": "http://localhost:8081"})
        subjects = registry_client.get_subjects()
        print(f"✅ Connected to Schema Registry. Current subjects: {subjects}")

        # 3. Initialize schema manager
        print("\n2. Initializing schema manager...")
        schema_manager = create_schema_manager(
            registry_url="http://localhost:8081",
            format=SchemaFormat.AVRO,
        )
        print("✅ Schema manager initialized")

        # 4. Register schema
        print("\n3. Registering schema...")
        schema_id = schema_manager.register_schema("orka-memory-topic-value", "memory_entry")
        print(f"✅ Schema registered with ID: {schema_id}")

        # 5. Create test message
        test_message = {
            "id": "test-001",
            "content": json.dumps({"test": "Schema Registry Integration Test"}),
            "metadata": {
                "source": "schema-test",
                "confidence": 1.0,
                "timestamp": time.time(),
                "agent_id": "test-agent",
                "tags": ["test", "schema-registry"],
            },
            "ts": int(time.time() * 1000000000),
            "match_type": "exact",
            "stream_key": "orka:test",
        }

        # 6. Test serialization
        print("\n4. Testing serialization...")
        serializer = schema_manager.get_serializer("orka-memory-topic")
        serialized = serializer(
            test_message, SerializationContext("orka-memory-topic", MessageField.VALUE)
        )
        print("✅ Message serialized successfully")

        # 7. Test deserialization
        print("\n5. Testing deserialization...")
        deserializer = schema_manager.get_deserializer("orka-memory-topic")
        deserialized = deserializer(
            serialized, SerializationContext("orka-memory-topic", MessageField.VALUE)
        )
        print("✅ Message deserialized successfully")

        # 8. Verify message content
        print("\n6. Verifying message content...")
        assert deserialized["id"] == test_message["id"], "ID mismatch"
        assert deserialized["content"] == test_message["content"], "Content mismatch"
        print("✅ Message content verified")

        # 9. Test producer integration
        print("\n7. Testing producer integration...")
        producer = Producer(
            {
                "bootstrap.servers": "localhost:9092",
                "client.id": "schema-test-producer",
            }
        )

        producer.produce(
            topic="orka-memory-topic",
            value=serialized,
            callback=lambda err, msg: print(
                f"✅ Message delivered to {msg.topic()}"
                if err is None
                else f"❌ Failed to deliver message: {err}"
            ),
        )
        producer.flush()

        print("\n✅ Schema Registry integration test completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during schema registry test: {e!s}")
        raise


if __name__ == "__main__":
    test_schema_registry()
