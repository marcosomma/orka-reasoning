# GraphScout Agent

GraphScout is OrKa's dynamic routing agent.

In YAML, configure it as `type: graph-scout` (hyphen) and pass its settings as **top-level fields** on the agent (not nested under `config`).

## Basic Configuration

```yaml
orchestrator:
  id: my_workflow
  strategy: sequential
  agents: [graph_scout]

agents:
  - id: graph_scout
    type: graph-scout
    k_beam: 5
    max_depth: 3
    commit_margin: 0.15
    prompt: "Find the best path to handle: {{ input }}"
```

See also:
- [YAML Configuration](YAML_CONFIGURATION.md)
- [GraphScout Execution Modes](GRAPHSCOUT_EXECUTION_MODES.md)
- Examples: [examples/graph_scout_example.yml](../examples/graph_scout_example.yml), [examples/graph_scout_dynamic.yml](../examples/graph_scout_dynamic.yml)

<!--

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Decision Types](#decision-types)
- [Memory Agent Routing](#memory-agent-routing)
- [Examples](#examples)
- [Advanced Configuration](#advanced-configuration)
- [Performance Tuning](#performance-tuning)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

GraphScout provides dynamic routing as an alternative to static workflow definitions. It analyzes your workflow graph at runtime, discovers possible execution paths, evaluates them using heuristics and LLM-based scoring, and executes selected agent sequences.

### Before GraphScout (Static Routing)
```yaml
# Manual routing - predefined paths
- id: manual_router
  type: router
  params:
    decision_key: query_type
    routing_map:
      "question": [search_agent, answer_agent]
      "analysis": [analyzer_agent, summarizer_agent]
```

### After GraphScout (Dynamic Routing)
```yaml
# Dynamic routing - runtime path selection
- id: dynamic_router
  type: graph_scout
  config:
    k_beam: 5
    max_depth: 3
    commit_margin: 0.15
  prompt: "Find the best path to handle: {{ input }}"
```

---

## Key Features

### 🧭 **Path Discovery**
- **Graph Introspection**: Discovers all reachable paths through your workflow
- **Multi-hop Sequences**: Finds multi-agent sequences, not just single-step routing
- **Runtime Adaptation**: Adapts to workflow changes without manual reconfiguration

### 🎯 **LLM-Based Evaluation**
- **LLM Scoring**: Uses language models to evaluate path effectiveness
- **Heuristic Scoring**: Combines cost, latency, and capability analysis
- **Confidence-based Decisions**: Makes commit/shortlist decisions based on confidence levels

### 🧠 **Memory Agent Ordering**
- **Memory Agent Positioning**: Positions memory agents in execution order
  - `MemoryReaderNode` → Beginning of execution path
  - `MemoryWriterNode` → End of execution path
- **Operation-Aware Logic**: Differentiates read vs write operations for sequencing

### ⚡ **Performance Configuration**
- **Budget Control**: Respects token and latency budgets
- **Safety Assessment**: Evaluates path safety and reliability
- **Beam Search**: Uses k-beam search for efficient path exploration

---

## How It Works

GraphScout operates through a multi-stage process:

### 1. **Graph Introspection**
```
Input Query → Graph Analysis → Path Discovery
```
- Analyzes the current workflow graph structure
- Discovers all reachable agents from the current position
- Builds candidate paths up to `max_depth` levels deep

### 2. **Path Evaluation**
```
Candidate Paths → Simulation → Scoring → Ranking
```
- Simulates each path execution using the DryRunEngine
- Evaluates paths using heuristics and LLM-based scoring
- Scores based on relevance, cost, latency, and safety

### 3. **Decision Making**
```
Ranked Paths → Decision Engine → Execution Plan
```
- **Commit Next**: High confidence in single best path
- **Shortlist**: Multiple good options, execute sequentially
- **No Path**: No suitable path found, fallback to response builder

### 4. **Agent Execution**
```
Execution Plan → Memory Ordering → Agent Sequence → Results
```
- Applies memory agent ordering logic
- Executes the selected agent sequence
- Handles results and continues workflow

---

## Configuration

### Basic Configuration

```yaml
- id: my_graph_scout
  type: graph_scout
  config:
    k_beam: 5                    # Number of top paths to consider
    max_depth: 3                 # Maximum path depth to explore
    commit_margin: 0.15          # Confidence margin for commit decisions
    cost_budget_tokens: 1000     # Token budget limit
    latency_budget_ms: 2000      # Latency budget in milliseconds
    safety_threshold: 0.8        # Minimum safety score (0.0-1.0)
  prompt: "Find optimal path for: {{ input }}"
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `k_beam` | int | 3 | Number of top candidate paths to evaluate |
| `max_depth` | int | 2 | Maximum depth for path discovery |
| `commit_margin` | float | 0.1 | Confidence margin for commit vs shortlist decisions |
| `cost_budget_tokens` | int | 500 | Maximum token budget for path execution |
| `latency_budget_ms` | int | 1000 | Maximum latency budget in milliseconds |
| `safety_threshold` | float | 0.7 | Minimum safety score for path acceptance |

---

## Decision Types

GraphScout makes three types of routing decisions:

### 1. **Commit Next** - High Confidence Single Path
```json
{
  "decision_type": "commit_next",
  "target": "search_agent",
  "confidence": 0.95,
  "reasoning": "High confidence in search agent for factual query"
}
```
**When**: Clear winner with high confidence score
**Action**: Execute the single best agent immediately

### 2. **Shortlist** - Multiple Good Options
```json
{
  "decision_type": "shortlist", 
  "target": [
    {"node_id": "memory_reader", "path": ["memory_reader"]},
    {"node_id": "search_agent", "path": ["search_agent"]},
    {"node_id": "response_builder", "path": ["response_builder"]}
  ],
  "confidence": 0.75,
  "reasoning": "Multiple viable paths - executing sequence"
}
```
**When**: Multiple paths with similar scores
**Action**: Execute all agents in the shortlist sequentially

### 3. **No Path** - Fallback to Response Builder
```json
{
  "decision_type": "no_path",
  "target": "response_builder",
  "confidence": 0.3,
  "reasoning": "No suitable path found, using response builder"
}
```
**When**: No paths meet safety/budget requirements
**Action**: Fall back to response builder agent

---

## Memory Agent Routing

GraphScout includes memory agent positioning logic:

### Memory Agent Types
- **`MemoryReaderNode`**: Agents that read from memory (operation: read)
- **`MemoryWriterNode`**: Agents that write to memory (operation: write)

### Positioning Rules

```yaml
# Execution sequence is reordered:
# 1. Memory Readers (beginning)
# 2. Regular Agents (middle) 
# 3. Memory Writers (end)
# 4. Response Builder (always last)

# Example automatic sequencing:
# Input: [analyzer, memory_writer, search_agent, memory_reader]
# Output: [memory_reader, analyzer, search_agent, memory_writer, response_builder]
```

### Memory Routing Example

```yaml
orchestrator:
  id: memory_workflow
  agents: [graph_scout, memory_reader, search_agent, analyzer, memory_writer, response_builder]

agents:
  - id: graph_scout
    type: graph_scout
    config:
      k_beam: 5
      max_depth: 3
    prompt: "Route based on input: {{ input }}"
    
  - id: memory_reader
    type: memory
    memory_preset: "episodic"
    config:
      operation: read
      namespace: conversations
    prompt: "Search memory for: {{ input }}"
    
  - id: memory_writer  
    type: memory
    memory_preset: "episodic"
    config:
      operation: write
      namespace: conversations
    prompt: "Store result: {{ input }}"
```

**Result**: GraphScout automatically sequences as:
`memory_reader → search_agent → analyzer → memory_writer → response_builder`

---

## Examples

### 1. Basic Intelligent Routing

```yaml
# examples/graph_scout_basic.yml
orchestrator:
  id: basic_intelligent_routing
  agents: [graph_scout, search_agent, analyzer, response_builder]

agents:
  - id: graph_scout
    type: graph_scout
    config:
      k_beam: 3
      max_depth: 2
      commit_margin: 0.2
    prompt: "Find best path for: {{ input }}"
    
  - id: search_agent
    type: duckduckgo_tool
    prompt: "Search for: {{ input }}"
    
  - id: analyzer
    type: local_llm
    model: openai/gpt-oss-20b
    provider: lm_studio
    prompt: "Analyze: {{ input }}"
    
  - id: response_builder
    type: local_llm
    model: openai/gpt-oss-20b
    provider: lm_studio
    prompt: "Generate response: {{ input }}"
```

### 2. Memory-Aware Intelligent Routing

```yaml
# examples/graph_scout_memory_aware.yml
orchestrator:
  id: memory_aware_routing
  agents: [graph_scout, memory_reader, search_agent, analyzer, memory_writer, response_builder]

agents:
  - id: graph_scout
    type: graph_scout
    config:
      k_beam: 5
      max_depth: 3
      commit_margin: 0.15
      cost_budget_tokens: 1500
      latency_budget_ms: 3000
      safety_threshold: 0.8
    prompt: "Intelligently route with memory awareness: {{ input }}"
    
  - id: memory_reader
    type: memory
    memory_preset: "semantic"
    config:
      operation: read
      namespace: knowledge_base
      limit: 5
    prompt: "Search knowledge for: {{ input }}"
    
  - id: search_agent
    type: duckduckgo_tool
    prompt: "Web search: {{ input }}"
    
  - id: analyzer
    type: local_llm
    model: openai/gpt-oss-20b
    provider: lm_studio
    temperature: 0.3
    prompt: |
      Analyze the following information:
      Memory Results: {{ previous_outputs.memory_reader.result }}
      Search Results: {{ previous_outputs.search_agent.result }}
      Question: {{ input }}
      
  - id: memory_writer
    type: memory
    memory_preset: "semantic"
    config:
      operation: write
      namespace: knowledge_base
      vector: true
    prompt: "Store analysis: {{ previous_outputs.analyzer.result }}"
    
  - id: response_builder
    type: local_llm
    model: openai/gpt-oss-20b
    provider: lm_studio
    temperature: 0.7
    prompt: |
      Generate a comprehensive response based on:
      Analysis: {{ previous_outputs.analyzer.result }}
      Original Question: {{ input }}
```

### 3. Advanced Multi-Path Evaluation

```yaml
# examples/graph_scout_advanced.yml
orchestrator:
  id: advanced_multi_path
  agents: [graph_scout, classifier, search_agent, fact_checker, sentiment_analyzer, summarizer, response_builder]

agents:
  - id: graph_scout
    type: graph_scout
    config:
      k_beam: 7
      max_depth: 4
      commit_margin: 0.1
      cost_budget_tokens: 2000
      latency_budget_ms: 5000
      safety_threshold: 0.85
    prompt: "Find optimal multi-agent path for: {{ input }}"
    
  - id: classifier
    type: openai-classification
    options: [question, statement, request, analysis]
    prompt: "Classify input type: {{ input }}"
    
  - id: search_agent
    type: duckduckgo_tool
    prompt: "Search: {{ input }}"
    
  - id: fact_checker
    type: local_llm
    model: openai/gpt-oss-20b
    provider: lm_studio
    prompt: "Fact-check: {{ input }}"
    
  - id: sentiment_analyzer
    type: local_llm
    model: openai/gpt-oss-20b
    provider: lm_studio
    prompt: "Analyze sentiment: {{ input }}"
    
  - id: summarizer
    type: local_llm
    model: openai/gpt-oss-20b
    provider: lm_studio
    prompt: "Summarize: {{ input }}"
```

---

## Advanced Configuration

### Custom Scoring Weights

```yaml
- id: custom_graph_scout
  type: graph_scout
  config:
    k_beam: 5
    max_depth: 3
    # Advanced scoring configuration
    scoring_weights:
      llm_score: 0.6        # LLM evaluation weight
      cost_score: 0.2       # Cost efficiency weight  
      latency_score: 0.1    # Speed weight
      capability_score: 0.1 # Agent capability match weight
```

### Budget Control

```yaml
- id: budget_aware_scout
  type: graph_scout
  config:
    # Token budget management
    cost_budget_tokens: 1000
    cost_per_token: 0.0001
    
    # Latency budget management  
    latency_budget_ms: 2000
    latency_penalty_factor: 0.5
    
    # Safety requirements
    safety_threshold: 0.8
    safety_penalty_factor: 0.3
```

### LLM Evaluation Customization

```yaml
- id: custom_evaluation_scout
  type: graph_scout
  config:
    # LLM evaluation settings
    enable_llm_evaluation: true
    llm_evaluation_model: "gpt-4"
    llm_evaluation_temperature: 0.3
    llm_evaluation_prompt: |
      Evaluate path effectiveness for query: {{ query }}
      Path: {{ path }}
      Agent capabilities: {{ capabilities }}
      
      Rate from 0.0 to 1.0 and provide reasoning.
```

---

## Performance Tuning

### Optimization Guidelines

| Scenario | k_beam | max_depth | commit_margin | Notes |
|----------|--------|-----------|---------------|-------|
| **Fast Response** | 3 | 2 | 0.2 | Quick decisions, less exploration |
| **Balanced** | 5 | 3 | 0.15 | Good balance of speed and quality |
| **Thorough** | 7 | 4 | 0.1 | Comprehensive evaluation, slower |
| **Simple Workflows** | 3 | 2 | 0.25 | Fewer agents, simpler decisions |
| **Complex Workflows** | 8 | 5 | 0.05 | Many agents, detailed evaluation |

### Performance Monitoring

```bash
# Monitor GraphScout performance
orka memory watch --filter graph_scout

# Check decision statistics
redis-cli HGET orka:stats:graph_scout decisions_per_minute

# Analyze path evaluation times
orka system metrics --component graph_scout
```

### Memory Usage Optimization

```yaml
- id: memory_optimized_scout
  type: graph_scout
  config:
    # Reduce memory usage
    k_beam: 3              # Fewer candidates in memory
    max_depth: 2           # Shallower exploration
    
    # Optimize evaluation
    enable_path_caching: true
    cache_ttl_seconds: 300
    
    # Batch processing
    batch_evaluation: true
    batch_size: 5
```

---

## Troubleshooting

### Common Issues

#### 1. **No Paths Found**
```
GraphScout decision: no_path - No suitable candidates found
```
**Causes**:
- No connected agents in workflow graph
- All paths exceed budget limits
- Safety threshold too high

**Solutions**:
```yaml
# Increase budgets
cost_budget_tokens: 2000
latency_budget_ms: 5000

# Lower safety threshold
safety_threshold: 0.6

# Check graph connectivity
orka system graph --validate
```

#### 2. **Always Commits to Same Agent**
```
GraphScout always selects search_agent
```
**Causes**:
- commit_margin too high
- LLM evaluation bias
- Limited path diversity

**Solutions**:
```yaml
# Lower commit margin for more shortlists
commit_margin: 0.05

# Increase exploration
k_beam: 7
max_depth: 4

# Add path diversity scoring
enable_diversity_bonus: true
```

#### 3. **Slow Performance**
```
GraphScout taking >5 seconds per decision
```
**Causes**:
- Too many candidates (high k_beam/max_depth)
- LLM evaluation enabled with slow model
- Complex graph structure

**Solutions**:
```yaml
# Reduce exploration
k_beam: 3
max_depth: 2

# Optimize LLM evaluation
llm_evaluation_model: "gpt-3.5-turbo"
llm_evaluation_temperature: 0.1

# Enable caching
enable_path_caching: true
```

### Debug Mode

```yaml
- id: debug_graph_scout
  type: graph_scout
  config:
    debug_mode: true          # Enable detailed logging
    trace_decisions: true     # Log decision reasoning
    log_path_scores: true     # Log all path scores
```

### Validation Commands

```bash
# Validate GraphScout configuration
orka validate --agent graph_scout

# Test path discovery
orka test-paths --workflow my_workflow.yml --agent graph_scout

# Analyze decision patterns
orka analyze --component graph_scout --timeframe 1h
```

---

## Best Practices

### 1. **Workflow Design**

```yaml
# ✅ Good: Clear agent purposes
agents:
  - id: question_classifier
    type: openai-binary
    prompt: "Is this a question? {{ input }}"
    
  - id: search_specialist
    type: duckduckgo_tool
    prompt: "Search for factual information: {{ input }}"
    
  - id: analysis_expert
    type: local_llm
    prompt: "Provide detailed analysis: {{ input }}"

# ❌ Avoid: Overlapping agent capabilities
agents:
  - id: general_agent_1
    type: local_llm
    prompt: "Handle anything: {{ input }}"
    
  - id: general_agent_2  
    type: local_llm
    prompt: "Process input: {{ input }}"
```

### 2. **Configuration Tuning**

```yaml
# ✅ Start conservative, then optimize
- id: production_scout
  type: graph_scout
  config:
    # Conservative starting point
    k_beam: 3
    max_depth: 2
    commit_margin: 0.2
    
    # Monitor and adjust based on metrics
    cost_budget_tokens: 1000
    latency_budget_ms: 2000
    safety_threshold: 0.8
```

### 3. **Memory Integration**

```yaml
# ✅ Leverage memory agent routing
orchestrator:
  agents: [graph_scout, memory_reader, processor, memory_writer, response_builder]

# GraphScout automatically optimizes to:
# memory_reader → processor → memory_writer → response_builder
```

### 4. **Monitoring and Optimization**

```bash
# Regular performance monitoring
orka memory watch --component graph_scout

# Decision quality analysis
orka analyze --decisions --success-rate --timeframe 24h

# A/B testing different configurations
orka test --config-a conservative.yml --config-b aggressive.yml
```

### 5. **Error Handling**

```yaml
- id: robust_graph_scout
  type: graph_scout
  config:
    # Graceful degradation
    fallback_agent: "response_builder"
    max_retries: 3
    retry_delay_ms: 500
    
    # Error recovery
    enable_fallback_routing: true
    fallback_on_budget_exceeded: true
    fallback_on_safety_violation: true
```

---

## Integration with Other OrKa Features

### Memory Presets Integration
```yaml
- id: memory_aware_scout
  type: graph_scout
  # Automatically understands memory preset agents
  # and applies optimal routing logic
```

### Loop Node Integration
```yaml
- id: iterative_scout
  type: loop
  internal_workflow:
    orchestrator:
      agents: [graph_scout, analyzer, scorer]
    agents:
      - id: graph_scout
        type: graph_scout
        # GraphScout can be used inside loops for
        # iterative path optimization
```

### Fork/Join Integration
```yaml
- id: parallel_scout
  type: fork
  targets:
    - [graph_scout_path_a]
    - [graph_scout_path_b]
# Multiple GraphScout agents can run in parallel
# for different aspects of the same query
```

---

## Conclusion

GraphScout Agent provides dynamic routing for OrKa workflows. By discovering and evaluating paths at runtime, GraphScout eliminates the need for manual routing configuration while providing flexible workflow execution.

**Key Benefits**:
- 🧭 **Dynamic Routing**: Runtime path discovery and evaluation
- 🧠 **Memory Agent Ordering**: Positions memory agents in execution order
- ⚡ **Performance**: Budget-aware execution with safety controls
- 🔧 **Flexible**: Works with any workflow configuration
- 📊 **Observable**: Monitoring and debugging tools

Start with the basic examples and gradually explore advanced features as your workflows become more complex. GraphScout scales from simple routing decisions to sophisticated multi-agent orchestration scenarios.

---

**Next Steps**:
- Try the [basic GraphScout example](../examples/graph_scout_basic.yml)
- Explore [memory-aware routing](../examples/graph_scout_memory_aware.yml)
- Read the [performance tuning guide](#performance-tuning)
- Join the [OrKa community](https://discord.gg/orka) for support and examples
---
← [Memory Agents](memory-agents-guide.md) | [📚 INDEX](index.md) | [Best Practices](best-practices.md) →

-->
