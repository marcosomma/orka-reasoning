# OrKa Streaming Runtime Guide

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
