# Loop Node

**Type:** `loop`  
**Category:** Control Flow Node  
**Version:** v0.9.4+

## Overview

The Loop Node enables iterative improvement workflows that repeat until a quality threshold is met or maximum iterations reached. Includes cognitive extraction for learning from past attempts.

## Basic Configuration

```yaml
- id: improvement_loop
  type: loop
  max_loops: 5
  score_threshold: 0.85
  score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
  internal_workflow:
    orchestrator:
      id: internal-loop
      strategy: sequential
      agents: [improver, scorer]
    agents:
      - id: improver
        type: openai-answer
        prompt: "Improve: {{ input }}"
      - id: scorer
        type: openai-answer
        prompt: "Rate: SCORE: X.XX"

## Loop Validator Node

The `loop_validator` node is a specialized validator for loop workflows that evaluates the output of an internal agent (e.g., an `improver`) using boolean-based criteria and built-in parsing. Note: unlike many other agent types, **`loop_validator` expects the LLM model parameter under the YAML key `llm_model` instead of `model`**. This distinction ensures consistent configuration with PlanValidator and improves schema clarity.

Example:

```yaml
- id: boolean_evaluator
  type: loop_validator
  # IMPORTANT: use `llm_model`, not `model`
  llm_model: openai/gpt-oss-20b
  model_url: http://localhost:1234
  provider: lm_studio
  scoring_preset: moderate
  evaluation_target: improver
  temperature: 0.1
```
```

## Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `max_loops` | int | Maximum iterations |
| `score_threshold` | float | Target score (0.0-1.0) |
| `score_extraction_pattern` | string | Regex to extract score |
| `internal_workflow` | object | Workflow to repeat |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cognitive_extraction.enabled` | bool | `false` | Extract insights |
| `cognitive_extraction.extract_patterns` | object | - | Patterns for insights/improvements/mistakes |
| `past_loops_metadata` | object | - | Structure for loop history |
| `persist_across_runs` | bool | `false` | Keep history between runs |
| `timeout` | float | `300.0` | Total loop timeout |

## Usage Examples

### Example 1: Basic Quality Loop

```yaml
- id: quality_improver
  type: loop
  max_loops: 5
  score_threshold: 0.85
  score_extraction_pattern: "QUALITY:\\s*([0-9.]+)"
  
  internal_workflow:
    orchestrator:
      id: quality-loop
      strategy: sequential
      agents: [analyzer, scorer]
    
    agents:
      - id: analyzer
        type: openai-answer
        model: gpt-4o
        temperature: 0.5
        prompt: |
          Improve this content: {{ input }}
          
          {% if has_past_loops() %}
          Previous attempts: {{ get_past_loops() | length }}
          {% endif %}
      
      - id: scorer
        type: openai-answer
        model: gpt-4o
        temperature: 0.1
        prompt: |
          Rate quality (0.0-1.0):
          {{ previous_outputs.analyzer }}
          
          Format: QUALITY: X.XX
