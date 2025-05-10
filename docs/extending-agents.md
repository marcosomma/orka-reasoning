[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# Creating Custom Agents in OrKa

## Modern Async Pattern (Recommended)

### 1. Subclass `BaseAgent`
```python
from orka.agents.base_agent import BaseAgent

class MySummarizer(BaseAgent):
    async def _run_impl(self, ctx):
        # Access input via ctx dictionary
        input_data = ctx.get("input")
        
        # Process data asynchronously
        result = await self.summarize(input_data)
        
        # Return directly (will be wrapped in Output object)
        return result
        
    async def summarize(self, text):
        # Your custom summarization logic
        return "Summary: " + text[:100] + "..."
```

### 2. Add to your YAML
```yaml
- id: summarize
  type: my_summarizer
  timeout: 30.0
  max_concurrency: 5
  queue: orka:summarize
```

## Legacy Sync Pattern (Backward Compatibility)

### 1. Subclass `LegacyBaseAgent`
```python
from orka.agents.agent_base import BaseAgent  # Uses the legacy compatibility layer

class MySummarizer(BaseAgent):
    def run(self, input_data):
        # Direct synchronous processing
        result = self.summarize(input_data)
        return result
        
    def summarize(self, text):
        # Your custom summarization logic
        return "Summary: " + text[:100] + "..."
```

### 2. Add to your YAML
```yaml
- id: summarize
  type: my_summarizer
  queue: orka:summarize
```

## 3. Register in `agent_loader`
Add your custom class to the agent registry or import it dynamically in your fork.

## Benefits of Modern Async Pattern

- **Concurrency Control**: Limit parallel executions with `max_concurrency`
- **Timeout Handling**: Set execution time limits with `timeout`
- **Structured Output**: Results are automatically wrapped in `Output` objects
- **Error Handling**: Exceptions are caught and formatted consistently
- **Resource Management**: Lifecycle hooks for initialization and cleanup

[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
