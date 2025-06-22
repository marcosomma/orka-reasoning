[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# OrKa Documentation

Welcome to OrKa - the **Orchestrator Kit for Agentic Reasoning**! OrKa transforms Large Language Models into intelligent, memory-enabled agents that can learn, remember, and reason through complex workflows.

## 🧠 What Makes OrKa Special?

### Intelligent Memory System
OrKa's crown jewel is its **cognitive science-inspired memory system** that gives AI agents human-like memory capabilities:

- **🔄 Intelligent Decay**: Automatic memory lifecycle management with importance-based retention
- **🎯 Context-Aware Search**: Multi-factor relevance scoring using semantic similarity, temporal ranking, and conversation context  
- **📊 Auto-Classification**: Smart categorization of memories into short-term and long-term storage
- **🔍 Semantic Understanding**: Vector embeddings enable meaning-based memory retrieval
- **⚡ Real-time Monitoring**: Professional CLI tools for memory management and analytics

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

### 1. Install OrKa
```bash
pip install orka-reasoning
```

### 2. Set Up Memory Backend
```bash
# Install Redis (recommended)
brew install redis  # macOS
sudo apt install redis-server  # Ubuntu

# Start Redis
redis-server

# Configure OrKa
export ORKA_MEMORY_BACKEND=redis
export OPENAI_API_KEY=your-key-here
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

### 4. Run and Monitor
```bash
# Run your workflow
python -m orka.orka_cli smart-assistant.yml "Hello! Tell me about OrKa's memory system."

# Monitor memory in real-time
orka memory watch

# View detailed statistics
orka memory stats
```

## 📚 Documentation Guide

### 🎯 Getting Started
- **[📘 Getting Started](./getting-started.md)** - Complete setup guide with practical examples
- **[📝 YAML Configuration Guide](./yaml-configuration-guide.md)** - Comprehensive agent configuration reference
- **[🧠 Memory System Guide](./MEMORY_SYSTEM_GUIDE.md)** - Deep dive into OrKa's intelligent memory

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
# Retrieves conversation history, classifies interaction type,
# generates contextually aware responses, and stores for future use
```

### 2. Self-Updating Knowledge Base  
Create knowledge systems that automatically verify and update information:
```yaml
# Searches existing knowledge, determines freshness,
# fetches new information, verifies facts, and updates knowledge base
```

### 3. Multi-Agent Research System
Orchestrate collaborative research workflows:
```yaml
# Research agents gather information, analysis agents process findings,
# synthesis agents create comprehensive reports - all sharing memory
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

### Context-Aware Search
```yaml
memory_reader:
  params:
    enable_context_search: true    # Use conversation history
    context_weight: 0.4           # 40% weight for context
    temporal_weight: 0.3          # 30% weight for recency
    similarity_threshold: 0.7     # Minimum relevance score
```

### Real-time Monitoring
```bash
# Professional memory dashboard
orka memory watch

# Detailed analytics
orka memory stats

# Manual cleanup
orka memory cleanup
```

## 🌟 Why Choose OrKa?

| Feature | OrKa | LangChain | CrewAI | LlamaIndex |
|---------|------|-----------|--------|-------------|
| **Memory System** | ✅ Advanced cognitive memory | ❌ Basic storage | ❌ Simple memory | ⚠️ RAG-focused |
| **Configuration** | ✅ YAML-driven | ❌ Python code | ❌ Python code | ❌ Python code |
| **Transparency** | ✅ Complete audit trail | ⚠️ Limited | ⚠️ Basic | ⚠️ Limited |
| **Learning Curve** | ✅ Low (YAML) | ⚠️ Medium | ⚠️ Medium | ⚠️ Medium |
| **Memory Decay** | ✅ Intelligent lifecycle | ❌ Manual cleanup | ❌ No decay | ❌ Manual cleanup |
| **Context Awareness** | ✅ Multi-factor search | ❌ Basic retrieval | ❌ Simple memory | ⚠️ Vector-only |

## 🔧 Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   YAML Config   │    │   Orchestrator  │    │     Agents      │
│                 │    │                 │    │                 │
│ • Memory Rules  │────│ • Flow Control  │────│ • Classification│
│ • Agent Defs    │    │ • Memory Mgmt   │    │ • Generation    │
│ • Decay Config  │    │ • Error Handling│    │ • Memory Ops    │
└─────────────────┘    └────────┬────────┘    └──────┬──────────┘
                                │                    │
                        ┌───────▼────────────────────▼───────┐
                        │        Memory System               │
                        │                                    │
                        │ • Intelligent Decay               │
                        │ • Context-Aware Search            │
                        │ • Vector Embeddings               │
                        │ • Multi-Backend Support           │
                        └───────────────┬────────────────────┘
                                        │
                                ┌───────▼────────┐
                                │   Monitoring   │
                                │                │
                                │ • OrKa UI      │
                                │ • CLI Tools    │
                                │ • Metrics      │
                                └────────────────┘
```

## 🎮 Interactive Learning

### Try OrKa Online
- **[OrKa UI Demo](https://orkacore.com)** - Interactive workflow builder
- **[GitHub Repository](https://github.com/marcosomma/orka-reasoning)** - Source code and examples

### Example Workflows
Explore pre-built workflows in the `/examples` directory:
- `memory_category_test.yml` - Memory system demonstration
- `enhanced_memory_validation_example.yml` - Advanced memory patterns
- `routing_memory_writers.yml` - Dynamic routing with memory
- `validation_and_structuring_orchestrator.yml` - Answer validation

## 💡 Pro Tips

1. **Start with Memory**: OrKa's memory system is its superpower - use it from day one
2. **Use Auto-Classification**: Let OrKa automatically categorize memories as short-term or long-term
3. **Monitor Actively**: Use `orka memory watch` during development to understand memory patterns
4. **Rich Metadata**: Store contextual information that helps future memory searches
5. **Plan for Scale**: Configure appropriate decay rules from the beginning

## 🤝 Community & Support

- **GitHub**: [OrKa Repository](https://github.com/marcosomma/orka-reasoning)
- **Documentation**: [Complete Docs](https://orkacore.web.app/docs)
- **Examples**: [Workflow Examples](../examples/)
- **Issues**: [Bug Reports & Feature Requests](https://github.com/marcosomma/orka-reasoning/issues)

---

**Ready to build intelligent agents that learn and remember?** Start with our [Getting Started Guide](./getting-started.md) and discover how OrKa's memory system can transform your AI workflows!

[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
