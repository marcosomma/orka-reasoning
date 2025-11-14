# Scoring Architecture in OrKa

## Two Distinct Scoring Systems

OrKa uses TWO separate scoring systems for different purposes. Understanding this distinction is critical for proper usage.

---

## 1. PathScorer (Numeric Scoring)

**Location**: `orka/orchestrator/path_scoring.py`  
**Used By**: GraphScout for path discovery  
**Purpose**: Rank candidate paths during exploration

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

### When to Use

- GraphScout path discovery and ranking
- Real-time routing decisions
- Multi-criteria optimization
- Dynamic workflow planning

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

| Aspect | PathScorer (Numeric) | PlanValidator (Boolean) |
|--------|---------------------|------------------------|
| **Purpose** | Rank & select paths | Approve/reject proposals |
| **Output** | Continuous score 0.0-1.0 | Boolean pass/fail per criterion |
| **Speed** | Fast (heuristics + optional LLM) | Moderate (LLM reasoning required) |
| **Use Case** | Real-time routing | Validation before execution |
| **Flexibility** | Weighted multi-criteria | Fixed boolean checks |
| **Determinism** | Non-deterministic (LLM) | Deterministic (criteria-based) |

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
  llm_model: gpt-oss:20b
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

