# OrKa Core Components Guide

[📘 Getting Started](./getting-started.md) | [⚙️ Configuration](./CONFIGURATION.md) | [🐛 Debugging](./DEBUGGING.md) | [🧠 Memory System](./MEMORY_SYSTEM_GUIDE.md)

## Overview

This guide provides detailed documentation for OrKa's core components, focusing on the key areas where debugging and development challenges commonly occur. **All examples reference working files from [`../examples/`](../examples/) that you can copy and test immediately**.

## 🚀 Quick Component Examples

Instead of complex code examples, **see these components in action**:

```bash
# Agreement Finder in cognitive society
cp ../examples/cognitive_society_minimal_loop.yml test-agreement.yml
orka run test-agreement.yml "Should AI have consciousness?"

# LoopNode with learning
cp ../examples/cognitive_loop_scoring_example.yml test-loops.yml  
orka run test-loops.yml "Analyze climate change solutions"

# Memory Reader with context
cp ../examples/memory_validation_routing_and_write.yml test-memory.yml
orka run test-memory.yml "What is quantum computing?"

# Template Resolution in action
cp ../examples/person_routing_with_search.yml test-templates.yml
orka run test-templates.yml "Tell me about Einstein"
```

**Key Working Examples by Component:**
- **Agreement Finder**: [`cognitive_society_minimal_loop.yml`](../examples/cognitive_society_minimal_loop.yml)
- **LoopNode**: [`cognitive_loop_scoring_example.yml`](../examples/cognitive_loop_scoring_example.yml)
- **Memory Reader**: [`memory_validation_routing_and_write.yml`](../examples/memory_validation_routing_and_write.yml)
- **Template System**: [`person_routing_with_search.yml`](../examples/person_routing_with_search.yml)
- **Fork/Join**: [`conditional_search_fork_join.yaml`](../examples/conditional_search_fork_join.yaml)

## Table of Contents

