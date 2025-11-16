# OrKa V0.9.2 Configuration Guide - Simplified with Memory Presets

> ⚠️ **Deprecation Notice:** This general configuration guide is being deprecated. Memory-specific configuration has been moved to [MEMORY_SYSTEM_GUIDE.md](MEMORY_SYSTEM_GUIDE.md), and YAML configuration is now in [YAML_CONFIGURATION.md](YAML_CONFIGURATION.md). This file will be archived in v1.0.

> **Last Updated:** 16 November 2025  
> **Status:** 🔴 Deprecated - Use primary guides  
> **Replaced By:** [YAML_CONFIGURATION.md](YAML_CONFIGURATION.md) | [MEMORY_SYSTEM_GUIDE.md](MEMORY_SYSTEM_GUIDE.md)  
> **Related:** [INDEX](INDEX.md)

[📘 Getting Started](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Memory System](./MEMORY_SYSTEM_GUIDE.md) | [🧠 Memory Presets](./memory-presets.md) | [🐛 Debugging](./DEBUGGING.md)

## Overview

**NEW in V0.9.2**: OrKa introduces **Memory Presets** that simplify memory configuration. This guide covers the memory preset system alongside traditional configuration options for fine-grained control when needed.

## 🧠 Memory Presets Configuration - 90% Complexity Reduction

### Simplified Memory Configuration (Recommended)

**NEW in V0.9.2**: Use memory presets to simplify configuration:

```yaml
# Simple preset configuration (replaces 15+ lines of decay rules)
agents:
  - id: my_memory_agent
    type: memory
    memory_preset: "episodic"     # Cognitive memory type
    config:
      operation: read             # or "write" 
    namespace: conversations
```

**Available Memory Presets:**
- `sensory` - Real-time data (15 min retention) 
- `working` - Active context (4 hours retention)
- `episodic` - Personal experiences (7 days retention)
- `semantic` - Facts and knowledge (30 days retention) 
- `procedural` - Skills and processes (90 days retention)
- `meta` - System performance (365 days retention)

> **See Complete Guide**: [Memory Presets Documentation](./memory-presets.md)

### Environment Variables (Simplified)

**Minimal Configuration for V0.9.2:**
```bash
# Memory presets handle decay configuration with defaults
export ORKA_MEMORY_BACKEND=redisstack             # Default: redisstack  
export REDIS_URL=redis://localhost:6380/0         # RedisStack connection URL

# Optional: Override preset defaults (rarely needed)
# export ORKA_MEMORY_DECAY_ENABLED=true           # Handled by presets
```

**Legacy Configuration (for fine-grained control):**
```bash
# Only use if you need to override preset defaults
export ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2      # Default: 2 hours
export ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168     # Default: 168 hours (1 week)
export ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES=30  # Default: 30 minutes
```

### YAML Configuration

**Orchestrator-Level Memory Configuration:**
```yaml
orchestrator:
  id: my-orchestrator
  strategy: sequential
  memory_config:
    # Backend selection
    backend: redisstack                    # Options: redis, redisstack
    
    # Memory decay configuration
    decay:
      enabled: true
      default_short_term_hours: 2          # Working memory retention
      default_long_term_hours: 168         # Knowledge retention (1 week)
      check_interval_minutes: 30           # Cleanup frequency
      
      # Importance-based retention multipliers
      importance_rules:
        critical_info: 3.0                 # Critical info lasts 3x longer
        user_feedback: 2.5                 # User corrections are valuable
        successful_pattern: 2.0            # Learn from successes
        frequently_accessed: 1.8           # Popular memories stay longer
        routine_query: 0.8                 # Routine queries decay faster
        error_event: 0.5                   # Errors decay quickly
    
    # RedisStack-specific configuration
    redisstack:
      vector_index_name: "orka_enhanced_memory"
      vector_dimensions: 384               # all-MiniLM-L6-v2 embeddings
      hnsw_params:
        M: 16                             # HNSW connections per node
        EF_CONSTRUCTION: 200              # Build-time accuracy
        EF_RUNTIME: 10                    # Query-time accuracy
      embedding_model: "all-MiniLM-L6-v2" # SentenceTransformers model
```

