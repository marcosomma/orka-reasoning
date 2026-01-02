# OrKa YAML Configuration Guide

> **Last Updated:** 29 November 2025  
> **Status:** 🟢 Primary Configuration Guide  
> **Related:** [Getting Started](getting-started.md) | [Runtime Modes](runtime-modes.md) | [index](index.md)

## Orchestrator Configuration

OrKa workflows are defined as YAML with **two top-level sections**:

- `orchestrator`: workflow settings (execution strategy and agent order)
- `agents`: all runnable units (agents, nodes, tools) declared in one list

### Core Components

1. **Base Configuration**
   ```yaml
   orchestrator:
     id: "workflow_name"
     strategy: sequential   # sequential | parallel
     agents: [agent_1, agent_2]

   agents:
     - id: agent_1
       type: openai-answer
       prompt: "{{ input }}"

     - id: agent_2
       type: openai-answer
       prompt: "Refine: {{ previous_outputs.agent_1 }}"
   ```

**Notes**
- `orchestrator.queue` is optional (legacy).
- The orchestrator executes agents in the order listed in `orchestrator.agents`.

## Agent Configurations

Orka supports various types of agents that can be configured in the YAML workflow. Here are the available agent types and their configurations:

### Core Decision Agents

1. **Binary Agent**
   ```yaml
   agents:
     - id: "binary_decision"
       type: "binary"
       prompt: "Should this input be processed? {{ input }}"
       timeout: 30.0
       max_concurrency: 5
   ```

2. **Classification Agent** (Deprecated)
   ```yaml
   agents:
     - id: "classifier"
       type: "classification"
       prompt: "(deprecated)"
   ```

### LLM Integration Agents

1. **OpenAI Answer Builder**
   ```yaml
   agents:
     - id: "answer_gen"
       type: "openai-answer"
       model: "gpt-4"
       temperature: 0.7
       max_tokens: 1000
       prompt: "Generate a detailed answer: {{ input }}"
       system_prompt: "You are a helpful assistant..."
   ```

2. **OpenAI Binary Agent**
   ```yaml
   agents:
     - id: "ai_binary"
       type: "openai-binary"
       model: "gpt-4"
       temperature: 0.2
       prompt: "Should this be approved? {{ input }}"
       system_prompt: "You are a decision maker..."
   ```

3. **OpenAI Classification Agent**
   ```yaml
   agents:
     - id: "ai_classifier"
       type: "openai-classification"
       model: "gpt-4"
       temperature: 0.3
       options: ["urgent", "normal", "low"]
       prompt: "Classify the priority: {{ input }}"
   ```

4. **Local LLM Agent**
   ```yaml
   agents:
     - id: "local_llm"
       type: "local_llm"
       model: "llama2"
       provider: "ollama"  # ollama | lm_studio | openai_compatible
       model_url: "http://localhost:11434"
       prompt: "Process this input: {{ input }}"
   ```

### Specialized Agents

1. **Validation and Structuring Agent**
   ```yaml
   agents:
     - id: "validator"
       type: "validate_and_structure"
       prompt: |
         Validate the latest answer and return JSON with:
         - valid: boolean
         - reason: string
         - memory_object: object|null
       store_structure: |
         {
           "topic": "extracted topic",
           "confidence": "0.0-1.0",
           "key_points": ["..."]
         }
   ```

## Workflow Nodes (configured as agents)

OrKa uses a single `agents:` list. **Control-flow nodes** (router/fork/join/loop/…) are declared there too.

### Router Node (`type: router`)

```yaml
agents:
  - id: content_router
    type: router
    params:
      decision_key: safety_check
      routing_map:
        "true": [content_processor]
        "false": [human_review]
```

See: [Router node](./nodes/router.md)

### Fork + Join (`type: fork`, `type: join`)

```yaml
agents:
  - id: fanout
    type: fork
    mode: sequential
    targets:
      - [branch_a_1, branch_a_2]
      - [branch_b_1]

  - id: join_results
    type: join
    group: fanout
    max_retries: 30
```

