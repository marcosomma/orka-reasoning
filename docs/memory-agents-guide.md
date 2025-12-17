# Memory Agents - Complete Guide 🧠

> **OrKa's Memory System** - Guide to memory agents with operation-based default configuration

## 🧠 What Are Memory Agents?

Memory agents provide Redis-based storage and retrieval for workflow data. Key features:

- **Configurable Expiration** - Time-based expiration with importance factor multipliers
- **Vector Search** - Use embeddings for semantic similarity search
- **Configurable Retention** - Apply different expiration rules based on usage patterns
- **Namespace Organization** - Use namespaces and categories for logical separation

### Memory Agent Architecture

```yaml
- id: memory_storage
  type: memory          # Memory agent type
  memory_preset: "episodic"  # Preset template (optional)
  config:
    operation: write    # "read" or "write" operation
  namespace: conversations   # Logical memory organization
  params:
    vector: true       # Enable semantic search
    limit: 5           # For read operations
  prompt: "Store this interaction: {{ input }}"
```

## 🔄 Memory Operations

### 📖 Reading Memory (Search & Retrieval)

Memory reading searches stored memories using vector similarity:

```yaml
- id: memory_search
  type: memory
  config:
    operation: read     # Search existing memories
  namespace: knowledge_base
  params:
    limit: 5                    # Max results to return
    similarity_threshold: 0.8   # Minimum relevance (0.0-1.0)
    enable_context_search: true # Use conversation context
    enable_temporal_ranking: true # Boost recent memories
  prompt: "Find information about: {{ input }}"
```

**Key Parameters for Reading:**
- `limit` - Maximum number of memories to retrieve
- `similarity_threshold` - Minimum semantic similarity score
- `enable_context_search` - Use conversation history for context
- `enable_temporal_ranking` - Prefer recent memories
- `context_weight` - Weight for conversation context (0.0-1.0)
- `temporal_weight` - Weight for recent memories (0.0-1.0)

### 📝 Writing Memory (Storage & Persistence)

Memory writing stores data in Redis with optional vector embeddings:

```yaml
- id: memory_store
  type: memory
  config:
    operation: write    # Store new memories
  namespace: conversations
  params:
    vector: true        # Enable semantic search indexing
    metadata:
      source: "user_interaction"
      confidence: "high"
      tags: ["important", "conversation"]
  prompt: |
    Store this conversation:
    User: {{ input }}
    Assistant: {{ previous_outputs.response_generator }}
```

**Key Parameters for Writing:**
- `vector` - Enable vector embeddings for semantic search
- `metadata` - Additional structured information to store
- `key_template` - Custom key naming pattern
- `memory_type` - Override automatic classification ("short_term" or "long_term")
- `importance_score` - Override automatic importance calculation (0.0-1.0)

## 🧠 Memory Presets (Operation-Based Defaults)

**NEW in v0.9.2**: Memory presets provide configuration templates with operation-specific defaults based on retention duration patterns:

### 1. **Sensory Memory** (`sensory`)
```yaml
memory_preset: "sensory"
```
- **For**: Near real-time data, sensor input, immediate processing (deployment-dependent)
- **Duration**: 15 minutes (very short retention)
- **Read Defaults**: Fast retrieval (limit=3, similarity_threshold=0.95)
- **Write Defaults**: Minimal indexing (vector=false, speed-optimized)
- **Use Cases**: IoT sensors, streaming data, immediate alerts

### 2. **Working Memory** (`working`)  
```yaml
memory_preset: "working"
```
- **For**: Active processing, session context, temporary calculations
- **Duration**: 2-8 hours
- **Read Defaults**: Context-aware (limit=5, similarity_threshold=0.7, context_weight=0.5)
- **Write Defaults**: Session optimization (vector=true, temporary indexing)
- **Use Cases**: User sessions, workflow context, active processing

### 3. **Episodic Memory** (`episodic`)
```yaml
memory_preset: "episodic"
```
- **For**: Personal experiences, conversations, interaction history
- **Duration**: 1 day - 1 week
- **Read Defaults**: Conversational (limit=8, similarity_threshold=0.6, temporal_weight=0.3)
- **Write Defaults**: Rich metadata (vector=true, conversation-optimized)
- **Use Cases**: Chatbots, customer service, user interactions

