# PlanValidator Agent

**Type:** `plan_validator`  
**Category:** Meta-Cognitive Agent  
**Available:** v0.9.5+

## Overview

The PlanValidator agent validates and critiques proposed agent execution paths from planning agents like GraphScout. It evaluates paths across multiple dimensions and provides structured feedback for iterative improvement in loop-based workflows.

## Key Features

- **Multi-Dimensional Evaluation** - Assesses completeness, efficiency, safety, coherence, and fallback handling
- **Structured Feedback** - Returns validation scores, dimension-specific critiques, and recommended changes
- **Loop Integration** - Designed for iterative refinement with LoopNode until validation threshold met
- **Flexible LLM Support** - Works with Ollama, OpenAI-compatible APIs, or any local LLM provider
- **GraphScout Complementary** - Pairs with GraphScout for meta-cognitive workflow optimization

## Configuration

### Basic Configuration

```yaml
agents:
  - id: path_validator
    type: plan_validator
    llm_model: gpt-oss:20b
    llm_provider: ollama
    llm_url: http://localhost:11434/api/generate
    temperature: 0.2
    prompt: |
      Validate the proposed execution path for: {{ get_input() }}
      
      Proposed Path: {{ get_agent_response('graph_scout') }}
      
      Evaluate completeness, efficiency, safety, coherence, and fallback handling.
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `llm_model` | string | `gpt-oss:20b` | LLM model name for critique generation |
| `llm_provider` | string | `ollama` | Provider type: `ollama` or `openai_compatible` |
| `llm_url` | string | `http://localhost:11434/api/generate` | LLM API endpoint URL |
| `temperature` | float | `0.2` | LLM temperature (lower for consistent critiques) |
| `prompt` | string | Required | Validation prompt template with context |

## Evaluation Dimensions

The agent evaluates paths across five dimensions:

### 1. Completeness
- Does the path address all aspects of the query?
- Are all required steps included?
- Are there gaps in the execution sequence?

### 2. Efficiency
- Is the path optimal for cost and latency?
- Are agents selected appropriately?
- Could the path be simplified without losing functionality?

### 3. Safety
- Are there risky agent combinations?
- Are safeguards and error handling present?
- Could the path cause unintended side effects?

### 4. Coherence
- Do agents work well together in this sequence?
- Is data flow between agents logical?
- Are there conflicting agent behaviors?

### 5. Fallback
- Are error cases handled?
- Are edge cases considered?
- Are retry and recovery mechanisms present?

## Output Format

The agent returns a structured validation result:

```json
{
  "validation_score": 0.85,
  "overall_assessment": "APPROVED",
  "critiques": {
    "completeness": {
      "score": 0.9,
      "issues": [],
      "suggestions": ["Consider adding error logging"]
    },
    "efficiency": {
      "score": 0.85,
      "issues": ["Redundant memory read operation"],
      "suggestions": ["Combine memory operations"]
    },
    "safety": {
      "score": 0.9,
      "issues": [],
      "suggestions": ["Add rate limiting"]
    },
    "coherence": {
      "score": 0.8,
      "issues": ["Data format mismatch between agents"],
      "suggestions": ["Add data transformation step"]
    },
    "fallback": {
      "score": 0.8,
      "issues": ["Missing timeout handling"],
      "suggestions": ["Add timeout configuration"]
    }
  },
  "recommended_changes": [
    "Combine memory read operations",
    "Add timeout configuration",
    "Include data transformation step"
  ],
  "approval_confidence": 0.85,
  "rationale": "Path is well-structured with minor efficiency and fallback improvements needed."
}
```

### Score Interpretation

- **0.9-1.0**: Excellent - Approve immediately
- **0.8-0.89**: Good - Minor suggestions for improvement
- **0.7-0.79**: Needs improvement - Loop again with revisions
- **0.0-0.69**: Major issues - Reject or significantly revise

### Assessment Types

- **APPROVED**: Path meets validation threshold
- **NEEDS_IMPROVEMENT**: Path requires revisions (loop again)
- **REJECTED**: Path has major flaws (significant redesign needed)

## Usage Patterns

### Pattern 1: Simple Validation Loop

```yaml
orchestrator:
  id: design-validation
  strategy: sequential
  agents:
    - requirements_analyst
    - design_loop
    - implementation_planner

agents:
  - id: requirements_analyst
    type: local_llm
    model: gpt-oss:20b
    prompt: "Analyze requirements for: {{ input }}"

  - id: design_loop
    type: loop
    max_loops: 3
    score_threshold: 0.85
    score_extraction_config:
      strategies:
        - type: agent_key
          agents: ["plan_validator"]
          key: "validation_score"
    internal_workflow:
      orchestrator:
        strategy: sequential
        agents:
          - design_generator
          - plan_validator
      agents:
        - id: design_generator
          type: local_llm
          prompt: |
            Create workflow design for: {{ get_input() }}
            Requirements: {{ get_agent_response('requirements_analyst') }}
            {% if get_loop_number() > 1 %}
            Previous feedback: {{ get_past_loop_data('recommended_changes') }}
            {% endif %}

        - id: plan_validator
          type: plan_validator
          llm_model: gpt-oss:20b
          prompt: |
            Validate workflow design (Round {{ get_loop_number() }})
            Target Score: {{ get_score_threshold() }}+
            
            Query: {{ get_input() }}
            Design: {{ get_agent_response('design_generator') }}

  - id: implementation_planner
    type: local_llm
    prompt: "Create implementation plan for: {{ get_agent_response('design_loop') }}"
```