See: [Fork/Join](./nodes/fork-and-join.md)

### Failover (`type: failover`)

Failover is configured with **inline `children:`** (nested agents) and tries them in order.

```yaml
agents:
  - id: answer_with_fallback
    type: failover
    children:
      - id: try_memory
        type: memory
        namespace: knowledge_base
        config:
          operation: read
          limit: 8
          similarity_threshold: 0.6
        prompt: "Find context for: {{ input }}"

      - id: try_web
        type: duckduckgo
        prompt: "Search the web for: {{ input }}"

      - id: final_answer
        type: openai-answer
        prompt: |
          Use memory: {{ previous_outputs.try_memory }}
          Use web: {{ previous_outputs.try_web }}
          Answer: {{ input }}
```

See: [Failover node](./nodes/failover.md)

### Memory (`type: memory`)

Memory uses a single agent type and selects read vs write via `config.operation`.

## Streaming configuration keys ⚠️ BETA

> **Beta Feature**: Streaming runtime has known limitations including context loss across turns. See [STREAMING_GUIDE.md](./STREAMING_GUIDE.md) for details.

When using the streaming runtime:

- `orchestrator.mode`: set to `streaming`.
- `orchestrator.executor_invariants`: optional fields including `voice` (omit or empty for text-only), `identity`, `refusal`, `tool_permissions`, `safety_policies`.
- `orchestrator.prompt_budgets`: `{ total_tokens: int, sections: { <section>: int } }`.
- `orchestrator.refresh`: `{ cadence_seconds, debounce_ms, max_refresh_per_min }`.

```yaml
agents:
  - id: memory_read
    type: memory
    namespace: conversations
    memory_preset: episodic
    config:
      operation: read
      limit: 8
      similarity_threshold: 0.6
      enable_context_search: false
      enable_temporal_ranking: false
    prompt: "Find memories about: {{ input }}"

  - id: memory_write
    type: memory
    namespace: conversations
    memory_preset: working
    config:
      operation: write
    metadata:
      source: user
    prompt: "Store: {{ input }}"
```

See: [Memory System](MEMORY_SYSTEM_GUIDE.md)

### GraphScout (`type: graph-scout`)

See: [GraphScout](GRAPH_SCOUT_AGENT.md)

## Tool Configurations

Orka provides various tools that can be used within workflows. Here are the available tools and their configurations:

### Search Tools

1. **DuckDuckGo Search Tool**
   ```yaml
   agents:
     - id: "web_search"
       type: "duckduckgo"
       prompt: "Search for: {{ input }}"
   ```

**Note**: Tools are configured as agents in the YAML configuration. The DuckDuckGo tool supports intelligent query handling with fallback mechanisms for both text and news searches.

## Memory Configurations (Operation-Aware Presets)

**NEW in v0.9.2**: Simplified memory configuration with operation-aware presets!

### Modern Memory Presets (Minsky-Inspired)

Instead of complex manual configurations, use cognitive memory presets that automatically adapt to read vs write operations:

1. **Sensory Memory** (Near real-time processing; deployment-dependent)
   ```yaml
   # ❌ OLD WAY: Complex configuration (30+ lines)
   # memory:
   #   type: "redisstack"
   #   config:
   #     memory_type: "sensory"
   #     decay_config: { ... 20+ lines ... }
   #     vector_params: { ... 10+ lines ... }
   
   # ✅ NEW WAY: Simple preset (1 line!)
   - id: sensor_memory
     type: memory
     memory_preset: "sensory"  # 🎯 Auto-optimized for near real-time data (deployment-dependent)!
     config:
       operation: write
     namespace: sensor_data
         ef_construction: 100  # Build-time accuracy
       retrieval:
         strategy: "exact"  # No fuzzy matching
         top_k: 1  # Single best match
         similarity_threshold: 0.95  # Very strict matching
   ```

