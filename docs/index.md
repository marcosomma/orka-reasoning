[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# OrKa Documentation

Welcome to OrKa - the **Orchestrator Kit for Agentic Reasoning**! OrKa transforms Large Language Models into intelligent, memory-enabled agents that can learn, remember, and reason through complex workflows.

## 🚀 What's New in V0.7.0

- **🚀 100x Faster Vector Search** - RedisStack HNSW indexing now default across all components
- **⚡ Sub-millisecond Search Latency** - O(log n) complexity for massive datasets
- **🏗️ Unified Architecture** - All components now use RedisStack with intelligent fallback
- **🖥️ Professional CLI Dashboard** - Real-time performance monitoring and metrics
- **🔧 Zero-Breaking Migration** - Complete backward compatibility maintained

## 🧠 What Makes OrKa Special?

### Revolutionary Memory System with 100x Performance
OrKa's crown jewel is its **RedisStack-powered memory system** with enterprise-grade vector search:

- **🚀 100x Faster Vector Search**: RedisStack HNSW indexing delivers sub-millisecond semantic search
- **🔄 Intelligent Decay**: Automatic memory lifecycle management with importance-based retention
- **🎯 Context-Aware Search**: Multi-factor relevance scoring using semantic similarity, temporal ranking, and conversation context  
- **📊 Auto-Classification**: Smart categorization of memories into short-term and long-term storage
- **🔍 Semantic Understanding**: Advanced vector embeddings enable meaning-based memory retrieval
- **⚡ Real-time Monitoring**: Professional CLI dashboard with HNSW performance metrics

### YAML-Driven Orchestration
Build complex AI workflows using intuitive YAML configuration:
- **📝 Declarative Design**: Define what you want, not how to build it
- **🔧 Modular Agents**: Composable building blocks for any use case
- **🌊 Dynamic Routing**: Conditional workflows that adapt based on results
- **🔄 Fork/Join Patterns**: Parallel processing for complex reasoning

### Transparent Reasoning
Every decision is traceable and auditable:
- **📋 Complete Audit Trail**: Full history of agent interactions and decisions
- **🎭 Visual Workflows**: OrKa UI for monitoring and debugging
- **📊 Rich Metadata**: Detailed context for every memory and interaction

## 🚀 Quick Start

### 1. Install OrKa with Dependencies
```bash
# Install OrKa with all required dependencies
pip install orka-reasoning fastapi uvicorn kafka-python
```

### 2. Start OrKa (Automatic RedisStack Setup)
**Prerequisites:** Ensure Docker is installed and running on your system.

```bash
# Set your OpenAI key
export OPENAI_API_KEY=your-key-here

# Start OrKa (automatically includes RedisStack + 100x faster vector search)
# For LOCAL development:
python -m orka.orka_start

# For PRODUCTION with Kafka streaming:
python -m orka.start_kafka
```

### 3. Create Your First Memory-Enabled Agent
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

  - id: smart_response
    type: openai-answer
    prompt: |
      History: {{ previous_outputs.memory_search }}
      Current: {{ input }}
      Generate a contextually aware response.

  - id: memory_store
    type: memory-writer
    namespace: conversations
    params:
      # memory_type automatically classified based on content and importance
      vector: true
    prompt: "User: {{ input }} | Assistant: {{ previous_outputs.smart_response }}"
```

### 4. Run and Monitor with Professional Dashboard
```bash
# Run your workflow
python -m orka.orka_cli smart-assistant.yml "Hello! Tell me about OrKa's memory system."

# Monitor memory with RedisStack performance metrics
python -m orka.orka_cli memory watch

# View detailed statistics and HNSW performance
python -m orka.orka_cli memory stats

# Optional: Run OrKa UI for visual monitoring
docker pull marcosomma/orka-ui:latest
docker run -it -p 80:80 --name orka-ui marcosomma/orka-ui:latest
# Then open http://localhost in your browser
```

## 📚 Documentation Guide

### 🎯 Getting Started
- **[📘 Getting Started](./getting-started.md)** - Complete setup guide with V0.7.0 features
- **[📝 YAML Configuration Guide](./yaml-configuration-guide.md)** - Comprehensive agent configuration reference
- **[🧠 Memory System Guide](./MEMORY_SYSTEM_GUIDE.md)** - Deep dive into OrKa's RedisStack-powered memory

### 🔧 Core Concepts
- **[🤖 Agent Types](./agents.md)** - All available agent types and their capabilities
- **[🔍 Architecture](./architecture.md)** - System design and architectural principles
- **[⚙ Runtime Modes](./runtime-modes.md)** - Different execution strategies

### 🛠️ Advanced Topics
- **[🧪 Extending Agents](./extending-agents.md)** - Build custom agents and tools
- **[📊 Observability](./observability.md)** - Monitoring and debugging workflows
- **[🔐 Security](./security.md)** - Security considerations and best practices

### 📖 Reference
- **[📜 YAML Schema](./orka.yaml-schema.md)** - Complete YAML configuration schema
- **[❓ FAQ](./faq.md)** - Frequently asked questions and troubleshooting

## 🎯 Key Use Cases

### 1. Conversational AI with Memory
Build chatbots that remember context and learn from interactions:
```yaml
# Retrieves conversation history with 100x faster search,
# classifies interaction type, generates contextually aware responses,
# and stores for future use with intelligent decay
```

### 2. Self-Updating Knowledge Base  
Create knowledge systems that automatically verify and update information:
```yaml
# Searches existing knowledge with HNSW indexing, determines freshness,
# fetches new information, verifies facts, and updates knowledge base
```

### 3. Multi-Agent Research System
Orchestrate collaborative research workflows:
```yaml
# Research agents gather information, analysis agents process findings,
# synthesis agents create comprehensive reports - all sharing RedisStack memory
```

### 4. Error Learning System
Build systems that learn from mistakes:
```yaml
# Attempts solutions, validates results, learns from failures,
# and improves future responses based on past experience
```

## 🧠 Memory System Highlights

### Intelligent Decay
```yaml
memory_config:
  decay:
    enabled: true
    importance_rules:
      critical_info: 3.0      # Keep critical info 3x longer
      user_feedback: 2.5      # Value user corrections
      routine_query: 0.8      # Let routine queries decay faster
```

### Context-Aware Search with HNSW Performance
```yaml
memory_reader:
  params:
    enable_context_search: true    # Use conversation history
    context_weight: 0.4           # 40% weight for context
    temporal_weight: 0.3          # 30% weight for recency
    similarity_threshold: 0.8     # Minimum relevance score (HNSW optimized)
```

### Real-time Monitoring with RedisStack Metrics
```bash
# Professional memory dashboard with HNSW performance
python -m orka.orka_cli memory watch

# Detailed analytics with vector search metrics
python -m orka.orka_cli memory stats

# HNSW index optimization and cleanup
python -m orka.orka_cli memory cleanup
```

## 🌟 Why Choose OrKa?

| Feature | OrKa V0.7.0 | LangChain | CrewAI | LlamaIndex |
|---------|-------------|-----------|--------|-------------|
| **Memory System** | ✅ RedisStack HNSW (100x faster) | ❌ Basic storage | ❌ Simple memory | ⚠️ RAG-focused |
| **Vector Search** | ✅ Sub-millisecond HNSW | ❌ Basic similarity | ❌ No vector search | ⚠️ Limited indexing |
| **Configuration** | ✅ YAML-driven | ❌ Python code | ❌ Python code | ❌ Python code |
| **Transparency** | ✅ Complete audit trail | ⚠️ Limited | ⚠️ Basic | ⚠️ Limited |
| **Learning Curve** | ✅ Low (YAML) | ⚠️ Medium | ⚠️ Medium | ⚠️ Medium |
| **Memory Decay** | ✅ Intelligent lifecycle | ❌ Manual cleanup | ❌ No decay | ❌ Manual cleanup |
| **Context Awareness** | ✅ Multi-factor search | ❌ Basic retrieval | ❌ Simple memory | ⚠️ Vector-only |
| **Performance** | ✅ Enterprise-grade | ⚠️ Variable | ⚠️ Basic | ⚠️ Index-dependent |

## 📊 Performance Benchmarks

| Metric | Basic Redis | **RedisStack HNSW** | Improvement |
|--------|-------------|---------------------|-------------|
| **Vector Search** | 50-200ms | **0.5-5ms** | **100x faster** |
| **Memory Usage** | 100% baseline | **40%** | **60% reduction** |
| **Throughput** | 1,000/sec | **50,000/sec** | **50x higher** |
| **Concurrent Searches** | 10-50 | **1,000+** | **20x more** |

## 🔧 Architecture Overview

OrKa V0.7.0 uses a unified RedisStack architecture:

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   YAML      │     │  Orchestrator   │     │   Agents    │
│ Definition  ├────►│  (Control Flow) ├────►│ (Reasoning) │
└─────────────┘     └────────┬────────┘     └──────┬──────┘
                             │                     │
                     ┌───────▼─────────────────────▼───────┐
                     │     RedisStack HNSW Memory          │
                     │  (100x Faster Vector Search)        │
                     └───────────────────────────────────┬─┘
                                                         │
                                                 ┌───────▼────────┐
                                                 │   OrKa UI      │
                                                 │  (Monitoring)  │
                                                 └────────────────┘
```

**Ready to experience 100x faster AI workflows?** Start with our [📘 Getting Started](./getting-started.md) guide!

---

[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
