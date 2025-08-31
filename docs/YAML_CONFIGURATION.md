## Orchestrator Configuration

The Orchestrator is the core engine of Orka that coordinates all components. It uses a modular architecture with the following key components:

### Core Components

1. **Base Configuration (OrchestratorBase)**
   ```yaml
   orchestrator:
     name: "workflow_name"
     description: "Workflow description"
     version: "1.0"
     strategy: "sequential"  # or "parallel"
   ```

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
       prompt: "Classify this input: {{ input }}"
       options: ["positive", "negative", "neutral"]
       timeout: 30.0
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
       provider: "ollama"  # or "lm_studio"
       model: "llama2"
       endpoint: "http://localhost:11434"
       prompt: "Process this input: {{ input }}"
   ```

### Specialized Agents

1. **Validation and Structuring Agent**
   ```yaml
   agents:
     - id: "validator"
       type: "validate_and_structure"
       schema: "schemas/response.json"
       validation_rules:
         required_fields: ["title", "content"]
         max_length: 1000
       error_handling:
         strict: true
         return_partial: false
   ```

## Node Configurations

Orka provides various specialized nodes for workflow control and data management. Here are the available node types and their configurations:

### Flow Control Nodes

1. **Router Node**
   ```yaml
   nodes:
     - id: "content_router"
       type: "router"
       params:
         decision_key: "classification"
         routing_map:
           "urgent": ["urgent_handler", "notify_admin"]
           "normal": ["standard_processor"]
           "low": ["batch_processor"]
   ```

2. **Fork Node**
   ```yaml
   nodes:
     - id: "parallel_processor"
       type: "fork"
       params:
         parallel_agents: ["validator_1", "validator_2", "validator_3"]
         join_node: "results_aggregator"
         max_parallel: 5
   ```

3. **Join Node**
   ```yaml
   nodes:
     - id: "results_aggregator"
       type: "join"
       params:
         aggregation_strategy: "merge"  # or "first_success", "all_required"
         timeout: 30.0
         error_handling:
           partial_results: true
   ```

4. **Loop Node**
   ```yaml
   nodes:
     - id: "iteration_handler"
       type: "loop"
       params:
         max_iterations: 5
         condition_key: "continue_processing"
         exit_on_error: true
         iteration_data: "items"
   ```

### Error Handling Nodes

1. **Failover Node**
   ```yaml
   nodes:
     - id: "error_handler"
       type: "failover"
       params:
         fallback_agents: ["backup_processor", "human_review"]
         retry_original: true
         max_retries: 3
   ```

2. **Failing Node**
   ```yaml
   nodes:
     - id: "validation_gate"
       type: "failing"
       params:
         failure_conditions:
           - "quality_score < 0.8"
           - "error_count > 0"
         error_message: "Quality check failed"
   ```

### Memory Management Nodes

1. **Memory Reader Node**
   ```yaml
   nodes:
     - id: "context_loader"
       type: "memory_reader"
       params:
         query_type: "semantic"  # or "exact", "temporal"
         filters:
           memory_type: "long_term"
           time_window: "24h"
         top_k: 5
         similarity_threshold: 0.8
   ```

2. **Memory Writer Node**
   ```yaml
   nodes:
     - id: "memory_saver"
       type: "memory_writer"
       params:
         memory_type: "short_term"
         ttl: "1h"
         index_fields: ["title", "content"]
         deduplication:
           enabled: true
           similarity_threshold: 0.95
   ```

3. **RAG Node**
   ```yaml
   nodes:
     - id: "knowledge_augmenter"
       type: "rag"
       params:
         retrieval:
           strategy: "hybrid"  # semantic + keyword
           top_k: 3
           reranking: true
         augmentation:
           template: "Consider this context: {context}\nNow answer: {query}"
           max_tokens: 2000
   ```

## Tool Configurations

Orka provides various tools that can be used within workflows. Here are the available tools and their configurations:

### Search Tools

1. **DuckDuckGo Search Tool**
   ```yaml
   tools:
     - id: "web_search"
       type: "duckduckgo"
       params:
         max_results: 5
         search_type: "text"  # or "news"
         timeout: 30.0
         fallback_enabled: true
   ```

## Memory Configurations

### Minsky Memory Level Presets

Marvin Minsky's six levels of memory provide a framework for organizing different types of memory in AI systems. Here are the corresponding configurations for each level:

1. **Instinctive Memory (Level 1)**
   ```yaml
   memory:
     type: "redisstack"
     config:
       memory_type: "instinctive"
       decay_config:
         enabled: false  # No decay for instinctive memories
         importance_threshold: 1.0  # Always retain
       vector_params:
         M: 16  # HNSW graph connections
         ef_construction: 100  # Build-time accuracy
       retrieval:
         strategy: "exact"  # No fuzzy matching
         top_k: 1  # Single best match
         similarity_threshold: 0.95  # Very strict matching
   ```

2. **Learned Responses (Level 2)**
   ```yaml
   memory:
     type: "redisstack"
     config:
       memory_type: "learned"
       decay_config:
         enabled: true
         short_term_hours: 24
         long_term_hours: 720  # 30 days
         importance_threshold: 0.7
       vector_params:
         M: 16
         ef_construction: 150
       retrieval:
         strategy: "hybrid"
         top_k: 3
         similarity_threshold: 0.8
   ```

3. **Reflective Memory (Level 3)**
   ```yaml
   memory:
     type: "redisstack"
     config:
       memory_type: "reflective"
       decay_config:
         enabled: true
         short_term_hours: 48
         long_term_hours: 2160  # 90 days
         importance_threshold: 0.6
       vector_params:
         M: 24
         ef_construction: 200
       retrieval:
         strategy: "semantic"
         top_k: 5
         similarity_threshold: 0.7
         reranking: true
   ```

4. **Self-Reflective Memory (Level 4)**
   ```yaml
   memory:
     type: "redisstack"
     config:
       memory_type: "self_reflective"
       decay_config:
         enabled: true
         short_term_hours: 168  # 1 week
         long_term_hours: 4320  # 180 days
         importance_threshold: 0.5
       vector_params:
         M: 32
         ef_construction: 250
       retrieval:
         strategy: "hybrid"
         top_k: 10
         similarity_threshold: 0.6
         context_window: 5
   ```

5. **Self-Conscious Memory (Level 5)**
   ```yaml
   memory:
     type: "redisstack"
     config:
       memory_type: "self_conscious"
       decay_config:
         enabled: true
         short_term_hours: 336  # 2 weeks
         long_term_hours: 8760  # 1 year
         importance_threshold: 0.4
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

