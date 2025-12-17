# OrKa Integration Examples

[📘 Getting Started](./getting-started.md) | [📝 YAML Configuration](./YAML_CONFIGURATION.md) | [🔍 Architecture](./architecture.md) | [🧪 Testing](./TESTING.md)

## Overview

This document provides comprehensive integration examples showing how OrKa's core components work together in real-world scenarios. **All examples reference actual working files from the [`../examples/`](../examples/) folder** that you can copy and run immediately.

## 🚀 Quick Integration Start

```bash
# View all integration examples
ls ../examples/
cat ../examples/README.md

# Copy and run any integration example
cp ../examples/[example-name].yml my-integration.yml
orka run my-integration.yml "Your test input"
```

## Table of Contents

- [Cognitive Society Enhanced Workflow](#cognitive-society-enhanced-workflow)
- [Memory-Driven Learning System](#memory-driven-learning-system)  
- [Self-Improving Analysis Pipeline](#self-improving-analysis-pipeline)
- [Production Deployment Examples](#production-deployment-examples)

## Cognitive Society Enhanced Workflow

This example demonstrates a complete cognitive society implementation with Agreement Finder, LoopNode, Memory Search, and Template Resolution.

### Complete Integration Example

**Real Working Example**: [`../examples/cognitive_society_minimal_loop.yml`](../examples/cognitive_society_minimal_loop.yml)

**Key Integration Features:**
- **Multi-agent deliberation**: Logical, empathetic, skeptical, and creative perspectives
- **Agreement scoring**: Consensus detection and convergence tracking  
- **Loop learning**: Iterative improvement until threshold met
- **Memory integration**: Context-aware search with 100x faster HNSW
- **Template resolution**: Proper Jinja2 variable handling

**Quick Start:**
```bash
# Copy the working cognitive society example
cp ../examples/cognitive_society_minimal_loop.yml my-cognitive-society.yml

# Run with your topic
orka run my-cognitive-society.yml "Should AI systems have rights?"

# Monitor the deliberation process
orka memory watch
```

**Advanced Integration**: For local LLM deployment, see:
- [`../examples/orka_soc/cognitive_society_with_memory_local_optimal_deepseek-8b.yml`](../examples/orka_soc/)
- [`../examples/orka_smartest/genius_minds_convergence.yml`](../examples/orka_smartest/)

**Integration Architecture:**
```yaml
# Simplified cognitive society pattern
agents:
  - deliberation_loop          # Loop until consensus
    - fork_perspectives        # Parallel reasoning agents  
    - join_views              # Combine perspectives
    - consensus_evaluator     # Score agreement level
  - consensus_builder         # Final synthesis
```
## Memory-Driven Learning System

**Real Working Example**: [`../examples/memory_validation_routing_and_write.yml`](../examples/memory_validation_routing_and_write.yml)

This integration demonstrates:
- **Memory-first approach**: Search existing knowledge before external sources
- **Intelligent validation**: AI determines if memories are sufficient  
- **Automatic fallback**: Web search when memory is insufficient
- **Decay management**: Short-term and long-term memory classification
- **Context continuity**: Conversation-aware memory retrieval

```bash
# Copy the memory learning example
cp ../examples/memory_validation_routing_and_write.yml my-learning-system.yml

# Test memory learning
orka run my-learning-system.yml "What is machine learning?"
orka run my-learning-system.yml "Tell me more about neural networks" 
orka run my-learning-system.yml "How does this relate to what we discussed?"
```

## Self-Improving Analysis Pipeline

**Real Working Example**: [`../examples/cognitive_loop_scoring_example.yml`](../examples/cognitive_loop_scoring_example.yml)

This integration demonstrates:
- **Iterative improvement**: Loop until quality threshold met
- **Cognitive extraction**: Learn from mistakes and insights
- **Score-based continuation**: Automatic quality assessment
- **Learning memory**: Remember insights across iterations

```bash
# Copy the self-improving example  
cp ../examples/cognitive_loop_scoring_example.yml my-analysis-pipeline.yml

# Run iterative analysis
orka run my-analysis-pipeline.yml "Analyze the impact of remote work on productivity"
```
      consensus_score: "{{ score }}"
      timestamp: "{{ now() }}"
      
      # Learning elements  
      emerging_consensus: "{{ insights }}"
      remaining_tensions: "{{ improvements }}"
      cognitive_blind_spots: "{{ mistakes }}"
      
      # Context preservation
      participant_count: "{{ agent_responses | length | default(0) }}"
      discussion_depth: "{{ processing_duration | default('unknown') }}"
      template_resolution_status: "{{ 'resolved' if not has_unresolved_vars else 'partially_resolved' }}"
    
    # Internal deliberation workflow
    internal_workflow:
      orchestrator:
        id: multi-agent-deliberation
        strategy: sequential
        agents: 
          - past_context_integration
          - fork_perspectives
          - join_agent_views
          - agreement_finder
          - memory_persistence
      
      agents:
        # Integrate past loop context to prevent response duplication
        - id: past_context_integration
          type: openai-answer
          prompt: |
            DELIBERATION CONTEXT - Round {{ loop_number }}
            Topic: {{ input }}
            
            External Context:
            {{ previous_outputs.context_memory_search }}
            
            {% if previous_outputs.past_loops %}
            Previous Deliberation Rounds ({{ previous_outputs.past_loops | length }}):
            
            {% for loop in previous_outputs.past_loops %}
            === Round {{ loop.round_number }} (Score: {{ loop.consensus_score }}) ===
            Timestamp: {{ loop.timestamp }}
            Emerging Consensus: {{ loop.emerging_consensus }}
            Remaining Tensions: {{ loop.remaining_tensions }}
            Blind Spots Identified: {{ loop.cognitive_blind_spots }}
            
            {% if loop.template_resolution_status != 'resolved' %}
            ⚠️ Template Resolution Issues: Some variables were unresolved
            {% endif %}
            {% endfor %}
            
            CRITICAL REQUIREMENTS for Round {{ loop_number }}:
            1. Build upon previous emerging consensus
            2. Address remaining tensions identified
            3. Avoid blind spots from previous rounds  
            4. Provide NEW insights not previously discussed
            5. Show clear PROGRESSION from previous attempts
            
            {% else %}
            This is the initial deliberation round.
            Focus on establishing diverse baseline perspectives.
            {% endif %}
            
            Context Summary: Prepared for {{ loop_number }} round of deliberation
        
        # Multi-perspective agent deliberation
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
            LOGICAL REASONING - Round {{ loop_number }}
            Topic: {{ input }}
            
            Context: {{ previous_outputs.past_context_integration }}
            
            {% if previous_outputs.past_loops %}
            Previous Logical Insights (BUILD UPON THESE):
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round_number }}: {{ loop.emerging_consensus | truncate(200) }}
            {% endfor %}
            
            Remaining Logical Gaps: {{ previous_outputs.past_loops[-1].remaining_tensions }}
            
            REQUIREMENT: Advance logical framework beyond previous rounds.
            Provide NEW logical arguments and evidence not previously considered.
            {% endif %}
            
            Logical Analysis:
            1. Evidence-based reasoning with clear premises
            2. Structured argumentation with logical flow
            3. Address counterarguments and limitations
            4. Build upon previous insights while adding new perspectives
            
            Focus: Rational, evidence-based analysis with logical coherence
        
        - id: empathetic_reasoner
          type: openai-answer
          prompt: |
            EMPATHETIC REASONING - Round {{ loop_number }}
            Topic: {{ input }}
            
            Context: {{ previous_outputs.past_context_integration }}
            
            {% if previous_outputs.past_loops %}
            Previous Empathetic Considerations:
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round_number }}: Human-centered insights developed
            {% endfor %}
            
            Human Impact Gaps: {{ previous_outputs.past_loops[-1].remaining_tensions }}
            
            REQUIREMENT: Deepen empathetic understanding beyond previous rounds.
            Focus on NEW human-centered perspectives not yet explored.
            {% endif %}
            
            Empathetic Analysis:
            1. Human impact and emotional considerations
            2. Stakeholder perspectives and needs
            3. Ethical implications and moral dimensions
            4. Inclusive and compassionate viewpoints
            
            Focus: Human-centered analysis with emotional intelligence and inclusivity
        
        - id: skeptical_reasoner
          type: openai-answer
          prompt: |
            SKEPTICAL ANALYSIS - Round {{ loop_number }}
            Topic: {{ input }}
            
            Context: {{ previous_outputs.past_context_integration }}
            
            {% if previous_outputs.past_loops %}
            Previous Critical Points:
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round_number }} blind spots: {{ loop.cognitive_blind_spots }}
            {% endfor %}
            
            Unresolved Critical Issues: {{ previous_outputs.past_loops[-1].remaining_tensions }}
            
            REQUIREMENT: Identify NEW critical issues and blind spots.
            Challenge assumptions not yet questioned in previous rounds.
            {% endif %}
            
            Critical Analysis:
            1. Challenge underlying assumptions and premises
            2. Identify potential risks, limitations, and unintended consequences
            3. Question methodologies and evidence quality
            4. Probe for weaknesses, gaps, and logical fallacies
            
            Focus: Rigorous critical evaluation with healthy skepticism
        
        - id: creative_reasoner
          type: openai-answer
          prompt: |
            CREATIVE THINKING - Round {{ loop_number }}
            Topic: {{ input }}
            
            Context: {{ previous_outputs.past_context_integration }}
            
            {% if previous_outputs.past_loops %}
            Previous Creative Elements:
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round_number }}: Innovation areas explored
            {% endfor %}
            
            Areas Needing Innovation: {{ previous_outputs.past_loops[-1].remaining_tensions }}
            
            REQUIREMENT: Generate NOVEL creative approaches not attempted before.
            Think beyond conventional frameworks used in previous rounds.
            {% endif %}
            
            Creative Analysis:
            1. Out-of-the-box thinking and unconventional approaches
            2. Synthesis of seemingly unrelated concepts
            3. Innovative solutions and fresh perspectives
            4. Imaginative scenarios and possibilities
            
            Focus: Creative innovation and imaginative problem-solving
        
        # Synthesize all perspectives
        - id: join_agent_views
          type: join
          group: fork_perspectives
          prompt: |
            MULTI-PERSPECTIVE SYNTHESIS - Round {{ loop_number }}
            
            Perspectives to integrate:
            
            LOGICAL PERSPECTIVE:
            {{ previous_outputs.logical_reasoner }}
            
            EMPATHETIC PERSPECTIVE:
            {{ previous_outputs.empathetic_reasoner }}
            
            SKEPTICAL PERSPECTIVE:
            {{ previous_outputs.skeptical_reasoner }}
            
            CREATIVE PERSPECTIVE:
            {{ previous_outputs.creative_reasoner }}
            
            {% if previous_outputs.past_loops %}
            Synthesis Evolution ({{ previous_outputs.past_loops | length }} previous rounds):
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round_number }}: {{ loop.emerging_consensus | truncate(150) }}
            {% endfor %}
            
            Current synthesis must show CLEAR ADVANCEMENT from previous attempts.
            {% endif %}
            
            Integrated Analysis:
            Synthesize all perspectives into comprehensive understanding
            that honors each viewpoint while building coherent framework.
        
        # Agreement Finder implementation (addresses agreement score issues)
        - id: agreement_finder
          type: openai-answer
          prompt: |
            CONSENSUS EVALUATION - Round {{ loop_number }}
            Topic: {{ input }}
            
            Evaluate agreement among these agent perspectives:
            
            1. LOGICAL: {{ previous_outputs.logical_reasoner | truncate(300) }}
            
            2. EMPATHETIC: {{ previous_outputs.empathetic_reasoner | truncate(300) }}
            
            3. SKEPTICAL: {{ previous_outputs.skeptical_reasoner | truncate(300) }}
            
            4. CREATIVE: {{ previous_outputs.creative_reasoner | truncate(300) }}
            
            {% if previous_outputs.past_loops %}
            Consensus Evolution Across {{ previous_outputs.past_loops | length }} Previous Rounds:
            {% for loop in previous_outputs.past_loops %}
            Round {{ loop.round_number }}: Score {{ loop.consensus_score }} - {{ loop.emerging_consensus | truncate(100) }}
            {% endfor %}
            
            REQUIREMENT: Current round must demonstrate measurable progress.
            Score should reflect genuine advancement in consensus building.
            {% endif %}
            
            Agreement Analysis Process:
            1. Identify core themes present across all perspectives
            2. Calculate thematic overlap percentage (0-100%)
            3. Assess depth of agreement vs surface-level similarity
            4. Evaluate resolution of previous tensions
            5. Determine overall consensus strength
            
            Consensus Scoring Criteria:
            - 0.95-1.00: Full consensus - Complete alignment, ready for action
            - 0.85-0.94: Strong consensus - Minor refinements needed
            - 0.75-0.84: Good consensus - Some significant agreements reached  
            - 0.65-0.74: Moderate consensus - Mixed agreement, needs work
            - 0.50-0.64: Weak agreement - Major disagreements remain
            - 0.00-0.49: Low agreement - Fundamental disagreements persist
            
            Detailed Consensus Analysis:
            
            THEMATIC OVERLAP: [Percentage 0-100%]
            
            AREAS OF STRONG AGREEMENT:
            - [List specific points where all/most perspectives align]
            
            AREAS OF DISAGREEMENT:  
            - [List remaining tensions and divergent views]
            
            RESOLUTION OF PREVIOUS TENSIONS:
            {% if previous_outputs.past_loops %}
            - Previous Round Tensions: {{ previous_outputs.past_loops[-1].remaining_tensions }}
            - Resolution Status: [How well were these addressed?]
            {% endif %}
            
            CONSENSUS_SCORE: [0.XX - Based on analysis above]
            CONSENSUS_STATUS: [Full/Strong/Good/Moderate/Weak/Low] consensus
            EMERGING_CONSENSUS: [Clear statement of agreed-upon elements]
            REMAINING_TENSIONS: [Specific unresolved disagreements]
            NEXT_ROUND_FOCUS: [What should next iteration address?]
        
        # Store round results for future reference
        - id: memory_persistence
          type: memory-writer
          namespace: cognitive_deliberation
          params:
            vector: true
            memory_type: long_term                # Ensure retention
            
            # Rich metadata for searchability
            metadata:
              round_number: "{{ loop_number }}"
              consensus_score: "{{ previous_outputs.agreement_finder.consensus_score | default('unknown') }}"
              participant_count: 4
              topic_hash: "{{ input | hash }}"
              has_consensus: "{{ (previous_outputs.agreement_finder.consensus_score | default(0) | float) >= 0.85 }}"
              template_resolved: "{{ not has_unresolved_vars }}"
              processing_duration: "{{ processing_duration | default(0) }}"
              timestamp: "{{ now() }}"
              
            # Importance scoring for retention
            importance_score: "{{ (previous_outputs.agreement_finder.consensus_score | default(0.5) | float) * 0.8 + 0.2 }}"
            
          prompt: |
            COGNITIVE DELIBERATION ROUND {{ loop_number }} RESULTS
            
            Topic: {{ input }}
            Consensus Score: {{ previous_outputs.agreement_finder.consensus_score | default('not calculated') }}
            
            PARTICIPANT PERSPECTIVES:
            
            Logical Analysis:
            {{ previous_outputs.logical_reasoner | truncate(500) }}
            
            Empathetic Analysis:  
            {{ previous_outputs.empathetic_reasoner | truncate(500) }}
            
            Skeptical Analysis:
            {{ previous_outputs.skeptical_reasoner | truncate(500) }}
            
            Creative Analysis:
            {{ previous_outputs.creative_reasoner | truncate(500) }}
            
            SYNTHESIS RESULT:
            {{ previous_outputs.join_agent_views | truncate(800) }}
            
            CONSENSUS EVALUATION:
            {{ previous_outputs.agreement_finder }}
            
            ROUND METADATA:
            - Round: {{ loop_number }}
            - Timestamp: {{ now() }}
            - Template Variables Resolved: {{ 'Yes' if not has_unresolved_vars else 'No' }}
            - Processing Duration: {{ processing_duration | default('unknown') }}
            
            Status: Deliberation round {{ loop_number }} completed

  # 3. Final consensus synthesis
  - id: consensus_synthesis
    type: openai-answer
    prompt: |
      FINAL CONSENSUS SYNTHESIS
      
      Original Question: {{ input }}
      
      External Context Retrieved: {{ previous_outputs.context_memory_search.num_results | default(0) }} relevant memories
      
      Deliberation Process Summary:
      - Rounds Completed: {{ previous_outputs.cognitive_debate_loop.loops_completed }}
      - Final Consensus Score: {{ previous_outputs.cognitive_debate_loop.final_score }}
      - Threshold Achievement: {{ 'Yes' if previous_outputs.cognitive_debate_loop.threshold_met else 'No' }}
      
      {% if previous_outputs.cognitive_debate_loop.past_loops %}
      Evolution of Consensus:
      {% for loop in previous_outputs.cognitive_debate_loop.past_loops %}
      
      Round {{ loop.round_number }} (Score: {{ loop.consensus_score }}):
      - Emerging Consensus: {{ loop.emerging_consensus }}
      - Remaining Tensions: {{ loop.remaining_tensions }}  
      - Blind Spots: {{ loop.cognitive_blind_spots }}
      - Template Status: {{ loop.template_resolution_status }}
      {% endfor %}
      {% endif %}
      
      Final Deliberation Result:
      {{ previous_outputs.cognitive_debate_loop.result }}
      
      COMPREHENSIVE SYNTHESIS REQUIREMENTS:
      
      1. **Consensus Journey**: Trace the evolution of thinking across all rounds
      
      2. **Final Consensus Statement**: Clear, actionable consensus that emerged
      
      3. **Perspective Integration**: How logical, empathetic, skeptical, and creative views were synthesized
      
      4. **Tension Resolution**: Address how initial disagreements were resolved or managed
      
      5. **Actionable Recommendations**: Concrete next steps based on consensus
      
      6. **Future Considerations**: Remaining areas for future deliberation
      
      7. **Process Insights**: What the cognitive society learned about itself
      
      Create a comprehensive consensus that honors all perspectives while providing clear direction forward.

  # 4. Store insights for organizational learning
  - id: insight_storage
    type: memory-writer
    namespace: cognitive_insights
    params:
      vector: true
      memory_type: long_term
      
      metadata:
        consensus_achieved: "{{ previous_outputs.cognitive_debate_loop.threshold_met }}"
        final_score: "{{ previous_outputs.cognitive_debate_loop.final_score }}"
        rounds_required: "{{ previous_outputs.cognitive_debate_loop.loops_completed }}"
        topic_category: "{{ input | first_word }}"  # Categorize by first word of topic
        participant_perspectives: 4
        has_external_context: "{{ (previous_outputs.context_memory_search.num_results | default(0) | int) > 0 }}"
        synthesis_quality: "high"
        timestamp: "{{ now() }}"
        
    prompt: |
      COGNITIVE SOCIETY INSIGHTS - ORGANIZATIONAL LEARNING
      
      Session Topic: {{ input }}
      
      PROCESS METRICS:
      - Deliberation Rounds: {{ previous_outputs.cognitive_debate_loop.loops_completed }}
      - Final Consensus Score: {{ previous_outputs.cognitive_debate_loop.final_score }}
      - Threshold Met: {{ previous_outputs.cognitive_debate_loop.threshold_met }}
      - External Context Used: {{ (previous_outputs.context_memory_search.num_results | default(0) | int) > 0 }}
      
      CONSENSUS SYNTHESIS:
      {{ previous_outputs.consensus_synthesis }}
      
      META-LEARNING INSIGHTS:
      
      1. **Deliberation Effectiveness**: How well did the multi-round process work?
      
      2. **Perspective Integration**: Which perspectives were most valuable?
      
      3. **Memory Utilization**: How did past context influence the discussion?
      
      4. **Template Resolution**: Were all variables properly resolved?
      
      5. **Agreement Dynamics**: What patterns emerged in consensus building?
      
      6. **Process Improvements**: What could be enhanced for future deliberations?
      
      This represents completed cognitive society deliberation with comprehensive consensus building.
