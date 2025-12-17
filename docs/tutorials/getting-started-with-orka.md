# Getting Started with OrKa: Building Your First AI Workflow

This tutorial will guide you through creating your first OrKa workflow from scratch. We'll build a simple but powerful AI assistant that can answer questions, remember context, and learn from interactions.

## Prerequisites

Before starting, ensure you have:

1. Python 3.8 or higher installed
2. Docker installed and running
3. An OpenAI API key

## Step 1: Installation

First, let's install OrKa and its dependencies:

```bash
# Optional: Install
pip install orka-reasoning[all]

# Set your OpenAI API key
export OPENAI_API_KEY=your-key-here
```

## Step 2: Start OrKa

OrKa V0.7.0+ includes optional RedisStack setup for local development (performance varies by workload):

```bash
# Start OrKa with RedisStack (for development)
orka-start

# For deployment (same command):
orka-start
```

## Step 3: Create Your First Workflow

Create a file named `my-first-workflow.yml`:

```yaml
meta:
  version: "1.0"
  description: "Simple Q&A workflow with memory"

orchestrator:
  id: first-workflow
  strategy: sequential
  memory_config:
    decay:
      enabled: true
      default_short_term_hours: 2    # Recent conversations
      default_long_term_hours: 168   # Important information
  agents:
    - memory_search
    - answer_builder
    - memory_store

agents:
  # Search for relevant past conversations
  - id: memory_search
    type: memory-reader
    namespace: conversations
    params:
      limit: 5
      enable_context_search: true
      similarity_threshold: 0.8
    prompt: "Find relevant information about: {{ input }}"

  # Generate an answer using context
  - id: answer_builder
    type: openai-answer
    prompt: |
      Previous context: {{ previous_outputs.memory_search }}
      Current question: {{ input }}
      
      Generate a helpful answer that:
      1. Uses relevant context from memory if available
      2. Provides accurate and complete information
      3. Is clear and easy to understand

  # Store the interaction for future reference
  - id: memory_store
    type: memory-writer
    namespace: conversations
    params:
      vector: true  # Enable semantic search
      metadata:
        timestamp: "{{ now() }}"
    prompt: |
      Question: {{ input }}
      Answer: {{ previous_outputs.answer_builder }}
```

## Step 4: Run Your Workflow

Let's test the workflow with some questions:

```bash
# Ask a question
orka run my-first-workflow.yml "What is OrKa and how does it work?"

# Ask a follow-up question
orka run my-first-workflow.yml "Can you tell me more about its memory system?"

# Test memory recall
orka run my-first-workflow.yml "What were we just discussing?"
```

## Step 5: Monitor Performance

OrKa provides a professional dashboard to monitor your workflow:

```bash
# Watch memory performance in real-time
orka memory watch

# Check memory statistics
orka memory stats
```

## Understanding What's Happening

1. **Memory Search**: Each time you ask a question, OrKa searches its memory for relevant context using RedisStack's HNSW indexing (100x faster than basic vector search)

2. **Answer Generation**: The `answer_builder` agent uses both your question and any relevant context to generate a comprehensive response

3. **Memory Storage**: Each interaction is stored with vector embeddings for future semantic search

4. **Memory Decay**: Less important information naturally fades over time while crucial knowledge is preserved

## Next Steps

1. Try modifying the workflow:
   - Add a classifier agent to categorize questions
   - Implement web search for current information
   - Add fact-checking capabilities

2. Explore advanced features:
   - Fork/join for parallel processing
   - Loop nodes for iterative improvement
   - Cognitive society framework for multi-agent deliberation

3. Check out more examples in the `/examples` directory

## Common Issues and Solutions

1. **"FT.CREATE unknown command"**
   - Cause: Using basic Redis instead of RedisStack
   - Solution: Ensure Docker is running for automatic RedisStack setup

2. **Slow performance**
   - Check Docker is running: `docker ps`
   - Verify RedisStack: `redis-cli FT._LIST`

3. **Memory not persisting**
   - Verify RedisStack logs: `docker logs orka-redis`

## Getting Help

- 📚 [Full Documentation](https://orkacore.web.app/docs)
- 💬 [Community Discord](https://discord.gg/orka)
- 🐛 [GitHub Issues](https://github.com/marcosomma/orka-reasoning/issues)

## Next Tutorial

Continue learning with our [Advanced Workflows Tutorial](./advanced-workflows.md) where we'll explore:
- Complex agent interactions
- Custom agent development
- Production deployment strategies