### 4. **Semantic Memory** (`semantic`)
```yaml
memory_preset: "semantic"
```
- **For**: Knowledge, facts, learned information, documentation
- **Duration**: 3 days - 90 days
- **Read Defaults**: Knowledge matching (limit=10, similarity_threshold=0.65, no temporal bias)
- **Write Defaults**: Knowledge optimization (vector=true, long-term indexing)
- **Use Cases**: Knowledge bases, fact storage, documentation

### 5. **Procedural Memory** (`procedural`)
```yaml
memory_preset: "procedural"
```
- **For**: Skills, patterns, workflows, process optimization
- **Duration**: 1 week - 6 months
- **Read Defaults**: Pattern recognition (limit=6, similarity_threshold=0.7, minimal temporal bias)
- **Write Defaults**: Process indexing (vector=true, pattern-optimized)
- **Use Cases**: Workflow optimization, skill learning, process improvement

### 6. **Meta Memory** (`meta`)
```yaml
memory_preset: "meta"
```
- **For**: System insights, performance metrics, self-reflection
- **Duration**: 2 days - 1 year
- **Read Defaults**: System analysis (limit=4, similarity_threshold=0.8, high precision)
- **Write Defaults**: Performance optimization (vector=true, high-quality indexing)
- **Use Cases**: System monitoring, performance analysis, meta-learning

## 🎯 Common Memory Patterns

### 1. **Conversational Memory Pattern**
```yaml
orchestrator:
  memory_preset: "episodic"  # Main conversation memory

agents:
  # Search conversation history
  - id: conversation_search
    type: memory
    memory_preset: "episodic"
    config:
      operation: read
    namespace: conversations
    params:
      limit: 3
      similarity_threshold: 0.7
    prompt: "Find relevant conversation history: {{ input }}"

  # Generate contextual response
  - id: response_generator
    type: local_llm
    model: openai/gpt-oss-20b
    model_url: http://localhost:1234
    provider: lm_studio
    temperature: 0.7
    prompt: |
      Previous conversation: {{ previous_outputs.conversation_search }}
      Current input: {{ input }}
      
      Generate a contextual response.

  # Store the interaction
  - id: conversation_store
    type: memory
    memory_preset: "episodic"
    config:
      operation: write
    namespace: conversations
    params:
      vector: true
    prompt: |
      User: {{ input }}
      Assistant: {{ previous_outputs.response_generator }}
```

### 2. **Knowledge Management Pattern**
```yaml
agents:
  # Extract knowledge from input
  - id: knowledge_extractor
    type: local_llm
    model: openai/gpt-oss-20b
    model_url: http://localhost:1234
    provider: lm_studio
    temperature: 0.3
    prompt: "Extract key facts and knowledge from: {{ input }}"

  # Store knowledge with semantic memory
  - id: knowledge_store
    type: memory
    memory_preset: "semantic"
    config:
      operation: write
    namespace: knowledge_base
    params:
      vector: true
      metadata:
        source: "extraction"
        category: "facts"
    prompt: "{{ previous_outputs.knowledge_extractor }}"

  # Later: Search knowledge base
  - id: knowledge_search
    type: memory
    memory_preset: "semantic"
    config:
      operation: read
    namespace: knowledge_base
    params:
      limit: 5
      similarity_threshold: 0.8
    prompt: "Find relevant knowledge about: {{ input }}"
```

### 3. **System Monitoring Pattern**
```yaml
agents:
  # Monitor system performance
  - id: performance_analyzer
    type: local_llm
    model: openai/gpt-oss-20b
    model_url: http://localhost:1234
    provider: lm_studio
    temperature: 0.2
    prompt: |
      Analyze system performance:
      Input processing time: {{ processing_time }}
      Memory usage: {{ memory_stats }}
      Agent outputs: {{ previous_outputs | keys | length }}

  # Store system insights
  - id: system_memory
    type: memory
    memory_preset: "meta"
    config:
      operation: write
    namespace: system_insights
    params:
      vector: true
      metadata:
        category: "performance"
        timestamp: "{{ now() }}"
    prompt: |
      System Analysis:
      {{ previous_outputs.performance_analyzer }}
      
      Metrics:
      - Processing time: {{ processing_time }}
      - Memory usage: {{ memory_stats }}
      - Success rate: {{ success_rate }}
```

