# OrKa Agent, Node & Tool Documentation Index

Complete reference for all agent types, control flow nodes, and tools supported by the current OrKa codebase.

## 🤖 LLM Agents

Agents that use language models for processing and generation.

| Agent | Purpose | Documentation |
|-------|---------|---------------|
| **openai-answer** | Content generation, Q&A | [📖 View](./agents/openai-answer.md) |
| **openai-binary** | True/false decisions with LLM reasoning | [📖 View](./agents/openai-binary.md) |
| **openai-classification** | Multi-category classification | [📖 View](./agents/openai-classification.md) |
| **local_llm** | Local/private LLM processing (Ollama, LM Studio) | [📖 View](./agents/local-llm.md) |
| **binary** | Simple rule-based true/false | [📖 View](./agents/binary.md) |
| **validate_and_structure** | Answer validation with structured output | [📖 View](./agents/validate-and-structure.md) |
| **plan_validator** | Validate and critique execution paths | [📖 View](./agents/plan-validator.md) |

## 💾 Memory Agents

Intelligent memory storage and retrieval with RedisStack HNSW (100x faster).

| Agent | Purpose | Documentation |
|-------|---------|---------------|
| **memory** | Read/write memory (operation selected via `config.operation`) | [📖 View](./MEMORY_SYSTEM_GUIDE.md) |

**Features:**
- ⚡ 100x faster vector search with HNSW
- 🧠 Memory presets (sensory, working, semantic, procedural, episodic, meta)
- ⏰ Intelligent decay management
- 🎯 Context-aware search

## 🔀 Control Flow Nodes

Nodes that control workflow execution and logic.

| Node | Purpose | Documentation |
|------|---------|---------------|
| **router** | Conditional routing based on decisions | [📖 View](./nodes/router.md) |
| **fork** | Parallel execution of multiple branches | [📖 View](./nodes/fork-and-join.md) |
| **join** | Combine results from parallel branches | [📖 View](./nodes/fork-and-join.md) |
| **loop** | Iterative improvement with cognitive extraction | [📖 View](./nodes/loop.md) |
| **failover** | Resilient execution with fallbacks | [📖 View](./nodes/failover.md) |
| **graph-scout** | Intelligent path discovery | [📖 View](./GRAPH_SCOUT_AGENT.md) |
| **loop_validator** | Validate loop convergence | [📖 View](./nodes/loop.md) |
| **failing** | Intentionally fail (testing) | [📖 View](./nodes/failover.md) |
| **path_executor** | Execute a planned path | [📖 View](./nodes/path-executor.md) |

## 🔧 Tools

External tools and integrations.

| Tool | Purpose | Documentation |
|------|---------|---------------|
| **duckduckgo** | Web search | [📖 View](./tools/duckduckgo.md) |
| **rag** | Retrieval-Augmented Generation node | [📖 View](./tools/rag.md) |

## Quick Reference by Use Case

### Question Answering
- `openai-answer` - Generate answers
- `memory` (read) - Search knowledge base
- `duckduckgo` - Web search
- `rag` - Knowledge base Q&A

### Decision Making
- `openai-binary` - Complex true/false
- `openai-classification` - Categorization
- `binary` - Simple checks
- `router` - Route based on decisions
- `plan_validator` - Validate execution paths

### Content Processing
- `openai-answer` - Content generation
- `local_llm` - Private processing
- `validate_and_structure` - Validation
- `loop` - Iterative improvement

### Workflow Control
- `router` - Conditional branching
- `fork` + `join` - Parallel processing
- `loop` - Iterative refinement
- `failover` - Error handling
- `graph-scout` - Dynamic routing
- `plan_validator` - Path validation and critique

### Memory & Storage
- `memory` (read) - Semantic search
- `memory` (write) - Store memories
- Memory presets - Pre-configured settings

### Search & Retrieval
- `duckduckgo` - Near real-time web search (depends on API)
- `rag` - Document Q&A
- `memory` (read) - Semantic memory search

## Quick Start Examples

### Simple Q&A
```yaml
orchestrator:
  id: simple-qa
  strategy: sequential
  agents: [answer]

agents:
  - id: answer
    type: openai-answer
    model: gpt-4o
    prompt: "{{ input }}"
```

### Memory-First Pattern
```yaml
orchestrator:
  id: memory-first
  strategy: sequential
  agents: [memory_search, needs_web, router]

agents:
  - id: memory_search
    type: memory
    namespace: knowledge
    config:
      operation: read
      limit: 10
      similarity_threshold: 0.8
    prompt: "{{ input }}"
    
  - id: needs_web
    type: openai-binary
    prompt: |
      Memory: {{ previous_outputs.memory_search }}
      Question: {{ input }}
      Needs web search?
    
  - id: router
    type: router
    params:
      decision_key: needs_web
      routing_map:
        "true": [web_search, answer]
        "false": [answer_from_memory]
```

