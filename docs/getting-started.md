# Getting Started with OrKa

> **Last Updated:** 29 November 2025  
> **Status:** 🟢 Current  
> **Related:** [Quickstart](quickstart.md) | [Architecture](architecture.md) | [Agents](agents.md) | [INDEX](index.md)

This guide shows you how to set up OrKa and create your first AI workflows using YAML configuration files.

## What You'll Learn

- How to install OrKa and its dependencies
- How to create basic AI workflows in YAML
- How to use OrKa's memory system
- How to work with local LLMs for privacy

## Prerequisites

### Software Requirements
- **Python 3.11 or higher**
- **RedisStack** (one of the following):
  - Docker (easiest option - `orka-start` auto-configures)
  - Native RedisStack installation (see installation options below)
- **Docker** (optional but recommended for OrKa UI)
- Optional: Local LLM like Ollama, or OpenAI API key

### Hardware Requirements

OrKa is **local-first** focused, meaning you can run everything privately on your machine. Requirements depend on your chosen model:

**Minimum (for llama3.2:3b - used in most examples):**
- **RAM:** 8GB minimum, 16GB recommended
- **Storage:** 5GB for model + data
- **CPU:** Modern multi-core processor (Apple Silicon, Intel i5/i7, AMD Ryzen)

**Recommended (for better performance):**
- **RAM:** 16GB+ for smooth operation with multiple agents
- **GPU:** NVIDIA GPU with 6GB+ VRAM (optional, accelerates inference)
- **Storage:** 20GB+ for multiple models and memory data

**Model-Specific Requirements:**
- `llama3.2:3b` (3 billion parameters): ~4GB RAM, used in **all examples** except multi-model tests
- `gpt-oss:20b` (20 billion parameters): ~16GB RAM
- `deepseek-r1:8b`: ~8GB RAM
- `deepseek-r1:32b`: ~32GB RAM

> 💡 **Note:** All example workflows in `examples/` use `llama3.2:3b` by default for accessibility, except for:
> - `multi_model_local_llm_evaluation.yml` (tests different models)
> - Files with model names in their filename (e.g., `*deepseek-32b.yml`)

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
1. Starts **RedisStack** (native or Docker) on port 6380
2. Starts **OrKa Backend API** on port 8000
3. **Automatically pulls and starts OrKa UI** container on port 8080 (if Docker is available)
4. All services run until you press Ctrl+C

**Service Lifecycle:**
- **Startup:** Pulls latest UI image (can be skipped with `ORKA_UI_SKIP_PULL=true`)
- **Running:** All services available at their respective ports
- **Shutdown:** Clean stop of all services when you exit (Ctrl+C)

This means you can use OrKa **with or without Docker** - Docker is only required for the UI container.

## Services & Ports Overview

When you run `orka-start`, the following services are available:

| Service | Port | URL | Purpose | Auto-Start |
|---------|------|-----|---------|------------|
| **RedisStack** | 6380 | `redis://localhost:6380` | Memory backend & vector search | ✅ Always |
| **OrKa Backend API** | 8000 | `http://localhost:8000` | Workflow execution engine | ✅ Always |
| **OrKa UI** | 8080 | `http://localhost:8080` | Visual workflow builder | ✅ With Docker |

**Quick Access:**
- 🎨 **Build workflows visually:** http://localhost:8080 (opens automatically with `orka-start`)
- 📡 **API health check:** http://localhost:8000/health
- 💾 **Redis connection:** `redis://localhost:6380/0`
- 📚 **Browse 30+ examples:** Available in UI at http://localhost:8080/examples

### OrKa UI Integration

The **OrKa UI** is a visual workflow builder that runs as a Docker container and is **automatically started** when you run `orka-start`.

**Features:**
- 🎨 **Visual Workflow Builder:** Drag-and-drop YAML editor
- 📚 **Example Library:** 30+ pre-built workflows ready to use
- 🔍 **Live Validation:** Real-time YAML syntax checking
- 📊 **Execution Monitoring:** Track workflow progress
- 💾 **Local Storage:** Workflows saved in browser

