[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md)

# Getting Started with OrKa ***(Patent Pending)***

Welcome to **OrKa** — the Orchestrator Kit for Agentic Reasoning. This guide will help you set up the project, understand its basic components, and run your first orchestration pipeline.

---

## 📦 Prerequisites

Make sure you have the following installed:

- Python 3.10+
- Redis (running on localhost:6379)
- pip

You’ll also need API keys if you’re using OpenAI or Google CSE.

---

## 🚀 Installation

1. **Clone the repo:**

```bash
git clone https://github.com/marcosomma/orka.git
cd orka
```

2. **Set up your environment:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. **Set environment variables:**

Create a `.env` file in the root with the following (if applicable):

```bash
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-3.5-turbo
GOOGLE_API_KEY=your-google-api-key
GOOGLE_CSE_ID=your-cse-id
```

---

## ⚙️ Project Structure

```
orka/
├── agents/             # All agent logic (binary, classification, search, etc.)
├── orchestrator.py     # Core orchestration engine
├── memory_logger.py    # Redis-based logging
├── agent_base.py       # Abstract Agent class
├── loader.py           # YAML loader and validator
test_run.py             # Runner script for testing
orka.yaml               # Main YAML configuration file
```

---

## 🧠 Run a Demo

Try the default orchestration:

```bash
python test_run.py
```

Make sure your Redis server is running, and `orka.yaml` is properly configured.

---

## 📝 Customize Your Flow

Edit `orka.yaml` to define:
- Agents
- Their types and prompts
- Flow strategy (decision-tree, conditional)
- Routing logic

---

## 🧪 Next Steps

- Check out [agents.md](agents.md) for all available agent types.
- Use `RouterAgent` to add conditional logic.
- Build your own agent by subclassing `BaseAgent`.

---

## 🙌 Need Help?

Open an issue on GitHub or join the discussion [here](https://github.com/marcosomma/orka/issues).

[📘 Getting Start](./getting-started.md) | [🤖 Agent Types](./agents.md) | [🔍 Architecture](./architecture.md) | [🧠 Idea](./index.md)
