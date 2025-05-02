[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# Advanced Agent Reference

## Core Agent Types
| Type         | Input Format      | Output Format       | Description                          |
|--------------|-------------------|----------------------|--------------------------------------|
| binary       | string/payload    | bool (`true/false`)  | Yes/no decision                      |
| classification | string          | string (label)       | Multi-class classifier               |
| duckduckgo   | string            | list of strings      | Search snippets                      |
| router       | string + context  | string (next agent)  | Branching logic control              |
| builder      | dict              | string               | Compose structured final response    |

---
## Error Handling
- All agents return JSON.
- Use `MemoryLogger` to log status.
- Malformed outputs will raise orchestration halt unless fallback is defined.

---
# 🧠 Orchestrator Example

```yaml
orchestrator:
  id: full_nodes_test_orchestrator
  strategy: parallel
  queue: orka:test
  agents:
    - initial_classify
    - search_required
    - fork_parallel_checks
    - join_parallel_checks
    - router_search_path
    - final_router
```

This defines the core orchestration logic and agent order. Strategy `parallel` allows fork/join flows.

---
# 🔀 Router Node Example

```yaml
- id: router_search_path
  type: router
  params:
    decision_key: search_required
    routing_map:
      true: ["failover_search", "final_router"]
      false: ["info_completed", "final_router"]
```

Routes execution based on the value of a prior output.

---
# 🌿 Fork Node Example

```yaml
- id: fork_parallel_checks
  type: fork
  targets:
    - - topic_validity_check 
      - topic_depth_estimation
      - topic_final_validation
    - [summary_category_check, summary_needs_elaboration, summary_final_approval]
```

Splits execution into parallel branches. Each list is a sequential sub-branch.

---
# 🔗 Join Node Example

```yaml
- id: join_parallel_checks
  type: join
  group: fork_parallel_checks
```

Waits for all branches from `fork_parallel_checks` to finish before continuing.

---
# 🚨 Failover Node Example

```yaml
- id: failover_search
  type: failover
  children:
    - id: backup_duck_search
      type: duckduckgo
      prompt: Perform a backup web search for "{{ input }}"
      queue: orka:duck_backup
    - id: backup_duck_search_fallback
      type: duckduckgo
      prompt: Perform a backup web search for "{{ input }}"
      queue: orka:duck_backup_fallback
```

Tries child agents in order. If the first fails, moves to the next.

---
# 🔍 Classification Agent Example

```yaml
- id: initial_classify
  type: openai-classification
  prompt: >
    Classify this input "{{ input }}".
  options: [tech, science, history, nonsense]
  queue: orka:domain
```

Used for multi-class reasoning tasks. Outputs one label from predefined options.

---
# ✅ Binary Agent Example

```yaml
- id: search_required
  type: openai-binary
  prompt: >
    Is "{{ input }}" a question that requires deep internet research?
  queue: orka:need_search
```

Evaluates a yes/no question. Returns `true` or `false`.

---
# 🧩 Final Answer Builder Example

```yaml
- id: final_builder_true
  type: openai-answer
  prompt: |
    Build a detailed answer combining:
    - Classification result: {{ previous_outputs.initial_classify }}
    - Search result: {{ previous_outputs.failover_search }}
  queue: orka:final_output
```

Builds a composed final output using previous agent results.


[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
