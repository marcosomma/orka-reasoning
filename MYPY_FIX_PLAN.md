# MyPy Error Refactoring Plan

This document outlines the plan for addressing MyPy type checking errors in the `orka` codebase. The following rules will be strictly adhered to during this process:

- for any command you have to run remeber to activate conda environment with command `conda activate orka_test` do notrun commands outside this environment
- **Do not change existing working code:** Only modifications directly related to resolving MyPy type errors will be made. The functional behavior of the code must remain unchanged.
- **Do not delete code:** No existing code will be removed. Fixes will involve adding type hints, casting, or other MyPy-specific annotations.
- **Gradual Fixes and Status Tracking:** Files will be addressed one by one. The status of each file will be updated to track progress and note any potential backward compatibility issues.
- **Happy MyPy:** After fixing a file, run `mypy orka/filename.py` to ensure the fixes were effective and do not brake mypy rules before moving to the next file.

# Fix Implementation Plan

## 1. Fork Node Execution Fix

### 1.1 Execution Engine Updates
```python
# orka/orchestrator/execution_engine.py

class ExecutionEngine:
    async def run_parallel_agents(self, agent_ids, fork_group_id, input_data, previous_outputs):
        # Add proper context tracking
        context_tracker = {
            'fork_group': fork_group_id,
            'parent_context': previous_outputs,
            'step_results': {}
        }
        
        # Ensure complete context is passed
        enhanced_context = self._ensure_complete_context(previous_outputs)
        
        # Run each agent with proper context
        for agent_id in agent_ids:
            agent = self.agents[agent_id]
            agent_context = {
                'input': input_data,
                'previous_outputs': enhanced_context,
                'fork_context': context_tracker
            }
            
            # Execute agent with proper error handling
            try:
                result = await self._run_agent_async(agent_id, agent_context)
                context_tracker['step_results'][agent_id] = result
            except Exception as e:
                logger.error(f"Fork agent {agent_id} failed: {e}")
                context_tracker['step_results'][agent_id] = {'error': str(e)}
                
        return context_tracker['step_results']
```

### 1.2 Fork Node Updates
```python
# orka/nodes/fork_node.py

class ForkNode:
    async def run(self, context):
        # Validate context
        if not self._validate_context(context):
            raise ValueError("Invalid fork context")
            
        # Generate fork group ID
        fork_group_id = self._generate_fork_group_id()
        
        # Initialize fork state
        fork_state = {
            'group_id': fork_group_id,
            'targets': self.targets,
            'status': 'pending',
            'results': {}
        }
        
        # Store fork state in memory
        await self._store_fork_state(fork_state)
        
        # Return fork initialization data
        return {
            'status': 'forked',
            'fork_group': fork_group_id,
            'targets': self.targets
        }
```

## 2. Template Rendering Fix

### 2.1 Prompt Renderer Updates
```python
# orka/orchestrator/prompt_rendering.py

class PromptRenderer:
    def _enhance_payload_for_templates(self, payload):
        enhanced = payload.copy()
        
        # Handle nested input structure
        if isinstance(enhanced.get('input'), dict):
            for key, value in enhanced['input'].items():
                if key not in enhanced:
                    enhanced[key] = value
                    
        # Handle previous outputs
        if 'previous_outputs' in enhanced:
            enhanced['previous_outputs'] = self._flatten_outputs(
                enhanced['previous_outputs']
            )
            
        return enhanced
        
    def _flatten_outputs(self, outputs):
        flattened = {}
        for agent_id, result in outputs.items():
            if isinstance(result, dict):
                # Handle different result types
                if 'response' in result:
                    flattened[agent_id] = result['response']
                elif 'result' in result:
                    flattened[agent_id] = result['result']
                else:
                    flattened[agent_id] = result
            else:
                flattened[agent_id] = result
        return flattened
```

## 3. Memory System Fix

### 3.1 Memory Logger Updates
```python
# orka/memory/redisstack_logger.py

class RedisStackMemoryLogger:
    def log(self, agent_id, event_type, payload, **kwargs):
        # Enhance logging with proper categorization
        enhanced_payload = self._enhance_payload(payload)
        
        # Add proper metadata
        metadata = {
            'agent_id': agent_id,
            'event_type': event_type,
            'timestamp': datetime.now(UTC).isoformat(),
            'category': self._determine_category(event_type),
            **kwargs
        }
        
        # Store with proper indexing
        self._store_with_index(enhanced_payload, metadata)
        
    def _determine_category(self, event_type):
        # Implement proper categorization logic
        categories = {
            'ForkNode': 'orchestration',
            'JoinNode': 'orchestration',
            'LoopNode': 'control_flow',
            'MemoryReaderNode': 'memory',
            'MemoryWriterNode': 'memory'
        }
        return categories.get(event_type, 'default')
```

## 4. Loop State Fix

### 4.1 Loop Node Updates
```python
# orka/nodes/loop_node.py

class LoopNode:
    async def run(self, context):
        # Ensure proper loop state tracking
        loop_state = self._initialize_loop_state(context)
        
        # Execute loop iteration
        result = await self._execute_iteration(loop_state)
        
        # Update loop state
        updated_state = self._update_loop_state(loop_state, result)
        
        # Store loop state in memory
        await self._store_loop_state(updated_state)
        
        return self._prepare_loop_result(updated_state)
        
    def _initialize_loop_state(self, context):
        return {
            'current_loop': len(context.get('past_loops', [])) + 1,
            'past_loops': context.get('past_loops', []),
            'loop_metadata': context.get('past_loops_metadata', {})
        }
```

## Implementation Order

1. **Template Rendering Fix**
   - Implement the enhanced payload processing
   - Add proper context flattening
   - Test with various template scenarios

2. **Fork Node Execution Fix**
   - Update execution engine parallel processing
   - Enhance fork node state management
   - Test with complex fork scenarios

3. **Memory System Fix**
   - Implement proper categorization
   - Add enhanced logging
   - Test memory persistence and retrieval

4. **Loop State Fix**
   - Update loop state tracking
   - Enhance loop metadata handling
   - Test loop execution and state persistence

## Testing Strategy

1. **Unit Tests**
```python
# test/unit/test_fork_execution.py
def test_fork_execution_with_context():
    # Test fork node execution with various context scenarios
    
# test/unit/test_template_rendering.py
def test_template_rendering_with_nested_structure():
    # Test template rendering with complex nested structures
    
# test/unit/test_memory_logging.py
def test_memory_categorization():
    # Test memory categorization and retrieval
    
# test/unit/test_loop_state.py
def test_loop_state_persistence():
    # Test loop state tracking and updates
```

2. **Integration Tests**
```python
# test/integration/test_fork_workflow.py
def test_complete_fork_workflow():
    # Test end-to-end fork/join workflow
    
# test/integration/test_memory_workflow.py
def test_memory_persistence_workflow():
    # Test memory system in complete workflow
```

## Mypy Compliance

All changes will maintain strict mypy compliance:

1. Add proper type hints:
```python
from typing import Dict, List, Optional, Any, TypeVar, Generic

T = TypeVar('T')

class ForkNode(Generic[T]):
    def __init__(self, node_id: str, targets: List[List[str]], **kwargs: Any) -> None:
        ...
```

2. Use type guards:
```python
def is_dict_result(result: Any) -> TypeGuard[Dict[str, Any]]:
    return isinstance(result, dict)
```

3. Add type checking decorators:
```python
from typing_extensions import TypeGuard

@type_check_decorator
def process_result(result: Any) -> Dict[str, Any]:
    ...
```

Would you like me to proceed with implementing any specific part of this plan first?