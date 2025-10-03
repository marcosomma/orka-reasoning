# OrKa AI Agent Orchestration Framework - Copilot Instructions

## Project Overview
OrKa is a YAML-first AI agent orchestration framework that enables complex workflows through declarative configuration instead of procedural code. Think CrewAI/LangChain but with YAML configs, built-in intelligent memory, and first-class local LLM support.

## Core Architecture Patterns

### 1. Modular Component System
- **Orchestrator**: Main workflow engine (`orka/orchestrator.py`) uses multiple inheritance mixins
- **Agent Factory**: Dynamic agent registration via `AGENT_TYPES` registry (`orka/agents/`)
- **Memory System**: Redis-based persistent memory with decay and semantic search (`orka/memory/`)
- **CLI Interface**: Multi-command structure via argparse subcommands (`orka/orka_cli.py`)

### 2. Agent Implementation Patterns
```python
# Modern async pattern (preferred)
class MyAgent(BaseAgent):
    async def process(self, input_data: str) -> Dict[str, Any]:
        # Full async/await, timeout control, structured output
        
# Legacy sync pattern (backward compatibility)  
class MyLegacyAgent(LegacyBaseAgent):
    def process(self, input_data: str) -> str:
        # Simple synchronous execution
```

### 3. Configuration-First Approach
All workflows are YAML files with this structure:
```yaml
orchestrator:
  id: workflow_name
  strategy: sequential|parallel  
  agents: [agent1, agent2, ...]

agents:
  - id: agent_name
    type: memory|local_llm|openai-gpt-4|search|router|fork|join|loop|graph-scout
    prompt: "{{ input }} {{ previous_outputs }}"
    params: {...}
```

## Critical Development Workflows

### Running & Testing
```bash
# Start Redis backend (required for memory)
orka-start

# Run any workflow
orka run examples/workflow.yml "input text"

# Run tests with coverage (75% minimum)
pytest --cov=orka --cov-report=term-missing --cov-fail-under=75.0

# Memory debugging TUI
orka memory watch
```

### Agent Development Workflow
1. Add agent class to `orka/agents/` 
2. Register in `AGENT_TYPES` dict in `orka/agents/__init__.py`
3. Add example YAML to `examples/`
4. Add unit tests in `tests/unit/agents/`
5. Update documentation in docstring

## Project-Specific Conventions

### Code Structure
- **Package imports**: Use relative imports within orka package: `from .base_agent import BaseAgent`
- **Type hints**: Required for all public methods, use `Dict[str, Any]` for agent outputs
- **Error handling**: Wrap in `OrkaError` or subclasses, never bare exceptions
- **Async patterns**: Prefer async/await, use `asyncio.timeout()` for timeouts

### YAML Configuration Patterns
- **Template rendering**: Use Jinja2 syntax: `{{ input }}`, `{{ previous_outputs.agent_id }}`
- **Agent chaining**: Reference previous agents: `{{ get_agent_response('agent_name') }}`
- **Conditional routing**: Use `router` agent with `routing_map` for branching logic
- **Parallel execution**: Use `fork` → `join` pattern with group names

### Memory System Usage
- **Read operations**: `type: memory, operation: read, prompt: "Find: {{ input }}"`
- **Write operations**: `type: memory, operation: write, prompt: "Store: {{ input }} -> {{ result }}"`
- **Semantic search**: Automatic via sentence_transformers embeddings
- **Memory decay**: Automatic cleanup of old/unimportant entries

## Integration Points

### External Dependencies
- **Redis**: Required backend, configure via env vars or `orka-start` command
- **LLM Providers**: OpenAI (API key), Ollama (local), LM Studio (local API)
- **Search**: DuckDuckGo (no key), Google (API key required)

### CLI Extension Points
- Add new commands in `orka/cli/` directory
- Register in `orka/orka_cli.py` subparsers
- Follow pattern: `parser.set_defaults(func=your_function)`

### Agent Registration
```python
# In orka/agents/__init__.py
from .my_agent import MyAgent

AGENT_TYPES = {
    "my-agent": MyAgent,
    # ... existing agents
}
```

## Key Files for Understanding

- `orka/orchestrator.py`: Main workflow engine with mixin architecture
- `orka/agents/__init__.py`: Agent registry and type definitions  
- `orka/memory/__init__.py`: Memory system with Redis integration
- `examples/`: Real-world workflow patterns (fork/join, routing, loops)
- `pyproject.toml`: Dependencies, dev tools, version (currently 0.9.3)

## Testing Patterns
- **Unit tests**: Mock Redis with `fakeredis`, test agent logic in isolation
- **Integration tests**: Use `conftest.py` fixtures for full orchestrator setup
- **Performance tests**: Located in `tests/performance/`
- **Example validation**: All YAML examples should have corresponding tests

## Common Gotchas
- Use conda environment handling. Activate enviroment `orka_pre_release`
- Always call `orka-start` before running workflows (Redis dependency)
- Agent outputs must be JSON-serializable for cross-agent communication
- Memory operations require RedisStack with search module enabled
- Local LLM agents need Ollama/LM Studio running with models pulled
- YAML syntax is strict - use proper indentation and quote special characters

## GraphScout Agent (NEW in v0.9.3)
Advanced intelligent routing agent that discovers optimal workflow paths:
- **Usage**: `type: graph-scout` in YAML config
- **Path discovery**: Automatic evaluation of available agents
- **Budget controls**: Token and latency limits with `cost_budget_tokens`, `latency_budget_ms`
- **Two-stage evaluation**: Fast local model for screening, validation model for final decisions