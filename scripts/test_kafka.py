import os

from orka.memory_logger import create_memory_logger

# Set environment variables
os.environ["ORKA_MEMORY_BACKEND"] = "kafka"
os.environ["KAFKA_BOOTSTRAP_SERVERS"] = "localhost:9092"
os.environ["KAFKA_SCHEMA_REGISTRY_URL"] = "http://localhost:8081"
os.environ["KAFKA_USE_SCHEMA_REGISTRY"] = "true"
os.environ["KAFKA_TOPIC_PREFIX"] = "orka-memory"
os.environ["REDIS_URL"] = "redis://localhost:6380/0"

try:
    # Create memory logger
    memory = create_memory_logger(
        backend="kafka",
        bootstrap_servers="localhost:9092",
        redis_url="redis://localhost:6380/0",
    )

    # Try to write a test message
    memory.log(
        agent_id="test_agent",
        event_type="test_event",
        payload={"test": "message"},
        run_id="test_run",
        step=1,
    )
    print("✅ Successfully wrote message to Kafka")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