2. **Working Memory** (Session Context)
   ```yaml
   # ❌ OLD WAY: Complex configuration
   # memory:
   #   type: "redisstack"
   #   config:
   #     memory_type: "learned"
   #     decay_config: { ... 15+ lines ... }
   
   # ✅ NEW WAY: Simple preset
   - id: session_memory
     type: memory
     memory_preset: "working"  # 🎯 Auto-optimized for session context!
     config:
       operation: read          # (limit=5, context_weight=0.5, etc.)
     namespace: user_session
       vector_params:
         M: 16
         ef_construction: 150
       retrieval:
         strategy: "hybrid"
         top_k: 3
         similarity_threshold: 0.8
   ```

3. **Episodic Memory** (Conversations)
   ```yaml
   # ❌ OLD WAY: Complex configuration
   # memory:
   #   type: "redisstack"
   #   config:
   #     memory_type: "reflective"
   #     decay_config: { ... 20+ lines ... }
   
   # ✅ NEW WAY: Simple preset
   - id: conversation_memory
     type: memory
     memory_preset: "episodic"  # 🎯 Auto-optimized for conversations!
     config:
       operation: write         # (vector=true, conversation indexing, etc.)
     namespace: conversations
       vector_params:
         M: 24
         ef_construction: 200
       retrieval:
         strategy: "semantic"
         top_k: 5
         similarity_threshold: 0.7
         reranking: true
   ```

4. **Semantic Memory** (Knowledge Base)
   ```yaml
   # ❌ OLD WAY: Complex configuration
   # memory:
   #   type: "redisstack"
   #   config:
   #     memory_type: "self_reflective"
   #     decay_config: { ... 25+ lines ... }
   
   # ✅ NEW WAY: Simple preset
   - id: knowledge_memory
     type: memory
     memory_preset: "semantic"  # 🎯 Auto-optimized for knowledge!
     config:
       operation: read          # (limit=10, no temporal bias, etc.)
     namespace: knowledge_base
       vector_params:
         M: 32
         ef_construction: 250
       retrieval:
         strategy: "hybrid"
         top_k: 10
         similarity_threshold: 0.6
         context_window: 5
   ```

5. **Procedural Memory** (Workflows)
   ```yaml
   # ❌ OLD WAY: Complex configuration
   # memory:
   #   type: "redisstack"
   #   config:
   #     memory_type: "self_conscious"
   #     decay_config: { ... 30+ lines ... }
   
   # ✅ NEW WAY: Simple preset
   - id: workflow_memory
     type: memory
     memory_preset: "procedural"  # 🎯 Auto-optimized for processes!
     config:
       operation: write           # (pattern-optimized storage, etc.)
     namespace: workflows
       vector_params:
         M: 48
         ef_construction: 300
       retrieval:
         strategy: "semantic"
         top_k: 20
         similarity_threshold: 0.5
         temporal_boost: true
         context_window: 10
   ```

6. **Meta Memory** (System Insights)
   ```yaml
   # ❌ OLD WAY: Complex configuration
   # memory:
   #   type: "redisstack"
   #   config:
   #     memory_type: "self_ideal"
   #     decay_config: { ... 35+ lines ... }
   
   # ✅ NEW WAY: Simple preset
   - id: system_memory
     type: memory
     memory_preset: "meta"        # 🎯 Auto-optimized for system data!
     config:
       operation: write           # (high-quality indexing, etc.)
     namespace: system_metrics
       vector_params:
         M: 64
         ef_construction: 400
       retrieval:
         strategy: "hybrid"
         top_k: 50
         similarity_threshold: 0.4
         temporal_boost: true
         context_window: 20
         reranking: true
   ```

### Operation-Aware Preset Characteristics

**Each preset automatically provides different optimized defaults for READ vs WRITE operations:**

1. **Sensory Memory** (15 minutes)
   - **Read**: Fast retrieval (limit=3, similarity_threshold=0.95, no vector search)
   - **Write**: Minimal indexing (vector=false, speed-optimized storage)
   - **Use**: Near real-time data, sensor input, immediate processing (deployment-dependent)

