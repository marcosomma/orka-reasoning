# Boolean-Based Scoring System Guide

## Overview

OrKa's boolean-based scoring system provides **deterministic, auditable, and consistent** evaluation of agent execution paths. Instead of having LLMs directly generate numeric scores (which can be inconsistent), the LLM evaluates specific boolean criteria, and OrKa calculates the final score programmatically.

## Why Boolean Scoring?

### Problems with Direct Numeric Scoring

```yaml
# Old approach (non-deterministic):
LLM returns: "validation_score: 0.78"
Run again: "validation_score: 0.82"  # Different score for same input!
```

**Issues:**
- **Non-deterministic**: Same situation gets different scores across runs
- **Hard to audit**: Why 0.78 instead of 0.80? The LLM decided
- **Inconsistent across models**: GPT-4 might give 0.85, GPT-3.5 might give 0.72
- **Difficult to debug**: Can't see which specific criteria caused a low score

### Boolean Scoring Solution

```yaml
# New approach (deterministic):
LLM returns booleans:
  has_all_required_steps: true   (weight: 0.18)
  handles_edge_cases: false      (weight: 0.08)
  validates_inputs: true         (weight: 0.08)
  ...

OrKa calculates: 0.18 + 0.08 = 0.75 (always the same!)
```

**Benefits:**
- ✅ **Deterministic**: Same booleans always produce same score
- ✅ **Auditable**: See exactly which criteria passed/failed  
- ✅ **Consistent**: Different LLMs agree more on yes/no than numeric scores
- ✅ **Tunable**: Adjust weights without retraining
- ✅ **Testable**: Easy to write unit tests with exact expected scores

## Architecture

### Components

```
orka/scoring/
├── __init__.py           # Exports main classes
├── presets.py            # Predefined scoring configurations
└── calculator.py         # BooleanScoreCalculator class
```

### Scoring Presets

OrKa includes three built-in presets:

#### Strict (Production-Critical Paths)
- **Approval Threshold**: 0.90
- **Needs Improvement**: 0.75-0.89
- **Use Case**: Mission-critical production workflows
- **Emphasis**: High standards across all dimensions

#### Moderate (General-Purpose)
- **Approval Threshold**: 0.85
- **Needs Improvement**: 0.70-0.84
- **Use Case**: Standard workflows, balanced evaluation
- **Emphasis**: Balanced across completeness, efficiency, safety

#### Lenient (Exploratory Workflows)
- **Approval Threshold**: 0.80
- **Needs Improvement**: 0.65-0.79
- **Use Case**: Experimental features, rapid prototyping
- **Emphasis**: Efficiency and iteration speed

### Evaluation Dimensions

All presets evaluate across four dimensions:

#### 1. Completeness (35-45% of total score)
- `has_all_required_steps`: All necessary steps included
- `addresses_all_query_aspects`: Every aspect of query addressed
- `handles_edge_cases`: Edge cases and unusual inputs handled
- `includes_fallback_path`: Alternative paths for failures

#### 2. Efficiency (20-30% of total score)
- `minimizes_redundant_calls`: No unnecessary duplicate agent calls
- `uses_appropriate_agents`: Best agents selected for each task
- `optimizes_cost`: Token usage minimized where possible
- `optimizes_latency`: Response time optimized

#### 3. Safety (15-25% of total score)
- `validates_inputs`: Input validation performed
- `handles_errors_gracefully`: Comprehensive error handling
- `has_timeout_protection`: Timeouts prevent hanging
- `avoids_risky_combinations`: No dangerous agent combinations

#### 4. Coherence (4-5% of total score)
- `logical_agent_sequence`: Agents called in logical order
- `proper_data_flow`: Data flows correctly between agents
- `no_conflicting_actions`: No agents working against each other

## Usage

### PlanValidatorAgent

```yaml
agents:
  - id: path_validator
    type: plan_validator
    llm_model: gpt-oss:20b
    provider: ollama
    scoring_preset: moderate  # strict | moderate | lenient
```

#### With Custom Weights

