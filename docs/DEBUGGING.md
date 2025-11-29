# OrKa Debugging and Troubleshooting Guide

> **Last Updated:** 29 November 2025  
> **Status:** 🟢 Current  
> **Related:** [Troubleshooting](troubleshooting.md) | [FAQ](faq.md) | [Observability](observability.md) | [Testing](TESTING.md) | [INDEX](index.md)

[📘 Getting Started](./getting-started.md) | [⚙️ Configuration](./CONFIGURATION.md) | [🧠 Memory System](./MEMORY_SYSTEM_GUIDE.md) | [🤖 Agent Types](./agents.md)

## Overview

This guide provides comprehensive debugging procedures, troubleshooting steps, and diagnostic tools for OrKa framework issues. It addresses the specific debugging gaps identified in production deployments and provides step-by-step resolution procedures.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Memory System Debugging](#memory-system-debugging)
- [Component-Specific Debugging](#component-specific-debugging)
- [Log Analysis Guide](#log-analysis-guide)
- [Performance Troubleshooting](#performance-troubleshooting)
- [Common Issues and Solutions](#common-issues-and-solutions)

## Quick Diagnostics

### System Health Check

```bash
# Run complete system diagnostics
orka system status

# Memory system health check
orka memory stats
orka memory watch --interval 3

# Configuration verification
orka memory configure

# RedisStack connectivity test
redis-cli PING                           # Should return PONG
redis-cli FT._LIST                       # Should show orka_enhanced_memory
redis-cli FT.INFO orka_enhanced_memory   # Show index details
```

### Log Analysis Quick Start

**Enable Debug Logging:**
```bash
export ORKA_LOG_LEVEL=DEBUG
export ORKA_MEMORY_DEBUG=true
export ORKA_TRACE_ENABLED=true

# Run your workflow with verbose output
orka run your-workflow.yml "test input" --verbose
```

## Memory System Debugging

### FT.SEARCH Failures

**Symptom:** `num_results: 0`, logs show `Syntax error at offset 1 near ,`

**Debugging Steps:**

1. **Check RedisStack Installation:**
   ```bash
   # Verify RedisStack is running (not basic Redis)
   redis-cli MODULE LIST | grep -i search
   # Should show: 1) "search", 2) "20804"
   
   # If empty, you're running basic Redis, not RedisStack
   docker stop orka-redis
   docker run -d -p 6380:6380 --name orka-redis redis/redis-stack:latest
   ```

2. **Verify Index Creation:**
   ```bash
   # Check if index exists
   redis-cli FT._LIST
   # Should show: 1) "orka_enhanced_memory"
   
   # If missing, OrKa will recreate on next run
   # Force index recreation:
   orka memory cleanup --rebuild-index
   ```

3. **Test Query Syntax:**
   ```bash
   # Test basic text search
   redis-cli FT.SEARCH orka_enhanced_memory "test" LIMIT 0 3
   
   # Test with node_id filter  
   redis-cli FT.SEARCH orka_enhanced_memory "(@node_id:cognitive_debate_loop)" LIMIT 0 3
   
   # If syntax errors persist, check Redis version
   redis-cli INFO server | grep redis_version
   # Should be 7.2+ for full FT.SEARCH support
   ```

4. **Check Memory Contents:**
   ```bash
   # List memory keys
   redis-cli KEYS "orka_memory:*" | head -5
   
   # Examine memory structure
   redis-cli HGETALL "orka_memory:$(redis-cli KEYS 'orka_memory:*' | head -1)"
   ```

**Expected Output Examples:**
```bash
# Healthy FT.SEARCH response
1) (integer) 2                     # Number of results
2) "orka_memory:uuid-here"         # Memory key
3) 1) "content"
   2) "User input and response"
4) "orka_memory:uuid-here-2"      # Second result
5) 1) "content"
   2) "Another memory entry"
```

### Memory Decay Issues

**Symptom:** `expired_entries: 0` always, or TTL mismatch (0.1h vs 2h)

**Debugging Steps:**

1. **Check Decay Configuration:**
   ```bash
   # Verify decay settings
   orka memory configure
   
   # Check environment variables
   env | grep ORKA_MEMORY_DECAY
   
   # Expected output:
   # ORKA_MEMORY_DECAY_ENABLED=true
   # ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2
   # ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168
   ```

2. **Test Memory Expiration:**
   ```bash
   # Create test memory with short TTL (60 seconds)
   # This requires a test script - see Test Cases section
   
   # Monitor expiration in real-time
   orka memory watch --interval 5
   
   # After TTL expires, should see expired_entries > 0
   ```

3. **Check Redis TTL Values:**
   ```bash
   # Check actual Redis TTL for memories
   redis-cli KEYS "orka_memory:*" | head -1 | xargs redis-cli TTL
   # Should show seconds remaining, not -1 (never expires)
   
   # Check expire field in memory hash
   redis-cli HGET "orka_memory:$(redis-cli KEYS 'orka_memory:*' | head -1)" orka_expire_time
   ```

### Empty Memory Results

**Symptom:** `shared_memory_reader` consistently returns `num_results: 0`

**Debugging Steps:**

1. **Check Memory Storage:**
   ```bash
   # Verify memories are being stored
   orka memory stats
   # Should show Total Entries > 0
   
   # Check specific namespace
   redis-cli FT.SEARCH orka_enhanced_memory "(@namespace:your_namespace)" LIMIT 0 5
   ```

2. **Test Vector Search:**
   ```bash
   # Check if embeddings are generated
   redis-cli HGET "orka_memory:$(redis-cli KEYS 'orka_memory:*' | head -1)" embedding
   # Should return binary data, not empty string
   
   # Test vector search manually (requires embedding)
   # See Performance Troubleshooting section for embedding test
   ```

3. **Review Search Parameters:**
   ```yaml
   # Debug search configuration in your YAML
   - id: debug_memory_search
     type: memory-reader
     namespace: your_namespace
     params:
       limit: 20                    # Increase limit
       similarity_threshold: 0.5    # Lower threshold
       enable_context_search: false # Disable context temporarily
       memory_type_filter: "all"    # Don't filter by type
   ```

## Component-Specific Debugging

### LoopNode Debugging

**Common Issues:**
- Missing Round 2 scores
- Response duplication  
- Inconsistent agreement scores

**Debugging Steps:**

1. **Check Score Extraction:**
   ```yaml
   # Add debug output to score extraction
   - id: debug_loop
     type: loop
     max_loops: 3
     score_threshold: 0.8
     score_extraction_pattern: "QUALITY_SCORE:\\s*([0-9.]+)"  # Verify pattern matches output
     
     # Add explicit score debugging
     internal_workflow:
       agents:
         - id: scorer
           type: openai-answer
           prompt: |
             Rate this: {{ input }}
             
             DEBUG: Provide score in exact format: QUALITY_SCORE: 0.85
             
             Analysis: ...
             QUALITY_SCORE: [YOUR SCORE HERE]
   ```

2. **Monitor Loop State:**
   ```bash
   # Enable detailed loop debugging
   export ORKA_LOOP_DEBUG=true
   
   # Look for these log patterns:
   # - "Loop iteration X starting"
   # - "Score extracted: X.XX"
   # - "Threshold met: true/false"
   # - "Past loops updated with X entries"
   ```

3. **Check Past Loops Context:**
   ```yaml
   # Verify past_loops are passed correctly
   agents:
     - id: analyzer  
       prompt: |
         Analyze: {{ input }}
         
         {% if previous_outputs.past_loops %}
         Previous attempts ({{ previous_outputs.past_loops | length }}):
         {% for loop in previous_outputs.past_loops %}
         Round {{ loop.iteration }}: Score {{ loop.quality_score }}
         {% endfor %}
         {% else %}
         DEBUG: No past loops available
         {% endif %}
   ```

### Agreement Finder Debugging

**Issues:** Inconsistent scores, missing agreement detection

**Algorithm Details:**
The agreement finder uses cosine similarity on embeddings:
```python
# Simplified algorithm
def compute_agreement(responses):
    embeddings = [get_embedding(response) for response in responses]
    similarities = cosine_similarity(embeddings)
    mean_similarity = np.mean(similarities[np.triu_indices_from(similarities, k=1)])
    
    if mean_similarity >= 0.65:
        return {"score": mean_similarity, "status": "Consensus reached"}
    else:
        return {"score": mean_similarity, "status": "No agreement found"}
```

**Debugging Steps:**

1. **Check Embedding Generation:**
   ```bash
   # Verify sentence-transformers is working
   python -c "
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('all-MiniLM-L6-v2')
   print('Model loaded successfully')
   embedding = model.encode('test text')
   print(f'Embedding shape: {embedding.shape}')
   print(f'First 5 values: {embedding[:5]}')
   "
   ```

2. **Test Agreement Calculation:**
   ```yaml
   # Add debug output for agreement finder
   agents:
     - id: debug_agreement_finder
       type: openai-answer
       prompt: |
         Given these responses, calculate agreement:
         {% for response in agent_responses %}
         Response {{ loop.index }}: {{ response }}
         {% endfor %}
         
         DEBUG: Provide detailed similarity analysis
         
         1. Identify key themes in each response
         2. Calculate conceptual overlap percentage  
         3. Provide final agreement score (0.0-1.0)
         
         AGREEMENT_SCORE: [score]
         AGREEMENT_STATUS: [Consensus reached/No agreement found]
   ```

### Template Resolution Debugging

**Symptom:** `has_unresolved_vars: true` in logs

**Debugging Steps:**

1. **Check Variable Availability:**
   ```yaml
   # Add template debugging
   agents:
     - id: template_debugger
       type: openai-answer
       prompt: |
         DEBUG: Available variables:
         - input: {{ input | default('NOT AVAILABLE') }}
         - previous_outputs keys: {{ previous_outputs.keys() | list | join(', ') }}
         - loop_number: {{ loop_number | default('NOT AVAILABLE') }}
         - score: {{ score | default('NOT AVAILABLE') }}
         
         {% for key, value in previous_outputs.items() %}
         - {{ key }}: {{ value | string | truncate(100) }}
         {% endfor %}
   ```

2. **Use Safe Template Patterns:**
   ```yaml
   # Instead of direct access
   prompt: "Score: {{ score }}"
   
   # Use safe access with defaults
   prompt: "Score: {{ score | default('not available') }}"
   
   # For nested objects
   prompt: "Agreement: {{ previous_outputs.agreement_finder.result | default('no agreement data') }}"
   ```

## Log Analysis Guide

### Key Log Fields and Their Meanings

**Memory System Logs:**
```json
{
  "memory_stats": {
    "total_entries": 1247,           // Total memories stored
    "expired_entries": 156,          // Successfully expired memories
    "short_term": 423,              // Working memory count
    "long_term": 824,               // Knowledge memory count
    "namespaces": ["conversations", "knowledge_base"]
  }
}
```

**Search Result Logs:**
```json
{
  "shared_memory_reader": {
    "num_results": 5,               // Number of memories found
    "search_query": "machine learning", 
    "namespace": "conversations",
    "similarity_threshold": 0.8,
    "search_duration_ms": 12.5
  }
}
```

**Loop Node Logs:**
```json
{
  "past_loops_metadata": {
    "agreement_finder": "Consensus reached",  // Agreement status
    "agreement_score": 0.85,                 // Numerical agreement
    "loop_iteration": 2,                     // Current iteration
    "threshold_met": true                    // Whether to continue looping
  }
}
```

**Template Resolution Logs:**
```json
{
  "template_resolution": {
    "has_unresolved_vars": false,    // Template rendering success
    "resolved_vars": ["input", "previous_outputs", "loop_number"],
    "unresolved_vars": []            // Variables that couldn't be resolved
  }
}
```

### Log Pattern Analysis

**Healthy System Patterns:**
```
INFO: Memory stored successfully in namespace 'conversations'
DEBUG: FT.SEARCH returned 5 results in 3.2ms
INFO: Loop iteration 2 completed with score 0.85
DEBUG: Template rendered successfully, no unresolved variables
```

**Problem Patterns:**
```
ERROR: FT.SEARCH failed: Syntax error at offset 1 near ,
WARN: Memory search returned 0 results for query 'test'
ERROR: Score extraction failed, no pattern match found
WARN: Template has unresolved variables: ['score', 'agreement_finder']
```

## Performance Troubleshooting

### Memory Search Performance

**Slow Search (>100ms):**

1. **Check HNSW Parameters:**
   ```bash
   # View current index configuration
   redis-cli FT.INFO orka_enhanced_memory
   
   # Look for HNSW parameters:
   # M: 16 (connections per node)
   # EF_CONSTRUCTION: 200 (build quality)
   ```

2. **Optimize Search Parameters:**
   ```yaml
   params:
     ef_runtime: 10        # Lower for speed, higher for accuracy
     limit: 5             # Reduce result count
     enable_context_search: false  # Disable if not needed
   ```

3. **Test Vector vs Text Search:**
   ```bash
   # Time vector search
   time redis-cli FT.SEARCH orka_enhanced_memory "*=>[KNN 5 @embedding \$blob]" PARAMS 2 blob "..."
   
   # Time text search
   time redis-cli FT.SEARCH orka_enhanced_memory "machine learning" LIMIT 0 5
   ```

### Memory Usage Optimization

**High Memory Usage:**

1. **Check Memory Distribution:**
   ```bash
   orka memory stats --detailed
   
   # Look for:
   # - High short_term count (may need faster decay)
   # - Large embedding storage (check dimensions)
   # - Excessive metadata (optimize metadata fields)
   ```

2. **Cleanup Strategies:**
   ```bash
   # Force cleanup of expired memories
   orka memory cleanup --verbose
   
   # Dry run to see what would be deleted
   orka memory cleanup --dry-run
   
   # Cleanup specific namespace
   orka memory cleanup --namespace old_conversations
   ```

## Common Issues and Solutions

### Issue: Inconsistent Agreement Scores

**Symptoms:**
- Agreement scores vary wildly (0.6727 to 0.85) for similar content
- Missing Round 2 scores in loop iterations
- "No agreement found" despite high scores

**Root Causes & Solutions:**

1. **Embedding Consistency:**
   ```bash
   # Test embedding consistency
   python -c "
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('all-MiniLM-L6-v2')
   text = 'AI should prioritize social justice'
   emb1 = model.encode(text)
   emb2 = model.encode(text)
   print(f'Embeddings identical: {(emb1 == emb2).all()}')
   "
   ```

2. **Agreement Threshold Calibration:**
   ```yaml
   # Add explicit agreement threshold
   agents:
     - id: agreement_evaluator
       type: openai-answer
       prompt: |
         Evaluate agreement between responses:
         {% for response in responses %}
         Response {{ loop.index }}: {{ response }}
         {% endfor %}
         
         Agreement criteria:
         - Score ≥ 0.85: Strong consensus
         - Score ≥ 0.65: Moderate agreement  
         - Score < 0.65: No clear agreement
         
         AGREEMENT_SCORE: [0.0-1.0]
   ```

3. **Context Preservation in Loops:**
   ```yaml
   # Ensure proper context passing
   past_loops_metadata:
     iteration: "{{ loop_number }}"
     previous_score: "{{ score }}"
     previous_agreement: "{{ agreement_finder }}"
     context_size: "{{ previous_outputs | length }}"
   ```

### Issue: Response Duplication in Round 2

**Symptoms:**
- Identical responses across loop iterations
- No improvement despite cognitive extraction
- Cache-like behavior in loop nodes

**Solutions:**

1. **Clear Loop Cache:**
   ```bash
   # Clear Redis loop caches
   redis-cli DEL $(redis-cli KEYS "loop_cache:*")
   
   # Or restart Redis to clear all caches
   docker restart orka-redis
   ```

2. **Add Iteration Context:**
   ```yaml
   internal_workflow:
     agents:
       - id: progressive_refiner
         type: openai-answer
         prompt: |
           Iteration {{ loop_number }}: Refine this analysis
           Original: {{ input }}
           
           {% if previous_outputs.past_loops %}
           Previous attempts that need improvement:
           {% for loop in previous_outputs.past_loops %}
           Attempt {{ loop.iteration }} (Score: {{ loop.quality_score }}):
           - What worked: {{ loop.key_insights }}
           - What needs fixing: {{ loop.areas_to_improve }}
           {% endfor %}
           
           IMPORTANT: Provide a DIFFERENT and IMPROVED analysis than previous attempts.
           {% endif %}
   ```

3. **Force Variation:**
   ```yaml
   agents:
     - id: variation_enforcer
       type: openai-answer
       prompt: |
         {% if loop_number > 1 %}
         CRITICAL: This is iteration {{ loop_number }}. 
         You MUST provide a substantially different approach than:
         {{ previous_outputs.past_loops[-1].result | truncate(200) }}
         {% endif %}
         
         Provide fresh analysis for: {{ input }}
   ```

### Issue: Template Resolution Failures

**Symptoms:**
- `has_unresolved_vars: true` in logs
- Missing variable errors in templates
- Broken template rendering

**Solutions:**

1. **Use Safe Template Patterns:**
   ```yaml
   # Safe variable access
   prompt: |
     Input: {{ input | default('No input provided') }}
     Previous: {{ previous_outputs.agent_name.result | default('No previous result') }}
     Score: {{ score | default('No score available') }}
     
     {% if previous_outputs.past_loops %}
     Past loops: {{ previous_outputs.past_loops | length }}
     {% else %}
     No past loops available
     {% endif %}
   ```

2. **Debug Template Variables:**
   ```yaml
   # Template debugging agent
   - id: template_debugger
     type: openai-answer
     prompt: |
       TEMPLATE DEBUG INFO:
       Available variables: {{ vars() | list | join(', ') }}
       Previous outputs: {{ previous_outputs.keys() | list | join(', ') }}
       
       {% for key in previous_outputs.keys() %}
       {{ key }}: {{ previous_outputs[key] | string | truncate(50) }}...
       {% endfor %}
   ```

## Test Cases and Validation

### Memory System Tests

**Create Test Script (`test_memory_system.py`):**
```python
#!/usr/bin/env python3
"""
OrKa Memory System Test Suite
Tests memory storage, retrieval, and decay functionality
"""

import asyncio
import time
from orka.memory.redisstack_logger import RedisStackMemoryLogger

async def test_memory_operations():
    """Test basic memory operations"""
    logger = RedisStackMemoryLogger(redis_url="redis://localhost:6380/0")
    
    # Test 1: Store memory
    test_data = {
        "content": "Test memory for debugging",
        "node_id": "test_node",
        "trace_id": "debug_trace",
        "namespace": "debug_tests",
        "category": "stored",
        "memory_type": "short_term"
    }
    
    await logger.log_event(test_data)
    print("✅ Memory storage test passed")
    
    # Test 2: Search memory
    search_results = await logger.search_memories(
        query="Test memory",
        namespace="debug_tests",
        limit=5
    )
    
    assert len(search_results) > 0, "Memory search returned no results"
    print(f"✅ Memory search test passed - {len(search_results)} results")
    
    # Test 3: TTL test (short expiry)
    short_ttl_data = {
        **test_data,
        "memory_type": "short_term",
        "orka_expire_time": int(time.time()) + 60  # Expire in 60 seconds
    }
    
    await logger.log_event(short_ttl_data)
    print("✅ TTL test memory created (expires in 60s)")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_memory_operations())
```

**Run Tests:**
```bash
# Run memory system tests
python test_memory_system.py

# Monitor results
orka memory watch --interval 5
```

### FT.SEARCH Validation Tests

**Test HNSW Vector Search:**
```bash
# Test script: test_ft_search.sh
#!/bin/bash

echo "=== OrKa FT.SEARCH Diagnostic Tests ==="

# Test 1: Basic connectivity
echo "Test 1: Redis connectivity"
redis-cli PING
if [ $? -eq 0 ]; then
    echo "✅ Redis connection OK"
else
    echo "❌ Redis connection failed"
    exit 1
fi

# Test 2: RedisStack modules
echo "Test 2: RedisStack modules"
redis-cli MODULE LIST | grep -i search
if [ $? -eq 0 ]; then
    echo "✅ Search module loaded"
else
    echo "❌ Search module not found - using basic Redis instead of RedisStack"
    exit 1
fi

# Test 3: Index existence
echo "Test 3: Index existence"
redis-cli FT._LIST | grep orka_enhanced_memory
if [ $? -eq 0 ]; then
    echo "✅ Index exists"
else
    echo "⚠️ Index not found - will be created on first use"
fi

# Test 4: Basic search syntax
echo "Test 4: Basic search"
redis-cli FT.SEARCH orka_enhanced_memory "*" LIMIT 0 3
if [ $? -eq 0 ]; then
    echo "✅ Basic search syntax OK"
else
    echo "❌ Basic search failed"
fi

echo "=== Diagnostic Tests Complete ==="
```

### Agreement Finder Test Cases

**Test Agreement Calculation:**
```yaml
# test_agreement_scenarios.yml
orchestrator:
  id: agreement-test
  strategy: sequential
  agents:
    - agreement_tester

agents:
  - id: agreement_tester
    type: openai-answer
    prompt: |
      Test agreement calculation for these scenarios:
      
      Scenario 1 (High Agreement - Expected Score ≥ 0.85):
      Response A: "AI should prioritize ethical considerations and social justice"
      Response B: "Artificial intelligence must focus on ethics and fairness" 
      Response C: "AI systems need strong ethical frameworks for social good"
      
      Scenario 2 (Low Agreement - Expected Score < 0.65):
      Response A: "AI should prioritize economic efficiency"
      Response B: "Focus on environmental sustainability in AI"
      Response C: "AI development should emphasize military applications"
      
      Calculate cosine similarity for each scenario.
      Report: SCENARIO_1_SCORE: [score], SCENARIO_2_SCORE: [score]
```

**Run Agreement Tests:**
```bash
# Test agreement calculation
orka run test_agreement_scenarios.yml "Calculate agreement scores"

# Look for expected patterns in output:
# SCENARIO_1_SCORE: 0.87 (high agreement)
# SCENARIO_2_SCORE: 0.34 (low agreement)
```

## Monitoring and Alerting Setup

### Prometheus Metrics

**Enable Metrics Collection:**
```bash
export ORKA_METRICS_ENABLED=true
export ORKA_METRICS_PORT=9090

# Start OrKa with metrics endpoint
orka run your-workflow.yml "test" &

# Check metrics endpoint
curl http://localhost:9090/metrics | grep orka_memory
```

**Key Metrics to Monitor:**
```
orka_memory_total_entries            # Total stored memories
orka_memory_expired_entries          # Successfully expired memories  
orka_memory_search_duration_seconds  # Search performance
orka_memory_ft_search_failures       # FT.SEARCH error count
orka_loop_iterations_total          # Loop node iterations
orka_template_resolution_failures    # Template rendering errors
```

### Health Check Endpoints

```bash
# Memory system health
curl http://localhost:8000/health/memory
# Expected: {"status": "healthy", "backend": "redisstack", "index_exists": true}

# Component health
curl http://localhost:8000/health/components  
# Expected: {"loop_nodes": "healthy", "memory_readers": "healthy", ...}
```

This debugging guide provides comprehensive troubleshooting procedures for the most common OrKa issues. For component-specific debugging, refer to the respective documentation sections.
---
← [Testing](TESTING.md) | [📚 INDEX](index.md) | [Troubleshooting](troubleshooting.md) →
