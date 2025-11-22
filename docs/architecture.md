# OrKa Architecture V0.7.0

> **Last Updated:** 22 November 2025  
> **Status:** 🟢 Current  
> **Related:** [Components](COMPONENTS.md) | [Visual Architecture](VISUAL_ARCHITECTURE_GUIDE.md) | [Ontology](ONTOLOGY.md) | [INDEX](index.md)

OrKa (Orchestrator Kit for Agentic Reasoning) is built on a revolutionary architecture: modular AI agents orchestrated through a declarative YAML interface, with **100x faster vector search** powered by RedisStack HNSW indexing.

This document breaks down the key architectural components and how they work together in the V0.7.0 unified architecture.

---

## 🚀 V0.7.0 Architecture Revolution

- **🚀 RedisStack HNSW**: 100x faster vector search with sub-millisecond latency
- **🏗️ Unified Backend**: All components use RedisStack with intelligent fallback
- **⚡ Enterprise Performance**: 50,000+ memory operations per second
- **🔧 Zero-Breaking Migration**: Complete backward compatibility maintained

## 🧠 Core Concepts

- **Agents:** Pluggable units of reasoning (e.g., classifier, validator, search agent).
- **Orchestrator:** Controls the flow of data between agents with RedisStack memory.
- **RedisStack HNSW:** Ultra-fast vector indexing for semantic memory search.
- **Redis Streams:** High-performance event streaming and memory operations.
- **YAML Config:** Describes the orchestration graph with memory configuration.

---

## 🏗️ Modular Architecture (v0.6.4+)

Starting with version 0.6.4, OrKa's core components have been refactored into a modular architecture for improved maintainability and extensibility. Version 0.6.5 adds intelligent memory decay capabilities:

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
- **`simplified_prompt_rendering.py`** - Jinja2 template processing for prompts with OrkaResponse support
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

## 🚀 RedisStack HNSW Memory Architecture

- **Vector Search Performance**: Sub-millisecond latency with HNSW indexing (100x faster than basic Redis)
- **Enterprise Scale**: 50,000+ memory operations per second with 1000+ concurrent searches  
- **Memory Efficiency**: 60% reduction in memory usage through optimized indexing
- **Automatic Optimization**: Self-tuning HNSW parameters (M=16, ef_construction=200)

---

## 🔁 Message Passing & Backend Options

### RedisStack (Default)
- **Memory Operations**: HNSW vector indexing for all semantic search and storage
- **Performance**: Sub-millisecond search latency, 50x write throughput improvement
- **Features**: Automatic index creation, graceful fallback to basic Redis

### RedisStack (Enterprise)
- **Event Streaming**: Redis Streams handle message queuing and event replay
- **Memory Layer**: RedisStack HNSW for all memory operations with vector indexing
- **High Performance**: Optimized for enterprise AI workloads

### Basic Redis (Legacy)
- **Compatibility Mode**: Available via `ORKA_FORCE_BASIC_REDIS=true`
- **Use Case**: Development environments without Docker
- **Performance**: Standard Redis operations (100x slower than RedisStack)

---

## 📄 YAML-Driven Control with Memory Configuration

OrKa V0.7.0 is fully driven by `orka.yaml`, which defines:
- Agent IDs and types with RedisStack memory loggers
- Memory configuration with decay rules and HNSW settings
- Backend selection (redisstack/redis)
- Performance monitoring and observability settings

This allows reproducible reasoning pipelines with enterprise-grade memory.

---

## 🔍 RedisStack Memory Logging

All agent outputs are logged with HNSW-optimized metadata:

```json
{
  "agent_id": "validate_fact",
  "event_type": "output", 
  "backend": "redisstack",
  "timestamp": "2025-01-31T18:00:00Z",
  "vector_embedding": [0.1, 0.2, ...],
  "hnsw_metadata": {
    "index_name": "orka_memory_idx",
    "search_time_ms": 1.2,
    "similarity_score": 0.94
  },
  "payload": {
    "input": "Was the Eiffel Tower built before 1900?",
    "result": "true",
    "status": "success"
  }
}
```

## 📊 V0.7.0 Performance Benchmarks

| Metric | Basic Redis | **RedisStack HNSW** | Improvement |
|--------|-------------|---------------------|-------------|
| **Vector Search** | 50-200ms | **0.5-5ms** | **100x faster** |
| **Memory Usage** | 100% baseline | **40%** | **60% reduction** |
| **Throughput** | 1,000/sec | **50,000/sec** | **50x higher** |
| **Concurrent Searches** | 10-50 | **1,000+** | **20x more** |

---

## ✅ V0.7.0 Completed Features

- ✅ **RedisStack HNSW Integration** - 100x faster vector search across all components  
- ✅ **RedisStack Backend** - Enterprise-grade memory operations with HNSW indexing
- ✅ **Professional CLI Dashboard** - Real-time HNSW performance monitoring
- ✅ **Zero-Breaking Migration** - Complete backward compatibility maintained
- ✅ **Unified Architecture** - All components use RedisStack with intelligent fallback

---

OrKa's architecture is intentionally minimal, observable, and composable — so you can build LLM-based cognition that doesn't disappear into a black box.
---
← [Getting Started](getting-started.md) | [📚 INDEX](index.md) | [Components](COMPONENTS.md) →