```

### Running and Monitoring the Enhanced Workflow

**Execution Commands:**
```bash
# 1. Ensure proper environment setup
export ORKA_MEMORY_BACKEND=redisstack
export REDIS_URL=redis://localhost:6380/0
export ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2
export ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168

# 2. Start RedisStack
docker run -d -p 6380:6380 --name orka-redis redis/redis-stack:latest

# 3. Run the enhanced workflow
orka run cognitive-society-collaborative-enhanced-local.yml \
  "How should AI systems balance automation efficiency with preserving meaningful human work?"

# 4. Monitor execution in near real-time (deployment-dependent) (separate terminal)
orka memory watch --interval 5

# 5. Check memory statistics after completion
orka memory stats
```

**Expected Output Patterns:**
```
=== Round 1 ===
CONSENSUS_SCORE: 0.67
CONSENSUS_STATUS: Moderate consensus
EMERGING_CONSENSUS: Basic agreement on need for balance

=== Round 2 ===  
CONSENSUS_SCORE: 0.78
CONSENSUS_STATUS: Good consensus
EMERGING_CONSENSUS: Refined framework for human-AI collaboration

=== Round 3 ===
CONSENSUS_SCORE: 0.91
CONSENSUS_STATUS: Strong consensus
EMERGING_CONSENSUS: Comprehensive approach to meaningful work preservation

