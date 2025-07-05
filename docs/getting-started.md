[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# Getting Started with OrKa V0.7.0

Welcome to OrKa! This guide will help you get up and running with OrKa's powerful agent orchestration system and **100x faster vector search** in just a few minutes.

## 🚀 What's New in V0.7.0

- **🚀 100x Faster Vector Search** - RedisStack HNSW indexing now default
- **⚡ Automatic Setup** - No manual Redis configuration needed
- **🏗️ Unified Architecture** - All components use RedisStack with intelligent fallback
- **🖥️ Professional CLI Dashboard** - Real-time HNSW performance monitoring

## 🚀 Quick Setup

### Prerequisites

- Python 3.8 or higher
- Docker (installed and running)
- OpenAI API key

### Installation

```bash
# Install OrKa with all dependencies (includes automatic RedisStack setup)
pip install orka-reasoning fastapi uvicorn kafka-python

# Optional: Install schema management features (Avro/Protobuf support)
pip install orka-reasoning[schema]
```

**That's it!** OrKa V0.7.0 automatically handles RedisStack setup through Docker.

### Environment Configuration

```bash
# Only one environment variable needed:
export OPENAI_API_KEY=your-openai-api-key-here

# Optional: Force basic Redis mode (not recommended)
# export ORKA_FORCE_BASIC_REDIS=true
```

### Start OrKa

```bash
# For LOCAL development (automatically includes RedisStack + 100x faster vector search):
python -m orka.orka_start

# For PRODUCTION with Kafka streaming:
python -m orka.start_kafka

# Optional: Run OrKa UI for visual monitoring
docker pull marcosomma/orka-ui:latest
docker run -it -p 80:80 --name orka-ui marcosomma/orka-ui:latest
# Then open http://localhost in your browser
```

## 🎯 Your First OrKa Workflow with 100x Performance

Let's create a powerful workflow that demonstrates OrKa's RedisStack-powered memory capabilities:

### Create your first workflow file: `smart-assistant.yml`

```yaml
meta:
  version: "1.0"
  author: "Your Name"
  description: "Smart assistant with RedisStack memory and 100x faster vector search"

orchestrator:
  id: smart-assistant
  strategy: sequential
  queue: orka:smart-assistant
  
  # 🧠 Memory configuration with RedisStack HNSW performance
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2      # Conversations fade after 2 hours
      default_long_term_hours: 168     # Important info lasts 1 week
      check_interval_minutes: 30       # Clean up every 30 minutes
      
      # Importance rules - OrKa learns what matters
      importance_rules:
        user_correction: 3.0           # User corrections are very important
        positive_feedback: 2.0         # Learn from positive feedback
        successful_answer: 1.5         # Remember successful interactions
        routine_query: 0.8             # Routine questions decay faster

  agents:
    - conversation_memory
    - context_classifier
    - smart_responder
    - memory_storage

agents:
  # 1. Retrieve relevant conversation history with 100x faster HNSW search
  - id: conversation_memory
    type: memory-reader
    namespace: conversations
    params:
      limit: 5                         # Get up to 5 relevant memories
      enable_context_search: true      # Use conversation context
      context_weight: 0.4              # Context is 40% of relevance score
      temporal_weight: 0.3             # Recent memories get 30% boost
      similarity_threshold: 0.8        # HNSW-optimized threshold
      enable_temporal_ranking: true    # Boost recent interactions
    prompt: |
      Find relevant conversation history for: {{ input }}
      
      Look for:
      - Similar topics we've discussed
      - Previous questions from this user
      - Related context that might be helpful

  # 2. Classify the type of interaction
  - id: context_classifier
    type: openai-classification
    prompt: |
      Based on the conversation history: {{ previous_outputs.conversation_memory }}
      Current user input: {{ input }}
      
      Classify this interaction type:
    options: [new_question, followup, clarification, correction, feedback, greeting, casual_chat]

  # 3. Generate intelligent response using RedisStack memory
  - id: smart_responder
    type: openai-answer
    prompt: |
      You are a helpful AI assistant with RedisStack-powered memory of past conversations.
      
      **Conversation History (Retrieved with 100x faster search):**
      {{ previous_outputs.conversation_memory }}
      
      **Interaction Type:** {{ previous_outputs.context_classifier }}
      **Current Input:** {{ input }}
      
      Generate a response that:
      1. Acknowledges relevant conversation history when appropriate
      2. Directly addresses the current input
      3. Shows understanding of context and continuity
      4. Is helpful, accurate, and engaging
      
      {% if previous_outputs.context_classifier == "correction" %}
      Pay special attention - the user is correcting something. Learn from this!
      {% elif previous_outputs.context_classifier == "followup" %}
      This is a follow-up question. Build on the previous context.
      {% elif previous_outputs.context_classifier == "feedback" %}
      The user is providing feedback. Acknowledge and learn from it.
      {% endif %}

  # 4. Store the interaction in RedisStack for future reference
  - id: memory_storage
    type: memory-writer
    namespace: conversations
    params:
      # memory_type automatically classified as short-term or long-term
      vector: true                     # Enable semantic search with HNSW
      metadata:
        interaction_type: "{{ previous_outputs.context_classifier }}"
        has_context: "{{ previous_outputs.conversation_memory | length > 0 }}"
        search_performance: "hnsw_optimized"
        timestamp: "{{ now() }}"
    prompt: |
      Conversation Record:
      
      User: {{ input }}
      Type: {{ previous_outputs.context_classifier }}
      Context Found: {{ previous_outputs.conversation_memory | length }} previous interactions
      Assistant: {{ previous_outputs.smart_responder }}
      
      Memory Metadata:
      - Interaction type: {{ previous_outputs.context_classifier }}
      - Had relevant history: {{ previous_outputs.conversation_memory | length > 0 }}
      - Response quality: To be evaluated by user feedback
```

### Test Your Smart Assistant with RedisStack Performance

```bash
# Run your first conversation
python -m orka.orka_cli smart-assistant.yml "Hello! I'm new to OrKa. Can you help me understand how the new RedisStack memory works?"

# Ask a follow-up question
python -m orka.orka_cli smart-assistant.yml "What makes the new version 100x faster than before?"

# Test memory with a related question
python -m orka.orka_cli smart-assistant.yml "Can you remind me what we were just discussing about OrKa's performance improvements?"
```

**What you'll notice:**
- **First interaction**: No previous memory, creates new conversation entry
- **Second interaction**: Builds on previous context about OrKa with lightning-fast search
- **Third interaction**: Demonstrates 100x faster memory recall and contextual awareness

## 🧠 Understanding OrKa's RedisStack Memory Revolution

### What Just Happened?

1. **Memory Retrieval**: OrKa searched for relevant past conversations with **sub-millisecond HNSW indexing**
2. **Context Classification**: Determined interaction type to guide response generation
3. **Intelligent Response**: Generated contextually aware response using retrieved memories
4. **Memory Storage**: Stored interaction with automatic importance classification and vector embeddings

### The RedisStack Advantage

**Before V0.7.0 (Basic Redis):**
- Vector search: 50-200ms
- Limited concurrent searches
- Manual index management

**V0.7.0 (RedisStack HNSW):**
- Vector search: 0.5-5ms (**100x faster**)
- 1000+ concurrent searches
- Automatic index optimization
- Enterprise-grade performance

## 🖥️ Monitor Your RedisStack Performance

```bash
# Professional dashboard with HNSW metrics
python -m orka.orka_cli memory watch

# You'll see:
┌─────────────────────────────────────────────────────────────┐
│ OrKa Memory Dashboard - 14:23:45 | Backend: redisstack     │
├─────────────────────────────────────────────────────────────┤
│ 🔧 Backend: redisstack (HNSW)  ⚡ Decay: ✅ Enabled        │
│ 📊 Memories: 1,247            📝 Active: 1,224             │
│ 🚀 HNSW Performance: 1,203     Avg: 2.1ms | Hybrid: 856   │
│ 🧠 Memory Types: Short: 423    💾 Long: 801 | 🔥 Recent   │
└─────────────────────────────────────────────────────────────┘

# Detailed performance analytics
python -m orka.orka_cli memory stats

# Clean up expired memories with HNSW optimization
python -m orka.orka_cli memory cleanup --dry-run
```

## 📊 Performance Comparison

| Operation | Basic Redis | RedisStack HNSW | Your Benefit |
|-----------|-------------|-----------------|--------------|
| **Vector Search** | 50-200ms | 0.5-5ms | **100x faster** |
| **Memory Indexing** | Manual | Automatic | **Zero maintenance** |
| **Concurrent Searches** | 10-50 | 1000+ | **Massive scale** |
| **Memory Efficiency** | 100% | 40% | **60% less RAM** |

## 🎯 Next Steps

### 1. Explore More Examples
```bash
# Try the built-in examples with RedisStack performance
python -m orka.orka_cli examples/enhanced_memory_validation_example.yml "Test RedisStack speed"
```

### 2. Build Advanced Workflows
Check out our comprehensive guides:
- **[📝 YAML Configuration Guide](./yaml-configuration-guide.md)** - Complete configuration reference
- **[🧠 Memory System Guide](./MEMORY_SYSTEM_GUIDE.md)** - Deep dive into RedisStack memory
- **[🤖 Agent Types](./agents.md)** - All available agent types

### 3. Production Deployment
```bash
# Use Kafka for enterprise streaming + RedisStack for memory
python -m orka.start_kafka

# Monitor with professional UI
docker run -it -p 80:80 marcosomma/orka-ui:latest
```

## 🐛 Troubleshooting RedisStack

### Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| `"unknown command 'FT.CREATE'"` | You're using basic Redis. OrKa will auto-fallback, but install Docker for RedisStack |
| Slow performance | Check Docker is running: `docker ps` |
| Memory not persisting | Verify RedisStack container: `docker logs orka-redis` |

### Verify RedisStack is Working
```bash
# Check if vector search is available
redis-cli FT._LIST

# Should show OrKa memory indexes
# If empty, OrKa will create them automatically
```

## 🌟 Why OrKa V0.7.0 is Game-Changing

**Enterprise Performance**: 100x faster vector search makes OrKa suitable for production AI applications that were previously impossible.

**Zero Configuration**: Automatic RedisStack setup means you focus on building, not infrastructure.

**Intelligent Memory**: Context-aware search with temporal ranking provides human-like memory patterns.

**Complete Transparency**: Every decision is auditable and explainable.

**Ready to experience the future of AI orchestration?** Your RedisStack-powered OrKa system is now running with 100x faster vector search!

---

[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
