[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

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

### Should I use sync or async agents?
Use the modern async pattern for new development. The legacy sync pattern is provided for backward compatibility with existing code. The async pattern offers better concurrency control, timeout handling, and resource management.

### Do my existing agents still work?
Yes. OrKa maintains backward compatibility with existing agents through the `LegacyBaseAgent` compatibility layer. Your existing code will continue to work without modification.

### How do I migrate from sync to async agents?
Convert your `run(input_data)` method to an async `_run_impl(ctx)` method. Access input via `ctx.get("input")` and return results directly. See [Extending Agents](./extending-agents.md) for examples.

### What's the difference between "true"/"false" strings and boolean values?
Modern agents use string values ("true"/"false") for binary decisions to maintain consistency across different agent implementations. This allows for more reliable routing and decision logic.

[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
