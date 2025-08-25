# OrKa Quickstart Guide

Get OrKa up and running in minutes with our one-click Docker setup. This guide will help you start building powerful AI workflows with 100x faster vector search.

## One-Click Setup

Copy and paste this command to get started:

```bash
# Download and run the OrKa quickstart script
curl -sSL https://orkacore.com/quickstart.sh | bash

# Or if you prefer wget:
wget -qO- https://orkacore.com/quickstart.sh | bash
```

This script will:
1. Install Docker if not present
2. Pull required images (RedisStack, OrKa)
3. Set up environment variables
4. Start OrKa with optimal configuration

## Manual Setup (Alternative)

If you prefer to set things up manually:

### 1. Prerequisites

```bash
# Install Python packages
pip install orka-reasoning[all]

# Set OpenAI API key
export OPENAI_API_KEY=your-key-here
```

### 2. Start OrKa

Choose your deployment mode:

```bash
# Development (RedisStack only)
orka-start

# Production (RedisStack + Kafka)
orka-kafka

# Optional: Start UI
docker run -d -p 80:80 marcosomma/orka-ui:latest
```

## Verify Installation

```bash
# Check OrKa status
orka system status

# Monitor memory performance
orka memory watch

# You should see:
┌─────────────────────────────────────────────────────────────┐
│ OrKa Memory Dashboard - 14:23:45 | Backend: redisstack     │
├─────────────────────────────────────────────────────────────┤
│ 🔧 Backend: redisstack (HNSW)  ⚡ Decay: ✅ Enabled        │
│ 📊 Memories: 1,247            📝 Active: 1,224             │
│ 🚀 HNSW Performance: 1,203     Avg: 2.1ms | Hybrid: 856   │
│ 🧠 Memory Types: Short: 423    💾 Long: 801 | 🔥 Recent   │
└─────────────────────────────────────────────────────────────┘
```

## Your First Workflow

Create `quickstart.yml`:

```yaml
orchestrator:
  id: quickstart
  strategy: sequential
  agents: [memory_search, answer_builder, memory_store]

agents:
  - id: memory_search
    type: memory-reader
    namespace: knowledge
    params:
      limit: 5
      enable_context_search: true
    prompt: "Find relevant info about: {{ input }}"

  - id: answer_builder
    type: openai-answer
    prompt: |
      Context: {{ previous_outputs.memory_search }}
      Question: {{ input }}
      Generate a comprehensive answer.

  - id: memory_store
    type: memory-writer
    namespace: knowledge
    params:
      vector: true
    prompt: |
      Q: {{ input }}
      A: {{ previous_outputs.answer_builder }}
```

Run your workflow:

```bash
# Ask a question
orka run quickstart.yml "What is OrKa?"

# Ask a follow-up
orka run quickstart.yml "How does its memory system work?"
```

## Docker Compose Setup

For more control, use our Docker Compose configuration:

```yaml
# docker-compose.yml
version: '3.8'
services:
  redis-stack:
    image: redis/redis-stack:latest
    ports:
      - "6380:6380"
    volumes:
      - redis_data:/data
    environment:
      - REDIS_ARGS=--save 60 1000

  orka:
    image: marcosomma/orka:latest
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis-stack:6380/0
      - ORKA_MEMORY_BACKEND=redisstack
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      - redis-stack

  orka-ui:
    image: marcosomma/orka-ui:latest
    ports:
      - "80:80"
    depends_on:
      - orka

volumes:
  redis_data:
```

Start with:

```bash
docker-compose up -d
```

## Next Steps

1. Try our [example workflows](../examples/)
2. Read the [tutorials](../tutorials/)
3. Join our [Discord community](https://discord.gg/orka)

## Troubleshooting

Common issues and solutions:

1. **"FT.CREATE unknown command"**
   - Cause: Using basic Redis instead of RedisStack
   - Solution: Ensure Docker is running

2. **Slow performance**
   - Check Docker status: `docker ps`
   - Verify RedisStack: `redis-cli FT._LIST`

3. **Memory not persisting**
   - Check RedisStack logs: `docker logs orka-redis`

## Getting Help

- 📚 [Full Documentation](https://orkacore.web.app/docs)
- 💬 [Discord Support](https://discord.gg/orka)
- 🐛 [GitHub Issues](https://github.com/marcosomma/orka-reasoning/issues)

## Security Note

The one-click installer script is served over HTTPS and is digitally signed. You can verify the signature with:

```bash
curl -sSL https://orkacore.com/quickstart.sh.asc | gpg --verify
```