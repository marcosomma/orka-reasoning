# OrKa Cloud API - Quick Start Guide

Welcome! This guide shows you how to use the **OrKa Cloud API** to run sophisticated AI workflows without any infrastructure setup.

## What You'll Need

1. **OpenAI API Key** - Get one at https://platform.openai.com/api-keys
2. **Postman or curl** - For making API requests
3. **5 minutes** - That's it!

## The Cloud API

```
Base URL: https://orka-demo-647096874165.europe-west1.run.app
Endpoint: POST /api/run
```

### Rate Limits
- 5 requests per minute per IP
- Execution timeout: 5 minutes
- YAML config limit: 100KB

### Cost
- **Infrastructure**: Free for public demo (rate-limited)
- **OpenAI API**: You pay for tokens used (~$0.01-0.03 per workflow)

---

## Quick Test: Iterative Learning Demo

This workflow shows AI learning within a session:
1. Initial analysis
2. Store insights in memory
3. Search for related concepts
4. Deeper analysis with memory context
5. Final synthesis showing evolution

### Postman (Recommended)

**Step 1: Create New Request**
```
Method: POST
URL: https://orka-demo-647096874165.europe-west1.run.app/api/run
Headers:
  Content-Type: application/json
```

**Step 2: Copy This Body (Raw JSON)**

```json
{
  "input": "Explain how neural networks learn from data",
  "openai_api_key": "sk-YOUR_OPENAI_KEY_HERE",
  "yaml_config": "orchestrator:\n  id: iterative-learning\n  strategy: sequential\n  agents:\n    - initial_analyzer\n    - insight_storer\n    - knowledge_retriever\n    - deep_analyzer\n    - learning_recorder\n    - final_synthesizer\n\nagents:\n  - id: initial_analyzer\n    type: openai-answer\n    model: gpt-4o-mini\n    temperature: 0.7\n    prompt: |\n      Analyze this topic: {{ get_input() }}\n      \n      Provide:\n      1. Core concepts (3-5 key points)\n      2. Connections to related topics\n      3. Areas needing deeper exploration\n      \n      Format as structured insights.\n\n  - id: insight_storer\n    type: memory\n    operation: write\n    prompt: |\n      Initial analysis of: {{ get_input() }}\n      \n      Key insights:\n      {{ get_agent_response('initial_analyzer') }}\n\n  - id: knowledge_retriever\n    type: memory\n    operation: read\n    prompt: |\n      Search for concepts related to:\n      {{ get_agent_response('initial_analyzer') }}\n\n  - id: deep_analyzer\n    type: openai-answer\n    model: gpt-4o\n    temperature: 0.6\n    prompt: |\n      Original question: {{ get_input() }}\n      \n      Initial analysis:\n      {{ get_agent_response('initial_analyzer') }}\n      \n      Related knowledge from memory:\n      {{ previous_outputs.knowledge_retriever }}\n      \n      Now provide a DEEPER analysis that:\n      1. Builds on the initial insights\n      2. Connects to related concepts from memory\n      3. Addresses the areas flagged for deeper exploration\n      4. Adds new perspectives not covered initially\n      \n      Show how the analysis has evolved.\n\n  - id: learning_recorder\n    type: memory\n    operation: write\n    prompt: |\n      Deep analysis of: {{ get_input() }}\n      \n      Advanced insights:\n      {{ get_agent_response('deep_analyzer') }}\n      \n      Evolution from initial analysis:\n      - Built upon: {{ get_agent_response('initial_analyzer') | truncate(200) }}\n      - Connected with: {{ previous_outputs.knowledge_retriever | truncate(200) }}\n\n  - id: final_synthesizer\n    type: openai-answer\n    model: gpt-4o-mini\n    temperature: 0.4\n    prompt: |\n      Create a comprehensive final answer for: {{ get_input() }}\n      \n      Synthesize these learning stages:\n      \n      **Stage 1 - Initial Understanding:**\n      {{ get_agent_response('initial_analyzer') }}\n      \n      **Stage 2 - Memory-Enhanced Analysis:**\n      {{ get_agent_response('deep_analyzer') }}\n      \n      **Your Task:**\n      1. Show how understanding evolved through the stages\n      2. Present the final, most complete answer\n      3. Highlight what was learned through iteration\n      4. Demonstrate the value of this multi-pass approach\n      \n      Structure:\n      - Evolution Summary (how thinking progressed)\n      - Comprehensive Answer (synthesized knowledge)\n      - Learning Insights (what the iteration revealed)"
}
```

