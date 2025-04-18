[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md)

# Agent Types in OrKa ***(Patent Pending)***

In OrKa, **agents** are modular processing units that receive input and return structured output — all orchestrated via a declarative YAML configuration.

Agents can represent different cognitive functions: classification, decision-making, web search, conditional routing, and more.

---

## 🧱 Core Agent Types

---

### 🔘 `binary`

Returns a boolean (`True` or `False`) based on a question or statement.

**Use case:**  
Fact checking, condition validation, flag triggering.

**Example config:**

```yaml
- id: is_fact
  type: binary
  prompt: >
    Is the following statement factually accurate? Return TRUE or FALSE.
  queue: orka:binary_check
```

---

### 🧾 `classification`

Returns one of several predefined options.

**Use case:**  
Topic detection, sentiment classification, domain filtering.

**Example config:**

```yaml
- id: topic
  type: classification
  prompt: >
    Classify this into one of the following: [science, history, tech]
  options: [science, history, tech]
  queue: orka:classify
```

---

### 🌐 `duckduckgo` / `google-search`

Performs web search and returns snippets for downstream agents.

**Use case:**  
Factual retrieval, search-enhanced answers, fallback evidence.

**Example:**

```yaml
- id: search
  type: duckduckgo
  prompt: Search the web for this input
  queue: orka:search
```

> Requires `duckduckgo-search` package or Google API key/CSE ID.

---

### 🔀 `router`

Controls flow dynamically by inspecting previous outputs and routing conditionally.

**Use case:**  
Branching logic, optional agent execution, fallback control.

**Example:**

```yaml
- id: router
  type: router
  decision_key: requires_search
  routing_map:
    true: [search, validate_fact]
    false: [validate_fact]
```

---

## 🛠 Custom Agents

You can subclass `BaseAgent` and define your own agent type:

```python
class MyCustomAgent(BaseAgent):
    def run(self, input_data):
        return {"result": "custom processing"}
```

Then reference it via `type: custom` and load dynamically via plugin hooks (planned feature).

---

## 🚦 Agent Execution Rules

- All agents receive either a raw `input_data` or a `payload` with previous outputs.
- Outputs are logged to Redis stream via `MemoryLogger`
- Routing agents modify the orchestration queue at runtime

---

## 💡 Coming Soon

- `validator` agents
- `summarizer`
- `chain-of-thought` agents
- `memory` agents (stateful, historical)

---

Agents are the core cognitive unit of OrKa — build your system by composing them.

[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md)
