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

## 🏗️ Modular Architecture (v0.6.4+)

Starting with version 0.6.4, OrKa's core components have been refactored into a modular architecture for improved maintainability and extensibility:

### Memory Logger Package (`orka/memory_logger/`)
The memory logging system is now split into focused components:

- **`base_logger.py`** - Abstract base class defining the memory logger interface
- **`serialization.py`** - JSON sanitization and memory processing utilities  
- **`file_operations.py`** - Save/load functionality and file I/O operations
- **`redis_logger.py`** - Complete Redis backend implementation
- **`__init__.py`** - Package initialization and factory functions

### Orchestrator Package (`orka/orchestrator/`)
The orchestration engine is decomposed into specialized modules:

- **`base.py`** - Core orchestrator initialization and configuration
- **`agent_factory.py`** - Agent registry and initialization logic
- **`prompt_rendering.py`** - Jinja2 template processing for prompts
- **`error_handling.py`** - Comprehensive error tracking and reporting
- **`metrics.py`** - LLM metrics collection and runtime analysis
- **`execution_engine.py`** - Main execution loop and agent coordination
- **`__init__.py`** - Package composition using multiple inheritance

### Backward Compatibility
- **100% API Compatibility**: All existing imports continue to work unchanged
- **Factory Functions**: `create_memory_logger()` and `Orchestrator()` provide seamless access
- **Zero Migration Required**: Existing code works without modification

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

OrKa's agent architecture provides two key implementation patterns:

1. **Modern Async Pattern (Recommended)**
   - Inherits from `BaseAgent` in `orka.agents.base_agent`
   - Uses `async/await` for concurrency support
   - Full lifecycle management through initialization hooks
   - Support for timeouts and concurrency limits

2. **Legacy Sync Pattern (Backward Compatibility)**
   - Inherits from `LegacyBaseAgent` in `orka.agents.base_agent`
   - Simple synchronous execution model
   - Compatible with older agent implementations

### Built-in Agent Types

- **Core Processing Agents**
  - `BinaryAgent`: Yes/no decisions
  - `ClassificationAgent`: Multi-class classification
  - `RouterAgent`: Dynamic flow control

- **LLM Integration Agents**
  - `OpenAIAnswerBuilder`: Text generation using OpenAI models
  - `OpenAIBinaryAgent`: Yes/no decisions using OpenAI
  - `OpenAIClassificationAgent`: Classification using OpenAI

- **Node Control Agents**
  - `ForkNode`: Splits processing into parallel branches
  - `JoinNode`: Combines parallel branches
  - `FailoverNode`: Provides fallback mechanisms

### Agent Registry System

The agent registry system maps agent type identifiers to their implementation classes:

```python
from orka.registry import registry

# Built-in registrations happen at framework initialization
registry.register_agent("binary", BinaryAgent)
registry.register_agent("openai-binary", OpenAIBinaryAgent)

# Custom agents can be registered by applications
registry.register_agent("my_custom_agent", MyCustomAgent)
```

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

