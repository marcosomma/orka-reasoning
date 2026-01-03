# OrKa Security & Privacy Considerations

> **Last Updated:** 03 January 2026  
> **Status:** 🟢 Current  
> **Related:** [Best Practices](best-practices.md) | [Memory Backends](MEMORY_BACKENDS.md) | [YAML Configuration](YAML_CONFIGURATION.md) | [index](index.md)

## Redis/RedisStack
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
