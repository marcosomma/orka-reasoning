# OrKa Memory System - Complete Guide

[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md) | [⚙️ Configuration](./CONFIGURATION.md) | [🐛 Debugging](./DEBUGGING.md) | [🧩 Components](./COMPONENTS.md) | [🧪 Testing](./TESTING.md) | [🔗 Integration](./INTEGRATION_EXAMPLES.md)

## 🧠 Introduction to OrKa's Memory System

OrKa's memory system is inspired by human cognitive science and provides sophisticated memory management that makes AI agents truly intelligent and contextually aware. Unlike traditional stateless AI systems, OrKa agents can remember, learn, and build on previous interactions.

### 🎯 Why Memory Matters for AI Agents

**Traditional AI Limitations:**
- Forget everything between interactions
- No learning from experience
- Repetitive processing of same information
- No contextual awareness
- Limited reasoning capabilities

**OrKa's Memory Advantages:**
- **Contextual Conversations**: Build on previous interactions
- **Learning from Experience**: Improve based on successes and failures
- **Efficient Processing**: Avoid recomputing known information
- **Transparent Reasoning**: Complete audit trail of decisions
- **Intelligent Forgetting**: Automatic cleanup of outdated information

## 🏗️ Memory Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Memory        │    │   Memory        │    │   Memory        │
│   Writers       │    │   Storage       │    │   Readers       │
│                 │    │                 │    │                 │
│ • Classification│    │ • Redis/RedisStack │    │ • Context Search│
│ • Vectorization │────│ • Namespaces    │────│ • Similarity    │
│ • Metadata      │    │ • Decay System  │    │ • Temporal Rank │
│ • Compression   │    │ • Indexing      │    │ • Filtering     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Memory        │
                    │   Management    │
                    │                 │
                    │ • Decay Engine  │
                    │ • CLI Tools     │
                    │ • Monitoring    │
                    │ • Cleanup       │
                    └─────────────────┘
```

### Memory Types

**Short-term Memory (Working Memory)**
- Duration: Minutes to hours
- Purpose: Temporary context, intermediate results
- Examples: Current conversation, processing steps
- Automatic cleanup: Yes

**Long-term Memory (Knowledge Store)**
- Duration: Days to months
- Purpose: Important knowledge, successful patterns
- Examples: Verified facts, user preferences, learned procedures
- Retention: Based on importance and access patterns

**Auto-classification**
- OrKa automatically determines memory type based on:
  - Content analysis
  - Interaction patterns
  - Importance scoring
  - User feedback

## 🔧 Memory Configuration

### Environment Setup

**Redis Backend (Recommended for Development)**
```bash
# Install and start Redis
brew install redis          # macOS
sudo apt install redis-server  # Ubuntu
redis-server

# Configure OrKa
export ORKA_MEMORY_BACKEND=redis
export REDIS_URL=redis://localhost:6380/0

# Optional: Memory-specific settings
export ORKA_MEMORY_DECAY_ENABLED=true
export ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2
export ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168
export ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES=30
```

**RedisStack Backend (Production)**
```bash
# Using Docker Compose
cat > docker-compose.yml << EOF
version: '3.8'
services:
  redis-stack:
    image: redis/redis-stack:latest
    ports:
      - "6380:6380"
    volumes:
      - redis_data:/data
    environment:
      - REDIS_ARGS=--save 60 1000

volumes:
  redis_data:
EOF

docker-compose up -d

# Configure OrKa
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6380/0
```

### YAML Configuration

**Global Memory Settings**
```yaml
orchestrator:
  id: intelligent-system
  strategy: sequential
  memory_config:
    # Backend configuration
    backend: redis  # or "redisstack"
    
    # Intelligent decay system
    decay:
      enabled: true
      default_short_term_hours: 2      # Working memory
      default_long_term_hours: 168     # Knowledge store (1 week)
      check_interval_minutes: 30       # Cleanup frequency
      
      # Importance-based retention multipliers
      importance_rules:
        critical_info: 3.0             # Critical info lasts 3x longer
        user_feedback: 2.5             # User corrections are valuable
        successful_pattern: 2.0        # Learn from successes
        frequently_accessed: 1.8       # Popular memories stay longer
        routine_query: 0.8             # Routine queries decay faster
        error_event: 0.5               # Errors decay quickly
        
    # Vector embeddings for semantic search
    embeddings:
      enabled: true
      model: "text-embedding-ada-002"  # OpenAI model
      dimension: 1536
      batch_size: 100                  # Process embeddings in batches
      
    # Memory organization
    namespaces:
      default_namespace: "general"
      auto_create: true
      cleanup_empty: true
      
    # Performance optimization
    caching:
      enabled: true
      ttl_seconds: 300                 # Cache search results for 5 minutes
      max_size: 1000                   # Max cached items
      
  agents:
    - memory_reader
    - processor
    - memory_writer