```

### Example 2: With Cognitive Extraction

```yaml
- id: learning_loop
  type: loop
  max_loops: 5
  score_threshold: 0.90
  score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
  
  # Extract insights from each iteration
  cognitive_extraction:
    enabled: true
    max_length_per_category: 500
    extract_patterns:
      insights:
        - "(?:provides?|shows?|demonstrates?)\\s+(.+?)(?:\\n|$)"
        - "(?:strong|effective|comprehensive)\\s+(.+?)(?:\\n|$)"
      improvements:
        - "(?:lacks?|needs?|requires?)\\s+(.+?)(?:\\n|$)"
        - "(?:could improve|should add)\\s+(.+?)(?:\\n|$)"
      mistakes:
        - "(?:error|wrong|incorrect)\\s+(.+?)(?:\\n|$)"
        - "(?:weakness|gap|flaw)\\s+(.+?)(?:\\n|$)"
  
  # Track metadata for each loop
  past_loops_metadata:
    iteration: "{{ loop_number }}"
    quality_score: "{{ score }}"
    key_insights: "{{ insights }}"
    needed_improvements: "{{ improvements }}"
    mistakes_found: "{{ mistakes }}"
  
  internal_workflow:
    orchestrator:
      id: cognitive-loop
      strategy: sequential
      agents: [analyzer, evaluator, scorer]
    
    agents:
      - id: analyzer
        type: openai-answer
        temperature: 0.4
        prompt: |
          Analyze: {{ get_input() }}
          
          {% if has_past_loops() %}
          Learning from {{ get_past_loops() | length }} previous attempts:
          {% for loop in get_past_loops() %}
          
          **Iteration {{ loop.iteration }}** (Score: {{ loop.quality_score }}):
          ✓ Insights: {{ loop.key_insights }}
          ⚠ Needs: {{ loop.needed_improvements }}
          ✗ Mistakes: {{ loop.mistakes_found }}
          {% endfor %}
          
          Build upon these lessons.
          {% endif %}
          
          Provide comprehensive analysis with clear insights, improvements, and mistake identification.
      
      - id: evaluator
        type: openai-answer
        temperature: 0.2
        prompt: |
          Evaluate this analysis:
          {{ previous_outputs.analyzer }}
          
          Identify:
          - What provides value (insights)
          - What lacks depth (improvements)
          - What is wrong (mistakes)
      
      - id: scorer
        type: openai-answer
        temperature: 0.1
        prompt: |
          Rate quality (0.0-1.0):
          {{ previous_outputs.analyzer }}
          
          Scoring:
          - 0.9-1.0: Exceptional
          - 0.8-0.9: High quality
          - 0.7-0.8: Good
          - <0.7: Needs improvement
          
          Format: SCORE: X.XX
```

### Example 3: Multi-Agent Cognitive Society

```yaml
- id: society_deliberation
  type: loop
  max_loops: 5
  score_threshold: 0.92
  score_extraction_pattern: "CONSENSUS:\\s*([0-9.]+)"
  
  cognitive_extraction:
    enabled: true
    extract_patterns:
      insights:
        - "strategy:\\s*(.+?)(?:\\n|$)"
        - "recommendation:\\s*(.+?)(?:\\n|$)"
      improvements:
        - "convergence:\\s*(.+?)(?:\\n|$)"
        - "alignment:\\s*(.+?)(?:\\n|$)"
  
  past_loops_metadata:
    round: "{{ loop_number }}"
    consensus_score: "{{ score }}"
    strategies: "{{ insights }}"
    convergence: "{{ improvements }}"
  
  internal_workflow:
    orchestrator:
      id: society
      strategy: sequential
      agents: [fork_agents, join_agents, moderator]
    
    agents:
      - id: fork_agents
        type: fork
        targets:
          - [logical_reasoner]
          - [empathetic_reasoner]
          - [skeptical_reasoner]
      
      - id: logical_reasoner
        type: openai-answer
        temperature: 0.3
        prompt: |
          Logical analysis: {{ get_input() }}
          Round: {{ get_loop_number() }}
          {% if has_past_loops() %}
          Previous rounds: {{ get_past_loops() }}
          {% endif %}
      
      - id: empathetic_reasoner
        type: openai-answer
        temperature: 0.4
        prompt: |
          Empathetic analysis: {{ get_input() }}
          Round: {{ get_loop_number() }}
      
      - id: skeptical_reasoner
        type: openai-answer
        temperature: 0.3
        prompt: |
          Critical analysis: {{ get_input() }}
          Round: {{ get_loop_number() }}
      
      - id: join_agents
        type: join
      
      - id: moderator
        type: openai-answer
        temperature: 0.2
        prompt: |
          Evaluate consensus among agents:
          
          Logical: {{ previous_outputs.logical_reasoner }}
          Empathetic: {{ previous_outputs.empathetic_reasoner }}
          Skeptical: {{ previous_outputs.skeptical_reasoner }}
          
          Consensus score (0.0-1.0): CONSENSUS: X.XX