**Step 3: Replace API Key**

Replace `sk-YOUR_OPENAI_KEY_HERE` with your actual OpenAI API key.

**Step 4: Send!**

Hit Send and watch the workflow execute. Response time: ~15-30 seconds.

### curl (Command Line)

```bash
curl -X POST https://orka-demo-647096874165.europe-west1.run.app/api/run \
  -H "Content-Type: application/json" \
  -d @iterative_learning_request.json
```

Where `iterative_learning_request.json` contains the JSON body above.

---

## Understanding the Response

### Success Response

```json
{
  "run_id": "abc-123-def-456",
  "input": "Explain how neural networks learn from data",
  "execution_log": {
    "_metadata": {
      "version": "1.2.0",
      "generated_at": "2025-10-13T22:30:00+00:00"
    },
    "events": [
      {
        "agent_id": "initial_analyzer",
        "event_type": "OpenAIAnswerBuilder",
        "timestamp": "2025-10-13T22:30:05+00:00",
        "payload": {...}
      },
      // ... more agent events
    ],
    "cost_analysis": {
      "summary": {
        "total_tokens": 2847,
        "prompt_tokens": 1432,
        "completion_tokens": 1415,
        "total_cost_usd": 0.0043,
        "models_used": ["gpt-4o-mini", "gpt-4o"]
      }
    }
  },
  "log_file_url": "/api/logs/abc-123-def-456",
  "timestamp": "2025-10-13T22:30:32"
}
```

### Key Fields

- **run_id**: Unique identifier for this execution
- **execution_log.events**: Each agent's execution details
- **execution_log.blob_store**: Actual agent responses (large data)
- **cost_analysis**: Token usage and cost breakdown
- **log_file_url**: Download complete trace JSON

### Download Full Trace

```
GET https://orka-demo-647096874165.europe-west1.run.app/api/logs/abc-123-def-456
```

This gives you the complete execution trace with all agent outputs, memory operations, and metadata.

---

## Interpreting Results

### Finding Agent Responses

Agent responses are in the `blob_store` with references in `events`:

```json
{
  "events": [
    {
      "agent_id": "final_synthesizer",
      "payload": {
        "ref": "abc123...",  // Reference to blob_store
        "_type": "blob_reference"
      }
    }
  ],
  "blob_store": {
    "abc123...": {
      "response": "The actual AI response here...",
      "confidence": "0.95",
      "internal_reasoning": "...",
      "_metrics": {...}
    }
  }
}
```

To get the final answer:
1. Find the `final_synthesizer` event
2. Get the `payload.ref` value
3. Look up that ref in `blob_store`
4. The `response` field has the answer

### Cost Analysis

```json
"cost_analysis": {
  "summary": {
    "total_tokens": 2847,
    "total_cost_usd": 0.0043,
    "models_used": ["gpt-4o-mini", "gpt-4o"]
  },
  "by_model": {
    "gpt-4o-mini": {
      "tokens": 1847,
      "cost_usd": 0.0028
    },
    "gpt-4o": {
      "tokens": 1000,
      "cost_usd": 0.0015
    }
  }
}
```

Typical costs for this workflow:
- **Simple question**: $0.01-0.02
- **Complex topic**: $0.02-0.03
- **Very detailed**: $0.03-0.05

---

## Try Different Questions

### Scientific Concepts
```json
{"input": "Explain quantum entanglement"}
{"input": "How does CRISPR gene editing work?"}
{"input": "What causes ocean currents?"}
```