2. **Working Memory** (2-8 hours)
   - **Read**: Context-aware search (limit=5, context_weight=0.5, temporal_weight=0.4)
   - **Write**: Session optimization (vector=true, temporary storage tuning)
   - **Use**: Session context, active workflows, temporary calculations

3. **Episodic Memory** (1 day - 1 week)
   - **Read**: Conversational context (limit=8, similarity_threshold=0.6, temporal_weight=0.3)
   - **Write**: Rich metadata storage (vector=true, conversation-optimized indexing)
   - **Use**: Conversations, personal experiences, interaction history

4. **Semantic Memory** (3 days - 90 days)
   - **Read**: Knowledge matching (limit=10, similarity_threshold=0.65, no temporal bias)
   - **Write**: Knowledge optimization (vector=true, long-term indexing)
   - **Use**: Facts, knowledge base, learned information

5. **Procedural Memory** (1 week - 6 months)
   - **Read**: Pattern recognition (limit=6, similarity_threshold=0.7, minimal temporal bias)
   - **Write**: Process indexing (vector=true, pattern-optimized storage)
   - **Use**: Skills, workflows, patterns, process optimization

6. **Meta Memory** (2 days - 1 year)
   - **Read**: System analysis (limit=4, similarity_threshold=0.8, high precision)
   - **Write**: Performance optimization (vector=true, high-quality indexing)
   - **Use**: System insights, performance metrics, meta-learning

## Prompt Rendering

The prompt renderer is a powerful component that uses Jinja2 templating for dynamic prompt construction. Here's a detailed guide on how to use prompts effectively in your YAML configurations:

### Basic Prompt Structure
```yaml
agents:
  - id: "example_agent"
    type: "openai-answer"
    prompt: "Process this input: {{ input }}"
```

### Available Template Variables

1. **Basic Variables**
   - `{{ input }}` - The current input data
   - `{{ agent_id }}` - Current agent's ID
   - `{{ trace_id }}` - Current execution trace ID
   - `{{ now() }}` - Current timestamp

2. **Previous Outputs**
   ```yaml
   prompt: |
     Previous classification: {{ previous_outputs.classifier }}
     Search results: {{ previous_outputs.search_agent }}
     Process this input: {{ input }}
   ```

3. **Memory Context**
   ```yaml
   prompt: |
     Memory context: {{ previous_outputs.memory_reader }}
     Current query: {{ input }}
     Previous interaction: {{ previous_outputs.conversation_history }}
   ```

4. **Conditional Rendering**
   ```yaml
   prompt: |
     {% if previous_outputs.web_search %}
     Web Results: {{ previous_outputs.web_search }}
     {% endif %}
     
     {% if previous_outputs.classification == 'urgent' %}
     URGENT: Handle with priority
     {% endif %}
     
     Input: {{ input }}
   ```

5. **Loop Context**
   ```yaml
   prompt: |
     Iteration {{ loop_number }} of {{ max_loops }}
     Previous attempts:
     {% for attempt in previous_outputs.past_loops %}
     - Attempt {{ attempt.iteration }}: {{ attempt.result }}
     {% endfor %}
     
     Current input: {{ input }}
   ```

6. **Error Handling**
   ```yaml
   prompt: |
     {% if previous_outputs.error %}
     Previous error: {{ previous_outputs.error }}
     Retry attempt: {{ retry_count }}
     {% endif %}
     
     Process: {{ input }}
   ```

### Advanced Template Features

1. **Filters and Functions**
   ```yaml
   prompt: |
     Length: {{ input | length }}
     Uppercase: {{ input | upper }}
     Timestamp: {{ now() | date }}
     JSON: {{ previous_outputs.data | tojson }}
   ```

2. **Multi-line Prompts**
   ```yaml
   prompt: |
     System: You are a helpful assistant.
     
     Context:
     {{ previous_outputs.context }}
     
     User Query:
     {{ input }}
     
     Previous Response:
     {{ previous_outputs.last_response }}
     
     Generate a response that:
     1. Addresses the query
     2. Maintains context
     3. Is consistent with previous responses
   ```

