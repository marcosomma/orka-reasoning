# DuckDuckGo Search Tool

**Type:** `duckduckgo`

## Overview

Performs web searches using DuckDuckGo via the optional `ddgs` dependency.

The current code path uses the agent `prompt` as the query. YAML `params` shown in older docs/examples are **not consumed** by the implementation.

## Basic configuration

```yaml
- id: web_search
  type: duckduckgo
  prompt: "{{ input }}"
```

## Common pattern: search → answer

```yaml
orchestrator:
  id: web-qa
  strategy: sequential
  agents: [web_search, answer]

agents:
  - id: web_search
    type: duckduckgo
    prompt: "{{ input }}"

  - id: answer
    type: openai-answer
    prompt: |
      Based on these search results:
      {{ previous_outputs.web_search }}

      Question: {{ input }}

      Provide a concise, accurate answer.
```

See also:
- [YAML Configuration](../YAML_CONFIGURATION.md)
