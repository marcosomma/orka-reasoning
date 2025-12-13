# RAG (Retrieval-Augmented Generation)

**Type:** `rag`

## Overview

RAG is implemented by `RAGNode` and is configured via **top-level fields** on the agent entry.

Older examples that put RAG settings under `params:` are not compatible with the current `AgentFactory` wiring.

## Basic configuration

```yaml
- id: knowledge_qa
  type: rag
  top_k: 10
  score_threshold: 0.75
  timeout: 30.0
  max_concurrency: 10
  prompt: "Answer: {{ input }}"
```

Supported fields (non-exhaustive):
- `top_k` (default `5`)
- `score_threshold` (default `0.7`)
- `timeout` (default `30.0`)
- `max_concurrency` (default `10`)

See also:
- [YAML Configuration](../YAML_CONFIGURATION.md)
