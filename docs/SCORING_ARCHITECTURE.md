# Scoring Architecture in OrKa

## Three Scoring Systems

OrKa provides THREE scoring systems for different purposes. Understanding these distinctions is critical for proper usage.

---

## 1. PathScorer with Dual-Mode Support

**Location**: `orka/orchestrator/path_scoring.py`  
**Used By**: GraphScout for path discovery  
**Purpose**: Rank and validate candidate paths during exploration

**NEW**: PathScorer now supports BOTH numeric and boolean modes, switchable via configuration.

---

### 1A. PathScorer - Numeric Mode (Default)

**Purpose**: Fast, weighted ranking of candidate paths

### Scoring Components

PathScorer combines multiple criteria with configurable weights:

- **LLM Evaluation** (weight: 0.45) - LLM-powered relevance assessment
- **Heuristics** (weight: 0.20) - Rule-based capability matching
- **Priors/History** (weight: 0.20) - Historical success rates
- **Cost** (weight: 0.10) - Estimated execution cost
- **Latency** (weight: 0.05) - Estimated execution time

### Output Format

```python
{
    "score": 0.87,  # Final weighted score (0.0-1.0)
    "confidence": 0.92,  # Confidence in the score
    "score_components": {
        "llm": 0.85,
        "heuristics": 0.90,
        "prior": 0.88,
        "cost": 0.92,
        "latency": 0.95
    }
}
```

### Configuration

PathScorer thresholds are configurable via `GraphScoutConfig`:

```python
config = GraphScoutConfig(
    max_reasonable_cost=0.10,        # $0.10 max cost
    path_length_penalty=0.10,        # Penalty per extra hop
    keyword_match_boost=0.30,        # Boost for keyword matches
    optimal_path_length=(2, 3),      # Optimal range
)
```

### When to Use Numeric Mode

- GraphScout path discovery and ranking
- Real-time routing decisions
- Multi-criteria optimization
- Dynamic workflow planning
- When you need soft rankings with weighted criteria

---

### 1B. PathScorer - Boolean Mode (**NEW**)

**Purpose**: Deterministic, auditable path validation with explicit pass/fail criteria

### Criteria Categories

Boolean mode evaluates 5 categories of criteria, each returning explicit True/False results:

#### 1. Input Readiness (CRITICAL)
- `all_required_inputs_available`: All required inputs exist in `previous_outputs`
- `no_circular_dependencies`: Agent not already in execution chain
- `input_types_compatible`: Data types match expected formats

#### 2. Safety (CRITICAL)
- `no_risky_capabilities_without_sandbox`: Dangerous operations have safety tags
- `output_validation_present`: Outputs are validated before use
- `rate_limits_configured`: API calls have rate limiting

#### 3. Capability Match (IMPORTANT)
- `capabilities_cover_question_type`: Agent can handle the question type
- `modality_match`: Text/image/audio capabilities match question
- `domain_overlap_sufficient`: Semantic similarity above threshold

#### 4. Efficiency (NICE-TO-HAVE)
- `path_length_optimal`: Length in optimal range (2-3 agents)
- `cost_within_budget`: Estimated cost < budget limit
- `latency_acceptable`: Estimated latency < timeout

#### 5. Historical Performance (NICE-TO-HAVE)
- `success_rate_above_threshold`: Historical success rate > 70%
- `no_recent_failures`: No failures in last 5 runs

### Decision Logic

```python
# All CRITICAL criteria must pass
if not all(input_readiness) or not all(safety):
    return FAIL

# At least 80% of IMPORTANT criteria must pass
if capability_match_percentage < 0.8:
    return FAIL

# NICE-TO-HAVE criteria don't block (unless strict_mode=True)
return PASS
```

### Output Format