```

## 🔍 Memory Reading - Intelligent Retrieval

### Basic Memory Reader

```yaml
- id: simple_memory_search
  type: memory-reader
  namespace: conversations
  params:
    limit: 5                           # Max memories to return
    similarity_threshold: 0.7          # Minimum relevance (0.0-1.0)
  prompt: "Find relevant memories about: {{ input }}"
```

### Advanced Context-Aware Search

```yaml
- id: context_aware_search
  type: memory-reader
  namespace: knowledge_base
  params:
    # Basic retrieval
    limit: 15
    similarity_threshold: 0.65
    
    # Context-aware search (revolutionary for conversations)
    enable_context_search: true        # Use conversation history
    context_weight: 0.4                # Context importance (40%)
    context_window_size: 7             # Look at last 7 agent outputs
    
    # Temporal relevance (recent memories boost)
    enable_temporal_ranking: true      # Boost recent memories
    temporal_weight: 0.3               # Recency importance (30%)
    temporal_decay_hours: 48           # How fast recency boost fades
    
    # Advanced filtering
    memory_type_filter: "all"          # "short_term", "long_term", "all"
    memory_category_filter: "stored"   # Only retrievable memories
    exclude_categories: ["debug", "error"]  # Skip debug info
    
    # Metadata filtering
    metadata_filters:
      confidence: "> 0.8"              # Only high-confidence memories
      verified: "true"                 # Only verified information
      user_id: "{{ user_id }}"         # User-specific memories
      
    # Performance tuning
    max_search_time_seconds: 8         # Search timeout
    enable_caching: true               # Cache frequent searches
    parallel_search: true             # Search multiple indexes in parallel
    
  prompt: |
    Find comprehensive information about: {{ input }}
    
    Consider the conversation context:
    {% for output in previous_outputs %}
    Previous: {{ output }}
    {% endfor %}
    
    Focus on:
    - Direct answers to the question
    - Related context that might be helpful
    - Recent interactions on similar topics
    
  timeout: 25
```

### Search Algorithm Explained

OrKa's memory search uses a sophisticated multi-factor ranking algorithm:

1. **Semantic Similarity (40%)**: Vector embeddings match meaning
2. **Context Overlap (30%)**: Relevance to recent conversation
3. **Temporal Decay (20%)**: Recent memories get boost
4. **Keyword Matching (10%)**: Exact term matches (TF-IDF)
5. **Importance Scoring**: Metadata-based relevance boost

**Final Score Calculation:**
```
final_score = (
    semantic_similarity * 0.4 +
    context_overlap * context_weight +
    temporal_boost * temporal_weight +
    keyword_match * 0.1 +
    importance_multiplier
) * metadata_filters
```

## 💾 Memory Writing - Intelligent Storage

### Basic Memory Writer

```yaml
- id: simple_storage
  type: memory-writer
  namespace: interactions
  params:
            # memory_type automatically classified as short/long term
    vector: true                       # Enable semantic search
  prompt: |
    Store this interaction:
    User: {{ input }}
    Response: {{ previous_outputs.response_generator }}