6. **Self-Ideal Memory (Level 6)**
   ```yaml
   memory:
     type: "redisstack"
     config:
       memory_type: "self_ideal"
       decay_config:
         enabled: true
         short_term_hours: 720  # 30 days
         long_term_hours: 17520  # 2 years
         importance_threshold: 0.3
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

### Memory Level Characteristics

1. **Instinctive Memory (Level 1)**
   - Fastest retrieval with exact matching
   - No decay (permanent storage)
   - Very strict similarity requirements
   - Used for core system behaviors and critical patterns

2. **Learned Responses (Level 2)**
   - Quick retrieval with some flexibility
   - Moderate decay for short-term memories
   - Balanced similarity matching
   - Used for learned patterns and responses

3. **Reflective Memory (Level 3)**
   - Enhanced semantic search capabilities
   - Longer retention of important memories
   - More flexible similarity matching
   - Used for pattern recognition and analysis

4. **Self-Reflective Memory (Level 4)**
   - Comprehensive context consideration
   - Extended memory retention
   - Broader similarity matching
   - Used for complex pattern analysis and learning

5. **Self-Conscious Memory (Level 5)**
   - Advanced temporal context awareness
   - Long-term memory storage
   - Flexible similarity matching
   - Used for high-level pattern recognition

6. **Self-Ideal Memory (Level 6)**
   - Most sophisticated retrieval system
   - Very long-term storage
   - Highly flexible matching
   - Used for abstract patterns and concepts

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
