[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# OrKa FAQ

### How is this different from LangChain?
LangChain wraps LLM APIs with logic. OrKa defines cognitive structure in YAML + has full introspection.

### Why YAML?
Declarative, composable, versionable. Think: Terraform for thought.

### What happens if an agent fails?
It logs the error. You can define `fallback:` agents to take over. No silent failures.

### Can I run this with local LLMs?
Yes. Via LiteLLM proxy, run with Ollama, LM Studio, Claude, OpenRouter.

### What about security?
Redis/Kafka can be encrypted. PII filters recommended. OrKaUI will support auth soon.

[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