```

### Advanced Memory Storage

```yaml
- id: intelligent_storage
  type: memory-writer
  namespace: user_interactions
  params:
    # Memory classification
    # memory_type automatically classified as "short_term" or "long_term"
    
    # Vector embeddings
    vector: true                       # Enable semantic search
    embedding_model: "text-embedding-ada-002"
    
    # Memory organization
    key_template: "interaction_{timestamp}_{user_id}_{topic}"
    
    # Rich metadata for enhanced retrieval
    metadata:
      # Static metadata
      source: "user_input"
      version: "1.0"
      
      # Dynamic metadata from previous outputs
      user_id: "{{ user_id }}"
      session_id: "{{ session_id }}"
      topic: "{{ previous_outputs.topic_classifier }}"
      confidence: "{{ previous_outputs.confidence_scorer }}"
      interaction_type: "{{ previous_outputs.interaction_classifier }}"
      sentiment: "{{ previous_outputs.sentiment_analyzer }}"
      
      # Processing metadata
      agent_chain: "{{ previous_outputs | keys | join(' → ') }}"
      processing_time: "{{ processing_duration }}"
      token_count: "{{ total_tokens }}"
      
    # Storage optimization
    compress: true                     # Compress large memories
    deduplicate: true                  # Avoid storing duplicates
    max_size_kb: 100                   # Limit memory size
    
    # Indexing for fast retrieval
    indexes:
      - field: "topic"
        type: "hash"
      - field: "user_id"
        type: "hash"
      - field: "timestamp"
        type: "sorted_set"
        
  # Agent-specific decay configuration
  decay_config:
    enabled: true
    default_long_term: false           # Don't force long-term
    default_short_term_hours: 6        # Override global setting
    default_long_term_hours: 720       # 30 days for this agent
    
    # Custom importance rules
    importance_rules:
      user_correction: 4.0             # User corrections are critical
      positive_feedback: 2.5           # Learn from positive feedback
      negative_feedback: 1.5           # Remember failures too
      high_confidence: 2.0             # Trust high-confidence results
      
  prompt: |
    Store comprehensive interaction data:
    
    === User Input ===
    {{ input }}
    
    === Processing Chain ===
    {% for agent_id, output in previous_outputs.items() %}
    {{ agent_id }}: {{ output }}
    {% endfor %}
    
    === Context ===
    Topic: {{ previous_outputs.topic_classifier }}
    Confidence: {{ previous_outputs.confidence_scorer }}
    User Sentiment: {{ previous_outputs.sentiment_analyzer }}
    
    === Metadata ===
    Timestamp: {{ now() }}
    Processing Duration: {{ processing_duration }}
    Total Tokens: {{ total_tokens }}
    
  timeout: 20
```

### 🏷️ Memory Metadata - Critical for Effective Memory

**Every memory-writer MUST include metadata** that gets stored with the memory for enhanced retrieval and management:

```yaml
- id: comprehensive_memory_writer
  type: memory-writer
  namespace: user_interactions
  params:
    # memory_type automatically classified based on content and importance
    vector: true
    # 🚨 ALWAYS include metadata - this is what makes memories searchable and manageable
    metadata:
      # Core identification
      interaction_type: "{{ previous_outputs.interaction_classifier }}"
      timestamp: "{{ now() }}"
      
      # Context information
      user_id: "{{ user_id | default('anonymous') }}"
      session_id: "{{ session_id | default('unknown') }}"
      has_context: "{{ previous_outputs.memory_search | length > 0 }}"
      
      # Quality metrics
      confidence: "{{ previous_outputs.confidence_scorer | default('medium') }}"
      response_length: "{{ previous_outputs.response_generator | length }}"
      
      # Processing information
      agent_chain: "{{ previous_outputs | keys | join(' → ') }}"
      processing_time: "{{ processing_duration | default('unknown') }}"
      
      # Custom domain-specific metadata
      topic: "{{ previous_outputs.topic_classifier }}"
      sentiment: "{{ previous_outputs.sentiment_analyzer }}"
      language: "{{ detected_language | default('en') }}"
```

**Why Metadata Matters:**
- **Enhanced Search**: Metadata enables precise filtering during memory retrieval
- **Analytics**: Track patterns, performance, and user behavior
- **Decay Management**: Importance rules use metadata for retention decisions
- **Debugging**: Trace memory origins and processing chains
- **Compliance**: Audit trails for regulatory requirements

### Memory Classification Logic

**Valid memory_type values: ONLY "short_term" and "long_term"**

OrKa automatically classifies memories when memory_type is not specified, using these criteria:

**Short-term Classification Triggers:**
- Routine queries or common questions
- Intermediate processing results
- Temporary context or session data
- Low confidence or uncertain information
- Error states or debugging information

**Long-term Classification Triggers:**
- High-confidence factual information
- User corrections or feedback
- Successful problem resolutions
- Frequently accessed information
- Verified or validated content
- Important user preferences

**Auto-classification Algorithm:**
```python
def classify_memory(content, metadata, context):
    score = 0.5  # Start neutral
    
    # Content analysis
    if contains_factual_info(content):
        score += 0.3
    if user_provided_correction(context):
        score += 0.4
    if high_confidence(metadata.get('confidence', 0)):
        score += 0.2
    if frequently_accessed(content):
        score += 0.2
        
    # Negative factors
    if is_routine_query(content):
        score -= 0.2
    if is_error_state(metadata):
        score -= 0.3
    if low_confidence(metadata.get('confidence', 1)):
        score -= 0.2
        
    return "long_term" if score > 0.6 else "short_term"
