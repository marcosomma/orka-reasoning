#!/usr/bin/env python3
"""
Migration script to transition OrKa from raw JSON to schema-based Kafka messages.
This script helps you migrate existing data and update your codebase.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add the orka directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from orka.memory.schema_manager import SchemaFormat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_existing_json_messages(json_file: str) -> Dict[str, Any]:
    """Analyze existing JSON messages to understand the data structure."""
    logger.info(f"Analyzing JSON messages in {json_file}")

    messages = []
    field_types = {}

    try:
        with open(json_file, "r") as f:
            for line in f:
                try:
                    msg = json.loads(line.strip())
                    messages.append(msg)

                    # Analyze field types
                    _analyze_fields(msg, field_types, "")

                except json.JSONDecodeError:
                    logger.warning(f"Skipping invalid JSON line: {line[:100]}...")

    except FileNotFoundError:
        logger.error(f"File not found: {json_file}")
        return {}

    logger.info(f"Analyzed {len(messages)} messages")
    logger.info("Field type analysis:")
    for field, types in field_types.items():
        logger.info(f"  {field}: {types}")

    return {
        "message_count": len(messages),
        "field_types": field_types,
        "sample_messages": messages[:5],  # First 5 messages as samples
    }


def _analyze_fields(obj: Any, field_types: Dict[str, set], prefix: str):
    """Recursively analyze field types in JSON objects."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            field_name = f"{prefix}.{key}" if prefix else key
            field_types.setdefault(field_name, set()).add(type(value).__name__)
            _analyze_fields(value, field_types, field_name)
    elif isinstance(obj, list) and obj:
        # Analyze the first item in the list
        list_field = f"{prefix}[]"
        field_types.setdefault(list_field, set()).add(
            f"list of {type(obj[0]).__name__}"
        )
        _analyze_fields(obj[0], field_types, list_field)


def validate_against_schema(
    messages: List[Dict], schema_format: SchemaFormat
) -> Dict[str, Any]:
    """Validate existing messages against the new schema."""
    logger.info(f"Validating messages against {schema_format.value} schema")

    valid_count = 0
    invalid_count = 0
    validation_errors = []

    # This is a simplified validation - in practice you'd use the actual schema
    required_fields = ["id", "content", "metadata", "ts", "stream_key"]

    for i, msg in enumerate(messages):
        try:
            # Basic validation
            missing_fields = [field for field in required_fields if field not in msg]
            if missing_fields:
                validation_errors.append(
                    {
                        "message_index": i,
                        "error": f"Missing required fields: {missing_fields}",
                        "message": msg,
                    }
                )
                invalid_count += 1
            else:
                valid_count += 1

        except Exception as e:
            validation_errors.append(
                {"message_index": i, "error": str(e), "message": msg}
            )
            invalid_count += 1

    return {
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "validation_errors": validation_errors[:10],  # First 10 errors
    }


def generate_migration_code(analysis: Dict[str, Any]) -> str:
    """Generate Python code to help with the migration."""
    return f"""
# Generated migration code for OrKa schema transition
# Based on analysis of {analysis["message_count"]} existing messages

from orka.memory.schema_manager import create_schema_manager, SchemaFormat
from confluent_kafka.serialization import SerializationContext, MessageField

# 1. Initialize schema manager
schema_manager = create_schema_manager(
    registry_url='http://localhost:8081',  # Update with your registry URL
    format=SchemaFormat.AVRO  # or SchemaFormat.PROTOBUF
)

# 2. Register your schemas
schema_manager.register_schema('orka-memory-topic-value', 'memory_entry')

# 3. Update your producer code
def send_memory_message(producer, topic: str, memory_data: dict):
    serializer = schema_manager.get_serializer(topic)
    
    # Transform your existing data structure if needed
    transformed_data = transform_legacy_message(memory_data)
    
    producer.produce(
        topic=topic,
        value=serializer(
            transformed_data,
            SerializationContext(topic, MessageField.VALUE)
        )
    )

# 4. Update your consumer code  
def consume_memory_messages(consumer, topic: str):
    deserializer = schema_manager.get_deserializer(topic)
    
    for message in consumer:
        if message.error():
            continue
            
        memory_data = deserializer(
            message.value(),
            SerializationContext(topic, MessageField.VALUE)
        )
        
        # Process your memory data
        process_memory(memory_data)

# 5. Data transformation function (customize based on your data)
def transform_legacy_message(legacy_msg: dict) -> dict:
    '''Transform legacy JSON message to match schema.'''
    return {{
        "id": legacy_msg.get("id", ""),
        "content": legacy_msg.get("content", ""),
        "metadata": {{
            "source": legacy_msg.get("metadata", {{}}).get("source", "unknown"),
            "confidence": float(legacy_msg.get("metadata", {{}}).get("confidence", 0.0)),
            "reason": legacy_msg.get("metadata", {{}}).get("reason"),
            "fact": legacy_msg.get("metadata", {{}}).get("fact"),
            "timestamp": float(legacy_msg.get("metadata", {{}}).get("timestamp", 0.0)),
            "agent_id": legacy_msg.get("metadata", {{}}).get("agent_id", ""),
            "query": legacy_msg.get("metadata", {{}}).get("query"),
            "tags": legacy_msg.get("metadata", {{}}).get("tags", []),
            "vector_embedding": legacy_msg.get("metadata", {{}}).get("vector_embedding")
        }},
        "similarity": legacy_msg.get("similarity"),
        "ts": int(legacy_msg.get("ts", 0)),
        "match_type": legacy_msg.get("match_type", "semantic"),
        "stream_key": legacy_msg.get("stream_key", "default")
    }}

# 6. Gradual migration strategy
# - Deploy schema registry and register schemas
# - Update producers to use schemas (they can coexist with JSON consumers)
# - Update consumers to handle both JSON and schema-based messages
# - Once all consumers are updated, remove JSON fallback
"""


