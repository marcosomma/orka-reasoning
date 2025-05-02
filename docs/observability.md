[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# Observability & Logging in OrKa

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

[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
