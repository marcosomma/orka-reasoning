[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# Agent Types in OrKa ***(Patent Pending)***

In OrKa, **agents** are modular processing units that receive input and return structured output — all orchestrated via a declarative YAML configuration.

Agents can represent different cognitive functions: classification, decision-making, web search, conditional routing, memory management, and more.

The OrKa framework uses a unified agent base implementation that supports both modern asynchronous patterns and legacy synchronous patterns for backward compatibility.

---

## 🧱 Core Agent Types

### 🔘 `binary`

Returns a boolean (`"true"` or `"false"` as strings) based on a question or statement.

**Use case:** Fact checking, condition validation, flag triggering.

**Example config:**
```yaml
- id: is_fact
  type: binary
  prompt: >
    Is the following statement factually accurate? Return TRUE or FALSE.
  queue: orka:binary_check
```

### 🧾 `classification`

**⚠️ DEPRECATED in v0.5.6** - Use `openai-classification` instead.

Returns one of several predefined options using simple rule-based matching.

**Use case:** Basic topic detection (legacy support only).

### 🤖 `openai-binary`

Uses OpenAI's LLM to perform binary classification with sophisticated reasoning.

**Use case:** Complex true/false decisions requiring natural language understanding.

**Example config:**
```yaml
- id: content_appropriate
  type: openai-binary
  prompt: >
    Is this content appropriate for a professional environment?
    Content: {{ input }}
  queue: orka:moderation
```

### 🎯 `openai-classification`

Uses OpenAI's LLM to classify input into multiple predefined categories.

**Use case:** Advanced topic classification, sentiment analysis, content categorization.

**Example config:**
```yaml
- id: domain_classifier
  type: openai-classification
  prompt: >
    Classify this question into one of the following domains:
  options: [science, geography, history, technology, general]
  queue: orka:classify
```

### 📝 `openai-answer`

Builds comprehensive answers using OpenAI's LLM, typically enriched with context from previous agents.

**Use case:** Question answering, content generation, summarization.

**Example config:**
```yaml
- id: answer_builder
  type: openai-answer
  prompt: |
    Based on the search results: {{ previous_outputs.web_search }}
    And classification: {{ previous_outputs.classifier }}
    Provide a comprehensive answer to: {{ input }}
  queue: orka:answer
```

### 🏠 `local_llm`

Interfaces with locally running large language models (Ollama, LM Studio, etc.) for privacy-preserving AI processing.

**Use case:** Offline processing, privacy-sensitive applications, custom model deployment.

**Supported Providers:**
- `ollama`: Native Ollama API
- `lm_studio`: LM Studio OpenAI-compatible endpoint
- `openai_compatible`: Any OpenAI-compatible API

**Example config:**
```yaml
- id: local_summarizer
  type: local_llm
  prompt: "Summarize this text: {{ input }}"
  model: "llama3.2:latest"
  model_url: "http://localhost:11434/api/generate"
  provider: "ollama"
  temperature: 0.7
  queue: orka:local
```

### ✅ `validate_and_structure`

Validates answers for correctness and structures them into memory objects with metadata.

**Use case:** Answer validation, data structuring, quality assurance.

**Example config:**
```yaml
- id: validator
  type: validate_and_structure
  prompt: "Validate and structure this answer"
  store_structure: |
    {
      "topic": "extracted topic",
      "confidence": "confidence score",
      "key_points": ["list", "of", "points"]
    }
  queue: orka:validate
```

---

## 🔧 Tools

### 🌐 `duckduckgo`

Performs real-time web search using DuckDuckGo's search engine.

**Use case:** Information retrieval, fact-checking, current events.

**Example config:**
```yaml
- id: web_search
  type: duckduckgo
  prompt: "Search for: {{ input }}"
  params:
    num_results: 5
    region: "us-en"
    safe_search: "moderate"
  queue: orka:search
```

---

## 💾 Memory Agents **⚡ 100x Faster with RedisStack HNSW**

### 📖 `memory-reader`

Searches and retrieves relevant memories using **RedisStack HNSW indexing** with sub-millisecond vector search performance. Advanced context-aware algorithms combine semantic similarity, keyword matching, and temporal ranking.

**Performance:** 100x faster than basic Redis (0.5-5ms vs 50-200ms search latency)

**Configuration:**
```yaml
- id: memory_reader
  type: memory-reader
  namespace: conversations
  params:
    limit: 10
    enable_context_search: true      # Use conversation context
    context_weight: 0.4              # 40% weight for context
    temporal_weight: 0.3             # 30% weight for recency
    enable_temporal_ranking: true    # Boost recent memories
    similarity_threshold: 0.8        # HNSW-optimized threshold
  prompt: "Find memories about: {{ input }}"
```

### 💾 `memory-writer`

Stores information with **RedisStack HNSW vector indexing** for lightning-fast retrieval. Features intelligent decay management and automatic classification.

**Performance:** 50x higher throughput (50,000/sec vs 1,000/sec write performance)

**Configuration:**
```yaml
- id: memory_writer
  type: memory-writer
  namespace: user_sessions
  params:
    # memory_type automatically classified based on content and importance
    vector: true                     # Enable HNSW semantic search
    metadata:
      source: "user_interaction"
      performance: "hnsw_optimized"
  decay_config:
    enabled: true
    default_long_term: true
    default_long_term_hours: 720
  prompt: "Store: {{ input }}"
```

---

## 🧵 Control Flow Nodes

### 🔀 `router`

Dynamically routes execution based on previous agent outputs.

**Example config:**
```yaml
- id: content_router
  type: router
  params:
    decision_key: content_type
    routing_map:
      "question": [search_agent, answer_builder]
      "statement": [fact_checker, validator]
      "request": [task_processor]
```

### 🔄 `failover`

Executes child agents sequentially until one succeeds, providing resilience.

**Example config:**
```yaml
- id: resilient_search
  type: failover
  children:
    - id: primary_search
      type: duckduckgo
      prompt: "Search: {{ input }}"
    - id: backup_method
      type: openai-answer
      prompt: "Answer from knowledge: {{ input }}"
```

### 🌿 `fork`

Splits execution into multiple parallel branches for concurrent processing.

**Example config:**
```yaml
- id: parallel_validation
  type: fork
  targets:
    - [sentiment_check]
    - [toxicity_check]
    - [fact_validation]
  mode: parallel
```

### 🔗 `join`

Waits for forked agents to complete and aggregates their outputs.

**Example config:**
```yaml
- id: validation_merger
  type: join
  prompt: "Combine validation results"
```

### 🔥 `failing`

Intentionally fails for testing error handling and failover scenarios.

**Example config:**
```yaml
- id: test_failure
  type: failing
  prompt: "This will always fail"
```

---

## 🤖 Advanced Nodes

### 🔍 `rag`

Performs Retrieval-Augmented Generation with vector search and LLM generation.

**Configuration:**
```yaml
- id: knowledge_qa
  type: rag
  params:
    top_k: 5
    score_threshold: 0.7
  prompt: "Answer using knowledge base"
```

---

## 📊 Agent Summary

| Agent Type | Category | Purpose | Status |
|:-----------|:---------|:--------|:-------|
| `binary` | Agent | Simple true/false decisions | Active |
| `classification` | Agent | Basic categorization | Deprecated |
| `openai-binary` | Agent | LLM-powered binary decisions | Active |
| `openai-classification` | Agent | LLM-powered categorization | Active |
| `openai-answer` | Agent | Content generation | Active |
| `local_llm` | Agent | Local model inference | Active |
| `validate_and_structure` | Agent | Answer validation | Active |
| `duckduckgo` | Tool | Web search | Active |
| `memory` (read) | Node | Memory retrieval | Active |
| `memory` (write) | Node | Memory storage | Active |
| `rag` | Node | RAG operations | Active |
| `router` | Node | Dynamic routing | Active |
| `failover` | Node | Error resilience | Active |
| `fork` | Node | Parallel execution | Active |
| `join` | Node | Result aggregation | Active |
| `failing` | Node | Testing failures | Active |

---

## 🚀 Getting Started

1. **Choose your agent types** based on your workflow needs
2. **Configure YAML** with appropriate prompts and parameters
3. **Test individually** before chaining agents
4. **Monitor execution** through OrKa UI or logs
5. **Iterate and optimize** based on results

For detailed configuration examples, see the [YAML Configuration Guide](./yaml-configuration-guide.md).

[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
