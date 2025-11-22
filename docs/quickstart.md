# OrKa Quickstart Guide

> **Last Updated:** 22 November 2025  
> **Status:** 🟢 Current  
> **Related:** [Getting Started](getting-started.md) | [Installation Guide](getting-started.md#installation) | [INDEX](index.md)

Get OrKa running in 5 minutes and create your first AI workflow.

## Quick Setup

```bash
# 1. Install OrKa
pip install orka-reasoning

# 2. Start all services (Redis + Backend + UI)
orka-start
# ✅ RedisStack: redis://localhost:6380
# ✅ Backend API: http://localhost:8000
# ✅ UI: http://localhost:8080

# 3. Install local LLM (recommended - runs privately on your machine)
# Install Ollama from https://ollama.ai
ollama pull llama3.2:3b  # Default model used in all examples (4GB RAM)

# 4. Optional: Set OpenAI key (if using cloud models instead)
export OPENAI_API_KEY=your-key-here
```

**What you get:**
- 🎨 **Visual Workflow Builder** at http://localhost:8080
- 💾 **Memory System** with RedisStack
- 🤖 **30+ Example Workflows** ready to use
- 🔒 **Privacy-first** with local LLM support

## Manual Setup (Alternative)

If you prefer to set things up manually:

### 1. Prerequisites

```bash
# Install Python packages
pip install orka-reasoning[all]

# Create and configure .env file (SIMPLIFIED in V0.9.2!)
cat > .env << EOF
# Optional: Local LLM (Recommended - No API keys needed!)
# No environment variables required for local LLM setup

# Optional: OpenAI API (if using cloud models)
# OPENAI_API_KEY=your-api-key-here

# OrKa Configuration (with smart defaults)
ORKA_LOG_LEVEL=INFO
ORKA_MEMORY_BACKEND=redisstack

# Memory presets handle all decay configuration automatically!
# No more complex memory decay rules needed - handled by cognitive presets

# Performance tuning (optional)
ORKA_MAX_CONCURRENT_REQUESTS=100
ORKA_TIMEOUT_SECONDS=300
EOF

# Load environment variables
# For Windows PowerShell:
Get-Content .env | ForEach-Object { if ($_ -match '^[^#]') { $env:$($_.Split('=')[0])=$($_.Split('=')[1]) } }
# For Linux/Mac:
source .env
```

### 2. Start OrKa

```bash
# All-in-one: Starts RedisStack + Backend + UI
orka-start

# Services available:
# - Redis: redis://localhost:6380
# - Backend: http://localhost:8000
# - UI: http://localhost:8080

# Optional: Fast startup (skip Docker image pull)
export ORKA_UI_SKIP_PULL=true
orka-start

# Optional: Backend only (no UI)
export ORKA_DISABLE_UI=true
orka-start

# Memory monitoring TUI
orka memory watch
```

## Verify Installation

```bash
# Check OrKa status
orka system status

# Monitor memory performance
orka memory watch

# You should see:
┌─────────────────────────────────────────────────────────────┐
│ OrKa Memory Dashboard - 14:23:45 | Backend: redisstack     │
├─────────────────────────────────────────────────────────────┤
│ 🔧 Backend: redisstack (HNSW)  ⚡ Decay: ✅ Enabled        │
│ 📊 Memories: 1,247            📝 Active: 1,224             │
│ 🚀 HNSW Performance: 1,203     Avg: 2.1ms | Hybrid: 856   │
│ 🧠 Memory Types: Short: 423    💾 Long: 801 | 🔥 Recent   │
└─────────────────────────────────────────────────────────────┘
```

## Your First Workflow - Memory Presets Demo

Create `quickstart.yml` with **90% simpler configuration**:

```yaml
orchestrator:
  id: quickstart-memory-presets
  strategy: sequential
  agents: [memory_search, answer_builder, memory_store]

agents:
  - id: memory_search
    type: memory                    # Unified memory agent (NEW in V0.9.2)
    memory_preset: "semantic"       # Facts and knowledge (30 days) 
    config:
      operation: read               # Operation-aware optimization
    namespace: knowledge
    prompt: "Search for: {{ get_input() }}"
    
  - id: answer_builder
    type: local_llm                 # Local LLM first (privacy-focused)
    model: gpt-oss:20b
    model_url: http://localhost:11434/api/generate
    provider: ollama
    temperature: 0.7
    prompt: |
      Based on the memory search results: {{ get_agent_response('memory_search') }}
      
      Question: {{ get_input() }}
      
      Provide a comprehensive answer.
    depends_on: [memory_search]
    
  - id: memory_store
    type: memory                    # Same unified type for writing
    memory_preset: "semantic"       # Same cognitive type  
    config:
      operation: write              # Auto-optimized for storage
    namespace: knowledge
    prompt: |
      Question: {{ get_input() }}
      Answer: {{ get_agent_response('answer_builder') }}
    depends_on: [answer_builder]
```

**Key Improvements in V0.9.2:**
- **90% Configuration Reduction**: `memory_preset: "semantic"` replaces 15+ lines
- **Operation-Aware**: Automatic read/write optimization
- **Local LLM First**: Privacy-focused with Ollama integration
- **Unified Memory Type**: Single `type: memory` for all memory operations
    params:
      limit: 5
      enable_context_search: true
    prompt: "Find relevant info about: {{ input }}"

  - id: answer_builder
    type: openai-answer
    prompt: |
      Context: {{ previous_outputs.memory_search }}
      Question: {{ input }}
      Generate a comprehensive answer.

  - id: memory_store
    type: memory-writer
    namespace: knowledge
    params:
      vector: true
    prompt: |
      Q: {{ input }}
      A: {{ previous_outputs.answer_builder }}
```

Run your workflow:

```bash
# Ask a question
orka run quickstart.yml "What is OrKa?"

# Ask a follow-up
orka run quickstart.yml "How does its memory system work?"
```

## Docker Compose Setup

For more control, use our Docker Compose configuration:

```yaml
# docker-compose.yml
version: '3.8'
services:
  redis-stack:
    image: redis/redis-stack:latest
    ports:
      - "6380:6380"
    volumes:
      - redis_data:/data
    environment:
      - REDIS_ARGS=--save 60 1000

  orka:
    image: marcosomma/orka:latest
    ports:
      - "8000:8000"
    environment:
      # Required environment variables
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ORKA_LOG_LEVEL=INFO
      
      # Memory configuration
      - ORKA_MEMORY_BACKEND=redisstack
      - REDIS_URL=redis://redis-stack:6380/0
      - ORKA_MEMORY_DECAY_ENABLED=true
      - ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2
      - ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168
      - ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES=30
      
      # Performance tuning
      - ORKA_MAX_CONCURRENT_REQUESTS=100
      - ORKA_TIMEOUT_SECONDS=300
    depends_on:
      - redis-stack

  orka-ui:
    image: marcosomma/orka-ui:latest
    ports:
      - "80:80"
    depends_on:
      - orka

volumes:
  redis_data:
```

Start with:

```bash
docker-compose up -d
```

## Next Steps

1. Try our [example workflows](../examples/)
2. Read the [tutorials](../tutorials/)
3. Join our [Discord community](https://discord.gg/orka)

## Troubleshooting

Common issues and solutions:

1. **Environment Variable Errors**
   - `OPENAI_API_KEY environment variable is required`:
     - Create a .env file with your OpenAI API key
     - Load it using the appropriate command for your shell
   - `KeyError: 'ORKA_LOG_LEVEL'`:
     - Add `ORKA_LOG_LEVEL=INFO` to your .env file
     - Reload environment variables
   - Environment variables not persisting:
     - For Windows: Add them to System Environment Variables
     - For Linux/Mac: Add them to ~/.bashrc or ~/.zshrc

2. **"FT.CREATE unknown command"**
   - Cause: Using basic Redis instead of RedisStack
   - Solution: Ensure Docker is running and using redis-stack image

3. **Slow performance**
   - Check Docker status: `docker ps`
   - Verify RedisStack: `redis-cli FT._LIST`
   - Check environment variables: `orka memory configure`

4. **Memory not persisting**
   - Check RedisStack logs: `docker logs orka-redis`
   - Verify REDIS_URL in .env matches your setup

## Getting Help

- 📚 [Full Documentation](https://orkacore.web.app/docs)
- 💬 [Discord Support](https://discord.gg/orka)
- 🐛 [GitHub Issues](https://github.com/marcosomma/orka-reasoning/issues)

## Security Note

The one-click installer script is served over HTTPS and is digitally signed. You can verify the signature with:

```bash
curl -sSL https://orkacore.com/quickstart.sh.asc | gpg --verify
```
---
← [INDEX](index.md) | [📚 INDEX](index.md) | [Getting Started](getting-started.md) →