**Agent-Level Memory Configuration Override:**
```yaml
agents:
  - id: critical_processor
    type: openai-answer
    # Override global decay settings for this agent
    decay_config:
      enabled: true
      default_short_term_hours: 8         # Keep critical processing longer
      default_long_term_hours: 720        # 30 days for critical data
      importance_rules:
        high_confidence: 2.0
        user_correction: 4.0
    params:
      memory_type: long_term              # Force long-term storage
    prompt: "Process critical information: {{ input }}"
```

## RedisStack Configuration

### Index Schema

OrKa automatically creates the `orka_enhanced_memory` index with the following schema:

```redis
FT.CREATE orka_enhanced_memory 
  ON HASH PREFIX 1 orka_memory:
  SCHEMA
    content TEXT SORTABLE
    node_id TEXT SORTABLE  
    trace_id TEXT SORTABLE
    namespace TEXT SORTABLE
    category TEXT SORTABLE
    memory_type TEXT SORTABLE
    importance_score NUMERIC SORTABLE
    timestamp NUMERIC SORTABLE
    embedding VECTOR HNSW 6 TYPE FLOAT32 DIM 384 DISTANCE_METRIC COSINE M 16 EF_CONSTRUCTION 200
```

### Connection Configuration

**Basic RedisStack Setup:**
```bash
# Start RedisStack with Docker
docker run -d -p 6380:6380 --name orka-redis redis/redis-stack:latest

# Configure OrKa to use RedisStack
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6380/0
```

**Production RedisStack Configuration:**
```yaml
# docker-compose.yml for production
version: '3.8'
services:
  redis-stack:
    image: redis/redis-stack:latest
    ports:
      - "6380:6380"
      - "8001:8001"  # RedisInsight UI
    volumes:
      - redis_data:/data
    environment:
      - REDIS_ARGS=--save 60 1000 --maxmemory 2gb --maxmemory-policy allkeys-lru
    command: redis-stack-server --requirepass your-secure-password
    restart: unless-stopped

volumes:
  redis_data:
```

**Advanced Connection Settings:**
```bash
# Authentication and SSL
export REDIS_URL=redis://:password@localhost:6380/0

# Redis Cluster (multiple nodes)
export REDIS_URL=redis://node1:6380,node2:6380,node3:6380/0

# Connection pooling and timeouts
export REDIS_POOL_MAX_CONNECTIONS=20
export REDIS_CONNECTION_TIMEOUT=30
export REDIS_SOCKET_TIMEOUT=30
```

## FT.SEARCH Query Configuration

### Query Syntax and Common Issues

**Correct FT.SEARCH Syntax:**
```redis
# Vector search with metadata filtering
FT.SEARCH orka_enhanced_memory "(@node_id:cognitive_debate_loop) => [KNN 10 @embedding $query_vec AS distance]" 
  PARAMS 2 query_vec "\x01\x02\x03..." 
  SORTBY distance 
  RETURN 6 content node_id trace_id namespace category distance

# Text search with filtering
FT.SEARCH orka_enhanced_memory "(@namespace:conversations) (@category:stored) machine learning"
  RETURN 3 content node_id timestamp
  LIMIT 0 10
```

**Common Query Errors and Fixes:**
```bash
# ❌ WRONG: Syntax error at offset 1 near ,
FT.SEARCH orka_enhanced_memory "(*) @node_id:cognitive_debate_loop"

# ✅ CORRECT: Proper parentheses and escaping
FT.SEARCH orka_enhanced_memory "(@node_id:cognitive_debate_loop)"

# ❌ WRONG: Invalid vector search syntax  
FT.SEARCH orka_enhanced_memory "*=>[KNN 10 @embedding $query_vec]"

# ✅ CORRECT: Proper vector search with metadata
FT.SEARCH orka_enhanced_memory "* => [KNN 10 @embedding $query_vec AS distance]"
  PARAMS 2 query_vec "\x..." RETURN 3 content distance node_id
```