### Parallel Analysis
```yaml
orchestrator:
  id: parallel-analysis
  strategy: sequential
  agents: [fork_analysis, sentiment, topic, quality, join_results]

agents:
  - id: fork_analysis
    type: fork
    targets:
      - [sentiment]
      - [topic]
      - [quality]
    mode: parallel
  
  - id: sentiment
    type: openai-classification
    options: [positive, negative, neutral]
    prompt: "{{ input }}"
  
  - id: topic
    type: openai-classification
    options: [tech, business, science]
    prompt: "{{ input }}"
  
  - id: quality
    type: openai-answer
    prompt: "Rate quality: {{ input }}"
  
  - id: join_results
    type: join
    prompt: "Combine: {{ previous_outputs }}"
```

### Iterative Improvement
```yaml
orchestrator:
  id: iterative-improvement
  strategy: sequential
  agents: [improvement_loop]

agents:
  - id: improvement_loop
    type: loop
    max_loops: 5
    score_threshold: 0.85
    score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
    internal_workflow:
      orchestrator:
        id: improvement-cycle
        strategy: sequential
        agents: [improver, scorer]
      agents:
        - id: improver
          type: openai-answer
          prompt: "Improve: {{ input }}"
        - id: scorer
          type: openai-answer
          prompt: "Rate: {{ previous_outputs.improver }} SCORE: X.XX"
```

## Configuration Patterns

### Memory Setup (RedisStack)
```yaml
orchestrator:
  memory:
    enabled: true
    backend: redisstack  # 100x faster
    config:
      redis_url: redis://localhost:6380/0
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2
      default_long_term_hours: 168
```

### Agent with Memory Preset
```yaml
- id: semantic_processor
  type: local_llm
  memory_preset: "semantic"  # 30 days, optimized for facts
  prompt: "{{ input }}"
```

### Resilient Execution
```yaml
- id: resilient_task
  type: failover
  children:
    - id: try_local
      type: local_llm
    - id: use_cloud
      type: openai-answer
```

## Performance Tips

### Speed Optimization
1. Use `redisstack` backend for 100x faster memory
2. Cache frequent queries in memory
3. Use `local_llm` for privacy and speed
4. Set appropriate timeouts per agent
5. Enable parallel processing with `fork`

### Cost Optimization
1. Use `local_llm` for non-critical tasks
2. Cache results in memory to reduce API calls
3. Use `gpt-3.5-turbo` for simple tasks
4. Implement failover: local → cheap cloud → expensive cloud

### Quality Optimization
1. Use `loop` for iterative improvement
2. Enable cognitive extraction to learn from iterations
3. Implement validation with `validate_and_structure`
4. Use `graph-scout` for intelligent routing
5. Combine multiple models with `fork` + `join`

## Common Workflows

### 1. Intelligent Q&A System
```
memory_reader → binary_check → router → [web_search OR answer_from_memory] → memory_writer
```

### 2. Content Quality Pipeline
```
fork[sentiment, quality, safety] → join → validate → loop[improve] → publish
```

### 3. Research & Synthesis
```
fork[memory, web, rag] → join → analyze → loop[refine] → structure → store
```

### 4. Multi-Agent Society
```
loop[fork[agent1, agent2, agent3] → join → moderator → score]
```

## Environment Variables

```bash
# Memory backend (required)
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6380/0

# Memory decay
export ORKA_MEMORY_DECAY_ENABLED=true
export ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2
export ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168

# LLM providers
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

## CLI Commands

```bash
# Start Redis/RedisStack
orka-start

# Run workflow
orka run workflow.yml "input text"

# Monitor memory
orka memory watch

# Memory statistics
orka memory stats

# Cleanup expired memories
orka memory cleanup --dry-run
```

## Additional Resources

- [Getting Started Guide](./getting-started.md)
- [Memory System Guide](./MEMORY_SYSTEM_GUIDE.md)
- [YAML Configuration Guide](./YAML_CONFIGURATION.md)
- [Architecture Overview](./architecture.md)
- [Best Practices](./best-practices.md)
- [Troubleshooting](./troubleshooting.md)
- [Example Workflows](../examples/README.md)

**Need Help?**
- 📖 [Full Documentation](https://orkacore.com/docs)
- 💬 [GitHub Issues](https://github.com/marcosomma/orka-reasoning/issues)
- 🎯 [Examples Directory](../examples/)

