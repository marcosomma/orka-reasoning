[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# orka.yaml Schema

## Top-Level Fields
| Field         | Type   | Required | Description                      |
|---------------|--------|----------|----------------------------------|
| `meta`        | dict   | No       | Flow version, author, etc.       |
| `orchestrator`| dict   | Yes      | ID, mode                         |
| `agents`      | list   | Yes      | List of agent configs            |

## Agent Fields
| Field       | Type   | Required | Description                        |
|-------------|--------|----------|------------------------------------|
| id          | string | yes      | Unique agent name                  |
| type        | string | yes      | One of: binary, classification...  |
| prompt      | string | yes      | LLM prompt                         |
| queue       | string | yes      | Redis stream name                  |
| options     | list   | depends  | For classification                 |
| routes      | dict   | router   | Routing targets                    |
| fallback    | list   | optional | Retry chain                        |

[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
