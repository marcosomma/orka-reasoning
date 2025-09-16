[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# Getting Started with OrKa V0.7.5

Welcome to OrKa! This guide will help you get up and running with OrKa's powerful agent orchestration system, **100x faster vector search**, and the new **iterative workflows** in just a few minutes.

## 🚀 What's New in V0.7.5

- **🔄 Advanced Loop Node** - Intelligent iterative workflows with cognitive insight extraction
- **🧠 Cognitive Society Framework** - Multi-agent deliberation and consensus building
- **🎯 Threshold-Based Execution** - Continue until quality meets requirements
- **📊 Past Loops Memory** - Learn from previous attempts and iteratively improve
- **🎓 Cognitive Insight Extraction** - Automatically identify insights, improvements, and mistakes

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
pip install orka-reasoning fastapi uvicorn

# Optional: Install extra features
pip install orka-reasoning[extra]
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
orka-start

# For PRODUCTION with RedisStack:
orka-start

# Optional: Run OrKa UI for visual monitoring
docker pull marcosomma/orka-ui:latest
docker run -it -p 80:80 --name orka-ui marcosomma/orka-ui:latest
# Then open http://localhost in your browser
```

## 🎯 Your First OrKa Workflow with 100x Performance

Let's create a powerful workflow that demonstrates OrKa's RedisStack-powered memory capabilities:

### Create your first workflow file: `smart-assistant.yml`

Use one of the curated examples to get started quickly:

```bash
# Copy a ready-to-use conversational AI example
cp ../examples/memory_validation_routing_and_write.yml smart-assistant.yml

# Or start with a simple Q&A workflow
cp ../examples/orka_framework_qa.yml smart-assistant.yml
```

This gives you a production-ready workflow with:
- **RedisStack HNSW memory** for 100x faster vector search
- **Intelligent memory decay** that learns what's important
- **Context-aware conversations** that remember previous interactions
- **Automatic fallback** to web search when memory is insufficient

> **See all available examples**: [`../examples/README.md`](../examples/README.md)
**Key Features in the Example:**
- **Memory-first approach**: Searches existing knowledge before web search
- **Intelligent routing**: Decides between memory-based answers or search fallback  
- **Context-aware search**: Uses conversation history for better relevance
- **Automatic decay**: Short-term and long-term memory classification
- **Vector search**: 100x faster semantic search with RedisStack HNSW

**Example workflow structure:**
```yaml
agents:
  - memory_reader      # Search existing knowledge (100x faster)
  - memory_validator   # Validate if memories are sufficient
  - answer_router      # Route to memory answer OR search fallback
  - search_fallback    # Web search if memories insufficient
  - memory_writer      # Store new knowledge with metadata
```

> **View the complete workflow**: [`../examples/memory_validation_routing_and_write.yml`](../examples/memory_validation_routing_and_write.yml)

### Test Your Smart Assistant with RedisStack Performance

```bash
# Run your first conversation
orka run smart-assistant.yml "Hello! I'm new to OrKa. Can you help me understand how the new RedisStack memory works?"

# Ask a follow-up question
orka run smart-assistant.yml "What makes the new version 100x faster than before?"

# Test memory with a related question
orka run smart-assistant.yml "Can you remind me what we were just discussing about OrKa's performance improvements?"
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
orka memory watch

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
orka memory stats

# Clean up expired memories with HNSW optimization
orka memory cleanup --dry-run
```

## 📊 Performance Comparison

| Operation | Basic Redis | RedisStack HNSW | Your Benefit |
|-----------|-------------|-----------------|--------------|
| **Vector Search** | 50-200ms | 0.5-5ms | **100x faster** |
| **Memory Indexing** | Manual | Automatic | **Zero maintenance** |
| **Concurrent Searches** | 10-50 | 1000+ | **Massive scale** |
| **Memory Efficiency** | 100% | 40% | **60% less RAM** |

## 🔄 Advanced: Iterative Workflows with LoopNode

OrKa V0.7.5 introduces the powerful **LoopNode** for iterative improvement workflows. Here's a quick example:

### Create an Iterative Improver: `iterative-assistant.yml`

```yaml
meta:
  version: "1.0"
  description: "Iterative improvement workflow with cognitive learning"

orchestrator:
  id: iterative-assistant
  strategy: sequential
  agents: [improvement_loop, final_summary]

agents:
  - id: improvement_loop
    type: loop
    max_loops: 5
    score_threshold: 0.85
    score_extraction_pattern: "QUALITY_SCORE:\\s*([0-9.]+)"
    
    # Cognitive extraction learns from each iteration
    cognitive_extraction:
      enabled: true
      extract_patterns:
        insights:
          - "(?:provides?|shows?|demonstrates?)\\s+(.+?)(?:\\n|$)"
        improvements:
          - "(?:lacks?|needs?|should?)\\s+(.+?)(?:\\n|$)"
        mistakes:
          - "(?:overlooked|missed?)\\s+(.+?)(?:\\n|$)"
    
    # Track learning across iterations
    past_loops_metadata:
      iteration: "{{ loop_number }}"
      quality_score: "{{ score }}"
      key_insights: "{{ insights }}"
      improvements_needed: "{{ improvements }}"
    
    # Internal workflow that gets repeated
    internal_workflow:
      orchestrator:
        id: improvement-cycle
        agents: [analyzer, quality_scorer]
      agents:
        - id: analyzer
          type: openai-answer
          prompt: |
            Analyze this request: {{ input }}
            
            {% if previous_outputs.past_loops %}
            Previous iterations:
            {% for loop in previous_outputs.past_loops %}
            - Iteration {{ loop.iteration }} (Score: {{ loop.quality_score }}):
              Insights: {{ loop.key_insights }}
              Improvements: {{ loop.improvements_needed }}
            {% endfor %}
            {% endif %}
            
            Provide comprehensive analysis building on previous insights.
        
        - id: quality_scorer
          type: openai-answer
          prompt: |
            Rate this analysis quality (0.0-1.0):
            {{ previous_outputs.analyzer.result }}
            
            Format: QUALITY_SCORE: X.XX
            Explain improvements needed if score < 0.85

  - id: final_summary
    type: openai-answer
    prompt: |
      Summarize the iterative learning process:
      
      Iterations: {{ previous_outputs.improvement_loop.loops_completed }}
      Final Score: {{ previous_outputs.improvement_loop.final_score }}
      
      Learning Journey:
      {% for loop in previous_outputs.improvement_loop.past_loops %}
      **Iteration {{ loop.iteration }}**: {{ loop.key_insights }}
      {% endfor %}
      
      Final Result: {{ previous_outputs.improvement_loop.result }}
```

### Test the Iterative Improver

```bash
# Run an iterative workflow
orka run iterative-assistant.yml "Explain how artificial intelligence will impact education in the next decade"

# Watch it improve over multiple iterations until quality threshold is met
```

**What you'll see:**
- **Iteration 1**: Basic analysis, identifies areas for improvement
- **Iteration 2**: Builds on insights, addresses gaps from iteration 1
- **Continues**: Until quality score reaches 0.85 or max loops reached
- **Final**: Comprehensive analysis with learning summary

## 🎯 Next Steps

### 1. Explore More Examples
```bash
# Try the built-in examples with RedisStack performance
orka run examples/enhanced_memory_validation_example.yml "Test RedisStack speed"

# Try the cognitive society example
orka run examples/cognitive_society_loop.yml "Should we implement universal basic income?"

# Try the simple loop example
orka run examples/simple_loop_example.yml "Analyze the pros and cons of remote work"
```

### 2. Build Advanced Workflows
Check out our comprehensive guides:
- **[📝 YAML Configuration Guide](./yaml-configuration-guide.md)** - Complete configuration reference including LoopNode
- **[🧠 Memory System Guide](./MEMORY_SYSTEM_GUIDE.md)** - Deep dive into RedisStack memory
- **[🤖 Agent Types](./agents.md)** - All available agent types including LoopNode

### 3. Production Deployment
```bash
# Use RedisStack for enterprise memory and vector search
orka-start

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