3. **Dynamic Routing**
   ```yaml
   prompt: |
     Based on:
     - Classification: {{ previous_outputs.classifier }}
     - Priority: {{ previous_outputs.priority_check }}
     - Sentiment: {{ previous_outputs.sentiment_analysis }}
     
     {% if previous_outputs.classifier == 'technical' %}
     Technical context: {{ previous_outputs.tech_context }}
     {% elif previous_outputs.classifier == 'business' %}
     Business context: {{ previous_outputs.business_context }}
     {% endif %}
     
     Process: {{ input }}
   ```

### Best Practices

1. **Structure and Readability**
   ```yaml
   prompt: |
     # Context
     {{ previous_outputs.context }}
     
     # Current Input
     {{ input }}
     
     # Instructions
     1. Analyze the input
     2. Consider the context
     3. Generate response
   ```

2. **Error Resilience**
   ```yaml
   prompt: |
     Input: {{ input | default('No input provided') }}
     Context: {{ previous_outputs.context | default('No context available') }}
     Classification: {{ previous_outputs.classifier | default('unclassified') }}
   ```

3. **Memory Integration**
   ```yaml
   prompt: |
     Short-term context:
     {{ previous_outputs.short_term_memory | default('No recent context') }}
     
     Long-term knowledge:
     {{ previous_outputs.long_term_memory | default('No relevant knowledge') }}
     
     Current query:
     {{ input }}
   ```

## Examples

### 1. Basic Sequential Workflow
```yaml
orchestrator:
  name: "simple_processor"
  description: "Basic sequential processing workflow"
  strategy: "sequential"
  agents:
    - id: "classifier"
      type: "openai-classification"
      prompt: "Classify this input: {{ input }}"
      options: ["urgent", "normal", "low"]
    
    - id: "processor"
      type: "openai-answer"
      prompt: "Process this {{ classification }} priority input: {{ input }}"

    - id: "validator"
      type: "validate_and_structure"
      schema: "schemas/response.json"
```

### 2. Parallel Processing with Memory
```yaml
orchestrator:
  name: "parallel_processor"
  description: "Parallel processing with memory storage"
  strategy: "parallel"
  agents:
    - id: "fork_node"
      type: "fork"
      params:
        parallel_agents: ["validator_1", "validator_2", "validator_3"]
        join_node: "aggregator"

    - id: "validator_1"
      type: "openai-binary"
      prompt: "Check grammar: {{ input }}"

    - id: "validator_2"
      type: "openai-binary"
      prompt: "Check content safety: {{ input }}"

    - id: "validator_3"
      type: "openai-binary"
      prompt: "Check relevance: {{ input }}"

    - id: "aggregator"
      type: "join"
      params:
        aggregation_strategy: "all_required"

    - id: "memory_writer"
      type: "memory_writer"
      params:
        memory_type: "reflective"  # Level 3 Minsky memory
        decay_config:
          enabled: true
          short_term_hours: 48
          long_term_hours: 2160
```

### 3. Complex Routing with Tools
```yaml
orchestrator:
  name: "smart_router"
  description: "Complex routing with web search integration"
  strategy: "sequential"
  agents:
    - id: "intent_classifier"
      type: "openai-classification"
      prompt: "What is the user's intent: {{ input }}"
      options: ["question", "task", "search"]

    - id: "router"
      type: "router"
      params:
        decision_key: "intent_classifier"
        routing_map:
          "question": ["qa_agent"]
          "task": ["task_processor"]
          "search": ["search_agent"]

    - id: "search_agent"
      type: "duckduckgo"
      params:
        max_results: 5

    - id: "qa_agent"
      type: "openai-answer"
      prompt: "Answer this question: {{ input }}"

    - id: "task_processor"
      type: "openai-answer"
      prompt: "How should I perform this task: {{ input }}"
```
---
← [Visual Architecture](VISUAL_ARCHITECTURE_GUIDE.md) | [📚 INDEX](index.md) | [Json Inputs Guide](JSON_INPUTS.md) →
