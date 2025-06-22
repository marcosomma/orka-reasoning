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

## 🧠 Memory System Configuration

OrKa's memory system is its most powerful feature. Here's how to configure it properly:

### Global Memory Configuration

Configure memory settings at the orchestrator level:

```yaml
orchestrator:
  id: intelligent-assistant
  strategy: sequential
  memory_config:
    # Memory backend configuration
    backend: redis  # or "kafka"
    
    # Decay configuration - inspired by human memory
    decay:
      enabled: true
      default_short_term_hours: 2      # Working memory duration
      default_long_term_hours: 168     # Long-term knowledge (1 week)
      check_interval_minutes: 30       # Cleanup frequency
      
      # Importance-based retention rules
      importance_rules:
        critical_info: 2.0             # Critical info lasts 2x longer
        user_feedback: 1.8             # User corrections are valuable
        successful_pattern: 1.5        # Learn from successes
        routine_query: 0.8             # Routine queries decay faster
        error_event: 0.6               # Errors decay quickly
        
    # Vector embeddings for semantic search
    embeddings:
      enabled: true
      model: "text-embedding-ada-002"  # OpenAI embedding model
      dimension: 1536
      
    # Memory organization
    namespaces:
      default_namespace: "general"
      auto_create: true
      
  agents:
    - memory_reader
    - processor
    - memory_writer
```

### Memory Agent Types

#### Memory Reader - Intelligent Retrieval

```yaml
- id: context_aware_search
  type: memory-reader
  namespace: knowledge_base  # Memory namespace to search
  params:
    # Basic retrieval settings
    limit: 10                          # Max memories to return
    similarity_threshold: 0.7          # Minimum relevance score (0.0-1.0)
    
    # Context-aware search (game-changer for conversations)
    enable_context_search: true        # Use conversation history
    context_weight: 0.4                # Context importance (40%)
    context_window_size: 5             # Look at last 5 agent outputs
    
    # Temporal relevance (recent memories matter more)
    enable_temporal_ranking: true      # Boost recent memories
    temporal_weight: 0.3               # Recency importance (30%)
    temporal_decay_hours: 24           # How fast memories lose recency boost
    
    # Advanced filtering
    memory_type_filter: "all"          # "short_term", "long_term", or "all"
    memory_category_filter: "stored"   # Only retrievable memories
    
    # Performance tuning
    max_search_time_seconds: 5         # Search timeout
    enable_caching: true               # Cache frequent searches
    
  prompt: |
    Find information relevant to: {{ input }}
    
    Consider the conversation context:
    {% for output in previous_outputs %}
    - {{ output }}
    {% endfor %}
    
  timeout: 20
```

#### Memory Writer - Intelligent Storage

```yaml
- id: intelligent_storage
  type: memory-writer
  namespace: user_interactions
      params:
      # Memory classification (ONLY "short_term" and "long_term" are valid)
      # If not specified, OrKa automatically classifies based on:
      # - Event type (success/completion → long_term, debug/processing → short_term)
      # - Importance score (≥0.7 → long_term, <0.7 → short_term) 
      # - Memory category ("stored" memories can be long_term, "log" entries are always short_term)
      memory_type: short_term          # Optional: "short_term" or "long_term" only
      
      # Vector embeddings for semantic search
    vector: true                       # Enable semantic search
    
    # Memory organization
    key_template: "interaction_{timestamp}_{user_id}"
    
    # Metadata for rich memory context
    metadata:
      source: "user_input"
      agent_chain: "{{ agent_sequence }}"
      confidence: "{{ previous_outputs.confidence_scorer }}"
      topic: "{{ previous_outputs.topic_classifier }}"
      
    # Storage optimization
    compress: true                     # Compress large memories
    deduplicate: true                  # Avoid storing duplicates
    
  # Agent-specific decay overrides
  decay_config:
    enabled: true
    default_long_term: false           # Don't force long-term
    default_short_term_hours: 4        # Override global setting
    default_long_term_hours: 336       # 2 weeks for this agent
    
    # Custom importance rules for this agent
    importance_rules:
      user_correction: 3.0             # User corrections are critical
      positive_feedback: 2.0           # Learn from positive feedback
      
  prompt: |
    Store this interaction with context:
    
    User Input: {{ input }}
    Processing Chain: {{ previous_outputs | keys | join(' → ') }}
    Final Result: {{ previous_outputs.final_processor }}
    
    Context Classification: {{ previous_outputs.context_classifier }}
    Confidence Score: {{ previous_outputs.confidence_scorer }}
    
  timeout: 15
```