```yaml
agents:
  - id: path_validator
    type: plan_validator
    llm_model: gpt-oss:20b
    provider: ollama
    scoring_preset: moderate
    custom_weights:
      # Override specific criteria
      completeness.has_all_required_steps: 0.25  # Increase emphasis
      safety.validates_inputs: 0.15              # Increase emphasis
      efficiency.optimizes_cost: 0.02            # Decrease emphasis
```

### LoopNode

```yaml
agents:
  - id: improvement_loop
    type: loop
    max_loops: 5
    score_threshold: 0.85
    
    # Boolean scoring configuration
    scoring:
      preset: strict  # Use strict preset for loop termination
    
    internal_workflow:
      # ... workflow that returns boolean evaluations
```

#### With Custom Weights

```yaml
agents:
  - id: improvement_loop
    type: loop
    max_loops: 5
    score_threshold: 0.85
    
    scoring:
      preset: moderate
      custom_weights:
        completeness.has_all_required_steps: 0.30
        safety.validates_inputs: 0.20
```

## Response Structure

### PlanValidator Output

```python
{
    "validation_score": 0.7543,  # Calculated from booleans
    "overall_assessment": "NEEDS_IMPROVEMENT",
    
    # Boolean evaluations from LLM
    "boolean_evaluations": {
        "completeness": {
            "has_all_required_steps": true,
            "addresses_all_query_aspects": false,  # Failed
            "handles_edge_cases": true,
            "includes_fallback_path": false         # Failed
        },
        "efficiency": { ... },
        "safety": { ... },
        "coherence": { ... }
    },
    
    # Summary information
    "passed_criteria": [
        "completeness.has_all_required_steps",
        "completeness.handles_edge_cases",
        ...
    ],
    "failed_criteria": [
        "completeness.addresses_all_query_aspects",  # Debug these!
        "completeness.includes_fallback_path"
    ],
    
    # Dimension breakdown
    "dimension_scores": {
        "completeness": {
            "score": 0.30,
            "max_score": 0.45,
            "percentage": 66.67
        },
        ...
    },
    
    "scoring_preset": "moderate",
    "rationale": "..."
}
```

## Debugging Low Scores

### Check Failed Criteria

```python
# In your workflow
if result["validation_score"] < 0.85:
    print(f"Failed {len(result['failed_criteria'])} criteria:")
    for criterion in result["failed_criteria"]:
        print(f"  - {criterion}")
```

### Examine Dimension Breakdown

```python
for dimension, data in result["dimension_scores"].items():
    print(f"{dimension}: {data['percentage']:.1f}% ({data['score']}/{data['max_score']})")
```

Example output:
```
completeness: 66.7% (0.30/0.45)
efficiency: 85.0% (0.25/0.30)
safety: 100.0% (0.20/0.20)
coherence: 100.0% (0.05/0.05)
```

## Creating Custom Presets

### In Python

```python
from orka.scoring import BooleanScoreCalculator

calculator = BooleanScoreCalculator(
    preset="moderate",
    custom_weights={
        "completeness.has_all_required_steps": 0.30,
        "safety.validates_inputs": 0.20,
        # ... other overrides
    }
)

result = calculator.calculate(boolean_evaluations)
print(f"Score: {result['score']:.4f}")
```

### Programmatically

```python
from orka.scoring.calculator import BooleanScoreCalculator

# Define completely custom weights
custom_calculator = BooleanScoreCalculator(
    preset="moderate",  # Start from base preset
    custom_weights={
        # Completeness (50% total)
        "completeness.has_all_required_steps": 0.30,
        "completeness.addresses_all_query_aspects": 0.10,
        "completeness.handles_edge_cases": 0.05,
        "completeness.includes_fallback_path": 0.05,
        
        # Safety (30% total)
        "safety.validates_inputs": 0.15,
        "safety.handles_errors_gracefully": 0.10,
        "safety.has_timeout_protection": 0.03,
        "safety.avoids_risky_combinations": 0.02,
        
        # ... must sum to ~1.0
    }
)
```

## Best Practices

### 1. Choose the Right Preset

- **Strict**: Use for production-critical systems, compliance-required workflows
- **Moderate**: Default for most applications
- **Lenient**: Use for experimental features, rapid iteration

### 2. Log Score Breakdowns

