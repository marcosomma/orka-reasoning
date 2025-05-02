[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)


# OrKa Security & Privacy Considerations

## Redis/Kafka
- Use TLS for Redis if deployed publicly
- Enable ACLs (requirepass + role enforcement)

## LLM Requests
- Filter inputs to prevent prompt injection
- Strip PII unless opt-in (sensitive flag)

## Secrets Management
- Use `.env` file (never commit it)
- Vault integration for prod (future)

## OrKaUI/Auth
- Admin-only OrKaUI in alpha
- Future: OAuth/token-based auth for multi-user flows

[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)