### Advanced Memory Patterns

#### Pattern 1: Conversational Memory with Context

```yaml
orchestrator:
  id: conversational-ai
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2
      default_long_term_hours: 168

agents:
  # Step 1: Retrieve conversation history
  - id: conversation_retrieval
    type: memory-reader
    namespace: conversations
    params:
      limit: 8
      enable_context_search: true
      context_weight: 0.5              # Conversation context is very important
      temporal_weight: 0.4             # Recent conversations matter
      similarity_threshold: 0.6        # Lower threshold for conversation context
    prompt: |
      Find relevant conversation history for: {{ input }}
      
      Look for:
      - Similar topics discussed
      - Previous questions from this user
      - Related context from recent chats

  # Step 2: Classify interaction type
  - id: interaction_type
    type: openai-classification
    prompt: |
      Based on conversation history: {{ previous_outputs.conversation_retrieval }}
      Current input: {{ input }}
      
      Classify this interaction:
    options: [new_question, followup, clarification, correction, feedback, off_topic]

  # Step 3: Generate contextually aware response
  - id: contextual_response
    type: openai-answer
    prompt: |
      Conversation History:
      {{ previous_outputs.conversation_retrieval }}
      
      Interaction Type: {{ previous_outputs.interaction_type }}
      Current Input: {{ input }}
      
      Generate a response that:
      1. Acknowledges relevant conversation history
      2. Addresses the current input appropriately
      3. Maintains conversation continuity
      4. References previous context when helpful

  # Step 4: Store the complete interaction
  - id: conversation_storage
    type: memory-writer
    namespace: conversations
    params:
              # memory_type automatically classified based on content and importance
      vector: true
      metadata:
        interaction_type: "{{ previous_outputs.interaction_type }}"
        has_history: "{{ previous_outputs.conversation_retrieval | length > 0 }}"
        timestamp: "{{ now() }}"
    prompt: |
      User: {{ input }}
      Type: {{ previous_outputs.interaction_type }}
      History Found: {{ previous_outputs.conversation_retrieval | length }} items
      Assistant: {{ previous_outputs.contextual_response }}
```

#### Pattern 2: Knowledge Base with Intelligent Updates