```python
import logging

logger.info(f"Validation Score: {result['validation_score']:.4f}")
logger.info(f"Passed: {result['passed_count']}/{result['total_criteria']}")

if result["failed_criteria"]:
    logger.warning(f"Failed: {', '.join(result['failed_criteria'][:3])}")
```

### 3. Iterate on Weights

1. Start with a standard preset
2. Run evaluations on test cases
3. Identify over/under-weighted criteria
4. Adjust weights incrementally
5. Re-test and validate

### 4. Version Control Weights

```yaml
# config/scoring_v1.yml
version: "1.0.0"
preset: moderate
overrides:
  completeness.has_all_required_steps: 0.25
  safety.validates_inputs: 0.15
```

### 5. Write Tests

```python
def test_scoring_determinism():
    calculator = BooleanScoreCalculator(preset="moderate")
    
    evaluations = {
        "completeness": {"has_all_required_steps": True, ...},
        # ...
    }
    
    score1 = calculator.calculate(evaluations)["score"]
    score2 = calculator.calculate(evaluations)["score"]
    
    assert score1 == score2  # Always passes!
```

## Migration from Legacy Scoring

### Old Approach

```yaml
- id: plan_validator
  type: plan_validator
  # LLM returned numeric score directly
```

Old output:
```python
{"validation_score": 0.78, "rationale": "..."}
```

### New Approach

```yaml
- id: plan_validator
  type: plan_validator
  scoring_preset: moderate  # Add this
```

New output:
```python
{
    "validation_score": 0.7543,  # Calculated, not from LLM
    "boolean_evaluations": { ... },
    "failed_criteria": [ ... ],
    "dimension_scores": { ... }
}
```

### Backward Compatibility

LoopNode supports both approaches:

```yaml
# New: Boolean scoring (preferred)
- id: loop
  type: loop
  scoring:
    preset: moderate

# Old: Pattern-based extraction (still works)
- id: loop
  type: loop
  score_extraction_pattern: "SCORE:\\s*([0-9.]+)"
```

## Troubleshooting

### Score Always 0.0

**Cause**: LLM not returning valid boolean structure

**Solution**: Check LLM prompt includes boolean evaluation format
```yaml
prompt: |
  Answer TRUE or FALSE for each criterion:
  
  completeness:
    has_all_required_steps: [true/false]
    ...
```

### Score Doesn't Change

**Cause**: All criteria have same boolean values

**Solution**: Verify LLM is actually evaluating, not just returning defaults

### Scores Too High/Low

**Cause**: Weight distribution doesn't match your priorities

**Solution**: Use custom_weights to adjust

## Examples

See `examples/` directory:
- `boolean_scoring_demo.yml` - Comprehensive demo
- `plan_validator_boolean_scoring.yml` - PlanValidator usage
- `cognitive_loop_scoring_example.yml` - LoopNode integration

## API Reference

### BooleanScoreCalculator

```python
class BooleanScoreCalculator:
    def __init__(
        self,
        preset: str = "moderate",
        custom_weights: Optional[Dict[str, float]] = None
    ):
        """
        Args:
            preset: Preset name ('strict', 'moderate', 'lenient')
            custom_weights: Optional weight overrides
        """
    
    def calculate(
        self,
        boolean_evaluations: Dict[str, Dict[str, bool]]
    ) -> Dict[str, Any]:
        """
        Calculate score from boolean evaluations.
        
        Returns:
            Dict with score, assessment, breakdown, etc.
        """
    
    def get_breakdown(self, result: Dict[str, Any]) -> str:
        """Format detailed breakdown as readable string."""
    
    def get_failed_criteria(self, result: Dict[str, Any]) -> List[str]:
        """Extract list of failed criteria."""
```

## Further Reading

- [PlanValidator Documentation](agents/plan-validator.md)
- [LoopNode Documentation](nodes/loop-node.md)
- [Testing Guide](TESTING.md)

## Acknowledgments

Special thanks to **[Rubén Puertas Rey](
linkedin.com/in/ruben-puertas-rey)** for the core idea of weighted boolean validation. This approach has made OrKa's scoring system more deterministic, auditable, and maintainable.

