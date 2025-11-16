# Getting Started with OrKa

> **Last Updated:** 16 November 2025  
> **Status:** 🟢 Current  
> **Related:** [Quickstart](quickstart.md) | [Architecture](architecture.md) | [Agents](agents.md) | [INDEX](INDEX.md)

This guide shows you how to set up OrKa and create your first AI workflows using YAML configuration files.

## What You'll Learn

- How to install OrKa and its dependencies
- How to create basic AI workflows in YAML
- How to use OrKa's memory system
- How to work with local LLMs for privacy

## Prerequisites

- Python 3.8 or higher
- **RedisStack** (one of the following):
  - Docker (easiest option - `orka-start` auto-configures)
  - Native RedisStack installation (see installation options below)
- Optional: Local LLM like Ollama, or OpenAI API key

## Installation

### Step 1: Install OrKa
```bash
pip install orka-reasoning
```

### Step 2: Set Up RedisStack

**Option A: Automatic Setup (Recommended)**
```bash
# OrKa will automatically try:
# 1. Native RedisStack (if installed)
# 2. Docker RedisStack (if Docker available)
orka-start
```

**Option B: Install RedisStack Natively (No Docker needed)**
```bash
# macOS
brew install redis-stack

# Ubuntu/Debian
sudo apt install redis-stack-server

# Windows
# Download from: https://redis.io/download

# Then run:
orka-start
```

**Option C: Use Docker Manually**
```bash
docker run -d -p 6380:6380 --name orka-redis redis/redis-stack:latest
```

**What happens when you run `orka-start`:**
1. First tries to find and use **native RedisStack** installation
2. If not found, falls back to **Docker RedisStack**
3. If neither available, provides installation instructions

This means you can use OrKa **with or without Docker** - just pick the method that works best for your environment.

## Environment Setup

```bash
# For local LLMs (no API key needed)
# Just install Ollama: https://ollama.ai

# For OpenAI models (optional)
export OPENAI_API_KEY=your-api-key-here

# For Windows PowerShell:
$env:OPENAI_API_KEY="your-api-key-here"
```

## Your First Workflow

Let's create a simple Q&A system that remembers previous conversations:

### Create your first workflow file: `smart-assistant.yml`

Use one of the preset-based examples to get started:

```bash
# Copy a memory preset example (simplified configuration)
cp ../examples/simple_memory_preset_demo.yml smart-assistant.yml

# Or try the preset showcase with multiple memory types
cp ../examples/memory_presets_showcase.yml smart-assistant.yml
```

This gives you a working workflow with simplified configuration:
- **🧠 Memory Presets** - Single parameter provides preconfigured retention rules
- **🎯 Operation-Based Defaults** - Different settings for read vs write operations
- **🤖 Local LLM Support** - Privacy-focused with Ollama integration
- **⚡ Minimal Configuration** - Preset templates reduce configuration complexity

> **See all available examples**: [`../examples/README.md`](../examples/README.md)

**Key Features with Memory Presets:**
- **Simplified Configuration**: `memory_preset: "episodic"` instead of manual decay rules
- **Preset Templates**: Memory types with predefined retention periods (sensory, working, episodic, semantic, procedural, meta)
- **Operation-Based Defaults**: Automatic parameter selection for read vs write operations
- **Local LLM Integration** - Full privacy with local model support

**Example workflow structure with presets:**
```yaml
agents:
  - id: memory_reader
    type: memory
    memory_preset: "episodic"    # Personal experiences (7 days default)
    config:
      operation: read
    # Preset provides default configuration
  
  - id: answer_builder  
    type: local_llm              # Local model for privacy
    model: gpt-oss:20b
    provider: ollama
    
  - id: memory_writer
    type: memory  
    memory_preset: "semantic"    # Facts and knowledge (30 days default)
    config:
      operation: write
```

> **View the complete workflow**: [`../examples/simple_memory_preset_demo.yml`](../examples/simple_memory_preset_demo.yml)

### Test Your Workflow

```bash
# Run your first conversation
orka run smart-assistant.yml "Hello! I'm new to OrKa. Can you help me understand how the memory system works?"

# Ask a follow-up question
orka run smart-assistant.yml "What are the performance characteristics?"

# Test memory retrieval
orka run smart-assistant.yml "Can you remind me what we were just discussing?"
```

**What happens:**
- **First interaction**: No previous memory, creates new entry
- **Second interaction**: Retrieves relevant context from previous conversation
- **Third interaction**: Demonstrates memory retrieval with vector search

## 🧠 Understanding OrKa's Memory System

