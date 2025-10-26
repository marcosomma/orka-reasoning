# GraphScout: Dynamic Multi-Agent Path Selection for Reasoning Workflows

## The Multi-Agent Routing Problem

Complex reasoning workflows require routing across multiple specialized agents. Traditional approaches use static decision trees. Hard-coded logic that breaks down as agent count and capabilities grow.

The maintenance burden compounds: every new agent requires routing updates, every capability change means configuration edits, every edge case adds another conditional branch.

GraphScout solves this by discovering and evaluating agent paths at runtime.

## Static vs. Dynamic Routing

**Static approach:**
```yaml
routing_map:
  "factual_query": [memory_check, web_search, fact_verification, synthesis]
  "analytical_query": [memory_check, analysis_agent, multi_perspective, synthesis]
  "creative_query": [inspiration_search, creative_agent, refinement, synthesis]
```

**GraphScout approach:**
```yaml
- type: graph_scout
  config:
    k_beam: 5
    max_depth: 3
    commit_margin: 0.15
  prompt: "Find optimal agent sequence for: {{ input }}"
```

GraphScout discovers available agents, evaluates multi-hop paths, and selects based on actual query content.

## Multi-Stage Evaluation

**Stage 1: Graph Introspection**  
Discovers reachable agents, builds candidate paths up to max_depth

**Stage 2: Path Scoring**  
- LLM-based relevance evaluation
- Heuristic scoring (cost, latency, capabilities)
- Safety assessment
- Budget constraint checking

**Stage 3: Decision Engine**  
- **Commit**: Single best path with high confidence
- **Shortlist**: Multiple viable paths, execute sequentially
- **Fallback**: No suitable path, use response builder

**Stage 4: Execution**  
Automatic memory agent ordering (readers -> processors -> writers)

## Multi-Agent Orchestration Features

**Path Discovery**: Finds multi-agent sequences, not just single-step routing  
**Memory Integration**: Positions memory read/write operations automatically  
**Budget Awareness**: Respects token and latency constraints  
**Beam Search**: k-beam exploration with configurable depth  
**Safety Controls**: Enforces safety thresholds and risk assessment

## Real-World Use Cases

**Adaptive RAG**: Dynamically route between memory retrieval, web search, and knowledge synthesis  
**Multi-Perspective Analysis**: Select agent sequences based on query complexity  
**Fallback Chains**: Automatically discover backup paths when primary agents fail  
**Cost Optimization**: Choose agent paths within budget constraints

## Configuration Example

```yaml
- id: intelligent_router
  type: graph_scout
  config:
    k_beam: 7
    max_depth: 4
    commit_margin: 0.1
    cost_budget_tokens: 2000
    latency_budget_ms: 5000
    safety_threshold: 0.85
    score_weights:
      llm: 0.6
      heuristics: 0.2
      cost: 0.1
      latency: 0.1
```

## Why It Matters for Agent Systems

Removes brittle routing logic. Agents become modular components that the system discovers and composes at runtime. Add capabilities without changing orchestration code.

It's the same pattern microservices use for dynamic routing, applied to agent reasoning workflows.

Part of OrKa-Reasoning v0.9.3+  
GitHub: [github.com/marcosomma/orka-reasoning](https://github.com/marcosomma/orka-reasoning)