### Technical Topics
```json
{"input": "Explain distributed consensus in blockchain"}
{"input": "What are transformer models in AI?"}
{"input": "How does public key cryptography work?"}
```

### Complex Ideas
```json
{"input": "What is emergence in complex systems?"}
{"input": "How do market bubbles form and burst?"}
{"input": "What causes social movements to succeed?"}
```

Watch how each workflow:
1. Gets initial understanding
2. Stores insights
3. Searches memory
4. Goes deeper with context
5. Synthesizes the learning evolution

---

## Other Available Endpoints

### Health Check
```
GET /api/health

Response:
{
  "status": "healthy",
  "service": "orka-api",
  "version": "1.0.0"
}
```

### Service Status
```
GET /api/status

Response:
{
  "service": "orka-api",
  "status": "operational",
  "dependencies": {
    "redis": {"status": "connected"}
  },
  "rate_limiting": {
    "enabled": true,
    "limit": "5/minute"
  }
}
```

---

## Common Errors

### Missing API Key
```json
{
  "detail": "Missing 'openai_api_key' in request. Get your key at: https://platform.openai.com/api-keys"
}
```
**Fix**: Add `openai_api_key` field to request body.

### Invalid API Key Format
```json
{
  "detail": "Invalid 'openai_api_key' format. Must start with 'sk-'"
}
```
**Fix**: Ensure your key starts with `sk-` (no "Bearer" prefix).

### Rate Limited
```json
{
  "detail": "Rate limit exceeded. Please try again in 60 seconds."
}
```
**Fix**: Wait 60 seconds before next request.

### YAML Too Large
```json
{
  "detail": "YAML config too large (max 100KB)"
}
```
**Fix**: Simplify your workflow or split into multiple smaller workflows.

---

## Cost Expectations

### Infrastructure (Cloud Run)
- **You don't pay** - This is a public demo
- If you deploy your own: ~$42/month at 50% uptime

### OpenAI API (You Pay)
- **gpt-4o-mini**: $0.15 per 1M input tokens, $0.60 per 1M output
- **gpt-4o**: $2.50 per 1M input tokens, $10.00 per 1M output

### Typical Workflow Costs
- **Iterative Learning Demo**: $0.01-0.03 per run
- **Simple Q&A**: $0.001-0.005 per run
- **Complex multi-agent**: $0.05-0.10 per run

**Daily testing budget**: $1-2 for 50-100 test runs

---

## Next Steps

### 1. Explore More Examples

Check the `/examples` directory in the repo:
- `multi_perspective_chatbot.yml` - Different viewpoints
- `memory_presets_showcase.yml` - Advanced memory features
- `cognitive_loop_scoring_example.yml` - Iterative improvement

### 2. Create Custom Workflows

Study the YAML structure and create your own:
- Define specialized agents
- Connect with template variables
- Add memory operations
- Test via Cloud API

### 3. Deploy Your Own Instance

Follow `PRIVATE/OPENAI_DEPLOYMENT.md`:
- Clone the repo
- Deploy to Google Cloud Run
- Custom domain & scaling
- Full control over infrastructure

---

## Support & Resources

**GitHub**: https://github.com/marcosomma/orka-reasoning

**Documentation**: 
- `PRIVATE/OPENAI_DEPLOYMENT.md` - Deployment guide
- `docs/` - Comprehensive documentation
- `examples/` - Working examples

**Issues**: https://github.com/marcosomma/orka-reasoning/issues

**Questions**: Open an issue or contribute to the project

---

## Summary

**To use OrKa Cloud API:**

1. Get OpenAI API key
2. Copy Postman request from above
3. Replace API key
4. Send request
5. Explore results

**That's it!** No setup, no installation, no infrastructure. Just orchestrate AI agents and watch them work together.

**Cost**: ~$0.01-0.03 per workflow run (you pay OpenAI directly)

**Ready to try?** Copy the Postman example and test it now! 🚀