- [Agreement Finder](#agreement-finder)
- [LoopNode](#loopnode)
- [Shared Memory Reader](#shared-memory-reader)
- [Template Resolution](#template-resolution)
- [Component Interaction Patterns](#component-interaction-patterns)

## Agreement Finder

### Overview

The Agreement Finder component computes consensus scores between multiple agent responses using semantic similarity analysis. It's a critical component in cognitive society workflows and multi-agent deliberation systems.

### Working Examples

**See Agreement Finder in action:**

- **Basic Cognitive Society**: [`../examples/cognitive_society_minimal_loop.yml`](../examples/cognitive_society_minimal_loop.yml)
- **Advanced Consensus**: [`../examples/orka_smartest/genius_minds_convergence.yml`](../examples/orka_smartest/genius_minds_convergence.yml)

```bash
# Test agreement finder with different topics
cp ../examples/cognitive_society_minimal_loop.yml test-agreement.yml

# Run with controversial topic (shows disagreement handling)
orka run test-agreement.yml "Should AI systems replace human jobs?"

# Run with factual topic (shows quick consensus)  
orka run test-agreement.yml "What is 2 + 2?"

# Monitor consensus scoring in real-time
orka memory watch
```

### Core Algorithm
    
    # Extract upper triangular matrix (avoid duplicate pairs and diagonal)
    upper_triangular = similarities[np.triu_indices_from(similarities, k=1)]
    mean_similarity = np.mean(upper_triangular)
    
    # Apply consensus logic
    if mean_similarity >= 0.65:
        status = "Consensus reached"
    else:
        status = "No agreement found"
        
    return {
        "agreement_score": float(mean_similarity),
        "agreement_finder": status,
        "individual_similarities": similarities.tolist(),
        "embedding_dimensions": embeddings.shape[1]
    }
```

### Input Requirements

**Expected Input Format:**
```yaml
# Agent responses should be properly structured
agent_responses:
  - id: "logical_reasoner"
    response: "AI should prioritize ethical considerations and social justice in all applications."
    embedding: [0.1, -0.2, 0.3, ...]  # Generated automatically
  - id: "empathetic_reasoner" 
    response: "Artificial intelligence must focus on human welfare and fairness to ensure equitable outcomes."
    embedding: [0.15, -0.18, 0.31, ...]
  - id: "skeptical_reasoner"
    response: "While ethics matter, we must also consider practical implementation challenges in AI systems."
    embedding: [0.08, -0.25, 0.28, ...]
```

**Input Validation:**
- Minimum 2 responses required for agreement calculation
- Each response must be non-empty string
- Embeddings are generated if not provided
- Responses should be substantive (>10 characters recommended)

### Output Format

**Standard Output Structure:**
```json
{
  "agreement_score": 0.847,
  "agreement_finder": "Consensus reached",
  "confidence_level": "high",
  "individual_similarities": [
    [1.0, 0.83, 0.71],
    [0.83, 1.0, 0.76], 
    [0.71, 0.76, 1.0]
  ],
  "consensus_themes": ["ethical AI", "social justice", "fairness"],
  "divergent_points": ["implementation challenges"]
}
```

**Score Interpretation:**
- `0.90 - 1.00`: Strong consensus (very high agreement)
- `0.75 - 0.89`: Good consensus (high agreement)  
- `0.65 - 0.74`: Moderate consensus (agreement threshold met)
- `0.50 - 0.64`: Weak agreement (below consensus threshold)
- `0.00 - 0.49`: Low agreement (significant disagreement)

### Usage in Workflows

**Basic Agreement Finder:**
```yaml
agents:
  - id: consensus_evaluator
    type: openai-answer
    prompt: |
      Evaluate consensus among these agent responses:
      
      {% for response in agent_responses %}
      {{ response.id }}: {{ response.response }}
      {% endfor %}
      
      Use cosine similarity analysis to determine agreement level.
      Provide score (0.0-1.0) and consensus status.
      
      Output format:
      AGREEMENT_SCORE: [score]
      AGREEMENT_STATUS: [Consensus reached/No agreement found]
```

**Advanced Agreement Analysis:**
```yaml
agents:
  - id: detailed_agreement_finder
    type: openai-answer
    prompt: |
      Perform comprehensive agreement analysis:
      
      Responses to analyze:
      {% for response in agent_responses %}
      {{ loop.index }}. {{ response.id }}: {{ response.response }}
      {% endfor %}
      
      Analysis steps:
      1. Identify key themes in each response
      2. Calculate thematic overlap percentage
      3. Assess semantic similarity
      4. Determine consensus level
      
      Consensus criteria:
      - Score ≥ 0.85: Strong consensus (continue with agreed approach)
      - Score 0.65-0.84: Moderate consensus (minor refinements needed) 
      - Score < 0.65: No consensus (significant disagreement, continue deliberation)
      
      AGREEMENT_SCORE: [0.0-1.0]
      AGREEMENT_STATUS: [Strong consensus/Moderate consensus/No consensus]
      CONSENSUS_THEMES: [theme1, theme2, ...]
      DIVERGENT_POINTS: [point1, point2, ...]
```

### Troubleshooting Agreement Issues

**Issue: Inconsistent Scores (0.6727 vs 0.85 for similar content)**

*Root Causes:*
1. **Embedding Model Inconsistency**: Different model instances or versions
2. **Input Preprocessing**: Inconsistent text cleaning or formatting
3. **Context Pollution**: Including irrelevant context in similarity calculation

*Solutions:*
```python
# Ensure consistent embedding generation
def generate_consistent_embedding(text):
    # Clean and normalize text
    cleaned_text = text.strip().lower()
    # Remove extra whitespace
    normalized_text = re.sub(r'\s+', ' ', cleaned_text)
    
    # Use consistent model instance
    embedding = model.encode(normalized_text, normalize_embeddings=True)
    return embedding
```

**Issue: Missing Round 2 Scores**

*Root Causes:*
1. **Loop Context Loss**: Previous scores not passed to subsequent iterations
2. **Template Resolution Failure**: Score extraction pattern not matching
3. **Memory Context Issues**: Agreement context lost between rounds

*Solutions:*
```yaml
# Ensure score preservation across rounds
past_loops_metadata:
  iteration: "{{ loop_number }}"
  previous_score: "{{ agreement_score | default('no score') }}"
  previous_status: "{{ agreement_finder | default('no status') }}"
  score_trend: "{{ score_history | join(',') }}"

# Robust score extraction
score_extraction_pattern: "AGREEMENT_SCORE:\\s*([0-9.]+)"
# Fallback patterns
score_extraction_fallbacks:
  - "(?i)score:\\s*([0-9.]+)"
  - "(?i)agreement:\\s*([0-9.]+)"
  - "(?i)consensus:\\s*([0-9.]+)"
```

## LoopNode

### Overview

LoopNode is a sophisticated component that executes iterative workflows with cognitive learning and improvement. It enables workflows to run multiple iterations, learning from each attempt until a quality threshold is met or maximum iterations are reached.

### Architecture and State Management

**Core Components:**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Loop Control  │────│  State Manager  │────│ Context Passer  │
│                 │    │                 │    │                 │
│ • Iteration     │    │ • past_loops    │    │ • Agent Context │
│ • Thresholds    │    │ • Metadata      │    │ • Memory State  │
│ • Termination   │    │ • Score History │    │ • Loop Cache    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Cognitive      │
                    │  Extraction     │
                    │                 │
                    │ • Insights      │
                    │ • Improvements  │
                    │ • Mistakes      │
                    └─────────────────┘
```

### Configuration Parameters

**Core Configuration:**
```yaml
agents:
  - id: improvement_loop
    type: loop
    
    # Termination conditions
    max_loops: 8                        # Maximum iterations
    score_threshold: 0.85               # Quality score to reach
    min_loops: 2                        # Minimum iterations (optional)
    
    # Score extraction configuration
    score_extraction_pattern: "QUALITY_SCORE:\\s*([0-9.]+)"
    score_extraction_key: "quality_score"  # Direct JSON key extraction
    high_priority_agents: ["quality_scorer", "agreement_finder"]  # Check these agents first
    
    # Cognitive learning system
    cognitive_extraction:
      enabled: true
      extract_patterns:
        insights:
          - "(?:insight|learning|discovery):\\s*(.+?)(?:\\n|$)"
          - "(?:identified|found|revealed)\\s+(.+?)(?:\\n|$)"
        improvements:
          - "(?:improve|enhance|strengthen)\\s+(.+?)(?:\\n|$)"
          - "(?:needs?|lacks?|requires?)\\s+(.+?)(?:\\n|$)"
        mistakes:
          - "(?:error|mistake|oversight):\\s*(.+?)(?:\\n|$)"
          - "(?:missed|overlooked|failed)\\s+(.+?)(?:\\n|$)"
    
    # Metadata tracking template
    past_loops_metadata:
      iteration: "{{ loop_number }}"
      quality_score: "{{ score }}"
      timestamp: "{{ now() }}"
      insights: "{{ insights }}"
      improvements: "{{ improvements }}"
      mistakes: "{{ mistakes }}"
      processing_time_ms: "{{ processing_duration }}"
    
    # Internal workflow definition
    internal_workflow:
      orchestrator:
        id: improvement-cycle
        strategy: sequential
        agents: [analyzer, quality_scorer]
      
      agents:
        - id: analyzer
          type: openai-answer
          prompt: |
            Iteration {{ loop_number }}: Analyze this input
            Original: {{ input }}
            
            {% if previous_outputs.past_loops %}
            Learning from {{ previous_outputs.past_loops | length }} previous attempts:
            {% for loop in previous_outputs.past_loops %}
            
            Round {{ loop.iteration }} (Score: {{ loop.quality_score }}):
            • Key insights: {{ loop.insights }}
            • Areas to improve: {{ loop.improvements }}  
            • Mistakes to avoid: {{ loop.mistakes }}
            {% endfor %}
            
            CRITICAL: Build upon these insights and address identified gaps.
            Provide a MORE COMPREHENSIVE analysis than previous attempts.
            {% endif %}
            
            Provide detailed analysis with clear quality improvements.
        
        - id: quality_scorer
          type: openai-answer
          prompt: |
            Rate the quality of this analysis (0.0-1.0):
            {{ previous_outputs.analyzer }}
            
            Evaluation criteria:
            - Depth and comprehensiveness (25%)
            - Accuracy and evidence support (25%)
            - Clarity and structure (25%)
            - Addressing of improvement areas (25%)
            
            {% if previous_outputs.past_loops %}
            Previous best score: {{ previous_outputs.past_loops | map(attribute='quality_score') | max }}
            Current analysis MUST exceed this score to show improvement.
            {% endif %}
            
            Format: QUALITY_SCORE: X.XX
            Justification: [detailed reasoning for score]
```

### State Management and Context Passing

**Past Loops Structure:**
```python
# past_loops data structure
past_loops = [
    {
        "iteration": 1,
        "quality_score": 0.72,
        "timestamp": "2025-01-08T14:23:45Z",
        "insights": "Identified key themes in social justice approach",
        "improvements": "Needs more specific implementation strategies",
        "mistakes": "Overlooked potential technical constraints",
        "result": {
            "analyzer": "Initial analysis of AI ethics...",
            "quality_scorer": "Quality assessment: 0.72..."
        }
    },
    {
        "iteration": 2,
        "quality_score": 0.86,
        "timestamp": "2025-01-08T14:24:12Z", 
        "insights": "Developed concrete implementation framework",
        "improvements": "Could strengthen risk mitigation strategies",
        "mistakes": "None identified in this iteration",
        "result": {
            "analyzer": "Enhanced analysis with implementation details...",
            "quality_scorer": "Quality assessment: 0.86..."
        }
    }
]
```

**Context Passing Mechanism:**
```yaml
# How past_loops context is made available to internal agents
internal_workflow:
  agents:
    - id: context_aware_agent
      type: openai-answer
      prompt: |
        Available context from previous iterations:
        
        {% if previous_outputs.past_loops %}
        Iteration history ({{ previous_outputs.past_loops | length }} previous):
        {% for loop in previous_outputs.past_loops %}
        
        === Round {{ loop.iteration }} ===
        Score: {{ loop.quality_score }}
        Key insights: {{ loop.insights }}
        Needed improvements: {{ loop.improvements }}
        Mistakes made: {{ loop.mistakes }}
        Full result: {{ loop.result | truncate(200) }}...
        {% endfor %}
        
        Analysis: Progressive improvement trend is 
        {{ 'positive' if past_loops[-1].quality_score > past_loops[0].quality_score else 'flat or declining' }}
        {% endif %}
```

### Cache Management

**Loop Cache Behavior:**
- Cache key format: `loop_cache:{orchestrator_id}:{loop_node_id}`
- Stores intermediate results and state between iterations
- Automatically cleared when threshold is met or max loops reached
- Manual clearing: `redis-cli DEL $(redis-cli KEYS "loop_cache:*")`

**Cache Debugging:**
```bash
# Check active loop caches
redis-cli KEYS "loop_cache:*"

# Inspect cache contents
redis-cli HGETALL "loop_cache:orchestrator_id:loop_node_id"

# Clear specific cache
redis-cli DEL "loop_cache:orchestrator_id:loop_node_id"

# Clear all loop caches
redis-cli DEL $(redis-cli KEYS "loop_cache:*")
```

### Troubleshooting LoopNode Issues

**Issue: Response Duplication in Round 2**

*Symptoms:*
- Identical or near-identical responses across iterations
- No evidence of learning from past_loops
- Score stagnation

*Root Causes & Solutions:*

1. **Context Not Being Passed:**
```yaml
# Verify context is available
- id: debug_context_checker
  type: openai-answer
  prompt: |
    DEBUG: Loop context check
    Loop number: {{ loop_number | default('NOT AVAILABLE') }}
    Past loops available: {{ previous_outputs.past_loops | length if previous_outputs.past_loops else 0 }}
    
    {% if previous_outputs.past_loops %}
    Most recent iteration:
    Score: {{ previous_outputs.past_loops[-1].quality_score }}
    Insights: {{ previous_outputs.past_loops[-1].insights }}
    {% else %}
    ERROR: No past loops context available!
    {% endif %}
```

2. **Insufficient Variation Enforcement:**
```yaml
# Force variation in responses
- id: variation_enforcer
  type: openai-answer
  prompt: |
    ITERATION {{ loop_number }} - VARIATION REQUIRED
    
    {% if loop_number > 1 and previous_outputs.past_loops %}
    CRITICAL REQUIREMENT: Your response must be SUBSTANTIALLY DIFFERENT from:
    
    Previous attempt {{ loop_number - 1 }}:
    {{ previous_outputs.past_loops[-1].result.analyzer | truncate(300) }}
    
    FORBIDDEN: Do not repeat the same points, structure, or approach.
    REQUIRED: Take a fresh perspective and explore new dimensions.
    {% endif %}
    
    Original input: {{ input }}
    Provide completely new analysis approach.
```

**Issue: Missing or Inconsistent Scores**

*Solutions:*
```yaml
# Robust score extraction with multiple patterns
score_extraction_config:
  strategies:
    - type: "regex_pattern"
      pattern: "QUALITY_SCORE:\\s*([0-9.]+)"
      priority: 1
    - type: "json_key"
      key: "quality_score"
      priority: 2
    - type: "regex_fallback"
      patterns:
        - "(?i)score:\\s*([0-9.]+)"
        - "(?i)rating:\\s*([0-9.]+)"
        - "(?i)quality:\\s*([0-9.]+)"
      priority: 3

# Explicit score validation
- id: score_validator
  type: openai-answer
  prompt: |
    Validate and extract score from: {{ previous_outputs.scorer }}
    
    Requirements:
    - Score must be between 0.0 and 1.0
    - Must be in format: QUALITY_SCORE: X.XX
    - Must include justification
    
    If no valid score found, assign based on content quality assessment.
    
    VALIDATED_SCORE: [score]
```

## Shared Memory Reader

### Overview

The Shared Memory Reader component performs intelligent memory retrieval using RedisStack's HNSW vector indexing combined with metadata filtering. It supports hybrid search capabilities that combine semantic similarity with traditional text search.

### Search Architecture

**Search Pipeline:**
```
Input Query
     │
     ▼
┌─────────────────┐
│ Query Analysis  │ ── Parse intent, extract filters
└─────────────────┘
     │
     ▼
┌─────────────────┐
│ Embedding Gen   │ ── Generate query vector (384-dim)
└─────────────────┘
     │
     ▼
┌─────────────────┐    ┌─────────────────┐
│ Vector Search   │────│ Metadata Filter │ ── HNSW + filtering  
│ (HNSW KNN)     │    │ (@namespace:...) │
└─────────────────┘    └─────────────────┘
     │                          │
     ▼                          ▼
┌─────────────────┐    ┌─────────────────┐
│ Text Search     │────│ Result Fusion   │ ── Combine + rank
│ (FT.SEARCH)    │    │ (Hybrid Score) │
└─────────────────┘    └─────────────────┘
     │
     ▼
Final Results
```

### Query Construction and Syntax

**HNSW Vector Search Query:**
```redis
# Correct HNSW query syntax
FT.SEARCH orka_enhanced_memory 
  "(@namespace:conversations) (@category:stored) => [KNN 10 @embedding $query_vec AS distance]" 
  PARAMS 2 query_vec "\x01\x02\x03..."
  SORTBY distance ASC
  RETURN 6 content node_id trace_id namespace category distance
  LIMIT 0 10
```

**Text Search Query:**
```redis
# Text search with metadata filtering
FT.SEARCH orka_enhanced_memory 
  "(@namespace:conversations) (@category:stored) machine learning AI ethics"
  RETURN 5 content node_id timestamp importance_score category
  SORTBY importance_score DESC
  LIMIT 0 10
```

**Common Query Errors and Fixes:**

| Error | Incorrect Syntax | Correct Syntax |
|-------|------------------|----------------|
| `Syntax error at offset 1 near ,` | `(*) @node_id:cognitive_debate_loop` | `(@node_id:cognitive_debate_loop)` |
| `Unknown index name` | Missing index | Recreate with `orka memory cleanup --rebuild-index` |
| `Invalid vector blob` | Binary encoding issue | Ensure proper FLOAT32 encoding |
| `Field not found` | Wrong field names | Use: `content`, `node_id`, `namespace`, `category` |

### Search Parameters and Configuration

**Basic Search Configuration:**
```yaml
agents:
  - id: memory_search
    type: memory-reader
    namespace: conversations
    params:
      # Core search parameters
      limit: 10                          # Maximum results to return
      similarity_threshold: 0.8           # Vector similarity threshold (0.0-1.0)
      max_search_time_seconds: 5         # Query timeout
      
      # RedisStack HNSW parameters  
      ef_runtime: 10                     # Search accuracy (higher = more accurate, slower)
      enable_vector_search: true         # Use HNSW vector index
      enable_text_search: true           # Fallback to text search
      
      # Hybrid search weighting
      vector_weight: 0.7                 # Vector similarity importance
      text_weight: 0.3                   # Text match importance
      enable_hybrid_search: true         # Combine vector + text scores
```

**Advanced Search with Context:**
```yaml
agents:
  - id: context_aware_search
    type: memory-reader
    namespace: knowledge_base
    params:
      # Context-aware search
      enable_context_search: true        # Use conversation history
      context_weight: 0.4                # Context influence on results
      context_window_size: 5             # Previous agent outputs to consider
      
      # Temporal ranking
      enable_temporal_ranking: true      # Boost recent memories
      temporal_weight: 0.3               # Recency boost strength
      temporal_decay_hours: 48           # How fast recency effect fades
      
      # Metadata filtering
      memory_type_filter: "long_term"    # Filter by memory type
      category_filter: "stored"          # Only retrievable memories
      exclude_categories: ["debug", "error"]  # Skip system memories
      
      # Advanced filters
      metadata_filters:
        confidence: "> 0.8"              # High-confidence only
        verified: "true"                 # Verified information
        importance_score: ">= 0.7"       # Important memories
        
    prompt: |
      Find comprehensive information about: {{ input }}
      
      Consider conversation context:
      {% for output in previous_outputs[-3:] %}
      Recent: {{ output | truncate(100) }}
      {% endfor %}
      
      Priority: Recent, relevant, high-confidence information
```

### Search Algorithm and Scoring

**Hybrid Search Score Calculation:**
```python
def calculate_hybrid_score(vector_score, text_score, metadata_boost):
    """
    Combine vector similarity, text relevance, and metadata boost
    
    Args:
        vector_score: Cosine similarity (0.0-1.0)
        text_score: TF-IDF relevance (0.0-1.0) 
        metadata_boost: Importance multiplier (0.5-2.0)
    
    Returns:
        Final relevance score (0.0-1.0)
    """
    # Weighted combination
    base_score = (vector_score * 0.7) + (text_score * 0.3)
    
    # Apply temporal decay
    time_factor = exp(-age_hours / temporal_decay_hours)
    temporal_boost = temporal_weight * time_factor
    
    # Apply context boost
    context_score = calculate_context_overlap(query, conversation_history)
    context_boost = context_weight * context_score
    
    # Combine all factors
    final_score = base_score * metadata_boost + temporal_boost + context_boost
    
    return min(final_score, 1.0)  # Cap at 1.0
```

### Embedding Storage and Retrieval

**Embedding Format:**
- **Model**: `all-MiniLM-L6-v2` (SentenceTransformers)
- **Dimensions**: 384 
- **Data Type**: FLOAT32
- **Normalization**: L2-normalized for cosine similarity
- **Storage**: Binary format in Redis hash field `embedding`

**Embedding Generation Process:**
```python
def generate_embedding(text):
    """Generate consistent embeddings for storage and search"""
    from sentence_transformers import SentenceTransformer
    
    # Use consistent model instance
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Normalize input text
    cleaned_text = text.strip()
    
    # Generate embedding
    embedding = model.encode(
        cleaned_text,
        normalize_embeddings=True,  # L2 normalization for cosine similarity
        convert_to_tensor=False     # Return numpy array
    )
    
    return embedding.astype(np.float32)  # Ensure FLOAT32 format
```

### Fallback Behavior and Error Handling

**Search Fallback Chain:**

1. **Primary: HNSW Vector Search**
   ```redis
   FT.SEARCH orka_enhanced_memory 
     "(@namespace:conversations) => [KNN 10 @embedding $vec]"
   ```

2. **Secondary: Text Search with Metadata**
   ```redis
   FT.SEARCH orka_enhanced_memory 
     "(@namespace:conversations) query terms"
   ```

3. **Tertiary: Redis SCAN Fallback**
   ```redis
   SCAN 0 MATCH orka_memory:* COUNT 1000
   ```

**Error Handling Logic:**
```python
async def robust_memory_search(query, namespace, limit=10):
    try:
        # Try HNSW vector search first
        results = await hnsw_vector_search(query, namespace, limit)
        if results:
            logger.debug(f"HNSW search returned {len(results)} results")
            return results
            
    except RedisError as e:
        logger.warning(f"HNSW search failed: {e}, trying text search")
        
    try:
        # Fallback to text search
        results = await text_search(query, namespace, limit)
        if results:
            logger.debug(f"Text search returned {len(results)} results")  
            return results
            
    except RedisError as e:
        logger.warning(f"Text search failed: {e}, using SCAN fallback")
        
    # Final fallback: Redis SCAN
    results = await scan_fallback(namespace, limit)
    logger.debug(f"SCAN fallback returned {len(results)} results")
    return results
```

### Troubleshooting Memory Search Issues

**Issue: Consistent `num_results: 0`**

*Debugging Steps:*

1. **Check Memory Existence:**
```bash
# Verify memories are stored
redis-cli KEYS "orka_memory:*" | wc -l

# Check specific namespace
redis-cli FT.SEARCH orka_enhanced_memory "(@namespace:your_namespace)" LIMIT 0 3
```

2. **Verify Index Integrity:**
```bash
# Check index exists
redis-cli FT._LIST | grep orka_enhanced_memory

# Examine index schema
redis-cli FT.INFO orka_enhanced_memory

# Rebuild index if corrupted
orka memory cleanup --rebuild-index
```

3. **Test Query Components:**
```bash
# Test basic search
redis-cli FT.SEARCH orka_enhanced_memory "*" LIMIT 0 3

# Test namespace filter  
redis-cli FT.SEARCH orka_enhanced_memory "(@namespace:conversations)" LIMIT 0 3

# Test with lower threshold
redis-cli FT.SEARCH orka_enhanced_memory "(@namespace:conversations) machine" LIMIT 0 5
```

**Issue: Vector Search Failures**

*Solutions:*

1. **Verify Embedding Generation:**
```python
# Test embedding pipeline
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
test_embedding = model.encode("test query")

print(f"Embedding shape: {test_embedding.shape}")  # Should be (384,)
print(f"Embedding type: {test_embedding.dtype}")   # Should be float32
print(f"Embedding range: {test_embedding.min():.3f} to {test_embedding.max():.3f}")
```

2. **Check Stored Embeddings:**
```bash
# Verify embeddings are stored
redis-cli HGET "orka_memory:$(redis-cli KEYS 'orka_memory:*' | head -1)" embedding | wc -c
# Should return 1536+ bytes (384 floats * 4 bytes each)
```

## Template Resolution

### Overview

Template Resolution in OrKa uses Jinja2 templating to dynamically generate prompts and content based on available context, previous agent outputs, and system state. Template resolution failures can cause cascading issues throughout workflows.

### Template Architecture

**Template Context Hierarchy:**
```
Global Context
├── input (original orchestrator input)
├── previous_outputs (dict of agent outputs)
├── system_context (runtime information)
└── component_context (component-specific variables)
    ├── loop_number (LoopNode only)
    ├── score (LoopNode only)  
    ├── past_loops (LoopNode only)
    └── memory_results (MemoryReader outputs)
```

### Available Template Variables

**Standard Variables (Always Available):**
```yaml
# Core context
{{ input }}                           # Original input string
{{ previous_outputs }}                 # Dict of all previous agent outputs
{{ now() }}                           # Current timestamp  
{{ processing_duration }}             # Time taken so far (if available)

# Agent-specific access
{{ previous_outputs.agent_id }}       # Specific agent's output
{{ previous_outputs.agent_id.result }}# Nested result access
{{ previous_outputs.keys() | list }}  # List of available agent IDs

# Safe access with defaults
{{ previous_outputs.agent_id | default('not available') }}
{{ score | default(0.0) }}
```

**LoopNode-Specific Variables:**
```yaml
# Loop iteration context  
{{ loop_number }}                     # Current iteration (1, 2, 3...)
{{ score }}                          # Extracted quality score from previous iteration
{{ threshold_met }}                  # Boolean: whether score threshold reached
{{ loops_completed }}                # Total iterations completed

# Past loops context
{{ previous_outputs.past_loops }}     # Array of previous loop metadata
{{ previous_outputs.past_loops | length }}  # Number of previous iterations

# Loop metadata access
{% for loop in previous_outputs.past_loops %}
{{ loop.iteration }}                 # Loop number
{{ loop.quality_score }}             # Score for that iteration  
{{ loop.insights }}                  # Extracted insights
{{ loop.improvements }}              # Areas for improvement
{{ loop.mistakes }}                  # Identified mistakes
{{ loop.result }}                    # Full agent outputs from that iteration
{% endfor %}
```

**Memory Reader Variables:**
```yaml
# Memory search results
{{ previous_outputs.memory_reader.results }}     # Array of memory entries
{{ previous_outputs.memory_reader.num_results }} # Number of memories found
{{ previous_outputs.memory_reader.search_query }}# Original search query

# Memory entry access
{% for memory in previous_outputs.memory_reader.results %}
{{ memory.content }}                 # Memory content
{{ memory.timestamp }}               # When memory was created
{{ memory.importance_score }}        # Memory importance rating
{{ memory.namespace }}               # Memory namespace
{% endfor %}
```

### Template Patterns and Best Practices

**Safe Variable Access:**
```yaml
# ❌ WRONG: Direct access can cause undefined variable errors
prompt: "Score: {{ score }}"
prompt: "Previous result: {{ previous_outputs.analyzer.result }}"

# ✅ CORRECT: Use defaults and safe access
prompt: "Score: {{ score | default('not available') }}"
prompt: "Previous result: {{ previous_outputs.analyzer.result | default('no previous result') }}"

# ✅ CORRECT: Check existence before access
prompt: |
  {% if score is defined %}
  Quality Score: {{ score }}
  {% else %}
  No quality score available
  {% endif %}
```

**Conditional Logic:**
```yaml
# Safe conditional access
prompt: |
  Analyze: {{ input }}
  
  {% if previous_outputs.past_loops %}
  Learning from {{ previous_outputs.past_loops | length }} previous attempts:
  
  {% for loop in previous_outputs.past_loops %}
  Round {{ loop.iteration }} (Score: {{ loop.quality_score | default('unknown') }}):
  - Insights: {{ loop.insights | default('none identified') }}
  - Improvements: {{ loop.improvements | default('none needed') }}
  {% endfor %}
  
  Build upon these insights for better results.
  {% else %}
  This is the first analysis attempt.
  {% endif %}
```

**Complex Data Handling:**
```yaml  
# Safe nested object access
prompt: |
  Memory search results:
  {% if previous_outputs.memory_search and previous_outputs.memory_search.results %}
  Found {{ previous_outputs.memory_search.results | length }} relevant memories:
  
  {% for memory in previous_outputs.memory_search.results[:3] %}
  {{ loop.index }}. {{ memory.content | truncate(200) }}
     (Score: {{ memory.similarity_score | round(3) | default('unknown') }})
  {% endfor %}
  {% else %}
  No relevant memories found.
  {% endif %}
```

### Template Configuration

**Jinja2 Environment Settings:**
```yaml
orchestrator:
  template_config:
    # Error handling
    strict_undefined: true              # Fail on undefined variables (recommended for debugging)
    undefined_behavior: "strict"        # Options: "strict", "debug", "silent"
    
    # Whitespace control
    trim_blocks: true                   # Remove newlines after blocks
    lstrip_blocks: true                 # Remove leading whitespace
    
    # Security settings
    auto_escape: false                  # Don't escape HTML (we're generating prompts, not HTML)
    
    # Custom filters (if needed)
    custom_filters:
      safe_truncate: "safe_string_truncation"
      format_score: "format_decimal_score"
```

### Troubleshooting Template Issues

**Issue: `has_unresolved_vars: true`**

*Debugging Template Variables:*
```yaml
# Template debugging agent
- id: template_debugger
  type: openai-answer
  prompt: |
    === TEMPLATE DEBUG INFO ===
    
    Available Variables:
    - input: {{ input | default('NOT AVAILABLE') }}
    - loop_number: {{ loop_number | default('NOT AVAILABLE') }}
    - score: {{ score | default('NOT AVAILABLE') }}
    
    Previous Outputs Available:
    {% if previous_outputs %}
    {% for key, value in previous_outputs.items() %}
    - {{ key }}: {{ value | string | truncate(100) }}...
    {% endfor %}
    {% else %}
    NO PREVIOUS OUTPUTS AVAILABLE
    {% endif %}
    
    Past Loops:
    {% if previous_outputs.past_loops %}
    {{ previous_outputs.past_loops | length }} previous loops available
    {% else %}
    NO PAST LOOPS AVAILABLE
    {% endif %}
    
    === END DEBUG INFO ===
    
    Proceed with template resolution debugging.
```

*Common Template Errors and Fixes:*

| Error | Cause | Solution |
|-------|-------|----------|
| `'score' is undefined` | Variable only available in LoopNode | Use `{{ score \| default('N/A') }}` |
| `'past_loops' is undefined` | Not in loop context | Check `{% if previous_outputs.past_loops %}` first |
| `'result' attribute missing` | Agent output structure varies | Use safe access: `{{ agent.result \| default(agent) }}` |
| `Template syntax error` | Invalid Jinja2 syntax | Validate template with online Jinja2 validator |
| `'NoneType' object has no attribute` | Null values in data | Add null checks: `{% if value and value.attribute %}` |

**Template Testing and Validation:**
```python
# Test template resolution
from jinja2 import Template, StrictUndefined

template_string = """
Analyze: {{ input }}
Score: {{ score | default('not available') }}
{% if previous_outputs.past_loops %}
Past attempts: {{ previous_outputs.past_loops | length }}
{% endif %}
"""

# Test with strict undefined checking
template = Template(template_string, undefined=StrictUndefined)

test_context = {
    "input": "test input",
    "score": 0.85,
    "previous_outputs": {
        "past_loops": [{"iteration": 1, "score": 0.72}]
    }
}

try:
    result = template.render(test_context)
    print("Template rendered successfully:")
    print(result)
except Exception as e:
    print(f"Template error: {e}")
```

## Component Interaction Patterns

### Cognitive Society Workflow Pattern

**Complete Component Integration:**
```yaml
orchestrator:
  id: cognitive-society-enhanced
  strategy: sequential
  agents: [deliberation_loop, consensus_builder]

agents:
  - id: deliberation_loop
    type: loop
    max_loops: 5
    score_threshold: 0.90
    score_extraction_pattern: "CONSENSUS_SCORE:\\s*([0-9.]+)"
    
    # Cognitive extraction for learning
    cognitive_extraction:
      enabled: true
      extract_patterns:
        insights: 
          - "consensus\\s+(?:emerging|developing)\\s+(?:around|on)\\s+(.+?)(?:\\n|$)"
          - "shared\\s+understanding\\s+of\\s+(.+?)(?:\\n|$)"
        improvements:
          - "(?:disagreement|tension)\\s+(?:remains|exists)\\s+(?:on|around)\\s+(.+?)(?:\\n|$)"
          - "needs?\\s+(?:more|further)\\s+(?:discussion|exploration)\\s+of\\s+(.+?)(?:\\n|$)"
        mistakes:
          - "(?:overlooked|ignored|missed)\\s+(.+?)\\s+perspective"
          - "insufficient\\s+consideration\\s+of\\s+(.+?)(?:\\n|$)"
    
    past_loops_metadata:
      round: "{{ loop_number }}"
      consensus_score: "{{ score }}"
      emerging_consensus: "{{ insights }}"
      remaining_tensions: "{{ improvements }}"
      blind_spots: "{{ mistakes }}"
      participant_responses: "{{ agent_responses | length }}"
    
    internal_workflow:
      orchestrator:
        id: multi-agent-deliberation
        strategy: sequential  
        agents: [memory_context, fork_perspectives, join_views, consensus_evaluator]
      
      agents:
        # Retrieve relevant discussion context
        - id: memory_context
          type: memory-reader
          namespace: deliberation_history
          params:
            limit: 8
            enable_context_search: true
            similarity_threshold: 0.7
            temporal_weight: 0.4
          prompt: |
            Find relevant context for deliberation on: {{ input }}
            
            {% if previous_outputs.past_loops %}
            Previous round themes:
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round }}: {{ loop.emerging_consensus }}
            {% endfor %}
            {% endif %}
        
        # Multi-perspective analysis
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
            Provide logical, evidence-based analysis for: {{ input }}
            
            Context from memory: {{ previous_outputs.memory_context }}
            
            {% if previous_outputs.past_loops %}
            Building on {{ previous_outputs.past_loops | length }} previous rounds:
            
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round }} insights: {{ loop.emerging_consensus }}
            Remaining issues: {{ loop.remaining_tensions }}
            {% endfor %}
            
            Focus on ADVANCING the logical framework beyond previous rounds.
            {% endif %}
            
            Provide structured logical reasoning with clear evidence support.
        
        - id: empathetic_reasoner
          type: openai-answer
          prompt: |
            Provide empathetic, human-centered analysis for: {{ input }}
            
            Context: {{ previous_outputs.memory_context }}
            
            {% if previous_outputs.past_loops %}
            Previous empathetic insights (build upon these):
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round }}: Focus on human impact and emotional considerations
            Key tensions: {{ loop.remaining_tensions }}
            {% endfor %}
            
            Deepen empathetic understanding beyond previous attempts.
            {% endif %}
            
            Focus on human impact, emotional intelligence, and inclusive perspectives.
        
        - id: skeptical_reasoner
          type: openai-answer
          prompt: |
            Provide critical, skeptical analysis of: {{ input }}
            
            Context: {{ previous_outputs.memory_context }}
            
            {% if previous_outputs.past_loops %}
            Previous critical points (strengthen and expand):
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round }} blind spots: {{ loop.blind_spots }}
            Unresolved tensions: {{ loop.remaining_tensions }}
            {% endfor %}
            
            Identify NEW critical issues not raised in previous rounds.
            {% endif %}
            
            Challenge assumptions, identify risks, and probe weak points.
        
        - id: creative_reasoner  
          type: openai-answer
          prompt: |
            Provide creative, innovative analysis for: {{ input }}
            
            Context: {{ previous_outputs.memory_context }}
            
            {% if previous_outputs.past_loops %}
            Build on creative insights from {{ previous_outputs.past_loops | length }} rounds:
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round }}: Creative elements explored
            Areas needing innovation: {{ loop.remaining_tensions }}
            {% endfor %}
            
            Generate NOVEL creative approaches not tried before.
            {% endif %}
            
            Think outside conventional frameworks, propose innovative solutions.
        
        - id: join_views
          type: join
          group: fork_perspectives
          prompt: |
            Synthesis of multi-perspective analysis:
            
            Logical: {{ previous_outputs.logical_reasoner }}
            Empathetic: {{ previous_outputs.empathetic_reasoner }}
            Skeptical: {{ previous_outputs.skeptical_reasoner }} 
            Creative: {{ previous_outputs.creative_reasoner }}
            
            Integrate all perspectives into coherent synthesis.
        
        # Agreement finder implementation
        - id: consensus_evaluator
          type: openai-answer
          prompt: |
            Evaluate consensus among these perspectives on: {{ input }}
            
            Perspectives to analyze:
            1. Logical: {{ previous_outputs.logical_reasoner }}
            2. Empathetic: {{ previous_outputs.empathetic_reasoner }}
            3. Skeptical: {{ previous_outputs.skeptical_reasoner }}
            4. Creative: {{ previous_outputs.creative_reasoner }}
            
            {% if previous_outputs.past_loops %}
            Consensus evolution across {{ previous_outputs.past_loops | length }} rounds:
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round }}: {{ loop.consensus_score }} - {{ loop.emerging_consensus }}
            {% endfor %}
            
            Current round MUST show measurable progress toward consensus.
            {% endif %}
            
            Consensus Analysis:
            1. Calculate thematic overlap between perspectives (0-100%)
            2. Identify areas of strong agreement
            3. Assess remaining disagreements
            4. Determine overall consensus level
            
            Scoring criteria:
            - 0.95-1.00: Full consensus achieved
            - 0.85-0.94: Strong consensus, minor refinements needed
            - 0.70-0.84: Moderate consensus, significant areas of agreement
            - 0.55-0.69: Weak consensus, major disagreements remain
            - 0.00-0.54: No consensus, fundamental disagreements
            
            CONSENSUS_SCORE: [0.0-1.0]
            CONSENSUS_STATUS: [Full/Strong/Moderate/Weak/No consensus]
            AGREEMENT_AREAS: [list key agreement points]
            DISAGREEMENT_AREAS: [list remaining tensions]
        
        # Store round results in memory
        - id: round_memory_storage
          type: memory-writer
          namespace: deliberation_history
          params:
            vector: true
            memory_type: long_term
            metadata:
              round_number: "{{ loop_number }}"
              consensus_score: "{{ score }}"
              participant_count: 4
              topic: "{{ input | truncate(100) }}"
              timestamp: "{{ now() }}"
          prompt: |
            Deliberation Round {{ loop_number }} Results:
            
            Topic: {{ input }}
            Consensus Score: {{ score }}
            
            Participant Perspectives:
            - Logical: {{ previous_outputs.logical_reasoner | truncate(300) }}
            - Empathetic: {{ previous_outputs.empathetic_reasoner | truncate(300) }}
            - Skeptical: {{ previous_outputs.skeptical_reasoner | truncate(300) }}
            - Creative: {{ previous_outputs.creative_reasoner | truncate(300) }}
            
            Consensus Evaluation: {{ previous_outputs.consensus_evaluator }}
            
            Status: Round {{ loop_number }} of deliberation process

  # Final consensus builder
  - id: consensus_builder
    type: openai-answer
    prompt: |
      Build final consensus from {{ previous_outputs.deliberation_loop.loops_completed }} rounds of deliberation:
      
      Original question: {{ input }}
      
      Deliberation progression:
      {% for loop in previous_outputs.deliberation_loop.past_loops %}
      Round {{ loop.round }} (Score: {{ loop.consensus_score }}):
      - Emerging consensus: {{ loop.emerging_consensus }}
      - Remaining tensions: {{ loop.remaining_tensions }}
      - Blind spots identified: {{ loop.blind_spots }}
      {% endfor %}
      
      Final deliberation result:
      {{ previous_outputs.deliberation_loop.result }}
      
      Synthesis Requirements:
      1. Acknowledge the evolution of thinking across rounds
      2. Present the emerged consensus clearly
      3. Address how initial disagreements were resolved
      4. Note any remaining areas for future consideration
      5. Provide actionable recommendations based on consensus
      
      Create a unified perspective that honors all viewpoints while establishing clear consensus.
```

This comprehensive component guide provides the detailed documentation needed for effective debugging and development of OrKa workflows, addressing the specific gaps identified in the problem statement.