```python
{
    "boolean_result": {
        "overall_pass": True,
        "criteria_results": {
            "input_readiness": {
                "all_required_inputs_available": True,
                "no_circular_dependencies": True,
                "input_types_compatible": True
            },
            "safety": {
                "no_risky_capabilities_without_sandbox": True,
                "output_validation_present": True,
                "rate_limits_configured": True
            },
            # ... other categories ...
        },
        "passed_criteria": 13,
        "total_criteria": 14,
        "pass_percentage": 0.929,
        "critical_failures": [],
        "reasoning": "All critical and important criteria passed. Path is valid and safe.",
        "audit_trail": "Boolean Criteria Evaluation:\n..."
    },
    "score": 0.929,  # For sorting
    "confidence": 1.0
}
```

### Configuration

Enable boolean mode via `GraphScoutConfig`:

```yaml
- id: graph_scout_router
  type: graph-scout
  params:
    scoring_mode: "boolean"  # Switch to deterministic mode
    strict_mode: false        # false = only critical + important matter
    require_critical: true    # true = all critical must pass
    important_threshold: 0.8  # 80% of important must pass
    include_nice_to_have: true  # true = check efficiency/history
    min_success_rate: 0.70    # Historical success threshold
    min_domain_overlap: 0.30  # Domain overlap threshold
    max_acceptable_cost: 0.10 # Maximum cost in USD
    max_acceptable_latency: 10000  # Maximum latency in ms
```

### When to Use Boolean Mode

- **Compliance & Audit**: When you need to prove why paths were selected/rejected
- **Production Safety**: When you need guaranteed safety checks
- **Debugging**: When numeric scores are mysterious and you need clarity
- **Regulatory Requirements**: When decisions must be explainable
- **Testing**: When you want deterministic, repeatable outcomes

---

## 2. PlanValidator (Boolean Scoring)

**Location**: `orka/nodes/plan_validator_node.py`  
**Used By**: Validation loops for proposal approval  
**Purpose**: Deterministic pass/fail validation

### Validation Criteria

PlanValidator evaluates 15 boolean checks across 4 dimensions:

#### Completeness (5 criteria)
- `has_all_required_steps`: All necessary agents present
- `addresses_input_requirements`: Input requirements satisfied
- `produces_required_output`: Generates expected output
- `includes_terminal_agent`: Has terminal/response agent
- `covers_all_aspects`: Addresses all query aspects

#### Coherence (4 criteria)
- `logical_agent_sequence`: Proper execution order
- `proper_data_flow`: Data dependencies satisfied
- `no_circular_dependencies`: No circular paths
- `maintains_context`: Context preserved across agents

#### Efficiency (3 criteria)
- `uses_appropriate_agents`: Right agents for the task
- `avoids_redundancy`: No duplicate operations
- `optimizes_resources`: Efficient resource usage

#### Safety (3 criteria)
- `handles_errors_gracefully`: Error handling present
- `validates_inputs`: Input validation included
- `respects_constraints`: Adheres to constraints

### Output Format

```python
{
    "validation_score": 0.867,  # Aggregate score (passed/total)
    "overall_assessment": "Approved - meets quality standards",
    "passed_criteria": [
        "has_all_required_steps",
        "logical_agent_sequence",
        # ... 11 more
    ],
    "failed_criteria": ["includes_fallback_path"],
    "dimension_scores": {
        "completeness": {"score": 5, "max_score": 5, "percentage": 100},
        "coherence": {"score": 4, "max_score": 4, "percentage": 100},
        "efficiency": {"score": 3, "max_score": 3, "percentage": 100},
        "safety": {"score": 1, "max_score": 3, "percentage": 33.33}
    }
}
```

### Configuration

PlanValidator uses presets (strict, moderate, lenient):

```yaml
- id: path_validator
  type: plan_validator
  scoring_preset: moderate  # or "strict" or "lenient"
  custom_weights:
    completeness.has_all_required_steps: 0.20
    efficiency.uses_appropriate_agents: 0.15
```

### When to Use

- Validation loops (propose → validate → execute)
- Quality gates before execution
- Compliance and audit requirements
- High-stakes decision approval

---

