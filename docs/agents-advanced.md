# Advanced Agent Reference

## Core Agent Types
| Type         | Input Format      | Output Format       | Description                          |
|--------------|-------------------|----------------------|--------------------------------------|
| binary       | string/payload    | bool (`true/false`)  | Yes/no decision                      |
| classification | string          | string (label)       | Multi-class classifier (deprecated)  |
| local_llm    | string/dict       | string               | Local LLM integration (Ollama, etc.) |
| openai-binary | string           | bool                 | LLM-powered yes/no decision          |
| openai-classification | string   | string (label)       | LLM-powered multi-class classifier   |
| openai-answer| dict/string       | string               | LLM-powered response generation      |
| validate_and_structure | dict    | structured object    | Answer validation and structuring    |
| duckduckgo   | string            | list of strings      | Web search snippets                  |

## Node Types
| Type         | Input Format      | Output Format       | Description                          |
|--------------|-------------------|----------------------|--------------------------------------|
| router       | string + context  | string (next agent)  | Branching logic control              |
| fork         | any               | parallel execution   | Parallel processing coordination     |
| join         | multiple inputs   | aggregated result    | Result aggregation from parallel paths |
| loop         | any               | iterative processing | Loop control with conditions         |
| failover     | any               | fallback result      | Error handling with fallbacks        |
| failing      | any               | controlled failure   | Validation gate with failure conditions |
| graph-scout  | string/dict       | path execution       | Intelligent workflow path discovery  |
| memory       | any               | memory operation     | Memory read/write with presets       |
| rag          | string/dict       | augmented response   | Retrieval-augmented generation (coming soon) |

---
## Error Handling
- All agents return standardized output formats.
- Use `MemoryLogger` to log status and track execution progress.
- Malformed outputs will raise orchestration halt unless fallback is defined.
- LLM agents gracefully handle API errors with configurable fallbacks.

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
# 🔍 OpenAI Classification Agent Example

```yaml
- id: initial_classify
  type: openai-classification
  prompt: >
    Classify this input "{{ input }}".
  options: [tech, science, history, nonsense]
  queue: orka:domain
  model: gpt-3.5-turbo
  temperature: 0.7
```

Used for multi-class reasoning tasks. Outputs one label from predefined options.

---
# ✅ OpenAI Binary Agent Example

```yaml
- id: search_required
  type: openai-binary
  prompt: >
    Is "{{ input }}" a question that requires deep internet research?
  queue: orka:need_search
  model: gpt-3.5-turbo
  temperature: 0.2
```

Evaluates a yes/no question using LLM reasoning. Returns a strict boolean value (true/false).

---
# 🧩 OpenAI Answer Builder Example

```yaml
- id: final_builder_true
  type: openai-answer
  prompt: |
    Build a detailed answer combining:
    - Classification result: {{ previous_outputs.initial_classify }}
    - Search result: {{ previous_outputs.failover_search }}
  queue: orka:final_output
  model: gpt-4
  temperature: 0.7
```

Builds a composed final output using previous agent results, leveraging OpenAI's capabilities.

---
← [Agents](agents.md) | [📚 INDEX](INDEX.md) | [Extending Agents](extending-agents.md) →
