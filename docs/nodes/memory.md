# Memory (Agent)

Unified memory is configured via `type: memory`.

- Use `config.operation: read` to retrieve memory.
- Use `config.operation: write` to store memory.

> For backend setup, decay, and presets, see [MEMORY_SYSTEM_GUIDE.md](../MEMORY_SYSTEM_GUIDE.md) and [MEMORY_BACKENDS.md](../MEMORY_BACKENDS.md).

## Read example

```yaml
orchestrator:
  id: memory-read
  strategy: sequential
  agents: [mem_read]

agents:
  - id: mem_read
    type: memory
    prompt: "Find relevant context for: {{ input }}"
    config:
      operation: read
      # Read options are taken from `config`
      limit: 5
      similarity_threshold: 0.25
```

## Write example

```yaml
orchestrator:
  id: memory-write
  strategy: sequential
  agents: [mem_write]

agents:
  - id: mem_write
    type: memory
    prompt: "Store this: {{ input }}"
    config:
      operation: write

    # Write options are top-level fields (not nested under `config`)
    namespace: default
    metadata:
      source: "workflow"
```

## Notes

- `prompt` is the content used for the read query or write payload (after template rendering).
- The current codebase treats read and write settings differently (read options inside `config`, write options as top-level fields).
