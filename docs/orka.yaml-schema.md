[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# orka.yaml Schema

## Top-Level Fields
| Field         | Type   | Required | Description                      |
|---------------|--------|----------|----------------------------------|
| `meta`        | dict   | No       | Flow version, author, etc.       |
| `orchestrator`| dict   | Yes      | ID, mode                         |
| `agents`      | list   | Yes      | List of agent configs            |

## Agent Fields
| Field           | Type   | Required | Description                        |
|-----------------|--------|----------|------------------------------------|
| id              | string | yes      | Unique agent name                  |
| type            | string | yes      | One of: binary, classification, local_llm, openai-answer, openai-binary, openai-classification, validate_and_structure, duckduckgo, router, fork, join, loop, failover, failing, graph-scout, memory |
| prompt          | string | depends  | LLM prompt (required for most agents) |
| queue           | string | optional | Redis stream name                  |
| options         | list   | depends  | For classification agents          |
| params          | dict   | depends  | Node-specific parameters           |
| config          | dict   | depends  | Agent configuration (memory agents) |
| memory_preset   | string | depends  | Memory preset for memory agents    |
| routes          | dict   | depends  | Routing targets (router nodes)     |
| fallback        | list   | optional | Retry chain                        |
| timeout         | float  | optional | Maximum execution time in seconds (default: 30.0) |
| max_concurrency | int    | optional | Maximum parallel executions (default: 10) |

## Modern Agent Configuration Example

```yaml
- id: fact_checker
  type: binary
  prompt: Is the following statement factually correct?
  queue: orka:fact_check
  timeout: 45.0  # Longer timeout for complex fact checking
  max_concurrency: 5  # Limit parallel executions
```

## Legacy Agent Configuration Example

```yaml
- id: simple_classifier
  type: classification
  prompt: Classify this input
  options: [a, b, c]
  queue: orka:classify
```

[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