## 🤖 Local LLM Configuration

All examples use **local LLM models** for privacy and cost-effectiveness. The standard configuration uses Ollama with a local model:

```yaml
- id: my_agent
  type: local_llm
  model: openai/gpt-oss-20b              # Model name in Ollama
  model_url: http://localhost:1234  # Ollama API endpoint
  provider: lm_studio                # LLM provider
  temperature: 0.7               # Creativity level (0.0-1.0)
  prompt: "Your prompt here"
```

**Temperature Guidelines:**
- `0.1-0.2` - Deterministic tasks (classification, scoring)
- `0.3-0.5` - Analytical tasks (reasoning, extraction)  
- `0.6-0.8` - Creative tasks (conversation, generation)

**Model Recommendations:**
- **Fast**: `llama3.2:3b` for quick responses
- **Balanced**: `gpt-oss:20b` for good quality/speed
- **Quality**: `llama3.1:70b` for best results

## 🛠️ Advanced Memory Configuration

### Memory Agent with Custom Decay
```yaml
- id: custom_memory
  type: memory
  memory_preset: "episodic"  # Base configuration
  config:
    operation: write
  namespace: conversations
  decay:  # Override preset values
    default_long_term_hours: 336  # 2 weeks instead of 1
    importance_rules:
      event_type_boosts:
        user_feedback: 0.5  # Custom event boost
  params:
    vector: true
```

### Namespace Organization
```yaml
agents:
  # Organize by domain
  - id: tech_memory
    type: memory
    namespace: technology
    
  - id: business_memory
    type: memory
    namespace: business
    
  # Organize by user
  - id: user_memory
    type: memory
    namespace: "user_{{ user_id }}"
    
  # Organize by session
  - id: session_memory
    type: memory
    namespace: "session_{{ session_id }}"
```

### Metadata Enrichment
```yaml
- id: enriched_memory
  type: memory
  config:
    operation: write
  namespace: conversations
  params:
    vector: true
    metadata:
      # User context
      user_id: "{{ user_id }}"
      session_id: "{{ session_id }}"
      
      # Content analysis
      sentiment: "{{ previous_outputs.sentiment_analyzer }}"
      topic: "{{ previous_outputs.topic_classifier }}"
      language: "{{ detected_language }}"
      
      # Quality metrics
      confidence: "{{ previous_outputs.confidence_scorer }}"
      importance: "{{ calculated_importance }}"
      
      # Processing info
      agent_chain: "{{ previous_outputs | keys | join(' → ') }}"
      processing_time: "{{ processing_duration }}"
```

## 🔍 Memory Search Strategies

### 1. **Semantic Search**
```yaml
- id: semantic_search
  type: memory
  config:
    operation: read
  params:
    similarity_threshold: 0.8  # High semantic similarity
    limit: 5
```

### 2. **Contextual Search**
```yaml
- id: contextual_search
  type: memory
  config:
    operation: read
  params:
    enable_context_search: true
    context_weight: 0.5  # Strong context influence
    similarity_threshold: 0.6  # Lower threshold for context
```

### 3. **Recent Memory Bias**
```yaml
- id: recent_search
  type: memory
  config:
    operation: read
  params:
    enable_temporal_ranking: true
    temporal_weight: 0.4  # Strong recency bias
    temporal_decay_hours: 24  # Boost last 24 hours
```

### 4. **Hybrid Search**
```yaml
- id: hybrid_search
  type: memory
  config:
    operation: read
  params:
    enable_context_search: true
    enable_temporal_ranking: true
    context_weight: 0.3
    temporal_weight: 0.2
    similarity_threshold: 0.7
```

