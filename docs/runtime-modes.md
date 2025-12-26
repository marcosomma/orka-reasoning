[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📝 YAML Configuration](./YAML_CONFIGURATION.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# OrKa Runtime Modes

## Sequential (Default)
Agents are executed in order. Ideal for deterministic flows.

## Router (Dynamic)
A `router` agent decides the next agent(s) based on prior outputs. Enables branching and fallback.

## Decision Tree (ORCA-CORE)
Dynamic trees based on cascading conditions. Defined via nested route maps and fallback logic. Requires private repo.

## Retry/Fallback (ORCA-CORE)
Define retry chains per agent. Useful for failure tolerance:
```yaml
  fallback:
    - search_agent
    - final_output
```

## Streaming (live)
The streaming regime adds an event-driven runtime with low-latency refreshes. It is transport-agnostic: use it for text-only chat or with an external voice stack. Voice is optional metadata inside invariants and is not required for operation.

- Enable with environment variable ORKA_ENABLE_STREAMING=1.
- Start with: `orka streaming run <config> --session <id>`.
- YAML must set orchestrator.mode: streaming and can define executor_invariants and prompt_budgets.