def create_migration_plan(analysis: Dict[str, Any]) -> str:
    """Create a step-by-step migration plan."""
    return f"""
OrKa Schema Migration Plan
==========================

Current State Analysis:
- Total messages analyzed: {analysis["message_count"]}
- Unique field patterns detected: {len(analysis["field_types"])}

Migration Steps:

1. PREPARATION (0-1 days)
   □ Install schema dependencies: pip install -r requirements-schema.txt
   □ Start schema registry: docker-compose --profile kafka up -d
   □ Verify schema registry: curl http://localhost:8081/subjects
   □ Register schemas: python scripts/register_schemas.py

2. PRODUCER MIGRATION (1-2 days)
   □ Update Kafka producers to use schema serialization
   □ Deploy dual-mode producers (both JSON and Avro/Protobuf)
   □ Monitor producer metrics and error rates
   □ Gradually shift traffic to schema-based messages

3. CONSUMER MIGRATION (2-3 days)  
   □ Update consumers to handle both formats during transition
   □ Deploy schema-aware consumers
   □ Monitor consumer lag and processing errors
   □ Validate data integrity

4. CLEANUP (1 day)
   □ Remove JSON serialization code
   □ Update monitoring and alerting
   □ Document new schema management processes
   □ Archive old JSON-based topic data

5. VALIDATION
   □ Schema evolution testing
   □ Backward compatibility verification
   □ Performance impact assessment
   □ Rollback procedures documentation

Estimated Total Time: 4-7 days

Benefits After Migration:
✓ Strong type safety and data validation
✓ Schema evolution and backward compatibility
✓ Better documentation of data contracts
✓ Reduced storage overhead (Avro) or better performance (Protobuf)
✓ Integration with Confluent ecosystem tools
"""


def main():
    parser = argparse.ArgumentParser(
        description="Migrate OrKa from JSON to schema-based Kafka messages"
    )
    parser.add_argument("--analyze", type=str, help="JSON file to analyze")
    parser.add_argument(
        "--format",
        choices=["avro", "protobuf"],
        default="avro",
        help="Schema format to use",
    )
    parser.add_argument(
        "--generate-code", action="store_true", help="Generate migration code"
    )
    parser.add_argument(
        "--create-plan", action="store_true", help="Create migration plan"
    )

    args = parser.parse_args()

    if args.analyze:
        analysis = analyze_existing_json_messages(args.analyze)

        if args.generate_code:
            code = generate_migration_code(analysis)
            with open("migration_code.py", "w") as f:
                f.write(code)
            logger.info("Generated migration code in migration_code.py")

        if args.create_plan:
            plan = create_migration_plan(analysis)
            with open("migration_plan.md", "w") as f:
                f.write(plan)
            logger.info("Created migration plan in migration_plan.md")

        # Validate messages against schema
        schema_format = (
            SchemaFormat.AVRO if args.format == "avro" else SchemaFormat.PROTOBUF
        )
        if analysis.get("sample_messages"):
            validation = validate_against_schema(
                analysis["sample_messages"], schema_format
            )
            logger.info(
                f"Schema validation: {validation['valid_count']} valid, {validation['invalid_count']} invalid"
            )
            if validation["validation_errors"]:
                logger.warning("Sample validation errors:")
                for error in validation["validation_errors"][:3]:
                    logger.warning(f"  {error}")

    else:
        logger.info("Use --analyze <json_file> to start migration analysis")
        logger.info(
            "Example: python scripts/migrate_to_schemas.py --analyze logs/kafka_messages.json --generate-code --create-plan"
        )


if __name__ == "__main__":
    main()