### What the Workflow Does

1. **Memory Retrieval**: OrKa searches for relevant past conversations using vector similarity with HNSW indexing
2. **Context Processing**: Retrieved memories are included in LLM prompt as context
3. **Response Generation**: LLM generates response based on current input and retrieved context
4. **Memory Storage**: Interaction is stored in Redis with vector embeddings and expiration rules

### RedisStack HNSW Indexing

**Basic Redis (pre-V0.7.0):**
- Vector search: 50-200ms (linear scan)
- Limited concurrent searches
- Manual index management

**RedisStack HNSW (V0.7.0+):**
- Vector search: 0.5-5ms (HNSW index)
- 1000+ concurrent searches supported
- Automatic index optimization
- Measured 100x faster on benchmarks

## 🖥️ Monitor Memory State

```bash
# View memory dashboard with metrics
orka memory watch

# Example output:
┌─────────────────────────────────────────────────────────────┐
│ OrKa Memory Dashboard - 14:23:45 | Backend: redisstack     │
├─────────────────────────────────────────────────────────────┤
│ 🔧 Backend: redisstack (HNSW)  ⚡ Decay: ✅ Enabled        │
│ 📊 Memories: 1,247            📝 Active: 1,224             │
│ 🚀 HNSW Searches: 1,203        Avg: 2.1ms | Hybrid: 856   │
│ 🧠 Memory Types: Short: 423    💾 Long: 801 | Recent: 43  │
└─────────────────────────────────────────────────────────────┘

# View detailed statistics
orka memory stats

# Preview cleanup without deleting
orka memory cleanup --dry-run
```

## 📊 Performance Comparison

Performance measurements on test dataset:

| Operation | Basic Redis | RedisStack HNSW | Measured Difference |
|-----------|-------------|-----------------|--------------|
| **Vector Search** | 50-200ms | 0.5-5ms | **~100x faster** |
| **Index Management** | Manual | Automatic | **Automatic** |
| **Concurrent Searches** | 10-50 | 1000+ | **20x+ more** |
| **Memory Efficiency** | 100% baseline | 40% | **60% reduction** |

*Note: Performance varies based on dataset size and hardware.*

## 🔄 Advanced: Iterative Workflows with LoopNode

OrKa V0.7.5 introduces **LoopNode** for workflows that repeat until a condition is met:

### Create an Iterative Workflow: `iterative-assistant.yml`

```yaml
meta:
  version: "1.0"
  description: "Iterative refinement workflow with score-based exit"

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
    
    # Extract metrics from each iteration
    cognitive_extraction:
      enabled: true
      extract_patterns:
        insights:
          - "(?:provides?|shows?|demonstrates?)\\s+(.+?)(?:\\n|$)"
        improvements:
          - "(?:lacks?|needs?|should?)\\s+(.+?)(?:\\n|$)"
        mistakes:
          - "(?:overlooked|missed?)\\s+(.+?)(?:\\n|$)"
    
    # Store iteration metadata
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
            
            Provide analysis based on previous iterations.
        
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
      Summarize the iteration process:
      
      Iterations: {{ previous_outputs.improvement_loop.loops_completed }}
      Final Score: {{ previous_outputs.improvement_loop.final_score }}
      
      Learning Journey:
      {% for loop in previous_outputs.improvement_loop.past_loops %}
      **Iteration {{ loop.iteration }}**: {{ loop.key_insights }}
      {% endfor %}
      
      Final Result: {{ previous_outputs.improvement_loop.result }}
```

### Test the Iterative Workflow

```bash
# Run an iterative workflow
orka run iterative-assistant.yml "Explain how artificial intelligence will impact education in the next decade"

# Workflow repeats until quality threshold is met
```

**What happens:**
- **Iteration 1**: Initial analysis, generates quality score
- **Iteration 2**: Refines based on identified gaps from iteration 1
- **Continues**: Until quality score reaches 0.85 or max loops (5) reached
- **Final**: Aggregated output with summary of iterations

## 🎯 Next Steps

### 1. Explore More Examples
```bash
# Try the built-in examples
orka run examples/enhanced_memory_validation_example.yml "Test memory search"

# Try the multi-agent deliberation example
orka run examples/cognitive_society_loop.yml "Should we implement universal basic income?"

# Try the loop example
orka run examples/simple_loop_example.yml "Analyze the pros and cons of remote work"
```

### 2. Build Advanced Workflows
Check out our guides:
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


---
← [Quickstart](quickstart.md) | [📚 index](index.md) | [Architecture](architecture.md) →
