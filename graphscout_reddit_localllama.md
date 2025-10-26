# GraphScout: Intelligent Routing for Local LLM Agent Workflows

## The Local LLM Orchestration Challenge

When running local models, every token matters. You can't afford to waste inference calls on irrelevant agent sequences. Static routing often over-provisions, calling agents "just in case" because the logic can't adapt to actual query content.

GraphScout provides runtime path discovery for local LLM workflows. It evaluates which agents to call based on actual input, reducing unnecessary inference overhead.

## The Token Waste Problem

Static routing with local models:

```yaml
# Always calls this sequence, regardless of query
workflow: [memory_check, web_search, analysis, synthesis, response]
```

For simple queries, you're paying for memory checks and web searches you don't need. For complex queries, you might need multiple analysis passes that aren't in the sequence.

## Dynamic Path Selection

GraphScout uses your local LLM to evaluate which agent sequence makes sense:

```yaml
- id: smart_router
  type: graph_scout
  config:
    k_beam: 5
    max_depth: 3
    evaluation_model: "local_llm"
    evaluation_model_name: "gpt-oss:20b"
    cost_budget_tokens: 1000
  prompt: "Select optimal path for: {{ input }}"
```

The system discovers available agents, simulates paths, and executes only what's needed.

## Cost Control for Local Models

**Token Budget Management**  
Set maximum tokens per path: `cost_budget_tokens: 1000`  
GraphScout filters candidates that exceed budget before evaluation

**Latency Constraints**  
Control max execution time: `latency_budget_ms: 2000`  
Important when running quantized models with variable throughput

**Beam Search**  
Configurable exploration depth prevents combinatorial explosion  
`k_beam: 3` with `max_depth: 2` keeps evaluation overhead minimal

## Works with Any Local Provider

**Ollama**:
```yaml
evaluation_model: "local_llm"
evaluation_model_name: "gpt-oss:20b"
provider: "ollama"
```

**LM Studio**, **llama.cpp**, **vLLM**: Any OpenAI-compatible endpoint

GraphScout uses your local model for path evaluation. No external API calls required for routing decisions.

## Example: Memory-Aware Local Workflow

```yaml
orchestrator:
  agents: [graph_scout, memory_reader, local_analyzer, memory_writer, response_builder]

agents:
  - id: graph_scout
    type: graph_scout
    config:
      evaluation_model: "local_llm"
      evaluation_model_name: "qwen2.5:7b"
      k_beam: 3
      cost_budget_tokens: 800
    
  - id: local_analyzer
    type: local_llm
    model: "gpt-oss:20b"
    provider: ollama
    
  - id: response_builder
    type: local_llm
    model: "qwen2.5:7b"
    provider: ollama
```

GraphScout automatically orders memory operations (readers first, writers last) and only calls the analyzer when needed.

## Real Benefit: Adaptive Token Usage

Instead of fixed sequences that waste tokens on unnecessary operations, GraphScout adapts to query complexity:

- Simple query: Skip memory check, direct to response builder
- Factual query: Memory check -> web search -> response
- Complex query: Memory -> multiple analysis passes -> synthesis -> write back

The routing intelligence runs locally on your own hardware.

## Privacy First

All routing decisions happen locally using your models. No external API calls for path selection. Complete control over execution.

Works with RedisStack for local vector storage or in-memory backends. Entire reasoning workflow stays on your infrastructure.

## Performance Notes

Tested with models from 7B to 70B parameters. Works well with quantized models (Q4, Q5). Path evaluation adds ~0.5-2s overhead depending on model size, but saves tokens by avoiding unnecessary agent calls.

Part of OrKa-Reasoning v0.9.3+  
GitHub: [github.com/marcosomma/orka-reasoning](https://github.com/marcosomma/orka-reasoning)  
Apache 2.0 licensed, self-hostable

