[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)

# Getting Started with OrKa

## 1. Install
```bash
git clone https://github.com/marcosomma/orka-resoning.git
cd orka
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure `.env`
```
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-3.5-turbo
```

## 3. Run Demo
```bash
python test_run.py
```
This runs `orka.yaml` against a sample input.

## 4. Inspect Logs
```bash
redis-cli xrevrange orka:memory + - COUNT 5
```

## 5. Edit `orka.yaml`
- Change prompts
- Add agents
- Insert fallback paths
- Configure timeouts and concurrency limits

## 6. Create Custom Agent
```python
# Modern async pattern (recommended)
from orka.agents.base_agent import BaseAgent

class MyCustomAgent(BaseAgent):
    async def _run_impl(self, ctx):
        input_data = ctx.get("input")
        # Your custom processing logic
        return "processed result"
```

## 7. Add to Your YAML Config
```yaml
- id: my_agent
  type: my_custom_agent
  prompt: Process this input
  queue: orka:my_agent
  timeout: 30.0  # Optional: Set custom timeout
  max_concurrency: 5  # Optional: Set concurrency limit
```

## 8. Need Help?
GitHub issues or Discord: https://discord.gg/UthTN8Xu

---

## 🏗️ For Developers: Modular Architecture

Starting with v0.6.4, OrKa uses a modular architecture internally while maintaining full backward compatibility:

- **Memory Logger**: Split into `orka/memory_logger/` package with focused components
- **Orchestrator**: Decomposed into `orka/orchestrator/` package with specialized modules
- **Imports**: All existing `from orka.orchestrator import Orchestrator` patterns work unchanged
- **Extensibility**: New modular structure makes contributing and extending much easier

See [Architecture](./architecture.md) for detailed information about the internal module organization.

[📘 Getting Start](./getting-started.md) | [🤖 Advanced Agents](./agents-advanced.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md) | [🧪 Extending Agents](./extending-agents.md) | [📊 Observability](./observability.md) | [📜 YAML Schema](./orka.yaml-schema.md) | [📝 YAML Configuration Guide](./yaml-configuration-guide.md) | [⚙ Runtime Modes](./runtime-modes.md) | [🔐 Security](./security.md) | [❓ FAQ](./faq.md)
