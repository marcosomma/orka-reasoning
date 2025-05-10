[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# OrKa Architecture ***(Patent Pending)***

OrKa (Orchestrator Kit for Agentic Reasoning) is built on a simple but powerful architecture: modular AI agents orchestrated through a declarative YAML interface, with messaging and traceability powered by Redis (and soon Kafka).

This document breaks down the key architectural components and how they work together.

---

## 🧠 Core Concepts

- **Agents:** Pluggable units of reasoning (e.g., classifier, validator, search agent).
- **Orchestrator:** Controls the flow of data between agents.
- **Redis Streams:** Used for async messaging and trace logging.
- **YAML Config:** Describes the orchestration graph.

---

## 📐 Component Diagram

```
┌────────────┐    input    ┌──────────────┐
│  User CLI  ├────────────►│ Orchestrator │
└────────────┘             └──────┬───────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              [Agent A]      [Agent X]      [Agent B]
                    │             │             │
                    ▼             ▼             ▼
               [Output A]    [Next Agent(s)] [Output B]
```

---

## 📦 Orchestrator Flow

1. Reads `orka.yaml`
2. Instantiates each agent with its type, queue, and prompt
3. Initializes the execution queue (static or routed)
4. Passes input to each agent and collects results
5. Logs each interaction in Redis using `MemoryLogger`

---

## 🔁 Agent Implementation

OrKa uses a unified agent base implementation with two supported patterns:

### Modern Async Pattern
```python
from orka.agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    async def _run_impl(self, ctx):
        # Async implementation with full context
        return result
```

### Legacy Sync Pattern
```python
from orka.agents.agent_base import BaseAgent  # Legacy compatibility

class MyAgent(BaseAgent):
    def run(self, input_data):
        # Sync implementation with direct input
        return result
```

Both patterns are supported through a unified execution model that provides:
- Concurrency control
- Timeout handling
- Standardized error handling
- Consistent output formatting
- Resource lifecycle management

---

## 🔁 Message Passing

- **Queueing model:** Each agent has its own Redis channel/stream.
- **Communication:** Simple function calls + optional pub/sub abstraction.
- **Planned Kafka backend:** For durable distributed cognition.

---

## 📄 YAML-Driven Control

OrKa is fully driven by `orka.yaml`, which defines:
- Agent IDs and types
- Prompts and behavior
- Execution strategy (sequential)
- Timeout and concurrency settings (for modern agents)

This allows reproducible reasoning pipelines and declarative logic.

---

## 🔍 Logging with Redis

All agent outputs are logged with metadata:

```json
{
  "agent_id": "validate_fact",
  "event_type": "output",
  "timestamp": "2024-04-12T18:00:00Z",
  "payload": {
    "input": "Was the Eiffel Tower built before 1900?",
    "result": "true",
    "status": "success"
  }
}
```

> You can inspect these with `xread` or `xrevrange` on the stream key `orka:memory`.

---

## 🛣 Roadmap Additions

- 🔜 Kafka support (stream processing + replay)
- 🔜 DAG visualization of agent flow
- 🔜 Agent plugins via Python entrypoints
- 🔜 Memory agent (stateful across runs)

---

OrKa's architecture is intentionally minimal, observable, and composable — so you can build LLM-based cognition that doesn't disappear into a black box.

[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

