[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# Creating Custom Agents in OrKa

> **Last Updated:** 29 November 2025  
> **Status:** 🟢 Current  
> **Related:** [Agents](agents.md) | [Advanced Agents](agents-advanced.md) | [API Reference](api-reference.md) | [INDEX](index.md)

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
from orka.agents.base_agent import LegacyBaseAgent  # Updated import path

class MySummarizer(LegacyBaseAgent):
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

## Extending LLM Agents

You can also extend existing LLM agents to customize their behavior:

```python
from orka.agents.llm_agents import OpenAIAnswerBuilder

class CustomAnswerBuilder(OpenAIAnswerBuilder):
    def run(self, input_data):
        # Preprocess the input
        enhanced_input = self.enhance_input(input_data)
        
        # Call the parent implementation
        result = super().run(enhanced_input)
        
        # Post-process the result
        return self.format_output(result)
        
    def enhance_input(self, input_data):
        # Add context or modify input before sending to LLM
        return input_data
        
    def format_output(self, result):
        # Format or clean up the LLM output
        return result
```

## 3. Register in `agent_registry`
Add your custom class to the agent registry by registering it in your application code:

```python
from orka.registry import registry

# Register your custom agent
registry.register_agent("my_summarizer", MySummarizer)
```

## Benefits of Modern Async Pattern

- **Concurrency Control**: Limit parallel executions with `max_concurrency`
- **Timeout Handling**: Set execution time limits with `timeout`
- **Structured Output**: Results are automatically wrapped in `Output` objects
- **Error Handling**: Exceptions are caught and formatted consistently
- **Resource Management**: Lifecycle hooks for initialization and cleanup
---
← [Advanced Agents](agents-advanced.md) | [📚 INDEX](index.md) | [Memory System](MEMORY_SYSTEM_GUIDE.md) →
