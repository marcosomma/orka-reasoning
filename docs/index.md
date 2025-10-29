[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🧭 GraphScout Agent](./GRAPH_SCOUT_AGENT.md) | [🔍 Architecture](./architecture.md) | [🧩 Ontology](./ONTOLOGY.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# OrKa Documentation

Welcome to OrKa - the **Orchestrator Kit for Agentic Reasoning**. OrKa is a YAML-based framework for orchestrating LLM workflows with persistent memory storage and retrieval.

## 🚀 What's New in V0.9.3 - GraphScout Agent

- **🧭 GraphScout Agent** - Workflow graph traversal with multi-agent path execution based on LLM evaluation
- **🎯 Dynamic Path Discovery** - Runtime workflow analysis as alternative to static routing configuration
- **🧠 Memory Agent Ordering** - Positions memory readers before other agents and writers after
- **⚡ Multi-Agent Execution** - Execute ALL agents in shortlist sequentially, not just the first one
- **🔍 LLM-Based Evaluation** - Path selection using LLM-based confidence scoring

## 🚀 Previous Major Features - V0.9.2 Memory Presets

- **🧠 Memory Presets System** - Simplified memory configuration using preset templates based on memory duration patterns
- **🎯 Operation-Aware Configuration** - Different default parameters for read vs write operations
- **🔧 Unified Memory Agents** - Single `type: memory` replacing separate reader/writer types
- **🤖 Local LLM Integration** - Full Ollama support for running models locally
- **📚 Documentation Updates** - Reorganized examples with simplified preset-based configurations

## 🚀 Previous Major Features

### V0.7.5 - Loop Control
- **🔄 Loop Node** - Iterative workflow execution with configurable exit conditions
- **🧠 Multi-Agent Workflows** - Multiple agents collaborating on tasks with shared memory
- **🎯 Threshold-Based Execution** - Loop termination based on score thresholds

### V0.7.0 - RedisStack Integration
- **🚀 HNSW Vector Search** - RedisStack HNSW indexing for faster similarity search (benchmarked 100x faster than basic Redis)
- **⚡ Improved Search Latency** - Sub-millisecond search performance on indexed data
- **🏗️ Unified Backend** - All components now use RedisStack with fallback to basic Redis

## 🧠 Key Features

### Memory System with Presets
OrKa includes a Redis-based memory system with configurable retention policies:

- **🧠 Memory Presets**: 6 preset configurations with different retention durations (sensory, working, episodic, semantic, procedural, meta)
- **🎯 Simplified Configuration**: Single `memory_preset` parameter provides preconfigured defaults
- **⚡ Operation-Based Defaults**: Different default parameters for read vs write operations
- **🚀 HNSW Vector Indexing**: RedisStack HNSW provides faster vector similarity search (benchmarked 100x faster than basic Redis)
- **🔄 Configurable Expiration**: Time-based memory expiration with importance factor multipliers
- **📊 Preset Templates**: Preconfigured retention periods and importance rules per preset type
- **🔍 Semantic Search**: Vector embeddings for similarity-based retrieval
- **🖥️ CLI Monitoring**: Command-line tools for viewing memory state and metrics

### YAML-Based Configuration
Define workflows in YAML files instead of code:
- **📝 Declarative Format**: Specify agents and their connections in YAML
- **🔧 Modular Agents**: Composable agent types for different tasks
- **🌊 Conditional Routing**: Router agents for branching logic based on outputs
- **🔄 Fork/Join Patterns**: Parallel execution paths with result aggregation

### Execution Tracking
Workflows provide execution logs and metrics:
- **📋 Execution History**: Redis-based logging of agent interactions
- **🎭 Monitoring UI**: Optional web interface for workflow monitoring
- **📊 Metadata Storage**: Agent outputs and execution context stored in Redis

## 🚀 Quick Start

### 1. Install OrKa with Dependencies
```bash
# Install OrKa with all required dependencies
pip install orka-reasoning fastapi uvicorn

# Optional: Install extra features
pip install orka-reasoning[extra]
```

### 2. Start OrKa (Automatic RedisStack Setup)
**Prerequisites:** RedisStack via one of these methods:
- Docker (easiest - will be auto-configured)
- Native RedisStack installation (brew/apt/download)

```bash
# Set your OpenAI key (if using OpenAI models)
export OPENAI_API_KEY=your-key-here

# Start OrKa with automatic RedisStack detection
# Tries native first, then Docker, then shows install instructions
orka-start

# Alternative: Use Python module directly
python -m orka.orka_start
```

**What `orka-start` does:**
1. Checks for native RedisStack installation
2. Falls back to Docker if native not found
3. Provides installation instructions if neither available

### 3. Create Your First Workflow with Memory
```yaml
orchestrator:
  id: smart-assistant
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2
      default_long_term_hours: 168
      importance_rules:
        user_correction: 3.0
        successful_answer: 2.0

agents:
  - id: memory_search
    type: memory-reader
    namespace: conversations
    params:
      enable_context_search: true
      context_weight: 0.4
      temporal_weight: 0.3
      similarity_threshold: 0.8
    prompt: "Find relevant conversation history for: {{ input }}"

  - id: response_generation
    type: openai-answer
    prompt: |
      History: {{ previous_outputs.memory_search }}
      Current: {{ input }}
      Generate a response using the conversation history.

  - id: memory_store
    type: memory-writer
    namespace: conversations
    params:
      vector: true
    prompt: "User: {{ input }} | Assistant: {{ previous_outputs.response_generation }}"
```

### 4. Run and Monitor Workflows
```bash
# Run your workflow
python -m orka.orka_cli smart-assistant.yml "Hello! Tell me about OrKa's memory system."

# Monitor memory state
python -m orka.orka_cli memory watch

# View statistics
python -m orka.orka_cli memory stats

# Optional: Run OrKa UI for web-based monitoring
docker pull marcosomma/orka-ui:latest
docker run -it -p 80:80 --name orka-ui marcosomma/orka-ui:latest
# Then open http://localhost in your browser
```

## 📚 Documentation Guide

### 🎯 Getting Started
- **[📘 Getting Started](./getting-started.md)** - Complete setup guide
- **[📝 YAML Configuration Guide](./yaml-configuration-guide.md)** - Agent configuration reference
- **[🧠 Memory System Guide](./MEMORY_SYSTEM_GUIDE.md)** - Memory configuration and usage

### 🔧 Core Concepts
- **[🤖 Agent Types](./agents.md)** - All available agent types and their capabilities
- **[🔍 Architecture](./architecture.md)** - System design and architectural principles
- **[🧩 Ontology](./ONTOLOGY.md)** - Entities, identifiers, and relationships across OrKa
- **[⚙ Runtime Modes](./runtime-modes.md)** - Different execution strategies

### 🛠️ Advanced Topics
- **[🧪 Extending Agents](./extending-agents.md)** - Build custom agents and tools
- **[📊 Observability](./observability.md)** - Monitoring and debugging workflows
- **[🔐 Security](./security.md)** - Security considerations and best practices

### 📖 Reference
- **[📜 YAML Schema](./orka.yaml-schema.md)** - Complete YAML configuration schema
- **[❓ FAQ](./faq.md)** - Frequently asked questions and troubleshooting

## 🎯 Common Use Cases

### 1. Conversational Interface with Memory
Chatbots that retrieve and store conversation history:
```yaml
# Retrieves conversation history using vector search,
# classifies interaction type, generates responses based on context,
# and stores interactions with configurable expiration rules
```

### 2. Knowledge Base with Updates
Systems that search existing knowledge and add new information:
```yaml
# Searches existing knowledge with HNSW indexing, checks if content is recent,
# fetches new information via web search, validates facts using LLM,
# and updates knowledge base with new entries
```

### 3. Multi-Agent Workflows
Multiple agents working on related tasks with shared memory:
```yaml
# Research agents gather information, analysis agents process findings,
# synthesis agents create reports - all using shared Redis memory
```

### 4. Iterative Refinement
Workflows that repeat until output meets criteria:
```yaml
# Uses LoopNode to iteratively refine responses until quality threshold is met,
# extracts metrics from each iteration,
# stores iteration history in memory for tracking progress
```

### 5. Multi-Agent Deliberation
Multiple agents providing different perspectives on a topic:
```yaml
# Multiple agents (logical, empathetic, skeptical, creative) generate responses,
# moderator evaluates similarity between responses, process repeats until threshold reached,
# produces aggregated output combining different viewpoints
```

### 6. Workflow Validation
Systems that retry on failure with memory of past attempts:
```yaml
# Attempts task execution, validates results using validation agent,
# stores failures in memory, retries with adjustments based on past failures
```

## 🧠 Memory System Configuration

### Configurable Expiration Rules
```yaml
memory_config:
  decay:
    enabled: true
    importance_rules:
      critical_info: 3.0      # Multiply retention time by 3x
      user_feedback: 2.5      # Multiply retention time by 2.5x
      routine_query: 0.8      # Multiply retention time by 0.8x
```

### Context-Aware Search with HNSW
```yaml
memory_reader:
  params:
    enable_context_search: true    # Include conversation history in search
    context_weight: 0.4           # 40% weight for context matching
    temporal_weight: 0.3          # 30% weight for recency
    similarity_threshold: 0.8     # Minimum relevance score (HNSW-indexed)
```

### Monitoring Tools
```bash
# Command-line memory dashboard
python -m orka.orka_cli memory watch

# View memory statistics
python -m orka.orka_cli memory stats

# Clean up expired entries
python -m orka.orka_cli memory cleanup
```

## 🌟 Comparison to Alternatives

| Feature | OrKa V0.7.0 | LangChain | CrewAI | LlamaIndex |
|---------|-------------|-----------|--------|-------------|
| **Memory System** | ✅ RedisStack HNSW (benchmarked 100x faster) | ❌ Basic storage | ❌ Simple memory | ⚠️ RAG-focused |
| **Vector Search** | ✅ Sub-millisecond HNSW | ❌ Basic similarity | ❌ No vector search | ⚠️ Limited indexing |
| **Configuration** | ✅ YAML-based | ❌ Python code | ❌ Python code | ❌ Python code |
| **Execution Logging** | ✅ Redis-based logs | ⚠️ Limited | ⚠️ Basic | ⚠️ Limited |
| **Learning Curve** | ✅ Low (YAML) | ⚠️ Medium (Python) | ⚠️ Medium (Python) | ⚠️ Medium (Python) |
| **Memory Expiration** | ✅ Time-based with rules | ❌ Manual cleanup | ❌ No expiration | ❌ Manual cleanup |
| **Context Inclusion** | ✅ Multi-factor scoring | ❌ Basic retrieval | ❌ Simple memory | ⚠️ Vector-only |
| **Performance** | ✅ HNSW indexing | ⚠️ Varies by backend | ⚠️ Basic | ⚠️ Index-dependent |

## 📊 Performance Benchmarks

Performance measurements comparing basic Redis to RedisStack HNSW on a test dataset:

| Metric | Basic Redis | **RedisStack HNSW** | Measured Difference |
|--------|-------------|---------------------|-------------|
| **Vector Search** | 50-200ms | **0.5-5ms** | **~100x faster** |
| **Memory Usage** | 100% baseline | **40%** | **60% reduction** |
| **Throughput** | 1,000/sec | **50,000/sec** | **50x higher** |
| **Concurrent Searches** | 10-50 | **1,000+** | **20x more** |

*Note: Performance depends on dataset size, query complexity, and hardware. Your results may vary.*

## 🔧 Architecture Overview

OrKa uses a Redis-based architecture for workflow execution and memory:

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   YAML      │     │  Orchestrator   │     │   Agents    │
│ Definition  ├────►│  (Control Flow) ├────►│  (Execution)│
└─────────────┘     └────────┬────────┘     └──────┬──────┘
                             │                     │
                     ┌───────▼─────────────────────▼───────┐
                     │     RedisStack HNSW Memory          │
                     │  (Vector search with HNSW index)    │
                     └───────────────────────────────────┬─┘
                                                         │
                                                 ┌───────▼────────┐
                                                 │   OrKa UI      │
                                                 │  (Monitoring)  │
                                                 └────────────────┘
```

**Ready to get started?** See our [📘 Getting Started](./getting-started.md) guide!

---

[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