Final Synthesis: [Detailed consensus with actionable recommendations]
```

## Memory-Driven Learning System

This example shows how to build a system that learns from interactions and improves over time using OrKa's memory capabilities.

### Learning System Configuration

**File: `memory-driven-learning.yml`**

```yaml
orchestrator:
  id: adaptive-learning-system
  strategy: sequential
  
  memory_config:
    backend: redisstack
    decay:
      enabled: true
      default_short_term_hours: 8        # Learning sessions
      default_long_term_hours: 720       # 30 days for knowledge retention
      importance_rules:
        successful_pattern: 3.0
        user_correction: 4.0             # User feedback is critical
        error_pattern: 1.5               # Keep errors for learning
        high_confidence: 2.0
  
  agents:
    - interaction_history
    - error_pattern_analysis
    - adaptive_processor
    - learning_consolidation
    - performance_feedback

agents:
  # Retrieve relevant interaction history
  - id: interaction_history
    type: memory-reader
    namespace: learning_interactions
    params:
      limit: 15
      enable_context_search: true
      similarity_threshold: 0.6
      temporal_weight: 0.4              # Recent interactions important
      metadata_filters:
        interaction_type: "{{ input_type | default('general') }}"
        success_level: "> 0.6"          # Focus on successful patterns
    prompt: |
      Find relevant learning history for: {{ input }}
      
      Look for:
      - Similar successful interactions
      - Common error patterns to avoid  
      - User feedback and corrections
      - Progressive improvement patterns

  # Analyze error patterns for learning
  - id: error_pattern_analysis
    type: memory-reader
    namespace: error_patterns
    params:
      limit: 10
      similarity_threshold: 0.7
      memory_type_filter: "short_term"   # Recent errors most relevant
      metadata_filters:
        resolved: "false"                # Focus on unresolved issues
    prompt: |
      Analyze recent error patterns related to: {{ input }}
      
      Identify:
      - Recurring mistake patterns
      - Failed approaches to avoid
      - Common user correction themes
      - System limitation patterns

  # Main adaptive processing with learning
  - id: adaptive_processor
    type: openai-answer
    prompt: |
      ADAPTIVE PROCESSING WITH LEARNING
      Current Request: {{ input }}
      
      LEARNING CONTEXT:
      
      Successful Interaction History ({{ previous_outputs.interaction_history.num_results | default(0) }} entries):
      {{ previous_outputs.interaction_history }}
      
      Error Pattern Analysis ({{ previous_outputs.error_pattern_analysis.num_results | default(0) }} patterns):
      {{ previous_outputs.error_pattern_analysis }}
      
      ADAPTIVE PROCESSING INSTRUCTIONS:
      
      1. **Learn from Success**: Apply successful patterns from similar past interactions
      
      2. **Avoid Known Errors**: Explicitly avoid error patterns identified in analysis
      
      3. **Incorporate Feedback**: Build on user corrections and feedback from history
      
      4. **Progressive Improvement**: Show measurable advancement over past attempts
      
      5. **Confidence Assessment**: Rate confidence based on historical success patterns
      
      PROCESSING APPROACH:
      {% if previous_outputs.interaction_history.num_results > 0 %}
      Based on {{ previous_outputs.interaction_history.num_results }} similar successful interactions,
      apply proven approaches while avoiding {{ previous_outputs.error_pattern_analysis.num_results | default(0) }} known error patterns.
      {% else %}
      No direct historical guidance available. Proceed with standard approach while monitoring for new patterns.
      {% endif %}
      
      Provide comprehensive response with clear confidence assessment.
      
      CONFIDENCE_LEVEL: [0.0-1.0 based on historical success patterns]
      LEARNING_APPLIED: [How historical patterns influenced this response]
      RISK_FACTORS: [Potential issues based on error pattern analysis]

  # Consolidate learning from this interaction
  - id: learning_consolidation
    type: openai-answer
    prompt: |
      LEARNING CONSOLIDATION
      
      Current Interaction:
      Input: {{ input }}
      Processing: {{ previous_outputs.adaptive_processor }}
      
      Historical Context:
      - Success Patterns Applied: {{ previous_outputs.interaction_history.num_results | default(0) }}
      - Error Patterns Avoided: {{ previous_outputs.error_pattern_analysis.num_results | default(0) }}
      
      LEARNING ANALYSIS:
      
      1. **What Worked Well**: Identify successful elements in this interaction
      
      2. **Applied Learning**: How historical patterns were successfully used
      
      3. **New Insights**: What new patterns or approaches emerged
      
      4. **Potential Improvements**: Areas for future enhancement
      
      5. **Pattern Updates**: How this interaction refines existing patterns
      
      6. **Confidence Validation**: How well confidence prediction matched outcome
      
      LEARNING_SUMMARY: [Key insights from this interaction]
      SUCCESS_PATTERNS: [Patterns that worked well]
      IMPROVEMENT_AREAS: [Areas needing attention]
      CONFIDENCE_ACCURACY: [How well confidence was calibrated]

  # Store results with learning metadata
  - id: performance_feedback
    type: memory-writer
    namespace: learning_interactions
    params:
      vector: true
      memory_type: auto                  # Let system classify based on success
      
      metadata:
        interaction_type: "{{ input_type | default('general') }}"
        confidence_level: "{{ previous_outputs.adaptive_processor.confidence_level | default(0.5) }}"
        historical_patterns_applied: "{{ previous_outputs.interaction_history.num_results | default(0) }}"
        error_patterns_avoided: "{{ previous_outputs.error_pattern_analysis.num_results | default(0) }}"
        success_level: "{{ previous_outputs.learning_consolidation.success_rating | default(0.7) }}"
        learning_value: "high"
        timestamp: "{{ now() }}"
        
    prompt: |
      LEARNING INTERACTION RECORD
      
      Input: {{ input }}
      
      PROCESSING RESULTS:
      {{ previous_outputs.adaptive_processor }}
      
      LEARNING CONSOLIDATION:
      {{ previous_outputs.learning_consolidation }}
      
      METADATA:
      - Confidence Level: {{ previous_outputs.adaptive_processor.confidence_level | default('unknown') }}
      - Success Patterns Applied: {{ previous_outputs.interaction_history.num_results | default(0) }}
      - Error Patterns Avoided: {{ previous_outputs.error_pattern_analysis.num_results | default(0) }}
      - Learning Value: High (comprehensive learning record)
      - Timestamp: {{ now() }}
      
      This represents a complete learning interaction with historical context integration.
