# PlanValidator Agent

**Type:** `plan_validator`  
**Category:** Meta-Cognitive Agent  
**Available:** v0.9.5+

## Overview

The PlanValidator agent validates and critiques proposed agent execution paths from planning agents like GraphScout. It evaluates paths across multiple dimensions using **boolean-based scoring** for deterministic, auditable results, and provides structured feedback for iterative improvement in loop-based workflows.

## Key Features

- **Boolean-Based Scoring** - Deterministic scoring from boolean criteria (new in v0.9.6+)
- **Multi-Dimensional Evaluation** - Assesses completeness, efficiency, safety, and coherence
- **Structured Feedback** - Returns validation scores, boolean evaluations, and failed criteria
- **Auditable Results** - See exactly which criteria passed or failed
- **Loop Integration** - Designed for iterative refinement with LoopNode until validation threshold met
- **Flexible LLM Support** - Works with Ollama, OpenAI-compatible APIs, or any local LLM provider
- **GraphScout Complementary** - Pairs with GraphScout for meta-cognitive workflow optimization

## Configuration

### Basic Configuration (Boolean Scoring)

```yaml
agents:
  - id: path_validator
    type: plan_validator
    model:  openai/gpt-oss-20b
    llm_provider: lm_studio
    llm_url: http://localhost:1234
    temperature: 0.2
    scoring_preset: moderate  # strict | moderate | lenient
    scoring_context: graphscout  # Evaluate agent path quality (default)
```

### With Custom Weights

```yaml
agents:
  - id: path_validator
    type: plan_validator
    model:  openai/gpt-oss-20b
    llm_provider: lm_studio
    scoring_preset: moderate
    scoring_context: graphscout  # Agent path evaluation
    custom_weights:
      # Override specific criteria weights for agent paths
      completeness.has_all_required_steps: 0.25
      safety.validates_inputs: 0.15
      efficiency.uses_appropriate_agents: 0.12
```

### For Response Quality Validation

```yaml
agents:
  - id: quality_validator
    type: plan_validator
    model:  openai/gpt-oss-20b
    llm_provider: lm_studio
    scoring_preset: moderate
    scoring_context: quality  # Response quality assessment
    custom_weights:
      accuracy.factually_correct: 0.30
      clarity.well_structured: 0.25
      completeness.provides_comprehensive_answer: 0.20
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `llm_model` | string | `gpt-oss:20b` | LLM model name for boolean evaluation |
| `llm_provider` | string | `ollama` | Provider type: `ollama` or `openai_compatible` |
| `llm_url` | string | `http://localhost:1234` | LLM API endpoint URL |
| `temperature` | float | `0.2` | LLM temperature (lower for consistent evaluations) |
| `scoring_preset` | string | `moderate` | Scoring preset: `strict`, `moderate`, or `lenient` |
| `custom_weights` | dict | None | Optional weight overrides (e.g., `dimension.criterion: weight`) |

## Evaluation Dimensions

The agent evaluates paths using boolean criteria across four dimensions:

### 1. Completeness (35-45% of score)
- `has_all_required_steps`: All necessary steps included in path
- `addresses_all_query_aspects`: Every aspect of query addressed
- `handles_edge_cases`: Edge cases and unusual inputs handled
- `includes_fallback_path`: Alternative paths for failures

### 2. Efficiency (20-30% of score)
- `minimizes_redundant_calls`: No unnecessary duplicate agent calls
- `uses_appropriate_agents`: Best agents selected for each task
- `optimizes_cost`: Token usage minimized where possible
- `optimizes_latency`: Response time optimized

### 3. Safety (15-25% of score)
- `validates_inputs`: Input validation performed
- `handles_errors_gracefully`: Comprehensive error handling
- `has_timeout_protection`: Timeouts prevent hanging operations
- `avoids_risky_combinations`: No dangerous agent combinations

### 4. Coherence (4-5% of score)
- `logical_agent_sequence`: Agents called in logical order
- `proper_data_flow`: Data flows correctly between agents
- `no_conflicting_actions`: No agents working against each other

