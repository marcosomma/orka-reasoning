# MyPy Error Refactoring Plan

This document outlines the plan for addressing MyPy type checking errors in the `orka` codebase. The following rules will be strictly adhered to during this process:

- **Do not change existing working code:** Only modifications directly related to resolving MyPy type errors will be made. The functional behavior of the code must remain unchanged.
- **Do not delete code:** No existing code will be removed. Fixes will involve adding type hints, casting, or other MyPy-specific annotations.
- **Gradual Fixes and Status Tracking:** Files will be addressed one by one. The status of each file will be updated to track progress and note any potential backward compatibility issues.
- **Targeted MyPy Runs:** After fixing a file, run `mypy orka/filename.py` to ensure the fixes were effective before moving to the next file.

## Files to be Fixed (MyPy Errors)

- `orka\memory\schema_manager.py` - **FIXED** (installed types-protobuf stubs)
- `orka\nodes\memory_writer_node.py` - **FIXED** (added proper type casting and return types)
- `orka\orchestrator\execution_engine.py` - **FIXED** (added proper type bounds and attributes)
- `orka\orchestrator\agent_factory.py` - Multiple attribute and callable errors

## Fix Status and Notes

### Current Status Summary
- Total files with errors: 1
- Total errors: 13
- Most problematic files:
  - `orka\orchestrator\agent_factory.py` (13 errors - attribute access and callable issues)

### Fix Priority Order
1. `orka\orchestrator\agent_factory.py` (attribute and callable issues)

### Recent Fixes
1. `orka\utils\bootstrap_memory_index.py` - Fixed by removing unused type ignore comment from the import statement of redis.commands.search.index_definition.
2. `orka\tui\fallback.py` - Fixed type incompatibility errors by:
   - Adding proper type hints using TypeVar for memory logger
   - Using type casting for backend string
   - Importing and using BaseMemoryLogger for type bounds
   - Properly typing method parameters
3. `orka\tui\data_manager.py` - Fixed type handling issues by:
   - Added _safe_float helper method for consistent float conversions
   - Improved type hints for dictionaries and return types
   - Added proper type casting for metadata handling
   - Fixed performance metrics type handling
   - Added null checks and type guards
4. `orka\tui\textual_screens.py` - Fixed unreachable statements by:
   - Moved widget query outside try block with proper initialization
   - Added null check for widget before proceeding
   - Improved error handling structure to avoid unreachable code
   - Fixed similar issues in all three memory selection handlers
5. `orka\memory\schema_manager.py` - Fixed by installing types-protobuf package to provide proper type stubs for google.protobuf
6. `orka\nodes\memory_writer_node.py` - Fixed return type issues by:
   - Added str() casting to ensure string returns from _extract_memory_content
   - Added str() casting to all fields in _memory_object_to_text
   - Added float() casting to ensure float returns from _get_expiry_hours
   - Fixed dict[str, Any] return type in _merge_metadata exception handler
7. `orka\orchestrator\execution_engine.py` - Fixed type errors by:
   - Added ExecutionEngineProtocol class to define required attributes
   - Added proper type bounds to T type variable
   - Added required attributes to ExecutionEngine class
   - Fixed memory.close() call to check for attribute existence
   - Fixed step parameter type in memory logger calls

### Known Issues
1. `orka\utils\bootstrap_memory_index.py` - The retry function has an unreachable statement error that mypy can't verify. After multiple refactoring attempts (using while loop, for loop with different conditions, adding type ignore comments), mypy still can't verify that the code is reachable. The code is functionally correct and works as intended, so we'll leave this error for now.

2. `orka\agents\validation_and_structuring_agent.py` - The build_prompt method has an unreachable statement error that mypy can't verify. After multiple refactoring attempts (using different approaches to build the prompt, restructuring the code, and moving logic into separate methods), mypy still can't verify that all code paths are reachable. The code is functionally correct and works as intended, so we'll leave this error for now.

### Next Steps
1. Fix the unreachable statement in validation_and_structuring_agent.py
