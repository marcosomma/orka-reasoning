# OrKa-Reasoning


<div align="center">

<img src="https://orkacore.com/assets/ORKA_logo.png" alt="OrKa Logo" width="256" height="256"/>

[![orkacore](https://img.shields.io/badge/orkacore-.com-green?labelColor=blue&style=for-the-badge&link=https://orkacore.com/)](https://orkacore.com/)

![GitHub Tag](https://img.shields.io/github/v/tag/marcosomma/orka-reasoning?color=blue)
![PyPI - License](https://img.shields.io/pypi/l/orka-reasoning?color=blue)

[![codecov](https://codecov.io/gh/marcosomma/orka-reasoning/branch/master/graph/badge.svg?token=V91X4WGBBZ)](https://codecov.io/gh/marcosomma/orka-reasoning) [![orka-reasoning](https://snyk.io/advisor/python/orka-reasoning/badge.svg)](https://snyk.io/advisor/python/orka-reasoning)

[![PyPi](https://img.shields.io/badge/pypi-%23ececec.svg?style=for-the-badge&logo=pypi&logoColor=1f73b7)](https://pypi.org/project/orka-reasoning/) [![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/marcosomma/orka-ui) [![Static Badge](https://img.shields.io/badge/Docs-blue?style=for-the-badge&logo=googledocs&logoColor=%23fff&link=https%3A%2F%2Forkacore.com%2Fdocs%2Findex.html)](https://orkacore.com/docs/index.html)

[![Pepy Total Downloads](https://img.shields.io/pepy/dt/orka-reasoning?style=for-the-badge&label=Downloads%20from%20April%202025&color=blue&link=https%3A%2F%2Fpiptrends.com%2Fpackage%2Forka-reasoning)](https://clickpy.clickhouse.com/dashboard/orka-reasoning)

</div>

**AI Orchestration with 100x Faster Vector Search** - OrKa transforms your AI workflows with YAML-driven agent orchestration, intelligent memory management, and lightning-fast semantic search powered by RedisStack HNSW indexing.

---

## 🚀 What's New in V0.8.x

- **🔄 Advanced Loop Node** - Intelligent iterative workflows with cognitive insight extraction
- **🧠 Cognitive Society Framework** - Multi-agent deliberation and consensus building
- **🎯 Threshold-Based Execution** - Continue until quality meets requirements
- **📊 Past Loops Memory** - Learn from previous attempts and iteratively improve
- **🎓 Cognitive Insight Extraction** - Automatically identify insights, improvements, and mistakes
- **🐛 Bug Fixes** - Integration test stability and agent type compatibility improvements
- **🚀 Performance Optimizations** - Enhanced memory management and workflow execution
- **🗂️ Curated Example Suite** - See [`examples/README.md`](./examples/README.md) for the updated, categorized templates and quickstarts

## 🚀 What's New in V0.7.x

- **🚀 100x Faster Vector Search** - RedisStack HNSW indexing now default across all components
- **⚡ Sub-millisecond Search Latency** - O(log n) complexity for massive datasets
- **🏗️ Unified Architecture** - All components now use RedisStack with intelligent fallback
- **🖥️ Professional CLI Dashboard** - Real-time performance monitoring and metrics
- **🔧 Zero-Breaking Migration** - Complete backward compatibility maintained

---

## ⚡ 2-Minute Quickstart

Get OrKa running with enterprise-grade performance in 2 minutes:

**Prerequisites:** Ensure Docker is installed and running on your system.

```bash
# 1. Install OrKa with all dependencies
pip install orka-reasoning fastapi uvicorn kafka-python

# Optional: Install schema management features (Avro/Protobuf support)
pip install orka-reasoning[schema]

# 2. Set your OpenAI key
export OPENAI_API_KEY=your-key-here

# 3. Start OrKa (automatically includes RedisStack + 100x faster vector search)
# For LOCAL development:
orka-start

# For PRODUCTION to ensure Kafka streaming:
orka-kafka

# 4. Create a simple workflow
cat > quickstart.yml << EOF
orchestrator:
  id: intelligent-qa
  strategy: sequential
  agents: [classifier, memory_search, web_search, answer_builder, memory_store]

agents:
  - id: classifier
    type: openai-classification
    prompt: "Classify this query type"
    options: [factual_question, how_to_guide, current_events, opinion]

  - id: memory_search
    type: memory-reader
    namespace: knowledge_base
    params:
      limit: 5
      enable_context_search: true
      similarity_threshold: 0.8
    prompt: "Find relevant information about: {{ input }}"

  - id: web_search
    type: duckduckgo
    prompt: "{{ input }}"

  - id: answer_builder
    type: openai-answer
    prompt: |
      Query: {{ input }}
      Type: {{ previous_outputs.classifier }}
      Memory: {{ previous_outputs.memory_search }}
      Web Results: {{ previous_outputs.web_search }}
      
      Build a comprehensive answer combining memory and web results.

  - id: memory_store
    type: memory-writer
    namespace: knowledge_base
    params:
      vector: true
      metadata:
        query_type: "{{ previous_outputs.classifier }}"
        has_web_results: "{{ previous_outputs.web_search | length > 0 }}"
        confidence: "high"
    prompt: |
      Query: {{ input }}
      Answer: {{ previous_outputs.answer_builder }}
      Sources: Web + Memory
EOF

# 5. Run your intelligent AI workflow
orka run ./quickstart.yml "What are the latest developments in quantum computing?"

# 6. Monitor performance (in another terminal)
orka memory watch

# 7. Optional: Run OrKa UI for visual workflow monitoring
docker pull marcosomma/orka-ui:latest
docker run -it -p 80:80 --name orka-ui marcosomma/orka-ui:latest
# Then open http://localhost in your browser
```

This creates an intelligent Q&A system that:
- Classifies your query type
- Searches existing knowledge with 100x faster vector search
- Gets fresh information from the web
- Combines both sources into a comprehensive answer
- Stores the interaction for future reference

---

### Performance Comparison

| Setup | Vector Search | Typical Use Case | Performance |
|-------|---------------|------------------|-------------|
| **RedisStack** | ✅ HNSW Indexing | Production AI, semantic search | **100x faster** |
| **Basic Redis** | ❌ Text only | Development, simple workflows | Standard |

---

## 🧠 Hands-On: Build Your First AI Memory System

Let's build a conversational AI that remembers and learns from interactions:

### Step 1: Create the Workflow

```yaml
# conversational-ai.yml
orchestrator:
  id: conversational-ai
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2    # Conversations fade after 2 hours
      default_long_term_hours: 168   # Important info lasts 1 week
      check_interval_minutes: 30     # Memory cleanup frequency
  agents:
    - conversation_context
    - interaction_classifier  
    - response_generator
    - memory_storage

agents:
  # Retrieve relevant conversation history
  - id: conversation_context
    type: memory-reader
    namespace: user_conversations
    params:
      limit: 5
      enable_context_search: true
      context_weight: 0.4
      temporal_weight: 0.3
      enable_temporal_ranking: true
    prompt: "Find relevant conversation history for: {{ input }}"

  # Understand the interaction type
  - id: interaction_classifier
    type: openai-classification
    prompt: |
      Based on history: {{ previous_outputs.conversation_context }}
      Current input: {{ input }}
      
      Classify this interaction:
    options: [question, followup, correction, new_topic, feedback]

  # Generate contextually aware response
  - id: response_generator
    type: openai-answer
    prompt: |
      Conversation history: {{ previous_outputs.conversation_context }}
      Interaction type: {{ previous_outputs.interaction_classifier }}
      Current input: {{ input }}
      
      Generate a response that acknowledges the conversation history
      and maintains continuity.

  # Store the interaction with intelligent classification
  - id: memory_storage
    type: memory-writer
    namespace: user_conversations
    params:
      vector: true  # Enable semantic search
      metadata:
        interaction_type: "{{ previous_outputs.interaction_classifier }}"
        has_history: "{{ previous_outputs.conversation_context | length > 0 }}"
        response_quality: "pending_feedback"
        timestamp: "{{ now() }}"
    # memory_type automatically classified based on importance
    prompt: |
      User: {{ input }}
      Type: {{ previous_outputs.interaction_classifier }}
      Assistant: {{ previous_outputs.response_generator }}
```

### Step 2: Run and Monitor

```bash
# Start the conversation
python -m orka.orka_cli ./conversational-ai.yml "Hello, I'm working on a machine learning project"

# Continue the conversation (it will remember context)
python -m orka.orka_cli ./conversational-ai.yml "What algorithms would you recommend for image classification?"

# Monitor memory performance in real-time
python -m orka.orka_cli memory watch
```

You'll see a professional dashboard like this:
```
┌─────────────────────────────────────────────────────────────┐
│ OrKa Memory Dashboard - 14:23:45 | Backend: redisstack     │
├─────────────────────────────────────────────────────────────┤
│ 🔧 Backend: redisstack (HNSW)  ⚡ Decay: ✅ Enabled        │
│ 📊 Memories: 1,247            📝 Active: 1,224             │
│ 🚀 HNSW Performance: 1,203     Avg: 2.1ms | Hybrid: 856   │
│ 🧠 Memory Types: Short: 423    💾 Long: 801 | 🔥 Recent   │
└─────────────────────────────────────────────────────────────┘
```

### Step 3: Verify Memory Learning

```bash
# Check what the AI remembers about you
python -m orka.orka_cli memory stats

# Search specific memories
redis-cli FT.SEARCH orka:mem:idx "@namespace:user_conversations machine learning" LIMIT 0 5
```

---

## 📚 Ready-to-Use Workflow Templates

### 1. Intelligent Q&A with Web Search

```yaml
# intelligent-qa.yml
orchestrator:
  id: smart-qa
  strategy: sequential
  agents: [search_needed, router, web_search, answer_with_sources]

agents:
  - id: search_needed
    type: openai-binary
    prompt: "Does this question require recent information? {{ input }}"

  - id: router
    type: router
    params:
      decision_key: search_needed
      routing_map:
        "true": [web_search, answer_with_sources]
        "false": [answer_with_sources]

  - id: web_search
    type: duckduckgo
    prompt: "{{ input }}"

  - id: answer_with_sources
    type: openai-answer
    prompt: |
      Question: {{ input }}
      {% if previous_outputs.web_search %}
      Web Results: {{ previous_outputs.web_search }}
      {% endif %}
      
      Provide a comprehensive answer with sources.
```

### 2. Content Analysis Pipeline

```yaml
# content-analyzer.yml
orchestrator:
  id: content-analysis
  strategy: parallel
  agents: [fork_analysis, join_results]

agents:
  - id: fork_analysis
    type: fork
    targets:
      - [sentiment_analysis]
      - [topic_classification]
      - [toxicity_check]

  - id: sentiment_analysis
    type: openai-classification
    options: [positive, negative, neutral]
    prompt: "Analyze sentiment: {{ input }}"

  - id: topic_classification
    type: openai-classification
    options: [tech, business, science, politics, sports]
    prompt: "Classify topic: {{ input }}"

  - id: toxicity_check
    type: openai-binary
    prompt: "Is this content toxic or inappropriate? {{ input }}"

  - id: join_results
    type: join
    prompt: |
      Combine analysis results:
      Sentiment: {{ previous_outputs.sentiment_analysis }}
      Topic: {{ previous_outputs.topic_classification }}
      Safe: {{ previous_outputs.toxicity_check }}
```

### 3. Knowledge Base Builder

```yaml
# knowledge-builder.yml
orchestrator:
  id: knowledge-builder
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_long_term_hours: 720  # Keep knowledge for 30 days
  agents: [fact_checker, knowledge_storer, knowledge_retriever]

agents:
  - id: fact_checker
    type: openai-answer
    prompt: |
      Verify this information and rate confidence (1-10):
      {{ input }}

  - id: knowledge_storer
    type: memory-writer
    namespace: knowledge_base
    params:
      memory_type: long_term
      vector: true
      metadata:
        confidence: "{{ previous_outputs.fact_checker.confidence | default('unknown') }}"
        verified: "{{ previous_outputs.fact_checker.verified | default(false) }}"
        domain: "{{ previous_outputs.fact_checker.domain | default('general') }}"
    prompt: |
      Fact: {{ input }}
      Verification: {{ previous_outputs.fact_checker }}

  - id: knowledge_retriever
    type: memory-reader
    namespace: knowledge_base
    params:
      limit: 10
      similarity_threshold: 0.8
    prompt: "Find related knowledge: {{ input }}"
```

### 4. Iterative Improvement Loop

```yaml
# iterative-improver.yml
orchestrator:
  id: iterative-improver
  strategy: sequential
  agents: [improvement_loop, final_processor]

agents:
  - id: improvement_loop
    type: loop
    max_loops: 8
    score_threshold: 0.85
    score_extraction_pattern: "QUALITY_SCORE:\\s*([0-9.]+)"
    
    # Cognitive extraction to learn from each iteration
    cognitive_extraction:
      enabled: true
      extract_patterns:
        insights:
          - "(?:provides?|identifies?|shows?)\\s+(.+?)(?:\\n|$)"
          - "(?:comprehensive|thorough|detailed)\\s+(.+?)(?:\\n|$)"
        improvements:
          - "(?:lacks?|needs?|requires?|should)\\s+(.+?)(?:\\n|$)"
          - "(?:would improve|could benefit)\\s+(.+?)(?:\\n|$)"
        mistakes:
          - "(?:overlooked|missed|inadequate)\\s+(.+?)(?:\\n|$)"
          - "(?:weakness|gap|limitation)\\s+(.+?)(?:\\n|$)"
    
    # Track learning across iterations
    past_loops_metadata:
      iteration: "{{ loop_number }}"
      quality_score: "{{ score }}"
      key_insights: "{{ insights }}"
      areas_to_improve: "{{ improvements }}"
      mistakes_found: "{{ mistakes }}"
    
    # Internal workflow that gets repeated
    internal_workflow:
      orchestrator:
        id: improvement-cycle
        strategy: sequential
        agents: [analyzer, quality_scorer]
      
      agents:
        - id: analyzer
          type: openai-answer
          prompt: |
            Analyze this request: {{ input }}
            
            {% if previous_outputs.past_loops %}
            Previous analysis attempts ({{ previous_outputs.past_loops | length }}):
            {% for loop in previous_outputs.past_loops %}
            
            Iteration {{ loop.iteration }} (Score: {{ loop.quality_score }}):
            - Key insights: {{ loop.key_insights }}
            - Areas to improve: {{ loop.areas_to_improve }}
            - Mistakes found: {{ loop.mistakes_found }}
            {% endfor %}
            
            Build upon these insights and address the identified gaps.
            {% endif %}
            
            Provide a comprehensive, high-quality analysis.
        
        - id: quality_scorer
          type: openai-answer
          prompt: |
            Rate the quality of this analysis (0.0 to 1.0):
            {{ previous_outputs.analyzer.result }}
            
            Consider:
            - Depth and comprehensiveness
            - Accuracy and relevance
            - Clarity and structure
            - Addressing of key points
            
            Format: QUALITY_SCORE: X.XX
            
            If score is below 0.85, identify specific areas for improvement.

  - id: final_processor
    type: openai-answer
    prompt: |
      Process the final result from the improvement loop:
      
      Iterations completed: {{ previous_outputs.improvement_loop.loops_completed }}
      Final quality score: {{ previous_outputs.improvement_loop.final_score }}
      Threshold met: {{ previous_outputs.improvement_loop.threshold_met }}
      
      Learning Journey:
      {% for loop in previous_outputs.improvement_loop.past_loops %}
      **Iteration {{ loop.iteration }}** (Score: {{ loop.quality_score }}):
      - Insights: {{ loop.key_insights }}
      - Improvements: {{ loop.areas_to_improve }}
      - Mistakes: {{ loop.mistakes_found }}
      {% endfor %}
      
      Final Analysis: {{ previous_outputs.improvement_loop.result }}
      
      Provide a meta-analysis of the learning process and final insights.
```

### 5. Cognitive Society Deliberation

```yaml
# cognitive-society.yml
orchestrator:
  id: cognitive-society
  strategy: sequential
  agents: [deliberation_loop, consensus_builder]

agents:
  - id: deliberation_loop
    type: loop
    max_loops: 5
    score_threshold: 0.90
    score_extraction_pattern: "CONSENSUS_SCORE:\\s*([0-9.]+)"
    
    internal_workflow:
      orchestrator:
        id: multi-agent-deliberation
        strategy: sequential
        agents: [fork_perspectives, join_views, consensus_evaluator]
      
      agents:
        - id: fork_perspectives
          type: fork
          targets:
            - [logical_reasoner]
            - [empathetic_reasoner]
            - [skeptical_reasoner]
            - [creative_reasoner]
        
        - id: logical_reasoner
          type: openai-answer
          prompt: |
            Provide logical, evidence-based reasoning for: {{ input }}
            
            {% if previous_outputs.past_loops %}
            Previous logical insights:
            {% for loop in previous_outputs.past_loops %}
            - Round {{ loop.round }}: {{ loop.logical_insights }}
            {% endfor %}
            
            Build upon and refine these logical perspectives.
            {% endif %}
        
        - id: empathetic_reasoner
          type: openai-answer
          prompt: |
            Provide empathetic, human-centered reasoning for: {{ input }}
            
            {% if previous_outputs.past_loops %}
            Previous empathetic insights:
            {% for loop in previous_outputs.past_loops %}
            - Round {{ loop.round }}: {{ loop.empathetic_insights }}
            {% endfor %}
            
            Deepen and expand these empathetic perspectives.
            {% endif %}
        
        - id: skeptical_reasoner
          type: openai-answer
          prompt: |
            Provide critical, skeptical analysis of: {{ input }}
            
            {% if previous_outputs.past_loops %}
            Previous critical insights:
            {% for loop in previous_outputs.past_loops %}
            - Round {{ loop.round }}: {{ loop.critical_insights }}
            {% endfor %}
            
            Strengthen and refine these critical perspectives.
            {% endif %}
        
        - id: creative_reasoner
          type: openai-answer
          prompt: |
            Provide creative, innovative thinking for: {{ input }}
            
            {% if previous_outputs.past_loops %}
            Previous creative insights:
            {% for loop in previous_outputs.past_loops %}
            - Round {{ loop.round }}: {{ loop.creative_insights }}
            {% endfor %}
            
            Expand and develop these creative perspectives.
            {% endif %}
        
        - id: join_views
          type: join
          group: fork_perspectives
        
        - id: consensus_evaluator
          type: openai-answer
          prompt: |
            Evaluate consensus among these perspectives on: {{ input }}
            
            Logical: {{ previous_outputs.logical_reasoner.response }}
            Empathetic: {{ previous_outputs.empathetic_reasoner.response }}
            Skeptical: {{ previous_outputs.skeptical_reasoner.response }}
            Creative: {{ previous_outputs.creative_reasoner.response }}
            
            Rate the consensus level (0.0-1.0):
            CONSENSUS_SCORE: [score]
            
            Explain areas of agreement and remaining disagreements.

  - id: consensus_builder
    type: openai-answer
    prompt: |
      Build final consensus from the deliberation:
      
      Original question: {{ input }}
      Deliberation rounds: {{ previous_outputs.deliberation_loop.loops_completed }}
      Final consensus score: {{ previous_outputs.deliberation_loop.final_score }}
      
      Final result: {{ previous_outputs.deliberation_loop.result }}
      
      Provide a unified perspective that incorporates all viewpoints.
```

---

## 🎯 Agent Quick Reference

### Memory Agents (Powered by RedisStack HNSW)

```yaml
# Read memories with 100x faster search
- id: memory_search
  type: memory-reader
  namespace: my_namespace
  params:
    limit: 10                        # Max results
    enable_context_search: true      # Use conversation context
    similarity_threshold: 0.8        # Relevance threshold
    enable_temporal_ranking: true    # Boost recent memories
  prompt: "Search for: {{ input }}"

# Store memories with intelligent decay
- id: memory_store
  type: memory-writer
  namespace: my_namespace
  params:
    vector: true                     # Enable semantic search
    # memory_type: auto-classified   # short_term or long_term
    metadata:
      source: "user_input"
      confidence: "high"
      timestamp: "{{ now() }}"
  prompt: "Store: {{ input }}"
```

### LLM Agents

```yaml
# Binary classification
- id: yes_no_classifier
  type: openai-binary
  prompt: "Is this a question? {{ input }}"

# Multi-class classification  
- id: topic_classifier
  type: openai-classification
  options: [tech, science, business, other]
  prompt: "Classify: {{ input }}"

# Answer generation
- id: answer_builder
  type: openai-answer
  prompt: |
    Context: {{ previous_outputs.context }}
    Question: {{ input }}
    Generate a detailed answer.
```

### Routing & Control Flow

```yaml
# Dynamic routing
- id: content_router
  type: router
  params:
    decision_key: content_type
    routing_map:
      "question": [search_agent, answer_agent]
      "statement": [fact_checker]

# Parallel processing
- id: parallel_validator
  type: fork
  targets:
    - [sentiment_check]
    - [toxicity_check]
    - [fact_validation]

# Wait for parallel completion
- id: combine_results
  type: join
  prompt: "Combine all validation results"

# Iterative improvement loop
- id: iterative_improver
  type: loop
  max_loops: 5
  score_threshold: 0.85
  score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
  cognitive_extraction:
    enabled: true
    extract_patterns:
      insights: ["(?:provides?|shows?)\\s+(.+?)(?:\\n|$)"]
      improvements: ["(?:lacks?|needs?)\\s+(.+?)(?:\\n|$)"]
      mistakes: ["(?:overlooked|missed)\\s+(.+?)(?:\\n|$)"]
  past_loops_metadata:
    iteration: "{{ loop_number }}"
    score: "{{ score }}"
    insights: "{{ insights }}"
  internal_workflow:
    orchestrator:
      id: improvement-cycle
      agents: [analyzer, scorer]
    agents:
      - id: analyzer
        type: openai-answer
        prompt: |
          Analyze: {{ input }}
          {% if previous_outputs.past_loops %}
          Previous attempts: {{ previous_outputs.past_loops }}
          {% endif %}
      - id: scorer
        type: openai-answer
        prompt: "Rate quality (0.0-1.0): {{ previous_outputs.analyzer.result }}"
```

---

## 🖥️ CLI Commands You'll Use Daily

```bash
# Real-time memory monitoring with RedisStack metrics
orka memory watch --interval 3

# Check memory statistics and performance
orka memory stats

# Clean up expired memories (with HNSW index optimization)
orka memory cleanup --dry-run

# View configuration and backend status
orka memory configure

# Run workflows
orka run ./my-workflow.yml "Your input here"

# Check system health
orka system status

# Start OrKa with Redis only (for development)
orka-redis

# Start OrKa with Kafka (for production)
orka-kafka
```

---

## 🚀 Production Deployment

### Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  redis-stack:
    image: redis/redis-stack:latest
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    environment:
      - REDIS_ARGS=--save 60 1000

  orka:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis-stack:6379/0
      - ORKA_MEMORY_BACKEND=redisstack
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis-stack

volumes:
  redis_data:
```

### Environment Variables

```bash
# Core settings
export OPENAI_API_KEY=your-key-here
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6379/0

# Performance tuning
export ORKA_MAX_CONCURRENT_REQUESTS=100
export ORKA_TIMEOUT_SECONDS=300

# Memory management
export ORKA_MEMORY_DECAY_ENABLED=true
export ORKA_DEFAULT_SHORT_TERM_HOURS=2
export ORKA_DEFAULT_LONG_TERM_HOURS=168
```

---

## 🔧 Migration from Basic Redis

Upgrade to RedisStack for 100x performance improvement:

```bash
# 1. Analyze your current memories
python scripts/migrate_to_redisstack.py --dry-run

# 2. Backup existing data
redis-cli BGSAVE

# 3. Start RedisStack
docker run -d -p 6379:6379 --name orka-redis redis/redis-stack:latest

# 4. Migrate your memories
python scripts/migrate_to_redisstack.py --migrate

# 5. Validate migration
python scripts/migrate_to_redisstack.py --validate

# 6. Update your applications (no code changes needed!)
export ORKA_MEMORY_BACKEND=redisstack
```

---

## 🐛 Troubleshooting

### Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| `"unknown command 'FT.CREATE'"` | You're using basic Redis. Install RedisStack: `docker run -d -p 6379:6379 redis/redis-stack:latest` |
| `"Cannot connect to Redis"` | Check Redis is running: `redis-cli ping` |
| Memory search returns no results | Check vector indexing: `redis-cli FT._LIST` and see [Debugging Guide](./docs/DEBUGGING.md) |
| Slow performance | Verify RedisStack HNSW: `orka memory configure` |
| Out of memory errors | Run cleanup: `orka memory cleanup` |
| TTL mismatch (0.1h vs 2h) | Environment variables override YAML - see [Configuration Guide](./docs/CONFIGURATION.md) |
| FT.SEARCH syntax errors | Check query syntax in [Components Guide](./docs/COMPONENTS.md#shared-memory-reader) |

### Performance Optimization

```bash
# Check current performance
orka memory watch

# Optimize HNSW index
redis-cli FT.CONFIG SET FORK_GC_CLEAN_THRESHOLD 100

# Monitor Redis memory usage
redis-cli INFO memory
```

---

## 📊 Performance Benchmarks

| Metric | Basic Redis | RedisStack HNSW | Improvement |
|--------|-------------|-----------------|-------------|
| **Vector Search** | 50-200ms | 0.5-5ms | **100x faster** |
| **Memory Usage** | 100% baseline | 40% | **60% reduction** |
| **Throughput** | 1,000/sec | 50,000/sec | **50x higher** |
| **Concurrent Searches** | 10-50 | 1,000+ | **20x more** |

---

## 📚 Learn More

- 📖 **[Configuration Guide](./docs/CONFIGURATION.md)** - Detailed TTL, RedisStack, and component configuration
- 🐛 **[Debugging Guide](./docs/DEBUGGING.md)** - Troubleshooting procedures and diagnostic tools
- 🧩 **[Core Components](./docs/COMPONENTS.md)** - Agreement Finder, LoopNode, Memory Reader documentation
- 🧠 **[Memory System Guide](./docs/MEMORY_SYSTEM_GUIDE.md)** - Complete memory architecture and patterns
- 🎥 **[Video Tutorial](https://www.youtube.com/watch?v=hvVc8lSoADI)** - 5-minute OrKa overview
- 📚 **[Full Documentation](https://orkacore.web.app/docs)** - Complete API reference
- 💬 **[Community Discord](https://discord.gg/orka)** - Get help and share workflows
- 🐛 **[GitHub Issues](https://github.com/marcosomma/orka-reasoning/issues)** - Report bugs and request features

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## 📜 License

Apache 2.0 License. See [LICENSE](./LICENSE) for details.

---

<div align="center">

**Ready to supercharge your AI workflows?**

```bash
pip install orka-reasoning && docker run -d -p 6379:6379 redis/redis-stack:latest
```

[Get Started Now →](https://github.com/marcosomma/orka-reasoning/blob/master/docs/getting-started.md)

</div>