```

## Self-Improving Analysis Pipeline

Example showing iterative improvement with cognitive extraction and learning.

**File: `self-improving-analysis.yml`**

```yaml
orchestrator:
  id: self-improving-analysis-pipeline
  strategy: sequential
  agents: [analysis_loop, improvement_tracker]

agents:
  - id: analysis_loop
    type: loop
    max_loops: 6
    score_threshold: 0.92
    min_loops: 2
    
    # Advanced score extraction
    score_extraction_config:
      strategies:
        - type: "regex_pattern"
          pattern: "ANALYSIS_QUALITY:\\s*([0-9.]+)"
          priority: 1
        - type: "json_key" 
          key: "quality_score"
          priority: 2
    
    # Comprehensive cognitive extraction
    cognitive_extraction:
      enabled: true
      extract_patterns:
        insights:
          - "(?:key insight|important finding|significant discovery):\\s*(.+?)(?:\\n|\\.|$)"
          - "(?:analysis reveals|demonstrates|shows that)\\s+(.+?)(?:\\n|\\.|$)"
        improvements:
          - "(?:could be strengthened|needs enhancement|requires improvement)\\s+(.+?)(?:\\n|\\.|$)"
          - "(?:lacks|missing|insufficient)\\s+(.+?)(?:\\n|\\.|$)"
        mistakes:
          - "(?:overlooked|missed|failed to consider)\\s+(.+?)(?:\\n|\\.|$)"
          - "(?:error|mistake|incorrect assumption)\\s+(?:in|about|regarding)\\s+(.+?)(?:\\n|\\.|$)"
    
    past_loops_metadata:
      iteration: "{{ loop_number }}"
      quality_score: "{{ score }}"
      timestamp: "{{ now() }}"
      key_insights: "{{ insights }}"
      improvement_areas: "{{ improvements }}"
      mistakes_identified: "{{ mistakes }}"
      analysis_depth: "{{ previous_outputs.analyzer.word_count | default(0) }}"
      
    internal_workflow:
      orchestrator:
        id: improvement-cycle
        strategy: sequential
        agents: [analyzer, quality_evaluator, insight_extractor]
      
      agents:
        - id: analyzer
          type: openai-answer
          prompt: |
            ITERATIVE ANALYSIS - Iteration {{ loop_number }}
            Topic: {{ input }}
            
            {% if previous_outputs.past_loops %}
            LEARNING FROM {{ previous_outputs.past_loops | length }} PREVIOUS ITERATIONS:
            
            {% for loop in previous_outputs.past_loops %}
            === Iteration {{ loop.iteration }} (Quality: {{ loop.quality_score }}) ===
            Key Insights: {{ loop.key_insights }}
            Areas Needing Improvement: {{ loop.improvement_areas }}
            Mistakes to Avoid: {{ loop.mistakes_identified }}
            Analysis Depth: {{ loop.analysis_depth }} words
            
            {% endfor %}
            
            PROGRESSION REQUIREMENTS:
            1. Build upon all previous insights
            2. Address every improvement area identified
            3. Avoid all previously identified mistakes
            4. Provide NEW insights not yet discovered
            5. Increase depth and sophistication beyond previous attempts
            
            Target Improvement: Exceed previous best quality of {{ previous_outputs.past_loops | map(attribute='quality_score') | max | default(0) }}
            {% else %}
            This is the baseline analysis. Establish comprehensive foundation for iterative improvement.
            {% endif %}
            
            COMPREHENSIVE ANALYSIS REQUIREMENTS:
            
            1. **Depth**: Thorough exploration of all relevant dimensions
            2. **Breadth**: Consider multiple perspectives and stakeholder views  
            3. **Evidence**: Support claims with specific examples and data
            4. **Structure**: Logical organization with clear argumentation flow
            5. **Innovation**: Original insights and creative connections
            6. **Practicality**: Actionable implications and recommendations
            
            Provide the most comprehensive analysis possible, building on all previous learning.
        
        - id: quality_evaluator
          type: openai-answer
          prompt: |
            QUALITY EVALUATION - Iteration {{ loop_number }}
            
            Evaluate this analysis comprehensively:
            {{ previous_outputs.analyzer }}
            
            {% if previous_outputs.past_loops %}
            COMPARATIVE QUALITY ASSESSMENT:
            
            Previous Quality Progression:
            {% for loop in previous_outputs.past_loops %}
            Iteration {{ loop.iteration }}: {{ loop.quality_score }}
            {% endfor %}
            
            Highest Previous Quality: {{ previous_outputs.past_loops | map(attribute='quality_score') | max }}
            
            REQUIREMENT: Current analysis must demonstrate clear improvement.
            Score should reflect genuine advancement in quality, not just length.
            {% endif %}
            
            QUALITY EVALUATION CRITERIA:
            
            1. **Comprehensiveness** (25 points):
               - Covers all relevant aspects thoroughly
               - Addresses multiple dimensions and perspectives
               - Includes context and background appropriately
            
            2. **Insight Quality** (25 points):
               - Provides original, non-obvious insights
               - Makes meaningful connections between concepts
               - Demonstrates deep understanding of subject
            
            3. **Evidence & Support** (20 points):
               - Uses specific examples and evidence
               - Cites relevant sources and data where appropriate
               - Supports claims with logical reasoning
            
            4. **Structure & Clarity** (15 points):
               - Well-organized with logical flow
               - Clear, precise language and communication
               - Easy to follow and understand
            
            5. **Practical Value** (15 points):
               - Provides actionable insights or recommendations
               - Addresses real-world applications and implications
               - Offers practical solutions or next steps
            
            DETAILED EVALUATION:
            
            Comprehensiveness: [X/25] - [Detailed assessment]
            Insight Quality: [X/25] - [Detailed assessment]
            Evidence & Support: [X/20] - [Detailed assessment]
            Structure & Clarity: [X/15] - [Detailed assessment]
            Practical Value: [X/15] - [Detailed assessment]
            
            TOTAL SCORE: [X/100]
            NORMALIZED SCORE: [0.XX] (divide by 100)
            
            {% if previous_outputs.past_loops %}
            IMPROVEMENT ASSESSMENT:
            - Previous Best: {{ previous_outputs.past_loops | map(attribute='quality_score') | max }}
            - Current Score: [X.XX]
            - Improvement: [Yes/No] by [X.XX] points
            
            If improvement is insufficient, identify specific areas needing enhancement.
            {% endif %}
            
            ANALYSIS_QUALITY: [0.XX] (final normalized score)
            
            QUALITY_JUSTIFICATION: [Detailed explanation of score]
        
        - id: insight_extractor
          type: openai-answer
          prompt: |
            COGNITIVE INSIGHT EXTRACTION - Iteration {{ loop_number }}
            
            Extract learning insights from this analysis iteration:
            
            Analysis: {{ previous_outputs.analyzer }}
            Quality Assessment: {{ previous_outputs.quality_evaluator }}
            
            {% if previous_outputs.past_loops %}
            Previous Learning Journey:
            {% for loop in previous_outputs.past_loops %}
            Iteration {{ loop.iteration }}:
            - Insights: {{ loop.key_insights }}
            - Improvements Needed: {{ loop.improvement_areas }}
            - Mistakes: {{ loop.mistakes_identified }}
            {% endfor %}
            {% endif %}
            
            COMPREHENSIVE INSIGHT EXTRACTION:
            
            1. **Key Insights Discovered** (What valuable understanding emerged?):
            - [List 3-5 most important insights from current analysis]
            
            2. **Areas Still Needing Improvement** (What could be enhanced?):
            - [List 2-4 specific areas requiring further development]
            
            3. **Mistakes or Limitations Identified** (What was overlooked or incorrect?):
            - [List any errors, oversights, or limitations in current analysis]
            
            4. **Learning Progression** (How did this build on previous work?):
            {% if previous_outputs.past_loops %}
            - [Describe how current iteration advanced beyond previous attempts]
            {% else %}
            - [Describe baseline established for future iterations]
            {% endif %}
            
            5. **Next Iteration Focus** (What should next round emphasize?):
            - [Recommendations for improving next iteration]
            
            EXTRACTED_INSIGHTS: [Key learning discoveries]
            IMPROVEMENT_TARGETS: [Specific areas needing attention]
            IDENTIFIED_LIMITATIONS: [Mistakes or oversights to avoid]

  - id: improvement_tracker
    type: memory-writer
    namespace: self_improvement_analytics  
    params:
      vector: true
      memory_type: long_term
      
      metadata:
        iterations_completed: "{{ previous_outputs.analysis_loop.loops_completed }}"
        final_quality_score: "{{ previous_outputs.analysis_loop.final_score }}"
        threshold_achieved: "{{ previous_outputs.analysis_loop.threshold_met }}"
        improvement_trajectory: "{{ 'positive' if previous_outputs.analysis_loop.past_loops | length > 1 and previous_outputs.analysis_loop.past_loops[-1].quality_score > previous_outputs.analysis_loop.past_loops[0].quality_score else 'flat' }}"
        topic_category: "{{ input | first_word }}"
        learning_value: "high"
        
    prompt: |
      SELF-IMPROVEMENT ANALYTICS RECORD
      
      Topic Analyzed: {{ input }}
      
      IMPROVEMENT TRAJECTORY:
      - Iterations Completed: {{ previous_outputs.analysis_loop.loops_completed }}
      - Final Quality Score: {{ previous_outputs.analysis_loop.final_score }}
      - Quality Threshold Met: {{ previous_outputs.analysis_loop.threshold_met }}
      
      {% if previous_outputs.analysis_loop.past_loops %}
      LEARNING PROGRESSION:
      {% for loop in previous_outputs.analysis_loop.past_loops %}
      
      Iteration {{ loop.iteration }} (Quality: {{ loop.quality_score }}):
      Key Insights: {{ loop.key_insights }}
      Areas Improved: {{ loop.improvement_areas }}
      Limitations Addressed: {{ loop.mistakes_identified }}
      {% endfor %}
      {% endif %}
      
      FINAL ANALYSIS RESULT:
      {{ previous_outputs.analysis_loop.result }}
      
      META-LEARNING INSIGHTS:
      1. How effective was the iterative improvement process?
      2. Which types of improvements were most valuable?
      3. What patterns emerged in the learning progression?
      4. How can future analyses benefit from this learning?
      
      This represents a complete self-improving analysis with comprehensive learning tracking.