```

## 🔄 Memory Decay System

### Intelligent Decay Configuration

```yaml
orchestrator:
  memory_config:
    decay:
      enabled: true
      
      # Base retention periods
      default_short_term_hours: 4      # Working memory
      default_long_term_hours: 336     # Knowledge store (2 weeks)
      check_interval_minutes: 15       # Frequent cleanup
      
      # Importance-based multipliers
      importance_rules:
        # High-value content
        critical_info: 5.0             # Critical info lasts 5x longer
        user_feedback: 4.0             # User corrections are precious
        verified_fact: 3.5             # Verified facts are valuable
        successful_pattern: 3.0        # Learn from successes
        
        # Medium-value content
        frequently_accessed: 2.0       # Popular content stays longer
        high_confidence: 1.8           # Trust confident results
        user_preference: 1.5           # Remember user preferences
        
        # Low-value content
        routine_query: 0.7             # Routine queries decay faster
        intermediate_result: 0.5       # Processing steps decay quickly
        error_event: 0.3               # Errors decay very quickly
        debug_info: 0.2                # Debug info decays fastest
        
      # Advanced decay rules
      access_based_decay:
        enabled: true
        boost_on_access: 1.2           # 20% boost when accessed
        max_boost: 3.0                 # Maximum boost multiplier
        decay_without_access: 0.9      # 10% faster decay if not accessed
        
      # Conditional decay rules
      conditional_rules:
        - condition: "metadata.confidence < 0.5"
          multiplier: 0.4              # Low confidence decays fast
        - condition: "metadata.error_count > 3"
          multiplier: 0.2              # Error-prone memories decay quickly
        - condition: "metadata.user_rating == 'helpful'"
          multiplier: 2.5              # User-rated helpful content lasts longer
```

### Decay Lifecycle Example

```
Memory Created
│
├─ Short-term (2 hours base)
│  ├─ Routine query (0.7x) → 1.4 hours
│  ├─ User correction (4.0x) → 8 hours → Promoted to long-term
│  └─ Error (0.3x) → 36 minutes
│
└─ Long-term (14 days base)
   ├─ Critical info (5.0x) → 70 days
   ├─ Verified fact (3.5x) → 49 days
   ├─ Frequently accessed (+20% on each access)
   └─ Low confidence (0.4x) → 5.6 days
```

## 🎛️ Memory Management CLI

OrKa provides powerful command-line tools for memory management:

### Real-time Monitoring

```bash
# Real-time memory dashboard (like 'top' for memory)
orka memory watch

# Sample output:
# ┌─────────────────────────────────────────────────────────────┐
# │ OrKa Memory Dashboard - 14:23:45 | Backend: redis | 5s     │
# ├─────────────────────────────────────────────────────────────┤
# │ 🔧 Backend: redis        ⚡ Decay: ✅ Enabled              │
# │ 📊 Streams: 23          📝 Entries: 1,847                  │
# │ 🗑️ Expired: 156         🧠 Memory Types:                   │
# │ 🔥 Short: 423 (23%)     💾 Long: 1,424 (77%)              │
# │                                                             │
# │ Entry Types Breakdown:                                      │
# │ ├─ success: 1,203       ████████████████████ 65.1%        │
# │ ├─ classification: 287   ████ 15.5%                        │
# │ ├─ search: 201          ███ 10.9%                          │
# │ ├─ error: 89            ██ 4.8%                            │
# │ └─ validation: 67       ██ 3.6%                            │
# └─────────────────────────────────────────────────────────────┘

# Compact view for smaller terminals
orka memory watch --compact

# JSON output for monitoring tools
orka memory watch --json
```

### Memory Statistics

```bash
# Detailed memory statistics
orka memory stats

# Sample output:
# === OrKa Memory Statistics ===
# Backend: redis
# Decay Enabled: true
# Total Streams: 23
# Total Entries: 1,847
# Expired Entries: 156
# 
# Entries by Type:
#   success: 1,203
#   classification: 287
#   search: 201
#   error: 89
#   validation: 67
# 
# Entries by Memory Type:
#   short_term: 423 (22.9%)
#   long_term: 1,424 (77.1%)
# 
# Entries by Category:
#   stored: 1,691 (91.6%)
#   log: 156 (8.4%)
# 
# Decay Configuration:
#   Short-term retention: 2h
#   Long-term retention: 168h
#   Check interval: 30min
#   Last cleanup: 2024-01-15 14:20:33

# JSON format for scripts
orka memory stats --json
```

### Memory Cleanup

```bash
# Manual cleanup of expired memories
orka memory cleanup

# Sample output:
# === Memory Cleanup ===
# Backend: redis
# Status: completed
# Deleted Entries: 156
# Streams Processed: 23
# Total Entries Checked: 1,847
# Duration: 2.34s

# Dry run to preview what would be deleted
orka memory cleanup --dry-run

# Verbose output showing deleted entries
orka memory cleanup --verbose
```

### Configuration Management

```bash
# Display current memory configuration
orka memory configure