```yaml
orchestrator:
  id: knowledge-base-system
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 24     # Queries are short-term
      default_long_term_hours: 2160    # Knowledge lasts 90 days
      importance_rules:
        verified_fact: 3.0             # Verified facts are very important
        user_contributed: 2.0          # User contributions matter
        frequently_accessed: 1.8       # Popular knowledge stays longer

agents:
  # Step 1: Analyze the query
  - id: query_analyzer
    type: openai-classification
    prompt: |
      Analyze this query: {{ input }}
      
      What type of knowledge interaction is this?
    options: [factual_lookup, how_to_guide, troubleshooting, definition, comparison, update_request]

  # Step 2: Search existing knowledge
  - id: knowledge_search
    type: memory-reader
    namespace: knowledge_base
    params:
      limit: 15
      enable_context_search: false     # Don't use conversation context for facts
      temporal_weight: 0.1             # Facts don't age much
      similarity_threshold: 0.75       # High threshold for factual accuracy
      memory_type_filter: "long_term"  # Only search established knowledge
    prompt: |
      Search for information about: {{ input }}
      Query type: {{ previous_outputs.query_analyzer }}

  # Step 3: Determine if knowledge needs updating
  - id: knowledge_freshness_check
    type: openai-binary
    prompt: |
      Existing knowledge: {{ previous_outputs.knowledge_search }}
      New query: {{ input }}
      Query type: {{ previous_outputs.query_analyzer }}
      
      Does the existing knowledge need updating or is new information required?
      Consider:
      - Is the existing information outdated?
      - Does the query ask for information not covered?
      - Is there conflicting information?

  # Step 4: Router based on knowledge freshness
  - id: knowledge_router
    type: router
    params:
      decision_key: knowledge_freshness_check
      routing_map:
        "true": [web_search, fact_verification, knowledge_updater]
        "false": [knowledge_responder]

  # Step 5a: Web search for new information (if needed)
  - id: web_search
    type: duckduckgo
    prompt: |
      Search for current information about: {{ input }}
      Focus on: {{ previous_outputs.query_analyzer }}

  # Step 5b: Verify new information
  - id: fact_verification
    type: openai-answer
    prompt: |
      Verify and structure this information:
      
      Query: {{ input }}
      Existing Knowledge: {{ previous_outputs.knowledge_search }}
      New Information: {{ previous_outputs.web_search }}
      
      Provide:
      1. Verified facts
      2. Confidence level (0-100)
      3. Sources
      4. What changed from existing knowledge

  # Step 5c: Update knowledge base
  - id: knowledge_updater
    type: memory-writer
    namespace: knowledge_base
    params:
      memory_type: long_term           # Force long-term storage
      vector: true
      metadata:
        query_type: "{{ previous_outputs.query_analyzer }}"
        confidence: "{{ previous_outputs.fact_verification.confidence }}"
        sources: "{{ previous_outputs.web_search.sources }}"
        last_updated: "{{ now() }}"
        verification_status: "verified"
    decay_config:
      enabled: true
      default_long_term_hours: 2160    # 90 days for verified knowledge
    prompt: |
      Updated Knowledge Entry:
      
      Topic: {{ input }}
      Type: {{ previous_outputs.query_analyzer }}
      Verified Information: {{ previous_outputs.fact_verification }}
      Sources: {{ previous_outputs.web_search }}
      
      Previous Knowledge: {{ previous_outputs.knowledge_search }}

  # Step 5d: Respond with existing knowledge
  - id: knowledge_responder
    type: openai-answer
    prompt: |
      Based on existing knowledge: {{ previous_outputs.knowledge_search }}
      Answer the query: {{ input }}
      
      Provide a comprehensive response using the stored knowledge.

  # Step 6: Store the query interaction
  - id: query_storage
    type: memory-writer
    namespace: query_log
    params:
      memory_type: short_term          # Queries are temporary
      vector: false                    # Don't need vector search for logs
      metadata:
        query_type: "{{ previous_outputs.query_analyzer }}"
        knowledge_found: "{{ previous_outputs.knowledge_search | length > 0 }}"
        needed_update: "{{ previous_outputs.knowledge_freshness_check }}"
    prompt: |
      Query Log:
      User Query: {{ input }}
      Type: {{ previous_outputs.query_analyzer }}
      Knowledge Found: {{ previous_outputs.knowledge_search | length }} entries
      Update Needed: {{ previous_outputs.knowledge_freshness_check }}
```

#### Pattern 3: Multi-Agent Memory Sharing