### Embedding Configuration

**SentenceTransformers Model Settings:**
```python
# OrKa uses all-MiniLM-L6-v2 by default
# Embedding dimensions: 384
# Distance metric: COSINE
# Format: FLOAT32

# Custom embedding model configuration
embedding_config = {
    "model_name": "all-MiniLM-L6-v2",      # Default model
    "device": "cuda" if torch.cuda.is_available() else "cpu",
    "normalize_embeddings": True,           # Normalize for cosine similarity
    "batch_size": 32                       # Batch size for embedding generation
}
```

## Component-Specific Configuration

### LoopNode Configuration

```yaml
agents:
  - id: improvement_loop
    type: loop
    max_loops: 8                          # Maximum iterations
    score_threshold: 0.85                 # Quality threshold to stop
    score_extraction_pattern: "QUALITY_SCORE:\\s*([0-9.]+)"
    
    # Cognitive extraction for learning
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
    
    # Past loops metadata structure  
    past_loops_metadata:
      iteration: "{{ loop_number }}"
      quality_score: "{{ score }}"
      key_insights: "{{ insights }}"
      areas_to_improve: "{{ improvements }}"
      mistakes_found: "{{ mistakes }}"
    
    internal_workflow:
      # Sub-workflow configuration goes here
```

### Memory Reader Configuration

```yaml
agents:
  - id: enhanced_memory_search
    type: memory-reader
    namespace: knowledge_base
    params:
      # Search configuration
      limit: 10                          # Maximum results
      similarity_threshold: 0.8          # Relevance threshold (0.0-1.0)
      enable_context_search: true        # Use conversation context
      context_weight: 0.4                # Context importance
      temporal_weight: 0.3               # Recency boost
      
      # RedisStack-specific parameters
      ef_runtime: 20                     # HNSW query accuracy
      enable_hybrid_search: true         # Combine vector + text search
      vector_weight: 0.7                 # Vector vs text search balance
      
      # Metadata filtering
      memory_type_filter: "all"          # "short_term", "long_term", "all"
      category_filter: "stored"          # Only retrievable memories
      metadata_filters:
        confidence: "> 0.8"              # High-confidence only
        verified: "true"                 # Verified information only
```

### Memory Writer Configuration

```yaml
agents:
  - id: memory_storage
    type: memory-writer
    namespace: conversations
    params:
      vector: true                       # Enable semantic search
      memory_type: auto                  # Auto-classify as short/long term
      
      # Rich metadata for enhanced retrieval
      metadata:
        interaction_type: "{{ previous_outputs.classifier }}"
        confidence: "{{ previous_outputs.confidence_scorer }}"
        user_id: "{{ user_id }}"
        session_id: "{{ session_id }}"
        processing_time: "{{ processing_duration }}"
        
      # Storage optimization
      compress: true                     # Compress large memories
      deduplicate: true                  # Avoid duplicates
      max_size_kb: 100                   # Size limit
```

## Environment Setup Guide

### Development Environment

```bash
# 1. Install OrKa
pip install orka-reasoning

# 2. Start RedisStack
docker run -d -p 6380:6380 --name orka-redis redis/redis-stack:latest

# 3. Configure environment
export OPENAI_API_KEY=your-api-key-here
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6380/0
export ORKA_MEMORY_DECAY_ENABLED=true
export ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2
export ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168

# 4. Verify configuration
orka memory configure
orka memory stats
```

### Production Environment

```bash
# 1. Production-grade RedisStack cluster
# See docker-compose.yml example above

# 2. Environment configuration
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://:password@redis-cluster:6380/0
export ORKA_MEMORY_DECAY_ENABLED=true
export ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=8      # 8 hours for logs
export ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168     # 1 week for knowledge
export ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES=60

# 3. Performance tuning
export REDIS_POOL_MAX_CONNECTIONS=50
export ORKA_MAX_CONCURRENT_REQUESTS=100
export ORKA_TIMEOUT_SECONDS=300

# 4. Monitoring setup
export ORKA_METRICS_ENABLED=true
export ORKA_LOG_LEVEL=INFO
```