# Sample output:
# === OrKa Memory Decay Configuration ===
# Backend: redis
# 
# Environment Variables:
#   ORKA_MEMORY_BACKEND: redis
#   ORKA_MEMORY_DECAY_ENABLED: true
#   ORKA_MEMORY_DECAY_SHORT_TERM_HOURS: 2
#   ORKA_MEMORY_DECAY_LONG_TERM_HOURS: 168
#   ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES: 30
# 
# Testing Configuration:
#   Decay Enabled: true
#   Short-term Hours: 2.0
#   Long-term Hours: 168.0
#   Check Interval: 30 minutes
```

## 📊 Memory Patterns and Use Cases

### Pattern 1: Conversational AI with Memory

**Use Case**: Build a chatbot that remembers conversation history and learns from interactions.

```yaml
orchestrator:
  id: conversational-ai
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2
      default_long_term_hours: 168
      importance_rules:
        user_correction: 3.0
        positive_feedback: 2.0

agents:
  # 1. Retrieve conversation history
  - id: conversation_history
    type: memory-reader
    namespace: conversations
    params:
      limit: 8
      enable_context_search: true
      context_weight: 0.5
      temporal_weight: 0.4
      similarity_threshold: 0.6
    prompt: |
      Find relevant conversation history for: {{ input }}
      
      Look for:
      - Similar topics we've discussed
      - Previous questions from this user
      - Related context from recent conversations

  # 2. Classify the interaction
  - id: interaction_classifier
    type: openai-classification
    prompt: |
      Based on conversation history: {{ previous_outputs.conversation_history }}
      Current input: {{ input }}
      
      Classify this interaction:
    options: [new_question, followup, clarification, correction, feedback, greeting, goodbye]

  # 3. Generate contextually aware response
  - id: response_generator
    type: openai-answer
    prompt: |
      Conversation History:
      {{ previous_outputs.conversation_history }}
      
      Interaction Type: {{ previous_outputs.interaction_classifier }}
      Current Input: {{ input }}
      
      Generate a response that:
      1. Acknowledges relevant conversation history when appropriate
      2. Addresses the current input directly
      3. Maintains natural conversation flow
      4. Shows understanding of context

  # 4. Store the interaction with intelligent classification
  - id: conversation_storage
    type: memory-writer
    namespace: conversations
    params:
      # memory_type automatically classified as "short_term" or "long_term"
      vector: true
      metadata:
        interaction_type: "{{ previous_outputs.interaction_classifier }}"
        has_history: "{{ previous_outputs.conversation_history | length > 0 }}"
        response_quality: "pending"  # Could be updated by feedback
    prompt: |
      Conversation Entry:
      User: {{ input }}
      Type: {{ previous_outputs.interaction_classifier }}
      History Context: {{ previous_outputs.conversation_history | length }} previous items
      Assistant: {{ previous_outputs.response_generator }}
      Timestamp: {{ now() }}
```

**What this achieves:**
- Remembers conversation context across interactions
- Learns from user corrections and feedback
- Automatically forgets routine interactions after 2 hours
- Keeps important conversations for up to 1 week
- Builds increasingly sophisticated responses over time

### Pattern 2: Knowledge Base with Self-Updating

**Use Case**: Create a knowledge base that automatically updates itself with new information.

```yaml
orchestrator:
  id: self-updating-kb
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 24    # Queries are temporary
      default_long_term_hours: 2160   # Knowledge lasts 90 days
      importance_rules:
        verified_fact: 4.0
        user_contributed: 3.0
        frequently_accessed: 2.0