```

## Production Deployment Examples (examples; requires hardening and validation)

### Docker Compose for Deployment (example)

**File: `production-docker-compose.yml`**

```yaml
version: '3.8'

services:
  # RedisStack for high-performance memory
  redis-stack:
    image: redis/redis-stack:latest
    ports:
      - "6380:6380"
      - "8001:8001"  # RedisInsight UI
    volumes:
      - redis_data:/data
      - ./redis.conf:/usr/local/etc/redis/redis.conf
    environment:
      - REDIS_ARGS=--save 60 1000 --maxmemory 4gb --maxmemory-policy allkeys-lru
    command: redis-stack-server /usr/local/etc/redis/redis.conf
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # OrKa Application
  orka-app:
    build: .
    ports:
      - "8000:8000"
    environment:
      # Memory Configuration
      - ORKA_MEMORY_BACKEND=redisstack
      - REDIS_URL=redis://redis-stack:6380/0
      - ORKA_MEMORY_DECAY_ENABLED=true
      - ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=8
      - ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168
      - ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES=60
      
      # Performance Tuning
      - ORKA_MAX_CONCURRENT_REQUESTS=50
      - ORKA_TIMEOUT_SECONDS=300
      - REDIS_POOL_MAX_CONNECTIONS=20
      
      # Monitoring
      - ORKA_METRICS_ENABLED=true
      - ORKA_LOG_LEVEL=INFO
      
      # API Keys (use secrets in production)
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      
    volumes:
      - ./workflows:/app/workflows
      - ./logs:/app/logs
    depends_on:
      redis-stack:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Monitoring with Prometheus
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
    restart: unless-stopped

  # Grafana for Visualization
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  redis_data:
  prometheus_data:
  grafana_data:
