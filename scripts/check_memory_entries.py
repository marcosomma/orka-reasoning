#!/usr/bin/env python3
import redis


def check_memory_entries():
    r = redis.Redis(decode_responses=True)

    print("🔍 Checking Memory Entries")
    print("=" * 40)

    entries = r.xrange("orka:memory", count=10)
    print(f"Found {len(entries)} entries in orka:memory")

    for i, (entry_id, fields) in enumerate(entries):
        agent_id = fields.get("agent_id", "N/A")
        event_type = fields.get("event_type", "N/A")
        namespace = fields.get("orka_namespace", fields.get("namespace", "N/A"))

        print(f"  Entry {i + 1}: {agent_id} - {event_type} - namespace: {namespace}")

        # If it's a memory write event, show payload namespace
        if event_type == "write" and "payload" in fields:
            try:
                import json

                payload = json.loads(fields["payload"])
                payload_namespace = payload.get("namespace", "N/A")
                print(f"    Payload namespace: {payload_namespace}")
            except:
                pass


if __name__ == "__main__":
    check_memory_entries()