agents:
  # 1. Analyze the query
  - id: query_analyzer
    type: openai-classification
    prompt: |
      Analyze this query: {{ input }}
      What type of knowledge request is this?
    options: [factual_lookup, how_to_guide, troubleshooting, definition, comparison, update_request]

  # 2. Search existing knowledge
  - id: knowledge_search
    type: memory-reader
    namespace: knowledge_base
    params:
      limit: 20
      enable_context_search: false    # Facts don't need conversation context
      temporal_weight: 0.1           # Facts don't age much
      similarity_threshold: 0.8      # High threshold for accuracy
      memory_type_filter: "long_term"
      metadata_filters:
        verified: "true"
        confidence: "> 0.7"
    prompt: |
      Search for information about: {{ input }}
      Query type: {{ previous_outputs.query_analyzer }}
      Focus on verified, high-confidence information.

  # 3. Assess knowledge freshness
  - id: freshness_checker
    type: openai-binary
    prompt: |
      Existing Knowledge: {{ previous_outputs.knowledge_search }}
      New Query: {{ input }}
      Query Type: {{ previous_outputs.query_analyzer }}
      
      Is the existing knowledge sufficient and up-to-date?
      Consider:
      - Completeness of information
      - Recency of data (especially for fast-changing topics)
      - Accuracy and reliability
      - Coverage of the specific question asked

  # 4. Route based on knowledge assessment
  - id: knowledge_router
    type: router
    params:
      decision_key: freshness_checker
      routing_map:
        "true": [knowledge_responder, query_logger]
        "false": [web_search, fact_verifier, knowledge_updater, enhanced_responder, query_logger]

  # 5a. Web search for new information
  - id: web_search
    type: duckduckgo
    prompt: |
      Search for current information about: {{ input }}
      Focus on {{ previous_outputs.query_analyzer }} type content.
      
      Look for:
      - Recent developments
      - Authoritative sources
      - Comprehensive coverage

  # 5b. Verify and structure new information
  - id: fact_verifier
    type: openai-answer
    prompt: |
      Verify and analyze this information:
      
      Original Query: {{ input }}
      Existing Knowledge: {{ previous_outputs.knowledge_search }}
      New Web Results: {{ previous_outputs.web_search }}
      
      Provide:
      1. Verified facts (separate from opinions)
      2. Confidence level (0-100) for each fact
      3. Source reliability assessment
      4. What's new compared to existing knowledge
      5. Any contradictions found
      
      Structure as JSON:
      {
        "verified_facts": [...],
        "confidence_scores": [...],
        "source_reliability": "high/medium/low",
        "new_information": [...],
        "contradictions": [...]
      }

  # 5c. Update knowledge base
  - id: knowledge_updater
    type: memory-writer
    namespace: knowledge_base
    params:
      memory_type: long_term
      vector: true
      metadata:
        query_type: "{{ previous_outputs.query_analyzer }}"
        verification_confidence: "{{ previous_outputs.fact_verifier.confidence }}"
        source_reliability: "{{ previous_outputs.fact_verifier.source_reliability }}"
        last_updated: "{{ now() }}"
        update_reason: "new_information_available"
        verified: "true"
    decay_config:
      enabled: true
      default_long_term_hours: 2160  # 90 days
      importance_rules:
        high_confidence: 2.0
        authoritative_source: 1.8
    prompt: |
      Updated Knowledge Entry:
      
      Topic: {{ input }}
      Type: {{ previous_outputs.query_analyzer }}
      
      Verified Information: {{ previous_outputs.fact_verifier.verified_facts }}
      Confidence: {{ previous_outputs.fact_verifier.confidence_scores }}
      Sources: {{ previous_outputs.web_search.sources }}
      
      Previous Knowledge: {{ previous_outputs.knowledge_search }}
      What's New: {{ previous_outputs.fact_verifier.new_information }}

  # 5d. Enhanced response with new knowledge
  - id: enhanced_responder
    type: openai-answer
    prompt: |
      Provide a comprehensive answer using:
      
      Original Query: {{ input }}
      Existing Knowledge: {{ previous_outputs.knowledge_search }}
      New Verified Information: {{ previous_outputs.fact_verifier }}
      
      Create a response that:
      1. Directly answers the question
      2. Integrates old and new information seamlessly
      3. Indicates what information is recent/updated
      4. Provides source attribution
      5. Notes confidence levels where appropriate

  # 5e. Response from existing knowledge
  - id: knowledge_responder
    type: openai-answer
    prompt: |
      Based on existing verified knowledge: {{ previous_outputs.knowledge_search }}
      Answer: {{ input }}
      
      Provide a comprehensive, accurate response.
      Note the source and confidence level of information used.

  # 6. Log the query for analytics
  - id: query_logger
    type: memory-writer
    namespace: query_analytics
    params:
      memory_type: short_term
      vector: false
      metadata:
        query_type: "{{ previous_outputs.query_analyzer }}"
        knowledge_found: "{{ previous_outputs.knowledge_search | length > 0 }}"
        required_update: "{{ previous_outputs.freshness_checker == 'false' }}"
        timestamp: "{{ now() }}"
    prompt: |
      Query Analytics Entry:
      Query: {{ input }}
      Type: {{ previous_outputs.query_analyzer }}
      Existing Knowledge: {{ previous_outputs.knowledge_search | length }} entries
      Update Required: {{ previous_outputs.freshness_checker == 'false' }}
      Processing Path: {{ agent_sequence | join(' → ') }}
```

### Pattern 3: Learning from Errors

**Use Case**: System that learns from mistakes and improves over time.

```yaml
orchestrator:
  id: error-learning-system
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 48   # Keep errors for 2 days
      default_long_term_hours: 720   # Keep solutions for 30 days
      importance_rules:
        error_pattern: 1.5
        successful_fix: 3.0
        user_reported_error: 2.5