```yaml
orchestrator:
  id: collaborative-research
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 6
      default_long_term_hours: 720     # 30 days for research
      
agents:
  # Research Agent - Gathers information
  - id: researcher
    type: openai-answer
    prompt: |
      Research this topic thoroughly: {{ input }}
      
      Provide:
      1. Key facts and findings
      2. Important sources
      3. Areas needing further investigation
      4. Confidence level in findings

  # Store research findings
  - id: research_storage
    type: memory-writer
    namespace: shared_research
    params:
      memory_type: long_term
      vector: true
      metadata:
        research_phase: "initial"
        agent: "researcher"
        topic: "{{ input }}"
        confidence: "{{ previous_outputs.researcher.confidence }}"
    prompt: |
      Research Findings:
      Topic: {{ input }}
      Findings: {{ previous_outputs.researcher }}
      Research Date: {{ now() }}

  # Analysis Agent - Retrieves and analyzes research
  - id: research_retrieval
    type: memory-reader
    namespace: shared_research
    params:
      limit: 20
      enable_context_search: true
      similarity_threshold: 0.7
      temporal_weight: 0.2             # Recent research is more relevant
    prompt: |
      Find all research related to: {{ input }}
      Include related topics and cross-references

  - id: analyzer
    type: openai-answer
    prompt: |
      Analyze the research findings:
      
      Current Topic: {{ input }}
      Research Findings: {{ previous_outputs.research_retrieval }}
      
      Provide:
      1. Key insights and patterns
      2. Gaps in research
      3. Recommendations
      4. Confidence in analysis

  # Store analysis
  - id: analysis_storage
    type: memory-writer
    namespace: shared_research
    params:
      memory_type: long_term
      vector: true
      metadata:
        research_phase: "analysis"
        agent: "analyzer"
        based_on_research: "{{ previous_outputs.research_retrieval | length }}"
    prompt: |
      Research Analysis:
      Topic: {{ input }}
      Analysis: {{ previous_outputs.analyzer }}
      Based on {{ previous_outputs.research_retrieval | length }} research items

  # Synthesis Agent - Creates final output
  - id: synthesis_retrieval
    type: memory-reader
    namespace: shared_research
    params:
      limit: 50                        # Get comprehensive view
      enable_context_search: true
      similarity_threshold: 0.6        # Broader search for synthesis
    prompt: |
      Retrieve all research and analysis for: {{ input }}

  - id: synthesizer
    type: openai-answer
    prompt: |
      Create a comprehensive synthesis:
      
      Topic: {{ input }}
      All Research & Analysis: {{ previous_outputs.synthesis_retrieval }}
      
      Provide:
      1. Executive summary
      2. Detailed findings
      3. Recommendations
      4. Future research directions
      5. Confidence assessment

  # Store final synthesis
  - id: synthesis_storage
    type: memory-writer
    namespace: final_reports
    params:
      memory_type: long_term
      vector: true
      metadata:
        document_type: "synthesis"
        based_on_items: "{{ previous_outputs.synthesis_retrieval | length }}"
        completion_date: "{{ now() }}"
    decay_config:
      enabled: true
      default_long_term_hours: 2160    # Keep final reports for 90 days
    prompt: |
      Final Research Synthesis:
      Topic: {{ input }}
      Synthesis: {{ previous_outputs.synthesizer }}
      Based on {{ previous_outputs.synthesis_retrieval | length }} research items
```

### Memory Namespace Organization

Organize your memories logically:

```yaml
orchestrator:
  id: organized-system
  memory_config:
    # Define namespace hierarchy
    namespaces:
      # User interactions
      conversations: "user_chats"
      feedback: "user_feedback"
      corrections: "user_corrections"
      
      # Knowledge management
      facts: "verified_facts"
      procedures: "how_to_guides"
      definitions: "term_definitions"
      
      # System operations
      errors: "error_logs"
      performance: "system_metrics"
      debugging: "debug_traces"
      
      # Collaborative work
      research: "shared_research"
      analysis: "data_analysis"
      reports: "final_outputs"

agents:
  # Use specific namespaces for different types of memory
  - id: user_memory
    type: memory-reader
    namespace: conversations        # Only search user conversations
    
  - id: fact_memory
    type: memory-reader
    namespace: facts               # Only search verified facts
    
  - id: error_memory
    type: memory-writer
    namespace: errors              # Store errors separately
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