```

### Deployment Configuration Files (examples — validate before use)

**File: `redis.conf`**
```conf
# Redis Configuration for OrKa (deployment example)
bind 0.0.0.0
port 6380

# Memory Management
maxmemory 4gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# RedisStack Module Configuration
loadmodule /opt/redis-stack/lib/redisearch.so
loadmodule /opt/redis-stack/lib/rejson.so

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Security
requirepass ${REDIS_PASSWORD}
```

**File: `monitoring/prometheus.yml`**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'orka-app'
    static_configs:
      - targets: ['orka-app:8000']
    metrics_path: /metrics
    scrape_interval: 30s
    
  - job_name: 'redis-stack'
    static_configs:
      - targets: ['redis-stack:6380']
    metrics_path: /metrics
```

### Environment-Specific Configuration

**Development Environment (`.env.development`)**:
```bash
# Development Environment Configuration
ORKA_MEMORY_BACKEND=redisstack
REDIS_URL=redis://localhost:6380/0

# Development TTL Settings (faster for testing)
ORKA_MEMORY_DECAY_ENABLED=true
ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=2
ORKA_MEMORY_DECAY_LONG_TERM_HOURS=24
ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES=15

# Debug Settings
ORKA_LOG_LEVEL=DEBUG
ORKA_MEMORY_DEBUG=true
ORKA_TRACE_ENABLED=true

# Development Performance
ORKA_MAX_CONCURRENT_REQUESTS=10
ORKA_TIMEOUT_SECONDS=120
```