agents:
  # 1. Check for similar past errors
  - id: error_history_search
    type: memory-reader
    namespace: error_patterns
    params:
      limit: 10
      enable_context_search: true
      similarity_threshold: 0.7
      temporal_weight: 0.3
    prompt: |
      Search for similar errors or problems: {{ input }}
      
      Look for:
      - Similar error messages or symptoms
      - Related failure patterns
      - Previous solutions that worked

  # 2. Attempt primary solution
  - id: primary_processor
    type: openai-answer
    prompt: |
      Process this request: {{ input }}
      
      {% if previous_outputs.error_history_search %}
      Consider these past similar issues:
      {{ previous_outputs.error_history_search }}
      {% endif %}
      
      Provide a solution with confidence level.

  # 3. Validate the solution
  - id: solution_validator
    type: openai-binary
    prompt: |
      Evaluate this solution:
      
      Original Problem: {{ input }}
      Proposed Solution: {{ previous_outputs.primary_processor }}
      Past Similar Cases: {{ previous_outputs.error_history_search }}
      
      Is this solution likely to be correct and complete?
      Consider logic, completeness, and past success patterns.

  # 4. Route based on validation
  - id: solution_router
    type: router
    params:
      decision_key: solution_validator
      routing_map:
        "true": [success_recorder, final_response]
        "false": [alternative_processor, alternative_validator, error_recorder]

  # 5a. Record successful solution
  - id: success_recorder
    type: memory-writer
    namespace: successful_solutions
    params:
      memory_type: long_term
      vector: true
      metadata:
        solution_type: "primary"
        confidence: "{{ previous_outputs.primary_processor.confidence }}"
        validation_passed: "true"
    decay_config:
      enabled: true
      default_long_term_hours: 1440  # Keep successful solutions for 60 days
    prompt: |
      Successful Solution Record:
      Problem: {{ input }}
      Solution: {{ previous_outputs.primary_processor }}
      Validation: Passed
      Similar Past Cases: {{ previous_outputs.error_history_search | length }}
      Success Timestamp: {{ now() }}

  # 5b. Try alternative approach
  - id: alternative_processor
    type: openai-answer
    prompt: |
      The primary solution was deemed insufficient:
      
      Original Problem: {{ input }}
      Failed Solution: {{ previous_outputs.primary_processor }}
      Validation Issues: {{ previous_outputs.solution_validator }}
      
      Provide an alternative approach that addresses the validation concerns.

  # 5c. Validate alternative
  - id: alternative_validator
    type: openai-binary
    prompt: |
      Evaluate this alternative solution:
      
      Problem: {{ input }}
      Failed First Attempt: {{ previous_outputs.primary_processor }}
      Alternative Solution: {{ previous_outputs.alternative_processor }}
      
      Is this alternative solution better and likely to succeed?

  # 5d. Record the error pattern
  - id: error_recorder
    type: memory-writer
    namespace: error_patterns
    params:
      memory_type: short_term  # Errors are temporary learning
      vector: true
      metadata:
        error_type: "solution_failure"
        attempts: "2"
        final_success: "{{ previous_outputs.alternative_validator }}"
    prompt: |
      Error Pattern Record:
      Original Problem: {{ input }}
      Failed Solution 1: {{ previous_outputs.primary_processor }}
      Alternative Solution: {{ previous_outputs.alternative_processor }}
      Alternative Success: {{ previous_outputs.alternative_validator }}
      
      Learning Points:
      - What didn't work and why
      - What validation caught
      - Pattern for future reference

  # 6. Provide final response
  - id: final_response
    type: openai-answer
    prompt: |
      Provide the final response for: {{ input }}
      
      {% if previous_outputs.solution_validator == "true" %}
      Validated Solution: {{ previous_outputs.primary_processor }}
      {% else %}
      Alternative Solution: {{ previous_outputs.alternative_processor }}
      Success Likelihood: {{ previous_outputs.alternative_validator }}
      {% endif %}
      
      Include confidence level and any caveats based on past experience.
```

## 🔧 Advanced Configuration

### Custom Memory Backends

You can extend OrKa with custom memory backends:

```python
from orka.memory.base_logger import BaseMemoryLogger

class CustomMemoryBackend(BaseMemoryLogger):
    def __init__(self, config):
        super().__init__(config)
        # Initialize your custom backend
        
    async def log_event(self, event_data):
        # Implement custom storage logic
        pass
        
    async def search_memories(self, query, params):
        # Implement custom search logic
        pass
        
    def cleanup_expired_memories(self, dry_run=False):
        # Implement custom cleanup logic
        pass
