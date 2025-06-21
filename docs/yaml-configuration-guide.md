[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# YAML Configuration Guide for OrKa

This guide provides detailed examples and patterns for configuring different types of agents, nodes, and tools in your OrKa YAML configuration.

## Basic Structure

Every OrKa YAML file has the same basic structure:

```yaml
meta:
  version: "1.0"
  author: "Your Name"
  description: "Short description of what this flow does"

orchestrator:
  id: my_orchestrator
  strategy: sequential  # or "parallel" for fork/join flows
  queue: orka:main
  memory_config:  # Optional global memory configuration
    decay:
      enabled: true
      default_short_term_hours: 2
      default_long_term_hours: 168

agents:
  # List of agent configurations
  - id: agent1
    type: binary
    # agent-specific configuration
  - id: agent2
    type: classification
    # agent-specific configuration
```

## Core Agent Types

### Binary Agents

Simple true/false decisions:

```yaml
- id: is_relevant
  type: binary
  prompt: >
    Is the following statement relevant to cybersecurity? 
    Return TRUE if it is, or FALSE if it is not.
  queue: orka:relevance_check
  timeout: 15.0
  max_concurrency: 5
```

Advanced LLM-powered binary decisions:

```yaml
- id: content_safe
  type: openai-binary
  prompt: >
    Is this content safe for work and appropriate for all audiences?
    Content: {{ input }}
    
    Consider factors like:
    - Professional language
    - Appropriate topics
    - No offensive content
  queue: orka:safety_check
  timeout: 30.0
```

### Classification Agents

Multi-class classification:

```yaml
- id: topic_classifier
  type: openai-classification
  prompt: >
    Classify the following text into one of these categories.
    Respond with exactly one category.
    
    Text: {{ input }}
  options: [technology, science, politics, entertainment, sports, business]
  queue: orka:classify
  timeout: 20.0
```

### Answer Generation

Comprehensive answer building:

```yaml
- id: answer_builder
  type: openai-answer
  prompt: |
    You are an expert assistant. Based on the following information, provide a comprehensive answer.
    
    Topic Classification: {{ previous_outputs.topic_classifier }}
    Search Results: {{ previous_outputs.web_search }}
    User Question: {{ input }}
    
    Guidelines:
    - Be accurate and factual
    - Cite sources when available
    - Be concise but thorough
    - Use professional tone
  queue: orka:answer
  timeout: 45.0
```

### Local LLM Integration

For privacy-preserving local processing:

```yaml
# Ollama Configuration
- id: local_processor
  type: local_llm
  prompt: |
    Task: {{ input }}
    
    Please provide a detailed response with reasoning.
  model: "llama3.2:latest"
  model_url: "http://localhost:11434/api/generate"
  provider: "ollama"
  temperature: 0.7
  timeout: 60.0
  queue: orka:local

# LM Studio Configuration
- id: lm_studio_agent
  type: local_llm
  prompt: "Analyze this text: {{ input }}"
  model: "mistral-7b-instruct"
  model_url: "http://localhost:1234/v1/chat/completions"
  provider: "lm_studio"
  temperature: 0.3
  queue: orka:lm_studio

# Generic OpenAI-Compatible
- id: custom_local
  type: local_llm
  prompt: "Process: {{ input }}"
  model: "custom-model"
  model_url: "http://localhost:8080/v1/chat/completions"
  provider: "openai_compatible"
  temperature: 0.5
  queue: orka:custom
```

### Validation and Structuring

Answer validation with structured output:

```yaml
- id: answer_validator
  type: validate_and_structure
  prompt: |
    Validate the following answer and structure it for storage.
    
    Question: {{ input }}
    Context: {{ previous_outputs.context_collector }}
    Answer: {{ previous_outputs.answer_builder }}
  store_structure: |
    {
      "topic": "main topic of the answer",
      "confidence": "confidence score 0.0-1.0",
      "key_points": ["list", "of", "main", "points"],
      "sources": ["list", "of", "source", "references"],
      "validity": "assessment of answer quality"
    }
  queue: orka:validate
```

## Memory Management

### Advanced Memory Reading

Context-aware memory retrieval:

```yaml
- id: enhanced_memory_search
  type: memory
  namespace: knowledge_base
  config:
    operation: read
    limit: 15
    enable_context_search: true
    context_weight: 0.4
    temporal_weight: 0.3
    enable_temporal_ranking: true
    context_window_size: 7
    similarity_threshold: 0.65
  prompt: |
    Search for relevant information about: {{ input }}
    
    Context from conversation: {{ previous_outputs | join(', ') }}
  timeout: 20.0
```

### Intelligent Memory Writing

Memory storage with decay management:

```yaml
- id: smart_memory_writer
  type: memory
  namespace: user_interactions
  config:
    operation: write
    memory_type: auto  # Will classify as short-term or long-term
    vector: true       # Enable semantic search
  key_template: "user_{{ user_id }}_{{ timestamp }}"
  metadata:
    user_id: "{{ user_id }}"
    session_id: "{{ session_id }}"
    interaction_type: "{{ previous_outputs.classifier }}"
  decay_config:
    enabled: true
    default_short_term_hours: 4
    default_long_term_hours: 336  # 2 weeks
    importance_rules:
      critical_info: 2.0
      user_feedback: 1.8
      routine_query: 0.6
  prompt: |
    Store this interaction:
    User: {{ input }}
    Response: {{ previous_outputs.answer_builder }}
    Classification: {{ previous_outputs.topic_classifier }}
```

## Search and Tools

### Web Search Configuration

DuckDuckGo search with parameters:

```yaml
- id: web_search
  type: duckduckgo
  prompt: |
    Search for information about: {{ input }}
    
    Focus on recent and authoritative sources.
  params:
    num_results: 8
    region: "us-en"
    safe_search: "moderate"
    time_range: "m"  # Recent results
  queue: orka:search
  timeout: 25.0
```

## Control Flow Nodes

### Dynamic Routing

Smart routing based on content analysis:

```yaml
- id: intelligent_router
  type: router
  params:
    decision_key: content_analysis
    routing_map:
      "factual_question": [web_search, fact_checker, answer_builder]
      "opinion_request": [opinion_generator, bias_checker]
      "how_to_guide": [tutorial_builder, step_validator]
      "troubleshooting": [diagnostic_agent, solution_finder]
      "creative_writing": [creative_agent, style_checker]
  fallback_route: [general_processor]
```

### Parallel Processing

Fork for concurrent validation:

```yaml
- id: comprehensive_validation
  type: fork
  targets:
    - [content_safety_check]
    - [fact_accuracy_check]
    - [sentiment_analysis]
    - [bias_detection]
    - [readability_analysis]
  mode: parallel
  timeout: 30.0

- id: validation_aggregator
  type: join
  prompt: |
    Combine all validation results:
    
    Safety: {{ previous_outputs.content_safety_check }}
    Facts: {{ previous_outputs.fact_accuracy_check }}
    Sentiment: {{ previous_outputs.sentiment_analysis }}
    Bias: {{ previous_outputs.bias_detection }}
    Readability: {{ previous_outputs.readability_analysis }}
    
    Provide overall assessment and recommendations.
  timeout: 15.0
```

### Resilient Processing

Failover with multiple strategies:

```yaml
- id: resilient_information_gathering
  type: failover
  children:
    - id: primary_web_search
      type: duckduckgo
      prompt: "Search: {{ input }}"
      params:
        num_results: 5
        region: "us-en"
    
    - id: memory_fallback
      type: memory
      namespace: knowledge_base
      config:
        operation: read
        limit: 10
      prompt: "Find stored information about: {{ input }}"
    
    - id: llm_knowledge_fallback
      type: openai-answer
      prompt: |
        Based on your training knowledge, provide information about: {{ input }}
        
        Note: This information may not be current.
  queue: orka:resilient_search
```

## Advanced Patterns

### RAG (Retrieval-Augmented Generation)

Knowledge base question answering:

```yaml
- id: knowledge_qa
  type: rag
  params:
    top_k: 10
    score_threshold: 0.75
    rerank: true
  prompt: |
    Answer the question using the retrieved knowledge base information.
    
    Question: {{ input }}
    
    Provide accurate, well-sourced answers.
  queue: orka:rag
  timeout: 40.0
```

### Multi-Stage Processing Pipeline

Complex workflow with multiple stages:

```yaml
orchestrator:
  id: content_processing_pipeline
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 1
      default_long_term_hours: 72

agents:
  # Stage 1: Input Analysis
  - id: input_analyzer
    type: openai-classification
    prompt: "Classify input type and complexity"
    options: [simple_query, complex_question, multi_part_request, creative_task]
    
  # Stage 2: Dynamic Processing
  - id: processing_router
    type: router
    params:
      decision_key: input_analyzer
      routing_map:
        "simple_query": [quick_search, simple_answer]
        "complex_question": [comprehensive_search, detailed_analysis, expert_answer]
        "multi_part_request": [request_decomposer, parallel_processor, result_synthesizer]
        "creative_task": [creative_processor, quality_checker]
  
  # Stage 3: Quality Assurance
  - id: quality_validator
    type: validate_and_structure
    prompt: "Validate and structure the final output"
    
  # Stage 4: Memory Storage
  - id: interaction_storage
    type: memory
    namespace: processed_interactions
    config:
      operation: write
      memory_type: long_term
      vector: true
```

## Configuration Best Practices

### 1. Timeout Management

```yaml
# Short timeouts for simple operations
- id: quick_classifier
  type: openai-binary
  timeout: 10.0

# Longer timeouts for complex processing
- id: comprehensive_analyzer
  type: openai-answer
  timeout: 60.0

# Very long timeouts for local LLMs
- id: local_processor
  type: local_llm
  timeout: 120.0
```

### 2. Error Handling

```yaml
# Always include failover for critical paths
- id: critical_search
  type: failover
  children:
    - id: primary_method
      type: duckduckgo
    - id: backup_method
      type: memory
      config:
        operation: read
```

### 3. Memory Optimization

```yaml
# Use appropriate memory types
- id: temporary_data
  type: memory
  config:
    operation: write
    memory_type: short_term  # Will expire quickly

- id: important_knowledge
  type: memory
  config:
    operation: write
    memory_type: long_term   # Persistent storage
```

### 4. Prompt Engineering

```yaml
- id: well_prompted_agent
  type: openai-answer
  prompt: |
    ROLE: You are an expert {{ domain }} consultant.
    
    CONTEXT: {{ previous_outputs.context_builder }}
    
    TASK: {{ input }}
    
    CONSTRAINTS:
    - Be factual and accurate
    - Cite sources when available
    - Use professional language
    - Keep response under 500 words
    
    FORMAT: Provide a structured response with clear sections.
```

This comprehensive guide covers all the major agent types, configuration patterns, and best practices for building robust OrKa workflows.

[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md) 