**Deployment Environment (`.env.production`) (example)**:
```bash
# Production Environment Configuration
ORKA_MEMORY_BACKEND=redisstack
REDIS_URL=redis://:${REDIS_PASSWORD}@redis-cluster:6380/0

# Production TTL Settings (matches README)
ORKA_MEMORY_DECAY_ENABLED=true
ORKA_MEMORY_DECAY_SHORT_TERM_HOURS=8
ORKA_MEMORY_DECAY_LONG_TERM_HOURS=168
ORKA_MEMORY_DECAY_CHECK_INTERVAL_MINUTES=60

# Production Logging
ORKA_LOG_LEVEL=INFO
ORKA_MEMORY_DEBUG=false
ORKA_TRACE_ENABLED=false

# Production Performance
ORKA_MAX_CONCURRENT_REQUESTS=100
ORKA_TIMEOUT_SECONDS=300
REDIS_POOL_MAX_CONNECTIONS=50

# Monitoring
ORKA_METRICS_ENABLED=true
```

### Health Check and Monitoring

**File: `scripts/health_check.py`**
    print(f"OrKa Deployment Health Check - {datetime.now()}")
        if not pong:
            return False, "Redis not responding to ping"
        
        # RedisStack modules
        modules = client.execute_command("MODULE", "LIST")
        search_module = any("search" in str(module).lower() for module in modules)
        
        if not search_module:
            return False, "RedisStack search module not loaded"
            
        # Memory index check
        try:
            client.execute_command("FT.INFO", "orka_enhanced_memory")
            index_exists = True
        except redis.exceptions.ResponseError:
            index_exists = False
            
        return True, f"Redis OK, Search module loaded, Index exists: {index_exists}"
        
    except Exception as e:
        return False, f"Redis check failed: {e}"