## Configuration Validation

### Verify Settings

```bash
# Check current configuration
orka memory configure

# Expected output:
# === OrKa Memory Configuration ===
# Backend: redisstack
# Decay Enabled: true
# Short-term Hours: 2.0
# Long-term Hours: 168.0
# Check Interval: 30 minutes
# Redis URL: redis://localhost:6380/0
# Vector Index: orka_enhanced_memory
# Embedding Model: all-MiniLM-L6-v2
```

### Test Configuration

```bash
# Test memory operations
orka memory stats
orka memory watch --interval 5

# Test RedisStack connectivity
redis-cli PING
redis-cli FT._LIST  # Should show orka_enhanced_memory

# Test vector search
redis-cli FT.INFO orka_enhanced_memory
```

### Common Configuration Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| TTL mismatch | Logs show 0.1h/0.2h instead of 2h/168h | Check environment variables override YAML settings |
| FT.SEARCH failures | `Syntax error at offset 1` | Verify RedisStack installation and index creation |
| Empty search results | `num_results: 0` consistently | Check vector index exists and embeddings are generated |
| Memory not expiring | `expired_entries: 0` always | Verify decay is enabled and check_interval is reasonable |
| Connection errors | Redis connection timeouts | Check Redis URL and network connectivity |

## Template Resolution Configuration

### Template Variable Requirements

**Standard Variables Available:**
- `{{ input }}` - Original input to the orchestrator
- `{{ previous_outputs }}` - Dictionary of all previous agent outputs
- `{{ previous_outputs.agent_id }}` - Specific agent output
- `{{ loop_number }}` - Current loop iteration (in LoopNode)
- `{{ score }}` - Extracted quality score (in LoopNode)
- `{{ now() }}` - Current timestamp

**Custom Template Configuration:**
```yaml
orchestrator:
  template_config:
    strict_undefined: true              # Fail on undefined variables (recommended)
    auto_escape: false                  # Don't escape HTML in templates
    trim_blocks: true                   # Remove whitespace around blocks
    lstrip_blocks: true                 # Remove leading whitespace
```

### Debugging Template Issues

**Common Template Errors:**
```yaml
# ❌ WRONG: Variable doesn't exist
prompt: "Score: {{ score }}"  # Only available in LoopNode

# ✅ CORRECT: Check availability or provide default
prompt: "Score: {{ score | default('not available') }}"

# ❌ WRONG: Nested access without safety
prompt: "Agreement: {{ previous_outputs.agreement_finder.result }}"

# ✅ CORRECT: Safe nested access
prompt: "Agreement: {{ previous_outputs.agreement_finder.result | default('no agreement') }}"
```

## Advanced Configuration Examples

### Cognitive Society Workflow Configuration

```yaml
orchestrator:
  id: cognitive-society
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 4       # Debate context retention
      default_long_term_hours: 336      # Long-term consensus storage (2 weeks)
      importance_rules:
        consensus_reached: 3.0
        high_agreement: 2.5
        dissenting_view: 2.0            # Keep dissenting views for diversity
```

### High-Performance Search Configuration  

```yaml
orchestrator:
  memory_config:
    redisstack:
      # Optimize for speed
      hnsw_params:
        M: 24                           # Higher connectivity for speed
        EF_CONSTRUCTION: 300            # Higher build quality
        EF_RUNTIME: 50                  # Higher query accuracy
      connection_pool:
        max_connections: 20             # Support concurrent operations
        connection_timeout: 10          # Fast timeout for responsiveness
```

For more specific configuration examples, see:
- [Memory System Guide](./MEMORY_SYSTEM_GUIDE.md) for memory-specific configuration
- [YAML Configuration Guide](./yaml-configuration-guide.md) for agent configuration
- [Debugging Guide](./DEBUGGING.md) for troubleshooting configuration issues