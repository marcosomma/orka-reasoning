# Observability & Logging in OrKa

> **Last Updated:** 29 November 2025  
> **Status:** 🟢 Current  
> **Related:** [Debugging](DEBUGGING.md) | [Best Practices](best-practices.md) | [Architecture](architecture.md) | [INDEX](index.md)

## Redis Stream Logging
Every agent logs its input/output via:
```json
{
  "agent_id": "validate_fact",
  "event_type": "output",
  "timestamp": "...",
  "payload": {
    "input": "...",
    "result": true
  }
}
```

### Streams Used
- `orka:memory` — general memory log
- `orka:{agent_id}` — agent-specific stream

## Inspecting Logs
Use:
```bash
redis-cli xrevrange orka:memory + - COUNT 10
```

## OrKaUI (Tiamat)
- Replay traces
- Highlight branching decisions
- Future: confidence overlays, timeline scrubbing