async def check_orka_health():
    """Check OrKa application health"""
    try:
        async with httpx.AsyncClient() as client:
            # Health endpoint
            response = await client.get("http://localhost:8000/health", timeout=10)
            
            if response.status_code != 200:
                return False, f"Health endpoint returned {response.status_code}"
                
            health_data = response.json()
            
            # Memory system health
            memory_response = await client.get("http://localhost:8000/health/memory", timeout=10)
            
            if memory_response.status_code == 200:
                memory_data = memory_response.json()
                memory_ok = memory_data.get("status") == "healthy"
            else:
                memory_ok = False
                
            return memory_ok, f"OrKa health: {health_data}, Memory: {memory_ok}"
            
    except Exception as e:
        return False, f"OrKa check failed: {e}"

async def check_memory_statistics():
    """Check memory system statistics"""
    try:
        # This would use OrKa CLI or API
        # Placeholder for memory stats check
        return True, "Memory stats check not implemented"
    except Exception as e:
        return False, f"Memory stats failed: {e}"

async def main():
    """Run complete health check"""
    print(f"OrKa Deployment Health Check - {datetime.now()}")
    print("=" * 50)
    
    checks = [
        ("Redis/RedisStack", check_redis_health),
        ("OrKa Application", check_orka_health),
        ("Memory Statistics", check_memory_statistics),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"Checking {check_name}...")
        
        try:
            passed, message = await check_func()
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {message}")
            
            if not passed:
                all_passed = False
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            all_passed = False
    
    print("=" * 50)
    final_status = "✅ ALL SYSTEMS HEALTHY" if all_passed else "❌ SOME ISSUES DETECTED"
    print(f"Overall Status: {final_status}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

## 🚀 Complete Integration Examples

Instead of inline YAML (which can become outdated), **all integration examples are maintained as working files**:

### Core Integration Patterns

| Pattern | Example File | Description |
|---------|-------------|-------------|
| **Cognitive Society** | [`cognitive_society_minimal_loop.yml`](../examples/cognitive_society_minimal_loop.yml) | Multi-agent deliberation with consensus |
| **Memory Learning** | [`memory_validation_routing_and_write.yml`](../examples/memory_validation_routing_and_write.yml) | Memory-first with intelligent fallback |
| **Iterative Improvement** | [`cognitive_loop_scoring_example.yml`](../examples/cognitive_loop_scoring_example.yml) | Self-improving analysis loops |
| **Parallel Processing** | [`conditional_search_fork_join.yaml`](../examples/conditional_search_fork_join.yaml) | Fork/join with result aggregation |
| **Failover Handling** | [`failover_search_and_validate.yml`](../examples/failover_search_and_validate.yml) | Robust error handling patterns |
| **Memory Routing** | [`memory_read_fork_join_router.yml`](../examples/memory_read_fork_join_router.yml) | Memory-driven workflow routing |
| **Validation Pipeline** | [`validation_structuring_memory_pipeline.yml`](../examples/validation_structuring_memory_pipeline.yml) | Data validation and structuring |

### Advanced Integrations

| Category | Examples | Features |
|----------|----------|-----------|
| **Local LLM** | [`orka_soc/`](../examples/orka_soc/) | Local model deployment |
| **Genius Minds** | [`orka_smartest/`](../examples/orka_smartest/) | Advanced cognitive patterns |
| **Production** | [`multi_perspective_chatbot.yml`](../examples/multi_perspective_chatbot.yml) | Example chatbot configuration; review and harden before deployment |

### Quick Start

```bash
# View all integration examples
ls ../examples/
cat ../examples/README.md

# Copy any integration pattern
cp ../examples/[pattern-name].yml my-integration.yml

# Run and test
orka run my-integration.yml "Your test input"

# Monitor integration
orka memory watch
```

## 🔧 Deployment Examples (requires hardening and validation)

For deployment patterns, monitoring, and debugging (examples):

- **Docker Setup**: See [`../orka/docker/`](../orka/docker/) for container configurations
- **Environment Configuration**: See [README_BACKENDS.md](./README_BACKENDS.md) for backend and production settings
- **Monitoring Setup**: See [observability.md](./observability.md) for monitoring integration
- **Testing Patterns**: See [TESTING.md](./TESTING.md) for comprehensive testing strategies

These integration examples demonstrate how OrKa's components work together to address deployment requirements; they are provided as examples and require testing, configuration, and monitoring in your environment.