### Scoring Presets

**Strict** (Production-critical):
- Approval threshold: 0.90+
- High standards across all dimensions
- Use for mission-critical workflows

**Moderate** (Default):
- Approval threshold: 0.85+
- Balanced evaluation
- Use for general-purpose workflows

**Lenient** (Exploratory):
- Approval threshold: 0.80+
- Faster iteration
- Use for experimental features

## Output Format

The agent returns a structured validation result with boolean evaluations:

```json
{
  "validation_score": 0.7543,
  "overall_assessment": "NEEDS_IMPROVEMENT",
  
  "boolean_evaluations": {
    "completeness": {
      "has_all_required_steps": true,
      "addresses_all_query_aspects": false,
      "handles_edge_cases": true,
      "includes_fallback_path": false
    },
    "efficiency": {
      "minimizes_redundant_calls": true,
      "uses_appropriate_agents": true,
      "optimizes_cost": false,
      "optimizes_latency": true
    },
    "safety": {
      "validates_inputs": true,
      "handles_errors_gracefully": false,
      "has_timeout_protection": true,
      "avoids_risky_combinations": true
    },
    "coherence": {
      "logical_agent_sequence": true,
      "proper_data_flow": true,
      "no_conflicting_actions": true
    }
  },
  
  "passed_criteria": [
    "completeness.has_all_required_steps",
    "completeness.handles_edge_cases",
    "efficiency.minimizes_redundant_calls",
    ...
  ],
  
  "failed_criteria": [
    "completeness.addresses_all_query_aspects",
    "completeness.includes_fallback_path",
    "efficiency.optimizes_cost",
    "safety.handles_errors_gracefully"
  ],
  
  "dimension_scores": {
    "completeness": {
      "score": 0.28,
      "max_score": 0.45,
      "percentage": 62.2
    },
    ...
  },
  
  "scoring_preset": "moderate",
  "rationale": "Path addresses core requirements but needs fallback handling and cost optimization."
}
```

### Score Interpretation

- **0.90-1.0** (Strict): Excellent - Approve immediately
- **0.85-1.0** (Moderate): Approved
- **0.80-1.0** (Lenient): Approved
- Below threshold: Needs improvement

### Assessment Types

- **APPROVED**: Path meets validation threshold for chosen preset
- **NEEDS_IMPROVEMENT**: Path requires revisions (loop again)
- **REJECTED**: Path has major flaws (below 0.70)

### Debugging Low Scores

Check `failed_criteria` to see exactly what needs improvement:

```python
if result["validation_score"] < 0.85:
    print("Failed criteria:")
    for criterion in result["failed_criteria"]:
        print(f"  - {criterion}")
```

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
    model: openai/gpt-oss-20b
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
          model:  openai/gpt-oss-20b
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
          model:  openai/gpt-oss-20b
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
          model:  openai/gpt-oss-20b
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
- `examples/plan_validator_boolean_scoring.yml` - Boolean scoring demo (recommended)
- `examples/boolean_scoring_demo.yml` - Comprehensive scoring guide
- `examples/plan_validator_simple.yml` - Basic workflow validation
- `examples/plan_validator_complex.yml` - GraphScout integration

## Related Documentation

- **[Boolean Scoring Guide](../BOOLEAN_SCORING_GUIDE.md)** - Comprehensive guide to deterministic scoring
- [GraphScout Agent](../nodes/graph-scout.md) - Intelligent path discovery
- [Loop Node](../nodes/loop.md) - Iterative execution
- [Template Rendering](../YAML_CONFIGURATION.md) - Jinja2 helpers
- [Memory System](../MEMORY_SYSTEM_GUIDE.md) - Context passing

## Version History

- **v0.9.6** (2025-10-28): Added boolean-based scoring system for deterministic evaluation
- **v0.9.5** (2025-10-26): Initial release with multi-dimensional validation

