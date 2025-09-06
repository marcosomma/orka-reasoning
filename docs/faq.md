[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# OrKa FAQ

## 🚀 V0.7.0 RedisStack Questions

### What's new in V0.7.0?
V0.7.0 introduces **100x faster vector search** with RedisStack HNSW indexing, unified architecture across all components, and professional CLI monitoring. All components now use RedisStack by default with intelligent fallback to basic Redis.

### Do I need to install RedisStack manually?
No! OrKa V0.7.0 automatically handles RedisStack setup through Docker. Just ensure Docker is running and OrKa will configure everything for you.

### What if I don't have Docker?
OrKa will gracefully fallback to basic Redis mode. While you won't get the 100x performance improvement, everything will still work. Set `ORKA_FORCE_BASIC_REDIS=true` to explicitly use basic Redis.

### How much faster is RedisStack really?
Vector search latency drops from 50-200ms to 0.5-5ms (100x faster). Memory throughput increases from 1,000/sec to 50,000/sec (50x higher). These improvements are most noticeable with large memory datasets.

### Will my existing workflows break?
No! V0.7.0 maintains 100% backward compatibility. Your existing YAML files, agent configurations, and workflows continue to work unchanged while automatically benefiting from RedisStack performance.

### How do I monitor RedisStack performance?
Use `python -m orka.orka_cli memory watch` for a real-time dashboard showing HNSW metrics, search latency, and memory statistics. The dashboard automatically detects your backend and shows relevant performance data.

---

## 🧠 General OrKa Questions

### How is this different from LangChain?
LangChain wraps LLM APIs with logic. OrKa defines cognitive structure in YAML + has full introspection with enterprise-grade memory that learns and forgets intelligently.

### Why YAML?
Declarative, composable, versionable. Think: Terraform for thought. YAML configurations are easier to understand, version control, and modify than complex Python code.

### What happens if an agent fails?
It logs the error. You can define `failover:` agents to take over. No silent failures. All errors are logged with full context for debugging.

### Can I run this with local LLMs?
Yes. Via LiteLLM proxy, run with Ollama, LM Studio, Claude, OpenRouter. V0.7.0 includes enhanced local LLM support with better error handling.

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
A: Install Ollama, pull a model (`ollama pull llama3.2`), then configure your agent with `provider: "ollama"` and `model_url: "http://localhost:11434/api/generate"`.

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

[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