```

### Performance Optimization

**For High-Volume Applications:**

```yaml
orchestrator:
  memory_config:
    # Batch operations for better performance
    batch_operations:
      enabled: true
      batch_size: 100
      flush_interval_seconds: 5
      
    # Connection pooling
    connection_pool:
      min_connections: 5
      max_connections: 20
      connection_timeout: 30
      
    # Caching for frequent operations
    caching:
      enabled: true
      ttl_seconds: 300
      max_memory_mb: 100
      
    # Compression for large memories
    compression:
      enabled: true
      algorithm: "gzip"
      min_size_bytes: 1024
```

### Monitoring and Alerting

**Integration with monitoring systems:**

```bash
# Prometheus metrics endpoint
curl http://localhost:8000/metrics

# Sample metrics:
# orka_memory_total_entries 1847
# orka_memory_expired_entries 156
# orka_memory_cleanup_duration_seconds 2.34
# orka_memory_search_duration_seconds_avg 0.12
# orka_memory_storage_duration_seconds_avg 0.05

# Health check endpoint
curl http://localhost:8000/health/memory

# Sample response:
# {
#   "status": "healthy",
#   "backend": "redis",
#   "decay_enabled": true,
#   "last_cleanup": "2024-01-15T14:20:33Z",
#   "total_entries": 1847,
#   "expired_entries": 156
# }
```

## 🎯 Best Practices

### Memory Organization

1. **Use Meaningful Namespaces**
   ```yaml
   # Good: Organized by purpose
   namespace: user_conversations
   namespace: verified_facts
   namespace: error_logs
   
   # Bad: Generic or unclear
   namespace: data
   namespace: stuff
   ```

2. **Rich Metadata**
   ```yaml
   metadata:
     confidence: "{{ confidence_score }}"
     source: "user_input"
     verified: "true"
     topic: "{{ topic_classification }}"
     user_id: "{{ user_id }}"
   ```

3. **Appropriate Memory Types**
   ```yaml
   # Let OrKa automatically classify for most cases
   # (omit memory_type parameter for automatic classification)
   
   # Force long-term for critical info
   memory_type: long_term  # For facts, preferences
   
   # Force short-term for temporary data
   memory_type: short_term  # For debug, intermediate results
   ```

### Performance Optimization

1. **Limit Search Results**
   ```yaml
   params:
     limit: 10  # Don't retrieve more than needed
     max_search_time_seconds: 5  # Set reasonable timeouts
   ```

2. **Use Appropriate Thresholds**
   ```yaml
   params:
     similarity_threshold: 0.7  # Balance precision vs recall
     temporal_weight: 0.3       # Adjust based on use case
   ```

3. **Enable Caching for Frequent Searches**
   ```yaml
   params:
     enable_caching: true
   ```

### Memory Lifecycle Management

1. **Configure Decay Appropriately**
   ```yaml
   decay:
     default_short_term_hours: 4    # Long enough for context
     default_long_term_hours: 720   # Short enough to stay relevant
   ```

2. **Use Importance Rules**
   ```yaml
   importance_rules:
     user_feedback: 3.0  # Keep user corrections longer
     routine_query: 0.5  # Let routine queries decay faster
   ```

3. **Monitor Memory Usage**
   ```bash
   # Regular monitoring
   orka memory stats
   
   # Cleanup when needed
   orka memory cleanup
   ```

## 🚨 Troubleshooting

### Common Issues

**Memory Not Found**
```bash
# Check if memories exist
orka memory stats

# Check namespace
# Make sure you're searching the right namespace

# Check similarity threshold
# Lower the threshold if searches return empty
```

**Slow Memory Search**
```bash
# Check search parameters
# Reduce limit, increase similarity_threshold
# Disable context_search if not needed

# Monitor search performance
orka memory watch
```

**Memory Growing Too Large**
```bash
# Check decay configuration
orka memory configure

# Force cleanup
orka memory cleanup

# Adjust decay rules
# Reduce retention periods or importance multipliers
```

**Backend Connection Issues**
```bash
# Redis
redis-cli ping  # Should return PONG

# RedisStack
redis-cli FT._LIST  # Should show HNSW indexes
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
export ORKA_LOG_LEVEL=DEBUG
export ORKA_MEMORY_DEBUG=true

python -m orka.orka_cli your_config.yml "test input" --verbose
```

This comprehensive guide covers OrKa's memory system from basic concepts to advanced patterns. The memory system is what makes OrKa agents truly intelligent and capable of learning and improving over time. 