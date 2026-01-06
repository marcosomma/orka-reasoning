# Structured Output Guide

This guide explains how to enable and use model-level structured outputs in OrKa agents.

Benefits:
- Guaranteed valid JSON from supported providers
- Schema enforcement and type coercion
- Reduced tokens and latency compared to prompt-only formatting

Modes:
- model_json: Use provider JSON mode (e.g., OpenAI response_format)
- tool_call: Use function/tool calling with JSON Schema
- prompt: Prompt injection fallback (for local models)

Orchestrator-level defaults:

You can define workflow-wide defaults that agents inherit (agents may override):

```yaml
orchestrator:
  id: my_workflow
  strategy: sequential
  agents: [answer]
  structured_output_defaults:
    enabled: true
    mode: auto
    coerce_types: true
    strict: false
```
These defaults are injected in agent context as `structured_output_defaults` and merged by each agent.

Quick start (agent-level):

```yaml
agents:
  - id: simple_answer
    type: openai-answer
    prompt: "Answer: {{ input }}"
    params:
      model: gpt-4o
      structured_output:
        enabled: true
        mode: auto
```

Custom schema (tool_call):

```yaml
params:
  structured_output:
    enabled: true
    mode: tool_call
    schema:
      required: [response]
      optional:
        confidence: number
        internal_reasoning: string
```

Provider compatibility:
- OpenAI: model_json and tool_call supported on GPT-4o family
- Anthropic: tool_call (planned)
- Local (ollama, lm_studio): prompt

PlanValidator notes:
- When model-level structured output is enforced (tool_call or model_json), the PlanValidator prompt omits redundant JSON schema instructions (skip_json_instructions), relying on model-enforced structure.
- For local providers (prompt mode), OrKa injects JSON instructions derived from the plan-validator schema and still uses schema-aware parsing as a fallback.

Examples by agent type:

- Classification (OpenAI):

```yaml
agents:
  - id: classify
    type: openai-classification
    prompt: "Classify: {{ input }}"
    params:
      categories: [positive, negative, neutral]
      structured_output:
        enabled: true
        mode: tool_call
```

- Binary decision (OpenAI):

```yaml
agents:
  - id: validate
    type: openai-binary
    prompt: "Is this valid? {{ input }}"
    params:
      structured_output:
        enabled: true
        mode: tool_call
```

- Local LLM (prompt mode):

```yaml
agents:
  - id: summarize
    type: local_llm
    prompt: "Summarize: {{ input }}"
    params:
      provider: lm_studio
      model_url: http://localhost:1234
      model: any-local-chat-model
      structured_output:
        enabled: true
        mode: prompt
        schema:
          required: [summary]
          optional:
            key_points: array
            word_count: integer
```

Troubleshooting:
- If a model ignores JSON instructions, switch to tool_call where supported
- For local models, keep instructions short and rely on schema-aware parsing

See examples/structured_output_demo.yml for a reference workflow.