## 🚀 Best Practices

### 1. **Choose the Right Preset**
| Use Case | Recommended Preset |
|----------|-------------------|
| **Chatbots & Conversations** | `episodic` |
| **Knowledge Bases** | `semantic` |
| **Near real-time Processing (deployment-dependent)** | `sensory` |
| **Workflow Management** | `procedural` |
| **System Monitoring** | `meta` |
| **Session Context** | `working` |

### 2. **Namespace Strategy**
```yaml
# Good: Organized by domain
namespace: "conversations"
namespace: "knowledge_base"  
namespace: "system_metrics"

# Good: Organized by user/session
namespace: "user_{{ user_id }}"
namespace: "session_{{ session_id }}"

# Avoid: Generic namespaces
namespace: "default"
namespace: "memory"
```

### 3. **Metadata Strategy**
```yaml
# Good: Rich, searchable metadata
metadata:
  source: "user_interaction"
  category: "conversation"
  sentiment: "positive"
  topic: "technical_support"
  user_id: "{{ user_id }}"
  confidence: 0.9

# Avoid: Empty or minimal metadata
metadata: {}
```

### 4. **Search Optimization**
```yaml
# For precision: High threshold
similarity_threshold: 0.8

# For recall: Lower threshold  
similarity_threshold: 0.6

# For conversations: Enable context
enable_context_search: true
context_weight: 0.4

# For recent bias: Enable temporal
enable_temporal_ranking: true
temporal_weight: 0.3
```

### 5. **Memory Lifecycle**
```yaml
# Short-lived memories
memory_preset: "sensory"   # 15 minutes
memory_preset: "working"   # 2-8 hours

# Medium-lived memories  
memory_preset: "episodic"  # 1 day - 1 week

# Long-lived memories
memory_preset: "semantic"    # 3 days - 90 days
memory_preset: "procedural"  # 1 week - 6 months  
memory_preset: "meta"        # 2 days - 1 year
```

## 🔧 Troubleshooting

### Common Issues

**Q: Memory agent not storing anything**
```yaml
# Check: operation is set to "write"
config:
  operation: write  # Required for storage

# Check: prompt generates content
prompt: "Store: {{ input }}"  # Must produce output
```

**Q: Search returns no results**
```yaml
# Lower similarity threshold
params:
  similarity_threshold: 0.6  # Was 0.8

# Check namespace matches
namespace: "conversations"  # Must match stored namespace

# Enable broader search
params:
  enable_context_search: true
  limit: 10  # Increase result limit
```

**Q: Memory decays too quickly**
```yaml
# Use longer-lived preset
memory_preset: "semantic"  # Instead of "working"

# Override decay settings
decay:
  default_long_term_hours: 168  # 1 week
```

**Q: Poor search relevance**
```yaml
# Enable vector search
params:
  vector: true  # For semantic similarity

# Add rich metadata
metadata:
  topic: "{{ previous_outputs.topic_classifier }}"
  category: "conversation"

# Use context for better results
params:
  enable_context_search: true
  context_weight: 0.4
```

## 📊 Memory Performance

### Optimization Tips

1. **Vector Search**: Recommended: enable `vector: true` for semantic search; validate performance and costs for your workload
2. **Namespaces**: Use specific namespaces to limit search scope  
3. **Thresholds**: Tune similarity thresholds based on your use case
4. **Limits**: Set appropriate `limit` values to balance quality vs speed
5. **Metadata**: Add rich metadata for better filtering and organization

### Monitoring Memory Usage

```yaml
# Monitor memory statistics
- id: memory_stats
  type: memory
  config:
    operation: read
  params:
    limit: 0  # Just get stats, no content
  prompt: "Get memory statistics"

# The memory agent will return stats in metadata
```

Memory agents provide the foundation for workflows with persistent state that can retrieve and build on previous interactions. Use this guide to leverage OrKa's memory capabilities in your applications.
---
← [Memory System](MEMORY_SYSTEM_GUIDE.md) | [📚 INDEX](index.md) | [GraphScout](GRAPH_SCOUT_AGENT.md) →
