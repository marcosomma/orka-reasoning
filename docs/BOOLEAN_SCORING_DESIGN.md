# Boolean/Deterministic Scoring Architecture

## Overview

This document describes the deterministic boolean scoring system for Orka path evaluation.

## Problem Statement

Current `PathScorer` implementation:
- Returns continuous numeric scores (0.0-1.0)
- Uses placeholder logic with TODOs
- Non-deterministic LLM-based evaluation
- No auditable pass/fail criteria

## Solution: Boolean Criteria Matrix

### Criteria Schema

Each candidate path is evaluated against **boolean criteria** organized into categories:

```python
{
    "path": ["agent1", "agent2"],
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
        "capability_match": {
            "capabilities_cover_question_type": True,
            "modality_match": True,
            "domain_overlap_sufficient": True
        },
        "efficiency": {
            "path_length_optimal": False,
            "cost_within_budget": True,
            "latency_acceptable": True
        },
        "historical_performance": {
            "success_rate_above_threshold": True,
            "no_recent_failures": True
        }
    },
    "passed_criteria": 13,
    "total_criteria": 14,
    "overall_pass": False,  # One critical criterion failed
    "critical_failures": ["path_length_optimal"],
    "pass_percentage": 0.929,
    "audit_trail": "..."
}
```

### Criteria Categories

#### 1. Input Readiness (Critical)
- `all_required_inputs_available`: All inputs in `previous_outputs`
- `no_circular_dependencies`: Path doesn't depend on its own outputs
- `input_types_compatible`: Data types match expected formats

#### 2. Safety (Critical)
- `no_risky_capabilities_without_sandbox`: Dangerous ops have safety tags
- `output_validation_present`: Outputs are validated
- `rate_limits_configured`: API calls have rate limiting

#### 3. Capability Match (Important)
- `capabilities_cover_question_type`: Agent can handle question
- `modality_match`: Text/image/audio match
- `domain_overlap_sufficient`: Semantic similarity > threshold

#### 4. Efficiency (Nice-to-have)
- `path_length_optimal`: Length in optimal range (2-3)
- `cost_within_budget`: Estimated cost < budget
- `latency_acceptable`: Estimated latency < timeout

#### 5. Historical Performance (Nice-to-have)
- `success_rate_above_threshold`: >70% historical success
- `no_recent_failures`: No failures in last 5 runs

### Decision Logic

```python
def make_decision(criteria_results: Dict) -> bool:
    """Determine if path passes based on boolean criteria."""
    # All critical criteria must pass
    for category in ["input_readiness", "safety"]:
        if not all(criteria_results[category].values()):
            return False
    
    # At least 80% of important criteria must pass
    important_passed = sum(
        criteria_results["capability_match"].values()
    )
    if important_passed < 2:  # out of 3
        return False
    
    # Nice-to-have doesn't block but affects ranking
    return True
```

## Implementation Components

### 1. BooleanScoringEngine

```python
class BooleanScoringEngine:
    """Deterministic boolean scoring engine."""
    
    async def evaluate_candidate(
        self,
        candidate: Dict,
        question: str,
        context: Dict
    ) -> BooleanCriteriaResult:
        """Evaluate all boolean criteria."""
        results = {
            "input_readiness": await self._check_input_readiness(candidate, context),
            "safety": await self._check_safety(candidate, context),
            "capability_match": await self._check_capabilities(candidate, question, context),
            "efficiency": await self._check_efficiency(candidate, context),
            "historical_performance": await self._check_history(candidate, context)
        }
        
        return BooleanCriteriaResult(
            criteria_results=results,
            overall_pass=self._decide(results),
            audit_trail=self._generate_audit(results)
        )
```

### 2. PathExecutorNode

```python
class PathExecutorNode(BaseNode):
    """Executes a sequence of agents from a validated path."""
    
    async def _run_impl(self, context: Dict) -> Dict:
        """Execute path proposal from GraphScout."""
        # Get validated path
        path_source = self.config.get("path_source", "graph_scout.target")
        path = self._resolve_path_source(path_source, context)
        
        # Execute agents in sequence
        results = []
        for agent_id in path:
            result = await self.orchestrator.execute_agent(agent_id, context)
            results.append(result)
            
            # Update context for next agent
            context["previous_outputs"][agent_id] = result
        
        return {
            "executed_path": path,
            "results": results,
            "final_output": results[-1] if results else None
        }
```

### 3. ShortlistExecutor (Optional)

```python
class ShortlistExecutor:
    """Execute multiple candidate paths in parallel to compare results."""
    
    async def execute_shortlist(
        self,
        candidates: List[Dict],
        context: Dict
    ) -> List[Dict]:
        """Execute top N candidates in parallel."""
        tasks = [
            self._execute_path(candidate["path"], context)
            for candidate in candidates[:self.max_parallel]
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Rank by actual output quality
        return self._rank_by_output_quality(results)
```

## Migration Strategy

### Phase 1: Parallel Implementation
- Keep current numeric `PathScorer` working
- Implement `BooleanScoringEngine` alongside
- Add `scoring_mode` config parameter

### Phase 2: Integration
- Add boolean scoring to GraphScout as optional mode
- Create `PathExecutorNode`
- Update example workflows

### Phase 3: Testing & Validation
- Update tests to verify deterministic behavior
- Compare numeric vs boolean results
- Document differences and use cases

### Phase 4: Deprecation (Optional)
- Mark numeric scoring as legacy
- Recommend boolean scoring for production
- Keep numeric for quick prototyping

## Configuration

```yaml
orchestrator:
  agents:
    - id: graph_scout
      type: graph-scout
      params:
        scoring_mode: "boolean"  # or "numeric" (default)
        boolean_scoring_config:
          strict_mode: true  # All criteria must pass
          require_critical: true  # Critical criteria are mandatory
          important_threshold: 0.8  # 80% of important must pass
          include_nice_to_have: false  # Ignore efficiency/history in strict mode
```

## Benefits

1. **Auditability**: Clear pass/fail reasons for each criterion
2. **Determinism**: Same inputs always produce same results
3. **Transparency**: Stakeholders can see why paths were chosen/rejected
4. **Debugging**: Easy to identify which criteria are failing
5. **Compliance**: Meet regulatory requirements for explainability

## Trade-offs

1. **Flexibility**: Less nuanced than numeric scores
2. **Threshold Sensitivity**: Boolean cuts can be arbitrary (e.g., "70% success rate")
3. **Development Effort**: More code than simple weighted sums
4. **Performance**: More checks to run (but still fast)

## Next Steps

1. Implement `BooleanScoringEngine` class
2. Replace TODOs in PathScorer with real logic
3. Create `PathExecutorNode`
4. Add configuration switches
5. Write comprehensive tests
6. Update documentation

