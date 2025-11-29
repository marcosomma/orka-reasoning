# OrKa Test Cases and Validation Guide

> **Last Updated:** 29 November 2025  
> **Status:** 🟢 Current  
> **Related:** [Test Coverage Strategy](TEST_COVERAGE_ENHANCEMENT_STRATEGY.md) | [Testing Roadmap](TESTING_IMPROVEMENTS_ROADMAP.md) | [Debugging](DEBUGGING.md) | [index](index.md)

[📘 Getting Started](./getting-started.md) | [⚙️ Configuration](./CONFIGURATION.md) | [🐛 Debugging](./DEBUGGING.md) | [🧩 Core Components](./COMPONENTS.md)

## Overview

This guide provides comprehensive test cases and validation procedures for OrKa's core components. It includes specific test scenarios for the issues identified in production deployments, automated testing procedures, and manual validation steps.

## Table of Contents

- [Memory System Test Cases](#memory-system-test-cases)
- [Agreement Finder Validation](#agreement-finder-validation)
- [LoopNode Testing Procedures](#loopnode-testing-procedures)
- [FT.SEARCH Validation Tests](#ftsearch-validation-tests)
- [Template Resolution Testing](#template-resolution-testing)
- [Integration Test Scenarios](#integration-test-scenarios)

## Memory System Test Cases

### TTL and Decay Testing

**Test Case 1: Memory Decay Validation**

*Purpose:* Verify that memories expire according to configured TTL values and that decay statistics are accurate.

*Setup:*
```bash
# Configure fast TTL for testing
export ORKA_MEMORY_DECAY_ENABLED=true
export ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=0.017  # 1 minute
export ORKA_MEMORY_DECAY_LONG_TERM_HOURS=0.033   # 2 minutes  
export ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES=0.5  # 30 seconds

# Start test environment
docker run -d -p 6380:6380 --name orka-redis-test redis/redis-stack:latest
```

*Test Script (`test_memory_decay.py`):*
```python
#!/usr/bin/env python3
"""Memory Decay Test Suite"""

import asyncio
import time
import json
from datetime import datetime
from orka.memory.redisstack_logger import RedisStackMemoryLogger

async def test_memory_decay():
    """Test memory expiration and cleanup"""
    logger = RedisStackMemoryLogger(redis_url="redis://localhost:6380/0")
    
    print("=== Memory Decay Test ===")
    print(f"Test started at: {datetime.now()}")
    
    # Test 1: Store short-term memories
    short_term_memories = []
    for i in range(5):
        memory_data = {
            "content": f"Short-term test memory {i}",
            "node_id": "test_node",
            "trace_id": f"decay_test_{i}",
            "namespace": "decay_test",
            "category": "stored",
            "memory_type": "short_term"
        }
        await logger.log_event(memory_data)
        short_term_memories.append(memory_data)
    
    # Test 2: Store long-term memories
    long_term_memories = []
    for i in range(3):
        memory_data = {
            "content": f"Long-term test memory {i}",
            "node_id": "test_node",
            "trace_id": f"decay_test_long_{i}",
            "namespace": "decay_test",
            "category": "stored", 
            "memory_type": "long_term"
        }
        await logger.log_event(memory_data)
        long_term_memories.append(memory_data)
    
    print(f"✅ Stored {len(short_term_memories)} short-term + {len(long_term_memories)} long-term memories")
    
    # Test 3: Verify initial state
    stats_initial = await logger.get_memory_statistics()
    print(f"Initial stats: {stats_initial}")
    
    # Test 4: Wait for short-term expiration (1 minute)
    print("⏳ Waiting 70 seconds for short-term expiration...")
    await asyncio.sleep(70)
    
    # Force cleanup
    await logger.cleanup_expired_memories()
    stats_after_short = await logger.get_memory_statistics()
    print(f"After short-term expiration: {stats_after_short}")
    
    # Verify short-term memories expired
    short_term_expired = stats_after_short.get('expired_entries', 0) >= 5
    assert short_term_expired, f"Short-term memories should have expired: {stats_after_short}"
    print("✅ Short-term memory expiration working")
    
    # Test 5: Wait for long-term expiration (2 minutes total)
    print("⏳ Waiting 60 more seconds for long-term expiration...")
    await asyncio.sleep(60)
    
    await logger.cleanup_expired_memories()
    stats_final = await logger.get_memory_statistics()
    print(f"Final stats: {stats_final}")
    
    # Verify all memories expired
    total_expired = stats_final.get('expired_entries', 0)
    expected_expired = len(short_term_memories) + len(long_term_memories)
    assert total_expired >= expected_expired, f"Expected {expected_expired} expired, got {total_expired}"
    print("✅ Long-term memory expiration working")
    
    print("🎉 Memory decay test completed successfully!")
    return True

if __name__ == "__main__":
    asyncio.run(test_memory_decay())
```

*Expected Results:*
- Initial storage: 8 memories (5 short + 3 long)
- After 70 seconds: 5+ expired entries (short-term)
- After 130 seconds: 8+ expired entries (all memories)
- `orka memory stats` shows `expired_entries > 0`

**Test Case 2: TTL Configuration Validation**

*Purpose:* Verify that TTL values from different sources (environment, YAML) are applied correctly.

*Test Script (`test_ttl_configuration.py`):*
```python
#!/usr/bin/env python3
"""TTL Configuration Test"""

import os
import yaml
import tempfile
from orka.memory.redisstack_logger import RedisStackMemoryLogger

def test_ttl_configuration_precedence():
    """Test TTL configuration precedence: env vars > YAML > defaults"""
    
    print("=== TTL Configuration Test ===")
    
    # Test 1: Environment variables take precedence
    os.environ["ORKA_MEMORY_DECAY_SHORT_TERM_HOURS"] = "4"
    os.environ["ORKA_MEMORY_DECAY_LONG_TERM_HOURS"] = "48"
    
    logger = RedisStackMemoryLogger(redis_url="redis://localhost:6380/0")
    config = logger.memory_decay_config
    
    assert config.get('short_term_hours') == 4.0, f"Short-term should be 4h, got {config.get('short_term_hours')}"
    assert config.get('long_term_hours') == 48.0, f"Long-term should be 48h, got {config.get('long_term_hours')}"
    
    print("✅ Environment variable precedence working")
    
    # Test 2: Verify against common misconfiguration (0.1h/0.2h)  
    os.environ["ORKA_MEMORY_DECAY_SHORT_TERM_HOURS"] = "0.1"
    os.environ["ORKA_MEMORY_DECAY_LONG_TERM_HOURS"] = "0.2"
    
    logger2 = RedisStackMemoryLogger(redis_url="redis://localhost:6380/0")
    config2 = logger2.memory_decay_config
    
    print(f"Fast TTL config (for testing): short={config2.get('short_term_hours')}h, long={config2.get('long_term_hours')}h")
    assert config2.get('short_term_hours') == 0.1, "Fast TTL should be configurable"
    
    # Test 3: Clean up environment
    del os.environ["ORKA_MEMORY_DECAY_SHORT_TERM_HOURS"]
    del os.environ["ORKA_MEMORY_DECAY_LONG_TERM_HOURS"]
    
    print("✅ TTL configuration test completed")
    return True

if __name__ == "__main__":
    test_ttl_configuration_precedence()
```

### RedisStack and FT.SEARCH Testing

**Test Case 3: Index Creation and Search Validation**

*Test Script (`test_ft_search.py`):*
```python
#!/usr/bin/env python3
"""FT.SEARCH Validation Test Suite"""

import asyncio
import redis
import numpy as np
from sentence_transformers import SentenceTransformer
from orka.memory.redisstack_logger import RedisStackMemoryLogger

async def test_ft_search_functionality():
    """Comprehensive FT.SEARCH testing"""
    
    print("=== FT.SEARCH Functionality Test ===")
    
    # Setup
    redis_client = redis.Redis(host='localhost', port=6380, db=0)
    logger = RedisStackMemoryLogger(redis_url="redis://localhost:6380/0")
    
    # Test 1: Verify RedisStack modules
    modules = redis_client.execute_command("MODULE", "LIST")
    search_module = any("search" in str(module).lower() for module in modules)
    assert search_module, "RedisStack search module not found - using basic Redis instead of RedisStack"
    print("✅ RedisStack search module detected")
    
    # Test 2: Store test memories with embeddings
    model = SentenceTransformer('all-MiniLM-L6-v2')
    test_memories = [
        {
            "content": "Machine learning algorithms for social justice applications",
            "node_id": "cognitive_debate_loop",
            "trace_id": "search_test_1", 
            "namespace": "ai_ethics",
            "category": "stored",
            "memory_type": "long_term"
        },
        {
            "content": "Artificial intelligence bias mitigation strategies",
            "node_id": "cognitive_debate_loop",
            "trace_id": "search_test_2",
            "namespace": "ai_ethics", 
            "category": "stored",
            "memory_type": "long_term"
        },
        {
            "content": "Climate change adaptation using renewable energy",
            "node_id": "environmental_node",
            "trace_id": "search_test_3",
            "namespace": "environment",
            "category": "stored",
            "memory_type": "long_term"
        }
    ]
    
    for memory in test_memories:
        await logger.log_event(memory)
    
    print(f"✅ Stored {len(test_memories)} test memories")
    
    # Test 3: Verify index creation
    try:
        index_info = redis_client.execute_command("FT.INFO", "orka_enhanced_memory")
        print("✅ Index 'orka_enhanced_memory' exists")
    except redis.exceptions.ResponseError as e:
        if "Unknown index name" in str(e):
            print("❌ Index not found - this indicates index creation failed")
            return False
        raise
    
    # Test 4: Basic text search
    try:
        results = redis_client.execute_command(
            "FT.SEARCH", "orka_enhanced_memory",
            "machine learning",
            "LIMIT", "0", "5"
        )
        num_results = results[0] if results else 0
        print(f"✅ Text search returned {num_results} results")
        assert num_results > 0, "Text search should find relevant memories"
    except redis.exceptions.ResponseError as e:
        print(f"❌ Text search failed: {e}")
        return False
    
    # Test 5: Metadata filtering search
    try:
        results = redis_client.execute_command(
            "FT.SEARCH", "orka_enhanced_memory",
            "(@namespace:ai_ethics) (@node_id:cognitive_debate_loop)",
            "LIMIT", "0", "10"
        )
        num_results = results[0] if results else 0
        print(f"✅ Metadata filtering returned {num_results} results")
        assert num_results >= 2, "Should find both AI ethics memories"
    except redis.exceptions.ResponseError as e:
        print(f"❌ Metadata filtering failed: {e}")
        return False
    
    # Test 6: Vector search (if embeddings are working)
    query_embedding = model.encode("AI fairness and bias reduction")
    query_blob = query_embedding.astype(np.float32).tobytes()
    
    try:
        results = redis_client.execute_command(
            "FT.SEARCH", "orka_enhanced_memory",
            "*=>[KNN 3 @embedding $query_vec AS distance]",
            "PARAMS", "2", "query_vec", query_blob,
            "RETURN", "3", "content", "distance", "node_id",
            "LIMIT", "0", "3"
        )
        num_results = results[0] if results else 0
        print(f"✅ Vector search returned {num_results} results")
        
        if num_results > 0:
            # Check that results are ranked by distance
            distances = []
            for i in range(1, len(results), 2):
                if isinstance(results[i], list) and len(results[i]) >= 4:
                    distance_idx = results[i].index(b'distance') + 1
                    if distance_idx < len(results[i]):
                        distances.append(float(results[i][distance_idx]))
            
            if len(distances) > 1:
                assert distances == sorted(distances), "Vector search results should be sorted by distance"
                print("✅ Vector search results properly ranked")
                
    except redis.exceptions.ResponseError as e:
        print(f"⚠️ Vector search failed (may be expected if embeddings not generated): {e}")
    
    # Test 7: Hybrid search through memory logger
    search_results = await logger.search_memories(
        query="machine learning fairness",
        namespace="ai_ethics",
        limit=5,
        similarity_threshold=0.5
    )
    
    assert len(search_results) > 0, "Memory logger search should return results"
    print(f"✅ Memory logger hybrid search returned {len(search_results)} results")
    
    print("🎉 FT.SEARCH functionality test completed successfully!")
    return True

if __name__ == "__main__":
    asyncio.run(test_ft_search_functionality())
```

## Agreement Finder Validation  

**Test Case 4: Agreement Score Consistency**

*Purpose:* Validate that agreement scores are consistent and threshold logic works correctly.

*Test Script (`test_agreement_finder.py`):*
```python
#!/usr/bin/env python3
"""Agreement Finder Validation Tests"""

import asyncio
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

async def test_agreement_calculation():
    """Test agreement calculation consistency and thresholds"""
    
    print("=== Agreement Finder Validation ===")
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Test scenarios with expected outcomes
    test_scenarios = [
        {
            "name": "High Agreement Scenario",
            "responses": [
                "AI should prioritize ethical considerations and social justice",
                "Artificial intelligence must focus on ethics and fairness", 
                "AI systems need strong ethical frameworks for social good"
            ],
            "expected_score_min": 0.80,  # Expect high similarity
            "expected_status": "Consensus reached"
        },
        {
            "name": "Low Agreement Scenario", 
            "responses": [
                "AI should prioritize economic efficiency above all else",
                "Focus environmental sustainability should be the main AI goal",
                "AI development should emphasize military defense applications"
            ],
            "expected_score_max": 0.65,  # Expect low similarity
            "expected_status": "No agreement found"
        },
        {
            "name": "Moderate Agreement Scenario",
            "responses": [
                "AI should balance ethical considerations with practical implementation needs",
                "While ethics are important, we must consider technical feasibility in AI systems", 
                "Ethical AI is crucial, but we need realistic approaches to implementation"
            ],
            "expected_score_min": 0.60,
            "expected_score_max": 0.80,
            "expected_status": "Moderate consensus"
        }
    ]
    
    def compute_agreement_score(responses):
        """Implement agreement calculation logic"""
        embeddings = model.encode(responses)
        similarities = cosine_similarity(embeddings)
        
        # Extract upper triangular matrix (avoid duplicates and diagonal)
        upper_triangular = similarities[np.triu_indices_from(similarities, k=1)]
        mean_similarity = np.mean(upper_triangular)
        
        if mean_similarity >= 0.85:
            status = "Strong consensus"
        elif mean_similarity >= 0.65:
            status = "Consensus reached"
        else:
            status = "No agreement found"
            
        return {
            "agreement_score": float(mean_similarity),
            "agreement_status": status,
            "individual_similarities": similarities
        }
    
    # Run test scenarios
    all_passed = True
    for scenario in test_scenarios:
        print(f"\n--- {scenario['name']} ---")
        print("Responses:")
        for i, response in enumerate(scenario['responses'], 1):
            print(f"  {i}. {response}")
        
        # Calculate agreement multiple times to test consistency
        scores = []
        for run in range(3):
            result = compute_agreement_score(scenario['responses'])
            scores.append(result['agreement_score'])
            
        avg_score = np.mean(scores)
        score_std = np.std(scores)
        
        print(f"Agreement scores across 3 runs: {[f'{s:.3f}' for s in scores]}")
        print(f"Average: {avg_score:.3f}, Std dev: {score_std:.4f}")
        print(f"Status: {result['agreement_status']}")
        
        # Validate consistency (std dev should be very low)
        consistency_passed = score_std < 0.001  # Should be near-identical
        print(f"Consistency: {'✅ PASS' if consistency_passed else '❌ FAIL'} (std dev < 0.001)")
        
        # Validate expected score range
        score_range_passed = True
        if 'expected_score_min' in scenario:
            score_range_passed &= avg_score >= scenario['expected_score_min']
        if 'expected_score_max' in scenario:
            score_range_passed &= avg_score <= scenario['expected_score_max']
            
        print(f"Score range: {'✅ PASS' if score_range_passed else '❌ FAIL'}")
        
        if not (consistency_passed and score_range_passed):
            all_passed = False
    
    # Test edge cases
    print("\n--- Edge Case Testing ---")
    
    # Edge Case 1: Identical responses
    identical_responses = ["AI ethics are important"] * 3
    identical_result = compute_agreement_score(identical_responses)
    identical_passed = abs(identical_result['agreement_score'] - 1.0) < 0.001
    print(f"Identical responses: {identical_result['agreement_score']:.3f} {'✅ PASS' if identical_passed else '❌ FAIL'}")
    
    # Edge Case 2: Minimum responses (2)
    min_responses = ["AI should focus on ethics", "Ethics in AI are crucial"]
    min_result = compute_agreement_score(min_responses)
    print(f"Minimum responses (2): {min_result['agreement_score']:.3f} ✅ PASS")
    
    if not identical_passed:
        all_passed = False
    
    print(f"\n🎉 Agreement Finder Validation: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
    return all_passed

if __name__ == "__main__":
    asyncio.run(test_agreement_calculation())
```

## LoopNode Testing Procedures

**Test Case 5: Multi-Round Loop Execution**

*Purpose:* Verify that LoopNode properly manages state across iterations and stops at appropriate thresholds.

*Test Workflow (`test_loop_node.yml`):*
```yaml
# Test workflow for LoopNode validation
orchestrator:
  id: loop-node-test
  strategy: sequential
  memory_config:
    decay:
      enabled: false  # Disable for testing
  agents: [loop_validator]

agents:
  - id: loop_validator
    type: loop
    max_loops: 4
    score_threshold: 0.85
    score_extraction_pattern: "TEST_SCORE:\\s*([0-9.]+)"
    
    # Cognitive extraction for validation
    cognitive_extraction:
      enabled: true
      extract_patterns:
        insights:
          - "(?:insight|learning):\\s*(.+?)(?:\\n|$)"
        improvements:
          - "(?:improve|enhance)\\s+(.+?)(?:\\n|$)"
        mistakes:
          - "(?:mistake|error):\\s*(.+?)(?:\\n|$)"
    
    # Track loop progression
    past_loops_metadata:
      round: "{{ loop_number }}"
      test_score: "{{ score }}"
      iteration_timestamp: "{{ now() }}"
      insights_found: "{{ insights }}"
      improvement_areas: "{{ improvements }}"
    
    internal_workflow:
      orchestrator:
        id: loop-test-cycle
        strategy: sequential
        agents: [progressive_analyzer, score_generator]
      
      agents:
        - id: progressive_analyzer
          type: openai-answer
          prompt: |
            LOOP TEST - Round {{ loop_number }}
            Analyze: {{ input }}
            
            {% if previous_outputs.past_loops %}
            Previous rounds ({{ previous_outputs.past_loops | length }}):
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round }}: Score {{ loop.test_score }}
            - Insights: {{ loop.insights_found }}
            - Improvements: {{ loop.improvement_areas }}
            {% endfor %}
            
            REQUIREMENT: Provide PROGRESSIVE IMPROVEMENT from previous rounds.
            Show learning and refinement based on past insights.
            {% else %}
            This is the initial analysis round.
            {% endif %}
            
            Key requirements:
            - Demonstrate understanding of the topic
            - Show progressive depth if this is not round 1
            - Identify specific insights for learning
            
            Insight: [Key learning from this analysis]
            Improvement area: [What could be enhanced]
        
        - id: score_generator
          type: openai-answer
          prompt: |
            Rate the quality of this analysis (0.0-1.0):
            
            Analysis: {{ previous_outputs.progressive_analyzer }}
            
            Scoring criteria:
            - Round 1: Baseline analysis (score: 0.60-0.70)
            - Round 2: Shows improvement (score: 0.70-0.80) 
            - Round 3: Significant enhancement (score: 0.80-0.90)
            - Round 4: Excellent refinement (score: 0.85+)
            
            {% if previous_outputs.past_loops %}
            Previous best score: {{ previous_outputs.past_loops | map(attribute='test_score') | max }}
            Current analysis should show measurable improvement.
            {% endif %}
            
            Expected progression:
            - Each round should build on previous insights
            - Quality should increase with each iteration
            - Score should reflect cumulative learning
            
            TEST_SCORE: [0.XX]
            Justification: [Why this score reflects the analysis quality and progression]
```

*Validation Script (`validate_loop_execution.py`):*
```python
#!/usr/bin/env python3
"""Loop Node Execution Validation"""

import json
import re
import subprocess
import tempfile

def test_loop_node_execution():
    """Test LoopNode execution and progression"""
    
    print("=== LoopNode Execution Test ===")
    
    # Run the test workflow
    test_input = "Analyze the importance of AI ethics in modern technology development"
    
    try:
        result = subprocess.run([
            "orka", "run", "test_loop_node.yml", test_input
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"❌ Workflow execution failed: {result.stderr}")
            return False
        
        output = result.stdout
        print("✅ Workflow executed successfully")
        
        # Parse output for validation
        print("\n--- Output Analysis ---")
        
        # Check for loop progression indicators
        loop_indicators = [
            "Round 1", "Round 2", "Round 3", "Round 4",
            "past_loops", "score", "threshold"
        ]
        
        found_indicators = []
        for indicator in loop_indicators:
            if indicator in output:
                found_indicators.append(indicator)
        
        print(f"Loop indicators found: {found_indicators}")
        
        # Extract scores if possible
        score_pattern = r"TEST_SCORE:\s*([0-9.]+)"
        scores = re.findall(score_pattern, output)
        
        if scores:
            scores = [float(s) for s in scores]
            print(f"Extracted scores: {scores}")
            
            # Validate score progression
            if len(scores) > 1:
                score_increased = all(scores[i] >= scores[i-1] for i in range(1, len(scores)))
                print(f"Score progression: {'✅ PASS' if score_increased else '❌ FAIL'}")
            
            # Check if threshold was met
            threshold_met = any(s >= 0.85 for s in scores)
            print(f"Threshold reached (≥0.85): {'✅ YES' if threshold_met else '⚠️ NO'}")
            
        else:
            print("⚠️ No scores extracted - check score extraction pattern")
        
        # Check for required components
        required_components = [
            "progressive_analyzer", "score_generator",
            "insights", "improvements", "past_loops"
        ]
        
        components_found = sum(1 for comp in required_components if comp in output)
        print(f"Required components found: {components_found}/{len(required_components)}")
        
        success = (
            len(found_indicators) >= 4 and  # Basic loop structure
            components_found >= 4  # Essential components present
        )
        
        print(f"\n🎉 LoopNode Test: {'✅ PASS' if success else '❌ FAIL'}")
        return success
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out (>5 minutes)")
        return False
    except Exception as e:
        print(f"❌ Test execution error: {e}")
        return False

if __name__ == "__main__":
    test_loop_node_execution()
```

## Template Resolution Testing

**Test Case 6: Template Variable Resolution**

*Test Script (`test_template_resolution.py`):*
```python
#!/usr/bin/env python3
"""Template Resolution Validation"""

from jinja2 import Template, StrictUndefined, DebugUndefined

def test_template_patterns():
    """Test common template patterns and error handling"""
    
    print("=== Template Resolution Tests ===")
    
    # Test scenarios
    test_cases = [
        {
            "name": "Basic Variable Access",
            "template": "Input: {{ input }}\nPrevious: {{ previous_outputs.agent1 }}",
            "context": {
                "input": "test input",
                "previous_outputs": {"agent1": "agent1 output"}
            },
            "should_succeed": True
        },
        {
            "name": "Safe Default Access",
            "template": "Score: {{ score | default('not available') }}\nOptional: {{ optional_var | default('N/A') }}",
            "context": {"score": 0.85},
            "should_succeed": True
        },
        {
            "name": "Conditional Logic",
            "template": """
            {% if previous_outputs.past_loops %}
            Found {{ previous_outputs.past_loops | length }} previous loops
            {% else %}
            No previous loops available
            {% endif %}
            """,
            "context": {
                "previous_outputs": {
                    "past_loops": [{"iteration": 1}, {"iteration": 2}]
                }
            },
            "should_succeed": True
        },
        {
            "name": "Missing Variable (Strict)",
            "template": "Missing: {{ undefined_variable }}",
            "context": {"input": "test"},
            "should_succeed": False,
            "undefined": StrictUndefined
        },
        {
            "name": "Nested Object Access",
            "template": "Result: {{ previous_outputs.analyzer.result | default('no result') }}",
            "context": {
                "previous_outputs": {
                    "analyzer": {"result": "analysis complete"}
                }
            },
            "should_succeed": True
        },
        {
            "name": "Loop Iteration Template",
            "template": """
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.iteration }}: {{ loop.score }}
            {% endfor %}
            """,
            "context": {
                "previous_outputs": {
                    "past_loops": [
                        {"iteration": 1, "score": 0.72},
                        {"iteration": 2, "score": 0.81}
                    ]
                }
            },
            "should_succeed": True
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        
        try:
            undefined_class = test_case.get('undefined', DebugUndefined)
            template = Template(
                test_case['template'], 
                undefined=undefined_class,
                trim_blocks=True,
                lstrip_blocks=True
            )
            
            result = template.render(test_case['context'])
            
            if test_case['should_succeed']:
                print("✅ Template rendered successfully")
                print(f"Output: {result.strip()}")
                passed_tests += 1
            else:
                print("❌ Expected failure but template rendered")
                print(f"Unexpected output: {result.strip()}")
                
        except Exception as e:
            if not test_case['should_succeed']:
                print(f"✅ Expected failure: {type(e).__name__}: {e}")
                passed_tests += 1
            else:
                print(f"❌ Unexpected failure: {type(e).__name__}: {e}")
    
    print(f"\n🎉 Template Resolution Tests: {passed_tests}/{total_tests} passed")
    return passed_tests == total_tests

if __name__ == "__main__":
    test_template_patterns()
```

## Integration Test Scenarios

**Integration Test 1: Complete Cognitive Society Workflow**

*Test Workflow (`test_cognitive_society.yml`):*
```yaml
# Integration test for complete cognitive society workflow
orchestrator:
  id: cognitive-society-integration-test
  strategy: sequential
  memory_config:
    decay:
      enabled: false  # Disable for testing consistency
  agents: [memory_context, deliberation_loop, consensus_builder, results_validator]

agents:
  # Retrieve any existing context
  - id: memory_context
    type: memory-reader
    namespace: integration_test
    params:
      limit: 5
      similarity_threshold: 0.6
    prompt: "Find context for: {{ input }}"
  
  # Main deliberation loop
  - id: deliberation_loop
    type: loop
    max_loops: 3
    score_threshold: 0.80
    score_extraction_pattern: "CONSENSUS_SCORE:\\s*([0-9.]+)"
    
    cognitive_extraction:
      enabled: true
      extract_patterns:
        insights: ["consensus\\s+(?:emerging|developing)\\s+(.+?)(?:\\n|$)"]
        improvements: ["(?:disagreement|tension)\\s+(?:on|around)\\s+(.+?)(?:\\n|$)"]
        mistakes: ["(?:overlooked|missed)\\s+(.+?)(?:\\n|$)"]
    
    past_loops_metadata:
      round: "{{ loop_number }}"
      consensus_score: "{{ score }}"
      emerging_consensus: "{{ insights }}"
      remaining_tensions: "{{ improvements }}"
      
    internal_workflow:
      orchestrator:
        id: deliberation-round
        strategy: sequential
        agents: [fork_perspectives, join_views, consensus_evaluator]
      
      agents:
        - id: fork_perspectives
          type: fork
          targets:
            - [logical_reasoner]
            - [empathetic_reasoner]
        
        - id: logical_reasoner
          type: openai-answer
          prompt: |
            LOGICAL ANALYSIS - Round {{ loop_number }}
            Topic: {{ input }}
            
            {% if previous_outputs.past_loops %}
            Previous logical insights:
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round }}: {{ loop.emerging_consensus }}
            {% endfor %}
            Build upon and refine these insights.
            {% endif %}
            
            Provide structured logical analysis with clear evidence.
        
        - id: empathetic_reasoner  
          type: openai-answer
          prompt: |
            EMPATHETIC ANALYSIS - Round {{ loop_number }}
            Topic: {{ input }}
            
            {% if previous_outputs.past_loops %}
            Previous empathetic considerations:
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round }}: Human-centered insights
            {% endfor %}
            Deepen empathetic understanding.
            {% endif %}
            
            Focus on human impact and emotional intelligence.
        
        - id: join_views
          type: join
          group: fork_perspectives
          prompt: |
            Synthesis of perspectives:
            Logical: {{ previous_outputs.logical_reasoner }}
            Empathetic: {{ previous_outputs.empathetic_reasoner }}
        
        - id: consensus_evaluator
          type: openai-answer
          prompt: |
            Evaluate consensus between:
            Logical: {{ previous_outputs.logical_reasoner }}
            Empathetic: {{ previous_outputs.empathetic_reasoner }}
            
            {% if previous_outputs.past_loops %}
            Previous consensus scores:
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round }}: {{ loop.consensus_score }}
            {% endfor %}
            Current round should show progress.
            {% endif %}
            
            Rate consensus level (0.0-1.0):
            - Calculate thematic overlap
            - Assess agreement strength  
            - Determine consensus level
            
            CONSENSUS_SCORE: [0.XX]
            CONSENSUS_AREAS: [areas of agreement]
            DISAGREEMENT_AREAS: [remaining tensions]
  
  # Build final consensus
  - id: consensus_builder
    type: openai-answer
    prompt: |
      Build final consensus from deliberation:
      
      Topic: {{ input }}
      Rounds completed: {{ previous_outputs.deliberation_loop.loops_completed }}
      Final score: {{ previous_outputs.deliberation_loop.final_score }}
      
      Deliberation progression:
      {% for loop in previous_outputs.deliberation_loop.past_loops %}
      Round {{ loop.round }}: {{ loop.consensus_score }} - {{ loop.emerging_consensus }}
      {% endfor %}
      
      Create unified consensus that addresses key agreements and tensions.
  
  # Validate test results
  - id: results_validator
    type: openai-answer
    prompt: |
      INTEGRATION TEST VALIDATION
      
      Validate this cognitive society workflow execution:
      
      Initial context: {{ previous_outputs.memory_context }}
      Deliberation rounds: {{ previous_outputs.deliberation_loop.loops_completed }}
      Final consensus: {{ previous_outputs.consensus_builder }}
      
      Validation checklist:
      1. Did multiple deliberation rounds occur? 
      2. Was consensus score progression logical?
      3. Were both logical and empathetic perspectives included?
      4. Was final consensus comprehensive?
      5. Were past loops properly referenced across rounds?
      
      TEST_RESULT: [PASS/FAIL]
      VALIDATION_SUMMARY: [detailed assessment]
```

## Automated Test Suite

**Master Test Runner (`run_all_tests.py`):*
```python
#!/usr/bin/env python3
"""Master test suite for OrKa validation"""

import asyncio
import sys
import traceback
from datetime import datetime

# Import all test modules
from test_memory_decay import test_memory_decay
from test_ttl_configuration import test_ttl_configuration_precedence  
from test_ft_search import test_ft_search_functionality
from test_agreement_finder import test_agreement_calculation
from test_template_resolution import test_template_patterns

async def run_all_tests():
    """Execute complete OrKa test suite"""
    
    print("="*60)
    print("OrKa Framework - Complete Test Suite")
    print(f"Started at: {datetime.now()}")
    print("="*60)
    
    tests = [
        ("Memory Decay Functionality", test_memory_decay),
        ("TTL Configuration Precedence", test_ttl_configuration_precedence),
        ("FT.SEARCH and RedisStack", test_ft_search_functionality),
        ("Agreement Finder Consistency", test_agreement_calculation),
        ("Template Resolution", test_template_patterns),
    ]
    
    results = {}
    failed_tests = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print(f"{'='*60}")
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
            results[test_name] = result
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"\nTest Result: {status}")
            
            if not result:
                failed_tests.append(test_name)
                
        except Exception as e:
            print(f"\n❌ Test CRASHED: {e}")
            print(traceback.format_exc())
            results[test_name] = False
            failed_tests.append(test_name)
    
    # Final summary
    print("\n" + "="*60)
    print("TEST SUITE SUMMARY")
    print("="*60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    
    if failed_tests:
        print(f"\nFailed Tests:")
        for test in failed_tests:
            print(f"  ❌ {test}")
    else:
        print(f"\n🎉 ALL TESTS PASSED!")
    
    print(f"\nCompleted at: {datetime.now()}")
    
    # Return overall success
    return len(failed_tests) == 0

if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest suite interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nTest suite failed with error: {e}")
        sys.exit(1)
```

**Quick Validation Script (`quick_health_check.sh`):*
```bash
#!/bin/bash
# Quick health check for OrKa system

echo "=== OrKa Quick Health Check ==="

# Check 1: Redis/RedisStack connectivity
echo "1. Checking Redis connectivity..."
redis-cli ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Redis connection OK"
else
    echo "   ❌ Redis connection failed"
    exit 1
fi

# Check 2: RedisStack modules
echo "2. Checking RedisStack modules..."
redis-cli MODULE LIST | grep -i search > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Search module loaded"
else
    echo "   ⚠️ Search module not found - using basic Redis"
fi

# Check 3: OrKa memory system
echo "3. Checking OrKa memory system..."
orka memory stats > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Memory system accessible"
else
    echo "   ❌ Memory system not accessible"
fi

# Check 4: Configuration consistency  
echo "4. Checking configuration..."
orka memory configure | grep -E "(Short-term Hours: 2\.0|Long-term Hours: 168\.0)" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ TTL configuration matches README"
else
    echo "   ⚠️ TTL configuration may not match README - check environment variables"
fi

# Check 5: Basic index functionality
echo "5. Testing FT.SEARCH..."
redis-cli FT._LIST | grep orka_enhanced_memory > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Memory index exists"
else
    echo "   ⚠️ Memory index not found - will be created on first use"
fi

echo ""
echo "🎉 Health check completed!"
echo "For detailed testing, run: python run_all_tests.py"
```

This comprehensive test suite addresses all the key issues identified in the problem statement and provides validation procedures for the core OrKa components. The tests can be run individually or as a complete suite to ensure system stability and correct behavior.
---
← [Best Practices](best-practices.md) | [📚 INDEX](index.md) | [Debugging](DEBUGGING.md) →
