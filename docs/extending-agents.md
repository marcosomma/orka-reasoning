[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# Creating Custom Agents in OrKa

## 1. Subclass `BaseAgent`
```python
from agent_base import BaseAgent

class MySummarizer(BaseAgent):
    def run(self, input_data):
        result = summarize(input_data)
        return {"summary": result}
```

## 2. Add to your YAML
```yaml
- id: summarize
  type: my_summarizer
  queue: orka:summarize
```

## 3. Register in `agent_loader`
Add your custom class to the agent registry or import it dynamically in your fork.

[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
