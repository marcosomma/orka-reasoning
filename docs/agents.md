[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# Agent Types in OrKa ***(Patent Pending)***

In OrKa, **agents** are modular processing units that receive input and return structured output — all orchestrated via a declarative YAML configuration.

Agents can represent different cognitive functions: classification, decision-making, web search, conditional routing, and more.

The OrKa framework uses a unified agent base implementation that supports both modern asynchronous patterns and legacy synchronous patterns for backward compatibility.

---

## 🧱 Core Agent Types

---

### 🔘 `binary`

Returns a boolean (`"true"` or `"false"` as strings) based on a question or statement.

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
    "true": [search, validate_fact]
    "false": [validate_fact]
```

---

## 🤖 LLM Agents

OrKa includes built-in integrations with large language models:

### 🧠 `openai-answer`

Uses OpenAI models to generate answers based on a prompt and input data.

**Example config:**

```yaml
- id: generate_answer
  type: openai-answer
  prompt: >
    Generate a detailed answer about {{topic}} considering {{context}}.
  queue: orka:openai_answer
  model: gpt-3.5-turbo
  temperature: 0.7
```

### 🔄 `openai-binary`

Leverages OpenAI models to make binary decisions (yes/no).

**Example config:**

```yaml
- id: fact_check
  type: openai-binary
  prompt: >
    Is the following statement correct? Answer with yes or no only.
  queue: orka:openai_binary
```

### 📊 `openai-classification`

Uses OpenAI models to classify inputs into predefined categories.

**Example config:**

```yaml
- id: classify_topic
  type: openai-classification
  prompt: >
    Classify the following text into one of these categories.
  options: [technology, science, politics, entertainment, sports]
  queue: orka:openai_classification
```

## 🛠 Custom Agents

OrKa supports two patterns for creating custom agents:

### Modern Async Pattern (Recommended)

```python
from orka.agents.base_agent import BaseAgent

class MyCustomAgent(BaseAgent):
    async def _run_impl(self, ctx):
        # Process input asynchronously
        input_data = ctx.get("input")
        result = await self.process(input_data)
        return result
```

### Legacy Sync Pattern (Backward Compatibility)

```python
from orka.agents.base_agent import LegacyBaseAgent  # Updated import path

class MyCustomAgent(LegacyBaseAgent):
    def run(self, input_data):
        # Process input synchronously
        return {"result": "custom processing"}
```

See [Extending Agents](./extending-agents.md) for more details.

---

## 🚦 Agent Execution Rules

- All agents receive either a raw `input_data` or a `ctx` with input and metadata
- Outputs are standardized with status, result, and error information
- Modern agents support concurrency control and timeout handling
- Routing agents modify the orchestration queue at runtime

---

## 💡 Coming Soon

- `validator` agents
- `summarizer`
- `chain-of-thought` agents
- `memory` agents (stateful, historical)

---

Agents are the core cognitive unit of OrKa — build your system by composing them.

[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
