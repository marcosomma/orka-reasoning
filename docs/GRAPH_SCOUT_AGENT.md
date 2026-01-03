# GraphScout Agent

GraphScout is OrKa's dynamic routing agent.

In YAML, configure it as `type: graph-scout` (hyphen). Configuration is passed as **top-level fields** on the agent entry (not nested under `config`).

## Basic configuration

```yaml
orchestrator:
  id: my_workflow
  strategy: sequential
  agents: [graph_scout]

agents:
  - id: graph_scout
    type: graph-scout
    k_beam: 3
    max_depth: 2
    commit_margin: 0.15
    cost_budget_tokens: 800
    latency_budget_ms: 1200
    prompt: "Find the best path to handle: {{ input }}"
```

## Common settings

Non-exhaustive list of commonly used fields:

- `k_beam`
- `max_depth`
- `commit_margin`
- `cost_budget_tokens`
- `latency_budget_ms`

See also:
- [YAML Configuration](YAML_CONFIGURATION.md)
- [GraphScout Execution Modes](GRAPHSCOUT_EXECUTION_MODES.md)
- Examples: [examples/graph_scout_example.yml](../examples/graph_scout_example.yml), [examples/graph_scout_dynamic.yml](../examples/graph_scout_dynamic.yml)
---
← [Memory Agents](memory-agents-guide.md) | [📚 INDEX](index.md) | [Best Practices](best-practices.md) →