```

### Example 4: Code Quality Loop

```yaml
- id: code_quality_loop
  type: loop
  max_loops: 10
  score_threshold: 0.95
  score_extraction_pattern: "QUALITY:\\s*([0-9.]+)"
  
  internal_workflow:
    orchestrator:
      id: code-improvement
      strategy: sequential
      agents: [code_analyzer, code_improver, quality_checker]
    
    agents:
      - id: code_analyzer
        type: openai-answer
        model: gpt-4o
        temperature: 0.2
        prompt: |
          Analyze this code:
          {{ get_input() }}
          
          Check for:
          - Correctness
          - Performance
          - Security
          - Readability
          - Best practices
          
          Provide specific improvement suggestions.
      
      - id: code_improver
        type: openai-answer
        model: gpt-4o
        temperature: 0.3
        prompt: |
          Improve the code based on analysis:
          {{ previous_outputs.code_analyzer }}
          
          Original code:
          {{ get_input() }}
          
          Provide improved version.
      
      - id: quality_checker
        type: openai-answer
        model: gpt-4
        temperature: 0.1
        prompt: |
          Rate code quality (0.0-1.0):
          {{ previous_outputs.code_improver }}
          
          Criteria:
          - Correctness (30%)
          - Performance (20%)
          - Security (20%)
          - Readability (20%)
          - Best practices (10%)
          
          Format: QUALITY: X.XX
```

## Template Variables in Loops

Special variables available inside loop workflows:

```yaml
{{ loop_number }}                    # Current iteration (1, 2, 3...)
{{ score }}                          # Extracted score from previous iteration
{{ get_loop_number() }}              # Function to get iteration
{{ has_past_loops() }}               # Check if previous iterations exist
{{ get_past_loops() }}               # Get all past loop metadata
{{ get_past_insights() }}            # Get extracted insights
{{ previous_outputs.past_loops }}    # Access past loop data
```

## Output Format

```python
{
    "response": "Final improved result",
    "loops_completed": 4,
    "final_score": 0.89,
    "threshold_met": true,
    "past_loops": [
        {
            "iteration": 1,
            "quality_score": 0.65,
            "key_insights": "...",
            "needed_improvements": "..."
        },
        # ... more iterations
    ]
}
```

## Best Practices

### 1. Appropriate Thresholds

```yaml
# High bar for critical content
max_loops: 10
score_threshold: 0.95

# Balanced for general use
max_loops: 5
score_threshold: 0.85

# Quick iterations
max_loops: 3
score_threshold: 0.75
```

### 2. Clear Score Extraction

```yaml
# ✅ GOOD: Specific pattern
score_extraction_pattern: "QUALITY_SCORE:\\s*([0-9.]+)"
# In prompt: "QUALITY_SCORE: 0.85"

# ✅ ALSO GOOD: Simple pattern
score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
# In prompt: "SCORE: 0.85"

# ❌ BAD: Ambiguous pattern
score_extraction_pattern: "([0-9.]+)"
# Could match any number!
```

### 3. Learning from History

```yaml
prompt: |
  {% if has_past_loops() %}
  Previous attempts ({{ get_past_loops() | length }}):
  {% for loop in get_past_loops() %}
  Iteration {{ loop.iteration }}: Score {{ loop.quality_score }}
  - Insights: {{ loop.key_insights }}
  - Improvements: {{ loop.needed_improvements }}
  {% endfor %}
  
  Learn from these and improve.
  {% endif %}
  
  Current task: {{ input }}
```

### 4. Timeout Management

```yaml
# Individual agent timeouts
agents:
  - id: analyzer
    type: openai-answer
    timeout: 60.0  # Per iteration
    prompt: "..."

# Overall loop timeout
- id: loop
  type: loop
  timeout: 300.0  # 5 minutes total
  max_loops: 5  # Up to 60s per iteration
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Loop never ends | Threshold too high | Lower threshold or increase max_loops |
| Score not extracted | Wrong pattern | Fix `score_extraction_pattern` |
| No improvement | Not learning from history | Use `has_past_loops()` in prompts |
| Timeout errors | Individual agents too slow | Increase agent timeouts |
| Empty past_loops | Cognitive extraction disabled | Enable `cognitive_extraction` |

## Related Documentation

- [Fork and Join Nodes](./fork-and-join.md)
- [OpenAI Answer Agent](../agents/openai-answer.md)
- [Template Variables Guide](../template-variables.md)

## Version History

- **v0.9.4**: Current with cognitive extraction
- **v0.9.0**: Added past_loops metadata
- **v0.8.0**: Initial release

