[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# OrKa FAQ

> **Last Updated:** 29 November 2025  
> **Status:** 🟢 Current  
> **Related:** [Troubleshooting](troubleshooting.md) | [Debugging](DEBUGGING.md) | [Getting Started](getting-started.md) | [INDEX](index.md)

## General Questions

### What is OrKa?
OrKa is a tool for creating AI workflows using YAML configuration files instead of writing Python code. You define agents (like memory, LLMs, web search) and how they connect, then OrKa executes the workflow.

### How is OrKa different from LangChain?
LangChain requires writing Python code to orchestrate AI components. OrKa uses YAML files to define workflows declaratively. OrKa also includes built-in memory management and better support for local LLMs.

### How do I choose between local and cloud LLMs?
- **Local LLMs** (Ollama, LM Studio): Better for privacy, no API costs, but slower and less capable
- **Cloud LLMs** (OpenAI, Anthropic): Faster and more capable, but require API keys and cost money

### What's the memory system for?
OrKa's memory system stores and retrieves information from previous conversations or workflows. It can search semantically (finding related content, not just exact matches) and automatically forgets old information to save space.

## Installation and Setup

### Do I need Docker?
**Short answer:** Docker is recommended but not required.

**How it works:**
When you run `orka-start`, OrKa automatically tries multiple options:
1. **Native RedisStack** (if installed locally on your system)
2. **Docker RedisStack** (if Docker is available)
3. **Installation instructions** (if neither is available)

**Installation options:**
- **With Docker** (easiest): Just have Docker running, `orka-start` handles the rest
- **Without Docker**: Install RedisStack natively:
  - Windows: Download from https://redis.io/download
  - macOS: `brew install redis-stack`
  - Ubuntu: `sudo apt install redis-stack-server`

OrKa will automatically detect and use whichever is available.

### How do I set up local LLMs?
1. Install Ollama from https://ollama.ai
2. Pull a model: `ollama pull llama3.2`
3. Use `provider: lm_studio` in your YAML configuration

### What if I get Redis connection errors?
**Check if RedisStack is running:**
```bash
# For Docker-based setup
docker ps | grep redis

# For native setup
redis-cli -p 6380 ping
```

**Start RedisStack:**
```bash
# Option 1: Use orka-start (tries native first, then Docker)
orka-start

# Option 2: Docker manually
docker run -d -p 6380:6380 --name orka-redis redis/redis-stack:latest

# Option 3: Native RedisStack
redis-stack-server --port 6380
```

**Verify vector search capabilities:**
```bash
redis-cli -p 6380 FT._LIST
# Should show OrKa memory indexes if working correctly
```

## Configuration and Usage

### Why use YAML instead of Python code?
YAML is easier to read, modify, and version control. You can change workflows without writing code, and non-programmers can understand and modify configurations.

### What happens if an agent fails?
OrKa logs the error with full context. You can define fallback agents using `failover:` to handle failures gracefully.

### Can I run agents in parallel?
Yes, use `fork` to split execution into parallel branches, then `join` to combine results.

### What about security?
Redis/RedisStack can be encrypted. PII filters recommended. OrKa UI supports authentication, and all memory operations can be configured with encryption at rest.

### Should I use sync or async agents?
Use the modern async pattern for new development. The legacy sync pattern is provided for backward compatibility with existing code. The async pattern offers better concurrency control, timeout handling, and resource management.

### Do my existing agents still work?
Yes. OrKa maintains backward compatibility with existing agents through the `LegacyBaseAgent` compatibility layer. Your existing code will continue to work without modification.

### How do I migrate from sync to async agents?
Convert your `run(input_data)` method to an async `_run_impl(ctx)` method. Access input via `ctx.get("input")` and return results directly. See [Extending Agents](./extending-agents.md) for examples.

### What's the difference between "true"/"false" strings and boolean values?
Modern agents use string values ("true"/"false") for binary decisions to maintain consistency across different agent implementations. This allows for more reliable routing and decision logic.

### What changed in the modular architecture (v0.6.4+)?
OrKa's core components were refactored from monolithic files into focused modules for better maintainability. The memory logger and orchestrator are now split into specialized components, but all existing imports and APIs remain unchanged. This means your existing code continues to work while new development benefits from the improved internal structure.

### Do I need to change my imports after the modular refactoring?
No. All existing imports like `from orka.orchestrator import Orchestrator` and `from orka.memory_logger import create_memory_logger` continue to work exactly as before. The refactoring was designed with 100% backward compatibility.

### How does the memory decay system work (v0.6.5+)?
OrKa now automatically manages memory with intelligent decay. Memories are classified as short-term or long-term based on importance and event type. You can configure retention periods globally or per-agent. Use `orka memory watch` to monitor memory in real-time and `orka memory stats` to see current usage. Memory decay is enabled by default but fully configurable.

### Can I control memory retention for specific agents?
Yes. Each agent can have its own `decay:` configuration that overrides global settings. You can force memories to be short-term or long-term using `default_long_term: true/false`, set custom retention periods, and define importance rules. This allows fine-grained control over what gets remembered and for how long.

## 💾 Memory System

**Q: How does memory decay work?**
A: OrKa automatically manages memory lifecycle using configurable decay rules. Short-term memories expire quickly (default 2 hours), while long-term memories persist longer (default 1 week). The system uses importance factors to boost critical information and reduce routine queries.

**Q: Can I disable memory decay?**
A: Yes, set `decay.enabled: false` in your orchestrator configuration, or use `default_long_term: true` for specific agents to force long-term storage.

**Q: How accurate is context-aware search?**
A: The hybrid scoring algorithm combines semantic similarity (40%), keyword matching (30%), context similarity (configurable), and temporal decay (configurable) for highly relevant results.

**Q: What's the difference between vector and non-vector memory?**
A: Vector-enabled memory supports semantic search using embeddings, while non-vector memory uses keyword-based search. Vector search is more intelligent but requires more resources.

## 🏠 Local LLM Integration

**Q: Which local LLM providers are supported?**
A: OrKa supports Ollama, LM Studio, and any OpenAI-compatible API endpoint. Popular models include Llama 3.2, Mistral, DeepSeek, and Qwen.

**Q: How do I set up Ollama with OrKa?**
A: Install Ollama, pull a model (`ollama pull llama3.2`), then configure your agent with `provider: "ollama"` and `model_url: "http://localhost:1234"`.

**Q: Can I mix local and cloud LLMs in one workflow?**
A: Absolutely! You can use local LLMs for privacy-sensitive tasks and cloud LLMs for complex reasoning in the same workflow.

**Q: What are the performance differences?**
A: Local LLMs provide privacy and cost benefits but may be slower and less capable than cloud models. Use failover patterns to combine both approaches.

## 🔧 Advanced Configuration

**Q: How do I handle agent failures gracefully?**
A: Use `failover` nodes to define backup strategies. If the primary agent fails, OrKa automatically tries the next agent in the chain.

**Q: Can I run agents in parallel?**
A: Yes, use `fork` nodes to split execution into parallel branches, then `join` nodes to aggregate results.

**Q: How do I debug complex workflows?**
A: Enable verbose logging (`--verbose`), use the OrKa UI for visualization, and check Redis streams for detailed execution traces.
---
← [Troubleshooting](troubleshooting.md) | [📚 INDEX](index.md) | [Json Inputs Guide](JSON_INPUTS.md) →