## Comparison: When to Use Which

| Aspect | PathScorer Numeric | PathScorer Boolean | PlanValidator |
|--------|--------------------|--------------------|---------------|
| **Purpose** | Rank paths | Validate safety | Approve proposals |
| **Output** | Score 0.0-1.0 | Boolean + audit | Boolean + dimensions |
| **Speed** | Fast | Very fast | Moderate |
| **Use Case** | Routing | Safety gates | Quality assurance |
| **Flexibility** | Weighted | Fixed criteria | Customizable presets |
| **Determinism** | Non-deterministic | **Deterministic** | LLM-based |
| **Audit Trail** | Score components | **Full audit** | Dimension reasoning |

---

## Architectural Patterns

### Pattern 1: GraphScout Direct Routing

GraphScout uses **PathScorer** to select and route immediately:

```yaml
orchestrator:
  agents:
    - graph_scout_router  # Uses PathScorer internally
    - result_synthesizer
```

**Flow**: 
1. GraphScout discovers paths
2. PathScorer ranks paths (numeric)
3. Best path executes immediately

### Pattern 2: Validated Execution

GraphScout proposes, PlanValidator approves, PathExecutor executes:

```yaml
orchestrator:
  agents:
    - validation_loop      # GraphScout + PlanValidator inside
    - path_executor        # Executes approved path
    - final_report
```

**Flow**:
1. GraphScout proposes path (PathScorer ranks internally)
2. PlanValidator evaluates proposal (boolean scoring)
3. Loop repeats until passing score
4. PathExecutor executes validated path

---

## Implementation Details

### PathScorer Initialization

```python
from orka.orchestrator.path_scoring import PathScorer
from orka.nodes.graph_scout_agent import GraphScoutConfig

config = GraphScoutConfig(
    score_weights={
        "llm": 0.45,
        "heuristics": 0.20,
        "prior": 0.20,
        "cost": 0.10,
        "latency": 0.05
    }
)

scorer = PathScorer(config)
scores = await scorer.score_candidates(candidates, question, context)
```

### PlanValidator Usage

```yaml
- id: path_validator
  type: plan_validator
  model: openai/gpt-oss-20b
  scoring_preset: moderate
  custom_weights:
    completeness.has_all_required_steps: 0.20
```

---

## Branch Name Clarification

The `deterministic_scoring_new` branch name refers to the addition of the **PlanValidator's deterministic boolean scoring system**, not a replacement of PathScorer's numeric scoring.

**Both systems coexist:**
- PathScorer remains numeric/weighted for path discovery
- PlanValidator adds deterministic validation for quality gates

This dual-system architecture provides:
1. **Fast routing** (PathScorer with heuristics)
2. **Quality assurance** (PlanValidator with boolean checks)
3. **Flexibility** (choose pattern based on needs)

---

## Migration Guide

If you're upgrading from earlier versions:

### Using PathScorer

No changes required - PathScorer maintains backward compatibility while adding configurable thresholds.

### Adding PlanValidator

Add validation loops for quality gates:

```yaml
agents:
  - id: validation_loop
    type: loop
    score_threshold: 0.85
    internal_workflow:
      agents:
        - path_proposer
        - path_validator  # New: Boolean validation
```

---

## Related Documentation

- [GraphScout Agent](GRAPH_SCOUT_AGENT.md) - Path discovery details
- [Boolean Scoring Guide](BOOLEAN_SCORING_GUIDE.md) - PlanValidator usage
- [Agent Scoping](AGENT_SCOPING.md) - Agent visibility rules
- [Loop Node](nodes/loop.md) - Validation loop patterns

---

## Summary

- **PathScorer**: Numeric, weighted, fast → Use for routing
- **PlanValidator**: Boolean, deterministic, thorough → Use for validation
- **Together**: Combine for validated execution pattern
- **Separately**: Use PathScorer alone for simple routing

Choose the right tool for your use case, or combine both for robust, validated agent orchestration.

