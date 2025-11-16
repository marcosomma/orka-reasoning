# Agent Types in OrKa

> **Last Updated:** 16 November 2025  
> **Status:** 🟢 Current  
> **Related:** [Advanced Agents](agents-advanced.md) | [Extending Agents](extending-agents.md) | [Agent Index](AGENT_NODE_TOOL_INDEX.md) | [INDEX](INDEX.md)

In OrKa, **agents** are modular processing units that receive input and return structured output — all orchestrated via a declarative YAML configuration.

Agents can represent different cognitive functions: classification, decision-making, web search, conditional routing, memory management, and more.

The OrKa framework uses a unified agent base implementation that supports both modern asynchronous patterns and legacy synchronous patterns for backward compatibility.

---

## 🧱 Core Agent Types

### 🧭 `graph_scout` **NEW in v0.9.3**

Intelligent workflow graph inspection and optimal multi-agent path execution. GraphScout automatically discovers, evaluates, and executes the best sequence of agents for any given input.

**Use case:** Dynamic routing, intelligent workflow orchestration, adaptive agent selection.

**Key Features:**
- **Intelligent Path Discovery**: Automatically finds optimal agent sequences
- **Memory-Aware Routing**: Positions memory agents optimally (readers first, writers last)
- **Multi-Agent Execution**: Executes ALL agents in shortlist sequentially
- **LLM-Powered Evaluation**: Advanced reasoning for path selection
- **Budget & Safety Control**: Respects token/latency budgets and safety thresholds

**Example config:**
```yaml
- id: smart_router
  type: graph_scout
  config:
    k_beam: 5                    # Top-k candidate paths
    max_depth: 3                 # Maximum path depth
    commit_margin: 0.15          # Confidence threshold
    cost_budget_tokens: 1000     # Token budget limit
    latency_budget_ms: 2000      # Latency budget limit
    safety_threshold: 0.8        # Safety assessment threshold
  prompt: "Find the best path for: {{ input }}"
```

**Decision Types:**
- `commit_next`: High confidence single path → Execute immediately
- `shortlist`: Multiple good options → Execute all sequentially  
- `no_path`: No suitable path → Fallback to response builder

**📖 [Complete GraphScout Documentation](./GRAPH_SCOUT_AGENT.md)**

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

### 🔄 `loop`

Executes an internal workflow repeatedly until a score threshold is met or maximum loops are reached. Features cognitive insight extraction and iterative improvement capabilities.

**Use case:** Iterative refinement, consensus building, multi-agent deliberation, self-improving systems.

**Key Features:**
- **Threshold-based execution** - Continues until score meets requirements
- **Cognitive insight extraction** - Automatically extracts insights, improvements, and mistakes
- **Past loops context** - Maintains memory of previous iterations for learning
- **Flexible scoring** - Configurable score extraction via regex patterns or direct keys
- **Iterative improvement** - Agents learn from previous attempts

**Example config:**
```yaml
- id: iterative_improver
  type: loop
  max_loops: 10
  score_threshold: 0.85
  score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
  
  # Cognitive extraction configuration
  cognitive_extraction:
    enabled: true
    max_length_per_category: 300
    extract_patterns:
      insights:
        - "(?:provides?|identifies?|shows?)\\s+(.+?)(?:\\n|$)"
        - "(?:solid|good|comprehensive)\\s+(.+?)(?:\\n|$)"
      improvements:
        - "(?:lacks?|needs?|requires?|should)\\s+(.+?)(?:\\n|$)"
        - "(?:would improve|could benefit from)\\s+(.+?)(?:\\n|$)"
      mistakes:
        - "(?:overlooked|missed|inadequate)\\s+(.+?)(?:\\n|$)"
        - "(?:weakness|limitation|gap)\\s*[:\\s]*(.+?)(?:\\n|$)"
  
  # Past loops metadata template
  past_loops_metadata:
    loop_number: "{{ loop_number }}"
    score: "{{ score }}"
    key_insights: "{{ insights }}"
    improvements_needed: "{{ improvements }}"
    mistakes_identified: "{{ mistakes }}"
  
  # Internal workflow that gets repeated
  internal_workflow:
    orchestrator:
      id: internal-loop
      strategy: sequential
      agents: [analyzer, scorer]
    agents:
      - id: analyzer
        type: openai-answer
        prompt: |
          Analyze: {{ input }}
          
          {% if previous_outputs.past_loops %}
          Previous attempts:
          {% for loop in previous_outputs.past_loops %}
          - Loop {{ loop.loop_number }} (Score: {{ loop.score }}):
            * Insights: {{ loop.key_insights }}
            * Improvements: {{ loop.improvements_needed }}
            * Mistakes: {{ loop.mistakes_identified }}
          {% endfor %}
          
          Build upon these insights and address the gaps.
          {% endif %}
          
          Provide comprehensive analysis with clear insights.
      
      - id: scorer
        type: openai-answer
        prompt: |
          Rate this analysis (0.0 to 1.0): {{ previous_outputs.analyzer.result }}
          
          Format: SCORE: X.XX
          Explain what needs improvement if score is below threshold.
```

**Multi-Agent Deliberation Example:**
```yaml
- id: cognitive_society
  type: loop
  max_loops: 5
  score_threshold: 0.95
  score_extraction_pattern: "AGREEMENT_SCORE[\":]?\\s*\"?([0-9.]+)\"?"
  
  internal_workflow:
    orchestrator:
      id: deliberation
      strategy: sequential
      agents: [fork_reasoning, join_perspectives, moderator]
    agents:
      - id: fork_reasoning
        type: fork
        targets:
          - [logic_agent]
          - [empathy_agent]
          - [skeptic_agent]
      
      - id: logic_agent
        type: openai-answer
        prompt: "Provide logical analysis of: {{ input }}"
      
      - id: empathy_agent
        type: openai-answer
        prompt: "Provide empathetic perspective on: {{ input }}"
      
      - id: skeptic_agent
        type: openai-answer
        prompt: "Provide critical analysis of: {{ input }}"
      
      - id: join_perspectives
        type: join
        group: fork_reasoning
      
      - id: moderator
        type: openai-answer
        prompt: |
          Evaluate agent convergence on: {{ input }}
          
          Logic: {{ previous_outputs.logic_agent.response }}
          Empathy: {{ previous_outputs.empathy_agent.response }}
          Skeptic: {{ previous_outputs.skeptic_agent.response }}
          
          Score agreement level (0.0-1.0):
          AGREEMENT_SCORE: [score]
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
| `loop` | Node | Iterative workflows | Active |
| `failing` | Node | Testing failures | Active |

---

## 🚀 Getting Started

1. **Choose your agent types** based on your workflow needs
2. **Configure YAML** with appropriate prompts and parameters
3. **Test individually** before chaining agents
4. **Monitor execution** through OrKa UI or logs
5. **Iterate and optimize** based on results

For detailed configuration examples, see the [YAML Configuration Guide](./yaml-configuration-guide.md).

← [YAML Configuration](YAML_CONFIGURATION.md) | [📚 index](index.md) | [Advanced Agents](agents-advanced.md) →
