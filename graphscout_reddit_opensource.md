# GraphScout: Runtime Path Discovery for Open-Source AI Workflows

## Why Static Routing Doesn't Scale

Most AI orchestration frameworks lock you into static routing. You define agent sequences in configuration files, hard-code decision logic, and redeploy every time requirements change. The routing logic becomes unmaintainable.

This is a solved problem in distributed systems. Service discovery replaced hard-coded service endpoints decades ago. GraphScout brings the same pattern to AI agent orchestration.

## The Problem with Manual Routing

Typical static configuration:

```yaml
- id: manual_router
  type: router
  params:
    routing_map:
      "question": [search_agent, answer_agent]
      "analysis": [analyzer_agent, summarizer_agent]
```

Now add edge cases. Add memory integration. Add cost constraints. The configuration becomes brittle and hard to maintain.

## Runtime Path Discovery

GraphScout inspects your workflow graph at runtime, discovers available agents, evaluates possible paths, and executes the optimal sequence.

```yaml
- id: dynamic_router
  type: graph_scout
  config:
    k_beam: 5
    max_depth: 3
  prompt: "Find the best path to handle: {{ input }}"
```

Add new agents and GraphScout automatically considers them. No routing updates required.

## How It Works

1. **Graph Introspection**: Discovers reachable agents from current position
2. **Path Evaluation**: Simulates paths using dry-run engine, scores using LLM + heuristics
3. **Decision Making**: Commits to single path (high confidence) or shortlist (multiple options)
4. **Execution**: Runs selected sequence with automatic memory agent ordering

Evaluation considers relevance, cost, latency, and safety. Budget constraints enforced. Full trace logging for observability.

## Value Proposition

**Reduces maintenance**: Add agents without updating routing logic  
**Context-aware**: Routes based on actual content, not keywords  
**Handles complexity**: Multi-agent sequences, memory integration, budget awareness  
**Traceable**: Every decision includes reasoning and evaluation traces

It's not revolutionary. It's applying service discovery patterns to agent orchestration.

## Open Source

Part of OrKa-Reasoning v0.9.3+, Apache 2.0 licensed.  
Repo: [github.com/marcosomma/orka-reasoning](https://github.com/marcosomma/orka-reasoning)  
Docs: Full configuration guide and examples included

**Fully self-hostable**: Works with local open-source models via Ollama, llama.cpp, LM Studio, vLLM, or any OpenAI-compatible endpoint. No proprietary APIs required.

YAML-based configuration, Python-based execution. RedisStack backend for vector storage (also open source).