### Pattern 2: GraphScout Integration

```yaml
orchestrator:
  id: graphscout-validation
  strategy: sequential
  agents:
    - business_analyst
    - path_optimizer
    - execution_planner

agents:
  - id: business_analyst
    type: local_llm
    prompt: "Analyze business requirements: {{ input }}"

  - id: path_optimizer
    type: loop
    max_loops: 3
    score_threshold: 0.85
    score_extraction_config:
      strategies:
        - type: agent_key
          agents: ["plan_validator"]
          key: "validation_score"
    internal_workflow:
      orchestrator:
        strategy: sequential
        agents:
          - graph_scout
          - plan_validator
      agents:
        - id: graph_scout
          type: graph-scout
          llm_model: gpt-oss:20b
          max_depth: 5
          prompt: |
            Round {{ get_loop_number() }}: Propose optimal agent path
            
            Query: {{ get_input() }}
            Requirements: {{ get_agent_response('business_analyst') }}
            
            {% if get_loop_number() > 1 %}
            Previous critiques: {{ get_past_loop_data('critiques') }}
            Recommended changes: {{ get_past_loop_data('recommended_changes') }}
            {% endif %}

        - id: plan_validator
          type: plan_validator
          llm_model: gpt-oss:20b
          temperature: 0.2
          prompt: |
            Validate GraphScout path (Round {{ get_loop_number() }})
            
            Query: {{ get_input() }}
            Proposed Path: {{ get_agent_response('graph_scout') }}
            Requirements: {{ get_agent_response('business_analyst') }}
            
            {% if get_loop_number() > 1 %}
            Previous rounds: {{ get_past_loops() }}
            {% endif %}

  - id: execution_planner
    type: local_llm
    prompt: "Create execution plan from validated path"
```

## Context Requirements

The PlanValidator extracts information from the context:

### Required Context
- `input`: Original user query
- `previous_outputs`: Previous agent outputs (must include proposed path)

### Optional Context
- `loop_number`: Current iteration (default: 1)
- `past_loops`: Previous validation rounds for learning
- `score_threshold`: Target score for approval

### Proposed Path Location

The agent searches for proposed paths in `previous_outputs` using these keys (in order):
1. `graph_scout`
2. `graphscout_planner`
3. `path_proposer`
4. `dynamic_router`
5. Any agent with `decision_type`, `target`, or `path` fields

## Template Helpers

Available in validation prompts:

```jinja2
{{ get_input() }}                          # Original query
{{ get_agent_response('agent_id') }}       # Specific agent output
{{ get_loop_number() }}                    # Current iteration
{{ get_score_threshold() }}                # Target validation score
{{ get_past_loops() }}                     # All previous loop data
{{ get_past_loop_data('key') }}            # Specific field from last loop
```

## Best Practices

### 1. Temperature Configuration
- Use low temperature (0.1-0.3) for consistent validation
- Higher temperature (0.4-0.6) for creative critique generation

### 2. Prompt Engineering
- Provide clear validation criteria in the prompt
- Include context about the original query and requirements
- Reference previous critiques in loop iterations

### 3. Score Threshold Selection
- 0.85: Balanced quality and iteration count
- 0.90: High quality, may require more iterations
- 0.80: Faster convergence, acceptable quality

### 4. Loop Configuration
- Max loops: 2-3 for simple validation
- Max loops: 3-5 for complex path optimization
- Always include score extraction configuration

### 5. Error Handling
- Agent returns error critique on LLM failure
- Validation score: 0.0 on errors
- Overall assessment: "REJECTED"

## Limitations

- **LLM Dependency**: Requires LLM API availability
- **Critique Quality**: Depends on LLM model capabilities
- **Context Size**: Large paths may exceed LLM context limits
- **Subjectivity**: Validation scores reflect LLM judgment

## Troubleshooting

### Issue: Validation score always 0.0
**Solution**: Check LLM connectivity and model availability. Review agent logs for LLM call failures.

### Issue: No proposed path found
**Solution**: Ensure previous agent (GraphScout, etc.) outputs path data. Check `previous_outputs` keys match expected format.

### Issue: Loop never converges
**Solution**: Lower score threshold or increase max loops. Review critique feedback - path may need significant revision.

### Issue: Inconsistent validation scores
**Solution**: Lower LLM temperature for more consistent critiques. Use same model across iterations.

## Performance Considerations

- **LLM Latency**: 2-10 seconds per validation depending on model
- **Token Usage**: ~500-1000 tokens per validation (varies by path complexity)
- **Memory Footprint**: Minimal (<1MB per validation)
- **Concurrent Validations**: Support depends on LLM API rate limits

## Examples

See complete working examples in:
- `examples/plan_validator_simple.yml` - Basic workflow validation
- `examples/plan_validator_complex.yml` - GraphScout integration
- `examples/plan_validator_with_graphscout.yml` - Simplified pattern

## Related Documentation

- [GraphScout Agent](../nodes/graph-scout.md) - Intelligent path discovery
- [Loop Node](../nodes/loop.md) - Iterative execution
- [Template Rendering](../YAML_CONFIGURATION.md) - Jinja2 helpers
- [Memory System](../MEMORY_SYSTEM_GUIDE.md) - Context passing

## Version History

- **v0.9.5** (2025-10-26): Initial release with multi-dimensional validation

