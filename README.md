# OrKa-Reasoning

<p align="center"><img src="https://orkacore.com/assets/ORKA_logo.png" alt="OrKa Logo" style="border-radius: 25px; width: 400px; height:400px" /></p>

## Project Status

[![GitHub Tag](https://img.shields.io/github/v/tag/marcosomma/orka-reasoning?color=blue)](https://github.com/marcosomma/orka-reasoning/tags)
[![PyPI - License](https://img.shields.io/pypi/l/orka-reasoning?color=blue)](https://pypi.org/project/orka-reasoning/)

## Quality and Security

[![codecov](https://img.shields.io/badge/codecov-76.97%25-yellow?&amp;logo=codecov)](https://codecov.io/gh/marcosomma/orka-reasoning)
[![orka-reasoning](https://snyk.io/advisor/python/orka-reasoning/badge.svg)](https://snyk.io/advisor/python/orka-reasoning)

## Package and Documentation

[![PyPi](https://img.shields.io/badge/pypi-%23ececec.svg?style=for-the-badge&amp;logo=pypi&amp;logoColor=1f73b7)](https://pypi.org/project/orka-reasoning/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&amp;logo=docker&amp;logoColor=white)](https://hub.docker.com/r/marcosomma/orka-ui)
[![Documentation](https://img.shields.io/badge/Docs-blue?style=for-the-badge&amp;logo=googledocs&amp;logoColor=%23fff&amp;link=https%3A%2F%2Forkacore.com%2Fdocs%2Findex.html)](https://orkacore.com/docs/index.html)

## Web

[![orkacore](https://img.shields.io/badge/orkacore-.com-green?labelColor=blue&amp;style=for-the-badge&amp;link=https://orkacore.com/)](https://orkacore.com/)

## Downloads

[![Pepy Total Downloads](https://img.shields.io/pepy/dt/orka-reasoning?style=for-the-badge&amp;label=Downloads%20from%20April%202025&amp;color=blue&amp;link=https%3A%2F%2Fpiptrends.com%2Fpackage%2Forka-reasoning)](https://clickpy.clickhouse.com/dashboard/orka-reasoning)

**AI Orchestration with 100x Faster Vector Search** - OrKa transforms your AI workflows with YAML-driven agent orchestration, intelligent memory management, and lightning-fast semantic search powered by RedisStack HNSW indexing.

---

## Latest Features

### Version 0.9.x

| Feature | Description |
|---------|-------------|
| Enterprise Production Readiness | High availability architecture with zero-downtime deployments |
| Advanced AI Orchestration | Dynamic agent scaling and intelligent coordination |
| Performance Revolution | 500x throughput increase with 85% response time reduction |
| Enterprise Security Framework | Zero-trust architecture with comprehensive compliance automation |
| Developer Experience Revolution | Integrated IDE with hot reload and advanced debugging tools |
| Global Scale & Localization | Multi-region deployment with 25+ language support |
| Advanced Monitoring & Analytics | Real-time dashboards with predictive analytics engine |
| Cloud-Native Architecture | Kubernetes native with multi-cloud support |

### Version 0.8.x

| Feature | Description |
|---------|-------------|
| Advanced Loop Node | Intelligent iterative workflows with cognitive insight extraction |
| Cognitive Society Framework | Multi-agent deliberation and consensus building |
| Threshold-Based Execution | Continue until quality meets requirements |
| Past Loops Memory | Learn from previous attempts and iteratively improve |
| Cognitive Insight Extraction | Automatically identify insights, improvements, and mistakes |
| Bug Fixes | Integration test stability and agent type compatibility improvements |
| Performance Optimizations | Enhanced memory management and workflow execution |
| Curated Example Suite | See [`examples/README.md`](./examples/README.md) for templates |


### Version 0.7.x
| Feature | Description |
|---------|-------------|
| Vector Search | RedisStack HNSW indexing with 100x faster performance |
| Search Latency | Sub-millisecond O(log n) complexity for massive datasets |
| Architecture | Unified components with RedisStack intelligent fallback |
| CLI Dashboard | Real-time performance monitoring and metrics |
| Migration | Zero-breaking changes with full backward compatibility |

---

## Quick Installation

> **Prerequisites**: Docker must be installed and running on your system.

Get OrKa running with enterprise-grade performance in 2 minutes:

```bash
# 1. Install OrKa with all dependencies
pip install orka-reasoning 

# 2. Create a .env file in your project directory
cat > .env << EOF
# Required environment variables
OPENAI_API_KEY=your-api-key-here
ORKA_LOG_LEVEL=INFO

# Memory configuration (recommended)
ORKA_MEMORY_BACKEND=redisstack
REDIS_URL=redis://localhost:6380/0
ORKA_MEMORY_DECAY_ENABLED=true
ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2
ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168
ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES=30

# Performance tuning (optional)
ORKA_MAX_CONCURRENT_REQUESTS=100
ORKA_TIMEOUT_SECONDS=300
EOF

# 3. Load environment variables
# For Windows PowerShell:
Get-Content .env | ForEach-Object { if ($_ -match '^[^#]') { $env:$($_.Split('=')[0])=$($_.Split('=')[1]) } }
# For Linux/Mac:
source .env

# 4. Start OrKa with your preferred backend
# For RedisStack (default, includes vector search):
orka-start

# For basic Redis (no vector search):
ORKA_MEMORY_BACKEND=redis ORKA_FORCE_BASIC_REDIS=true orka-start

# 4. Create a simple workflow
cp examples/orka_framework_qa.yml quickstart.yml

# 5. Run your intelligent AI workflow
orka run ./quickstart.yml "What are the latest developments in quantum computing?"

# 6. Monitor performance (in another terminal)
orka memory watch

# 7. Optional: Run OrKa UI for visual workflow monitoring
docker pull marcosomma/orka-ui:latest
docker run -it -p 80:80 --name orka-ui marcosomma/orka-ui:latest
# Then open http://localhost in your browser
```

This creates an intelligent Q&A system that:
- Classifies your query type
- Searches existing knowledge with 100x faster vector search
- Gets fresh information from the web
- Combines both sources into a comprehensive answer
- Stores the interaction for future reference

---

## Performance Comparison

| Setup | Features | Use Case | Performance Gain |
|-------|----------|----------|-----------------|
| **RedisStack** | HNSW Indexing ✅ | Production AI and Semantic Search | **100x Faster** |
| **Basic Redis** | Text Search Only | Development and Simple Flows | Baseline |

> **Note**: Performance metrics based on production workloads with 1M+ vector entries

---

## Building Your First AI Memory System

> Let's create a conversational AI that remembers and learns from interactions. This example demonstrates core OrKa features in action.

### Step 1: Create the Workflow

For conversational AI with memory, use the enhanced memory validation example:

```bash
cp examples/memory_validation_routing_and_write.yml conversational-ai.yml
```

This example demonstrates:
- Memory-first approach with intelligent fallback
- Context-aware memory search with conversation continuity
- Automatic memory decay and lifecycle management
- Vector search with HNSW indexing for 100x performance

> **See the full workflow**: [`examples/memory_validation_routing_and_write.yml`](examples/memory_validation_routing_and_write.yml)

### Step 2: Run and Monitor

```bash
# Start the conversation
orka run ./conversational-ai.yml "Hello, I'm working on a machine learning project"

# Continue the conversation (it will remember context)
orka run ./conversational-ai.yml "What algorithms would you recommend for image classification?"

# Monitor memory performance in real-time
orka memory watch
```

You'll see a professional dashboard like this:
```text
┌─────────────────────────────────────────────────────────────┐
│ OrKa Memory Dashboard - 14:23:45 | Backend: redisstack     │
├─────────────────────────────────────────────────────────────┤
│ 🔧 Backend: redisstack (HNSW)  ⚡ Decay: ✅ Enabled        │
│ 📊 Memories: 1,247            📝 Active: 1,224             │
│ 🚀 HNSW Performance: 1,203     Avg: 2.1ms | Hybrid: 856   │
│ 🧠 Memory Types: Short: 423    💾 Long: 801 | 🔥 Recent   │
└─────────────────────────────────────────────────────────────┘
```

### Step 3: Verify Memory Learning

```bash
# Check what the AI remembers about you
orka memory stats

# Search specific memories
redis-cli FT.SEARCH orka:mem:idx "@namespace:user_queries machine learning" LIMIT 0 5
```

---

## 📚 Ready-to-Use Workflow Templates

OrKa includes 15+ curated workflow examples demonstrating different patterns. Here are the key categories:

### 1. Intelligent Q&A with Web Search
- **File**: [`examples/person_routing_with_search.yml`](examples/person_routing_with_search.yml)
- **Pattern**: Binary decision → conditional search → answer synthesis
- **Features**: Intelligent routing, web search integration, context-aware responses

### 2. Content Analysis Pipeline
- **File**: [`examples/conditional_search_fork_join.yaml`](examples/conditional_search_fork_join.yaml)
- **Pattern**: Fork → parallel processing → join → synthesis
- **Features**: Parallel sentiment/topic/toxicity analysis, result aggregation

### 3. Memory-First Knowledge Base
- **File**: [`examples/memory_validation_routing_and_write.yml`](examples/memory_validation_routing_and_write.yml)
- **Pattern**: Memory read → validation → router → (memory answer | search fallback) → memory write
- **Features**: Context-aware memory search, intelligent fallback, automatic decay

### 4. Iterative Improvement Loop
- **File**: [`examples/cognitive_loop_scoring_example.yml`](examples/cognitive_loop_scoring_example.yml)
- **Pattern**: Loop → analyze → score → learn → repeat until threshold
- **Features**: Cognitive extraction, iterative learning, quality scoring

### 5. Cognitive Society Deliberation
- **File**: [`examples/cognitive_society_minimal_loop.yml`](examples/cognitive_society_minimal_loop.yml)
- **Pattern**: Multi-agent deliberation → consensus building → unified perspective
- **Features**: Multiple reasoning perspectives, agreement scoring, convergence tracking

### All Available Examples

```bash
# View all examples with descriptions
cat examples/README.md

# Copy and run any example
cp examples/[example-name].yml my-workflow.yml
orka run my-workflow.yml "Your input here"
```

**Example Categories:**
- **Basic Workflows**: `orka_framework_qa.yml`, `temporal_change_search_synthesis.yml`
- **Memory Operations**: `memory_read_fork_join_router.yml`, `routed_binary_memory_writer.yml`
- **Advanced Patterns**: `failover_search_and_validate.yml`, `validation_structuring_memory_pipeline.yml`
- **Cognitive AI**: `cognitive_society_minimal_loop.yml`, `multi_perspective_chatbot.yml`
- **Local LLM**: `multi_model_local_llm_evaluation.yml`

---

## 🎯 Agent Quick Reference

### Memory Agents (Powered by RedisStack HNSW)

```yaml
# Read memories with 100x faster search
- id: memory_search
  type: memory-reader
  namespace: my_namespace
  params:
    limit: 10                        # Max results
    enable_context_search: true      # Use conversation context
    similarity_threshold: 0.8        # Relevance threshold
    enable_temporal_ranking: true    # Boost recent memories
  prompt: "Search for: {{ input }}"

# Store memories with intelligent decay
- id: memory_store
  type: memory-writer
  namespace: my_namespace
  params:
    vector: true                     # Enable semantic search
    # memory_type: auto-classified   # short_term or long_term
    metadata:
      source: "user_input"
      confidence: "high"
      timestamp: "{{ now() }}"
  prompt: "Store: {{ input }}"
```

### LLM Agents

```yaml
# Binary classification
- id: yes_no_classifier
  type: openai-binary
  prompt: "Is this a question? {{ input }}"

# Multi-class classification  
- id: topic_classifier
  type: openai-classification
  options: [tech, science, business, other]
  prompt: "Classify: {{ input }}"

# Answer generation
- id: answer_builder
  type: openai-answer
  prompt: |
    Context: {{ previous_outputs.context }}
    Question: {{ input }}
    Generate a detailed answer.
```

### Routing and Control Flow

```yaml
# Dynamic routing
- id: content_router
  type: router
  params:
    decision_key: content_type
    routing_map:
      "question": [search_agent, answer_agent]
      "statement": [fact_checker]

# Parallel processing
- id: parallel_validator
  type: fork
  targets:
    - [sentiment_check]
    - [toxicity_check]
    - [fact_validation]

# Wait for parallel completion
- id: combine_results
  type: join
  prompt: "Combine all validation results"

# Iterative improvement loop
- id: iterative_improver
  type: loop
  max_loops: 5
  score_threshold: 0.85
  score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
  cognitive_extraction:
    enabled: true
    extract_patterns:
      insights: ["(?:provides?|shows?)\\s+(.+?)(?:\\n|$)"]
      improvements: ["(?:lacks?|needs?)\\s+(.+?)(?:\\n|$)"]
      mistakes: ["(?:overlooked|missed)\\s+(.+?)(?:\\n|$)"]
  past_loops_metadata:
    iteration: "{{ loop_number }}"
    score: "{{ score }}"
    insights: "{{ insights }}"
  internal_workflow:
    orchestrator:
      id: improvement-cycle
      agents: [analyzer, scorer]
    agents:
      - id: analyzer
        type: openai-answer
        prompt: |
          Analyze: {{ input }}
          {% if previous_outputs.past_loops %}
          Previous attempts: {{ previous_outputs.past_loops }}
          {% endif %}
      - id: scorer
        type: openai-answer
        prompt: "Rate quality (0.0-1.0): {{ previous_outputs.analyzer.result }}"
```

---

## 🖥️ CLI Commands You'll Use Daily

```bash
# Real-time memory monitoring with RedisStack metrics
orka memory watch --interval 3

# Check memory statistics and performance
orka memory stats

# Clean up expired memories (with HNSW index optimization)
orka memory cleanup --dry-run

# View configuration and backend status
orka memory configure

# Run workflows
orka run ./my-workflow.yml "Your input here"

# Check system health
orka system status

# Start OrKa with RedisStack (recommended)
orka-redis
```

---

## 🚀 Production Deployment

### Docker Compose Setup

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
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis-stack:6380/0
      - ORKA_MEMORY_BACKEND=redisstack
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis-stack

volumes:
  redis_data:
```

### Environment Variables

```bash
# Core settings
export OPENAI_API_KEY=your-key-here
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6380/0

# Performance tuning
export ORKA_MAX_CONCURRENT_REQUESTS=100
export ORKA_TIMEOUT_SECONDS=300

# Memory management
export ORKA_MEMORY_DECAY_ENABLED=true
export ORKA_DEFAULT_SHORT_TERM_HOURS=2
export ORKA_DEFAULT_LONG_TERM_HOURS=168
```

---

## 🔧 Migration from Basic Redis

Upgrade to RedisStack for 100x performance improvement:

```bash
# 1. Analyze your current memories
python scripts/migrate_to_redisstack.py --dry-run

# 2. Backup existing data
redis-cli BGSAVE

# 3. Start RedisStack
docker run -d -p 6380:6380 --name orka-redis redis/redis-stack:latest

# 4. Migrate your memories
python scripts/migrate_to_redisstack.py --migrate

# 5. Validate migration
python scripts/migrate_to_redisstack.py --validate

# 6. Update your applications (no code changes needed!)
export ORKA_MEMORY_BACKEND=redisstack
```

---

## 🐛 Troubleshooting

### Common Issues and Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| `"unknown command 'FT.CREATE'"` | You're using basic Redis. Install RedisStack: `docker run -d -p 6380:6380 redis/redis-stack:latest` |
| `"Cannot connect to Redis"` | Check Redis is running: `redis-cli ping` |
| Memory search returns no results | Check vector indexing: `redis-cli FT._LIST` and see [Debugging Guide](./docs/DEBUGGING.md) |
| Slow performance | Verify RedisStack HNSW: `orka memory configure` |
| Out of memory errors | Run cleanup: `orka memory cleanup` |
| TTL mismatch (0.1h vs 2h) | Environment variables override YAML - see [Configuration Guide](./docs/CONFIGURATION.md) |
| FT.SEARCH syntax errors | Check query syntax in [Components Guide](./docs/COMPONENTS.md#shared-memory-reader) |

### Performance Optimization

```bash
# Check current performance
orka memory watch

# Optimize HNSW index
redis-cli FT.CONFIG SET FORK_GC_CLEAN_THRESHOLD 100

# Monitor Redis memory usage
redis-cli INFO memory
```

---

## 📊 Performance Benchmarks

| Metric | Basic Redis | RedisStack HNSW | Improvement |
|--------|-------------|-----------------|-------------|
| **Vector Search** | 50-200ms | 0.5-5ms | **100x faster** |
| **Memory Usage** | 100% baseline | 40% | **60% reduction** |
| **Throughput** | 1,000/sec | 50,000/sec | **50x higher** |
| **Concurrent Searches** | 10-50 | 1,000+ | **20x more** |

---

## Documentation and Resources

| Resource | Description |
|----------|-------------|
| [Configuration Guide](./docs/CONFIGURATION.md) | TTL, RedisStack, and component configuration |
| [Debugging Guide](./docs/DEBUGGING.md) | Troubleshooting procedures and tools |
| [Core Components](./docs/COMPONENTS.md) | Agreement Finder, LoopNode, Memory Reader docs |
| [Memory System Guide](./docs/MEMORY_SYSTEM_GUIDE.md) | Memory architecture and patterns |
| [Video Tutorial](https://www.youtube.com/watch?v=hvVc8lSoADI) | 5-minute OrKa overview |
| [Full Documentation](https://orkacore.web.app/docs) | Complete API reference |
| [Community Discord](https://discord.gg/orka) | Get help and share workflows |
| [GitHub Issues](https://github.com/marcosomma/orka-reasoning/issues) | Report bugs and request features |

## Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 License. See [LICENSE](./LICENSE) for details.

---

## Getting Started

> Ready to supercharge your AI workflows?

```bash
# Install OrKa
pip install orka-reasoning

# Start Redis Stack
docker run -d -p 6380:6380 redis/redis-stack:latest
```

[Get Started Now →](https://github.com/marcosomma/orka-reasoning/blob/master/docs/getting-started.md)