**Access & Requirements:**
- **URL:** http://localhost:8080 (automatically opens when `orka-start` runs)
- **Container:** `marcosomma/orka-ui:latest` (auto-pulled on first run)
- **Requirements:** Docker installed and running
- **Startup Time:** ~2-5 seconds (after initial image pull)

**Configuration Options:**
```bash
# Default: UI starts automatically with latest version
orka-start

# Fast startup: Skip Docker image pull (use cached version)
export ORKA_UI_SKIP_PULL=true
orka-start

# Backend only: Disable UI completely
export ORKA_DISABLE_UI=true
orka-start

# Custom API URL for UI
export ORKA_API_URL=http://custom-host:8000
orka-start

# Windows PowerShell:
$env:ORKA_UI_SKIP_PULL="true"
$env:ORKA_DISABLE_UI="true"
$env:ORKA_API_URL="http://custom-host:8000"
orka-start
```

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
    model: llama3.2:3b          # Default model used in all examples
    provider: lm_studio
    temperature: 0.7
    
  - id: memory_writer
    type: memory  
    memory_preset: "semantic"    # Facts and knowledge (30 days default)
    config:
      operation: write
```

> 💡 **Model Choice:** We use `llama3.2:3b` in all examples because it:
> - Runs on most modern laptops (4GB RAM requirement)
> - Provides good quality for learning and development
> - Fast inference times for interactive workflows
> - Can be easily swapped for larger models when needed

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

## 🐛 Troubleshooting

### Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| **UI not accessible at port 8080** | Check Docker is running: `docker ps \| grep orka-ui`. Use `ORKA_DISABLE_UI=false` if disabled |
| **UI shows "API connection error"** | Ensure OrKa backend is running on port 8000. Check with `curl http://localhost:8000/health` |
| **"unknown command 'FT.CREATE'"** | You're using basic Redis. OrKa will auto-fallback, but install RedisStack for full features |
| **Slow performance** | Check Docker is running: `docker ps` |
| **Memory not persisting** | Verify RedisStack container: `docker logs orka-redis` |
| **UI not updating** | Pull latest image: `docker pull marcosomma/orka-ui:latest` then restart `orka-start` |

### Verify Services are Running

```bash
# Check all OrKa services
docker ps --filter name=orka

# Expected output should show:
# - orka-ui (port 8080)
# - Redis container (if using Docker backend)

# Check OrKa backend
ps aux | grep orka  # Unix/macOS
Get-Process | Where-Object {$_.ProcessName -like "*python*"}  # Windows

# Test UI accessibility
curl http://localhost:8080

# Test backend API
curl http://localhost:8000/health
```

### RedisStack Verification
```bash
# Check if vector search is available
redis-cli -p 6380 FT._LIST

# Should show OrKa memory indexes
# If empty, OrKa will create them automatically
```

### UI-Specific Troubleshooting

**UI container won't start:**
```bash
# Check Docker logs
docker logs orka-ui

# Remove and restart
docker stop orka-ui
docker rm orka-ui
orka-start
```

**UI not connecting to backend:**
```bash
# Verify API URL configuration
docker inspect orka-ui | grep VITE_API_URL

# Should show: VITE_API_URL_LOCAL=http://localhost:8000/api/run@dist
```

**Force UI update:**
```bash
# Pull latest version and restart
docker pull marcosomma/orka-ui:latest
docker stop orka-ui && docker rm orka-ui
orka-start
```

## 🌟 Why OrKa V0.7.0 is Game-Changing

**Enterprise Performance**: 100x faster vector search makes OrKa suitable for production AI applications that were previously impossible.

**Zero Configuration**: Automatic RedisStack setup means you focus on building, not infrastructure.

**Intelligent Memory**: Context-aware search with temporal ranking provides human-like memory patterns.

**Complete Transparency**: Every decision is auditable and explainable.

**Ready to experience the future of AI orchestration?** Your RedisStack-powered OrKa system is now running with 100x faster vector search!

---
---
← [Quickstart](quickstart.md) | [📚 INDEX](index.md) | [Architecture](architecture.md) →
