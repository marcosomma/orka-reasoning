# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

OrKa is an unmaintained personal research playground (see the maintainer note in `README.md`). It is **not** production software, but it values stability: changes should preserve backward compatibility, keep agent-level logging/tracing intact, and come with a test or log trace. PRs that are "random LLM wrappers" or "black-box logic with no traceable reasoning" are explicitly out of scope.

## What OrKa is

A local-first, YAML-driven engine for composing AI agent workflows. You declare an `orchestrator` (strategy + ordered agent ids) and a list of `agents`/nodes in YAML, then run it with `orka run workflow.yml "input"`. Execution is async, traced, and backed by a RedisStack memory store with HNSW vector search and time-based decay.

## Common commands

```bash
# Install for development
pip install -e ".[dev]"          # or ".[all]" for prod+ml+docs extras

# Run a workflow
orka run workflow.yml "input text" [--verbose]
orka system status               # check services
orka memory watch                # TUI memory dashboard
orka-start                       # boot RedisStack + backend API (8000) + UI (8080)

# Tests (config in pytest.ini / pyproject.toml — coverage gate is 80%)
pytest                           # full unit+integration suite with coverage
pytest tests/unit/path/to/test_x.py::test_name   # single test
pytest -m "not slow"             # skip slow tests
pytest -m unit                   # markers: unit, integration, slow, performance, redis, llm, asyncio

# Lint / typecheck (must pass CI)
flake8 orka --count --select=E9,F63,F7,F82 --show-source --statistics   # critical errors (CI gate)
flake8 orka                      # full lint (max-line-length 120, max-complexity 10, google docstrings)
mypy orka                        # config in mypy.ini (permissive; many modules excluded)
black .                          # line-length 120, py311
```

Requires Python >= 3.11. Integration tests need real services (Redis/LLM) and run locally only; unit tests mock externals with `fakeredis`.

## Architecture

### Orchestrator (composed via multiple inheritance)
`orka/orchestrator.py` defines the public `Orchestrator(config_path)` class, but it is **only a composition of mixins** from `orka/orchestrator/` — understanding the system means reading the mixins, not the thin top-level file:
- `base.OrchestratorBase` — config loading, memory backend setup
- `agent_factory.AgentFactory` — the `AGENT_TYPES` registry (string type name → class) and `_init_agents()`
- `execution_engine.ExecutionEngine` — the main async run loop and agent coordination (provides `run()`)
- `simplified_prompt_rendering.SimplifiedPromptRenderer` — Jinja2 prompt rendering
- `error_handling.ErrorHandler`, `metrics.MetricsCollector`

MRO matters: `Orchestrator(ExecutionEngine, OrchestratorBase, AgentFactory, ErrorHandler, MetricsCollector)`. Each mixin's `__init__` is called explicitly in `Orchestrator.__init__`.

### Agents vs Nodes
The distinction blurs in the registry but conceptually: **agents** (`orka/agents/`) produce reasoning output (LLM answer builders, binary/classification, validation, RAG, local LLM via `litellm`/Ollama/LM Studio). **Nodes** (`orka/nodes/`) are control-flow primitives: `router` (conditional branching), `fork`/`join` (parallel execution + sync via `fork_group_manager.py`), `loop` (iterative refinement, see the `loop/` subpackage), `failover`, `memory_reader`/`memory_writer`, and `graph_scout_agent` (beta dynamic path discovery).

Both register through `AGENT_TYPES` in `agent_factory.py`. The string `"special_handler"` marks types instantiated specially in `_init_agents` (e.g. `memory`, `brain`, `path_executor` — the last is lazy-loaded to avoid circular imports). Third-party agents/nodes can also register via the `orka.agents` / `orka.nodes` entry points in `pyproject.toml`.

### Prompts and the template layer
Agent `prompt:` fields are Jinja2 templates rendered against workflow context. Custom helpers live in `orka/orchestrator/template_helpers.py` and are the canonical way to read prior state from a prompt: `get_input()`, `get_agent_response('agent_id')`, `safe_get_response(...)`, `previous_outputs.<agent_id>`. Prefer these helpers over raw dict access — they fail safe.

### Memory system
`memory_logger.py` / `create_memory_logger("redisstack"|"redis")` is the factory. The RedisStack backend (`orka/memory/redisstack_logger.py`) does HNSW vector search + hybrid metadata filtering with namespace isolation. Memory config is driven by **presets** (`orka/memory/presets.py`) — 6 Minsky-inspired cognitive types (`sensory`, `working`, `episodic`, `semantic`, `procedural`, `meta`) that bundle decay/TTL/importance/vector settings. In YAML, `memory_preset: "semantic"` replaces what used to be ~15 lines of decay config. The unified `type: memory` agent with `config.operation: read|write` handles both directions.

### Brain (learning/transfer engine)
`orka/brain/` is a separate, more experimental subsystem: a learn → recall → execute → feedback loop built on `SkillGraph`, `ContextAnalyzer`, and `SkillTransferEngine`. It abstracts reusable skills from successful executions and adapts them across domains. Wired in as the `brain` agent type.

### CLI and server
`orka/orka_cli.py` (entry `orka`) re-exports `orka/cli/` (parser, core, memory + orchestrator subcommands). `orka/server.py` is the FastAPI backend; `orka/orka_start.py` (entry `orka-start`) boots the full stack. `orka/tui/` is the Textual-based memory dashboard.

## Conventions

- Every source file carries the Apache-2.0 OrKa attribution header — preserve it on new files.
- Async-first: agents implement `async def _run_impl(self, ctx)`; use `await` throughout the execution path.
- Commits follow conventional-commit prefixes (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Runnable workflow examples live in `examples/*.yml` (30+); the `examples/benchmark*` dirs hold benchmark configs. Use these as references for valid YAML shapes.
- Extensive docs in `docs/` — `YAML_CONFIGURATION.md`, `MEMORY_SYSTEM_GUIDE.md`, `AGENT_NODE_TOOL_INDEX.md`, `GRAPH_SCOUT_AGENT.md`, `TESTING.md` are the most useful entry points.
