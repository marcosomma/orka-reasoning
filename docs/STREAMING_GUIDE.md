# OrKa Streaming Runtime Guide

> ⚠️ **BETA RELEASE** - The streaming runtime is currently in beta. While functional, it has known limitations and is under active development. See "Known Limitations" section below.

The streaming regime is transport-agnostic. It works for text-only chat and voice-assisted chat. Voice is optional.

Key concepts:
- Invariants vs Mutable: invariants (identity, voice, refusal, tool_permissions, safety_policies) are immutable at runtime. Voice is optional; omit or set empty to run text-only.
- Event bus: ingress/egress/state/alerts channels per session.
- PromptComposer: deterministic sections with per-section and total token budgets.
- Refresh: debounce and rate limits produce stable updates; critical triggers can bypass debounce.

Enabling streaming:
- Set environment variable ORKA_ENABLE_STREAMING=1
- Run orchestrator only: `orka streaming run examples/live_assist.yaml --session demo1`
- Interactive chat: `orka streaming chat examples/live_assist.yaml --session demo1`

YAML keys:
- orchestrator.mode: "streaming"
- orchestrator.executor_invariants: optional `voice` field
- orchestrator.prompt_budgets: { total_tokens, sections: { ... } }
- orchestrator.refresh: { cadence_seconds, debounce_ms, max_refresh_per_min }

Models (executor and satellites):
- In the example, the executor includes `provider` and `model` fields.
- In this initial skeleton, these are informational; token streaming from real models will be integrated in follow-ups.

## Known Limitations (Beta)

### Context Loss Across Turns

**Issue**: The satellite agents (summarizer, intent, compliance) currently **overwrite** state sections on each execution instead of accumulating context. This causes loss of conversational memory across multiple turns.

**Example Problem**:
```
User: "My favorite color is green"
Assistant: "Thanks for sharing!" ✅

User: "What are AI laws in Europe?"
Assistant: [provides detailed response] ✅

User: "What is my favorite color?"
Assistant: "I don't have that information" ❌
```

**Root Cause**: When satellites process a new user message, they generate fresh summaries/intent based only on the current turn. The `apply_patch()` operation replaces the entire `summary`, `intent`, and `constraints` sections, losing all prior conversational context.

**Current Behavior**:
- Satellites receive only: `intent or summary` from current state
- They don't receive: conversation history, previous summaries, or accumulated context
- Each satellite output completely replaces its target section

**Workarounds**:
1. Keep conversations focused on single topics
2. Re-state important context in follow-up questions
3. Use the rolling history (limited to recent turns only)

**Planned Fix**: Future versions will implement:
- Context-aware satellite prompts that include conversation history
- Accumulative state updates that merge rather than replace
- Persistent memory integration for long-term context retention

### Other Limitations
- Token budgets are enforced but may truncate important context
- Satellite failures are logged but don't halt execution
- No persistent session storage between restarts
---
← [Json Inputs Guide](JSON_INPUTS.md) | [📚 INDEX](index.md) | [Agents](agents.md) →
