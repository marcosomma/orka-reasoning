# Support Triage System

Ticket triage system with auditability, replay, and safety under tool use.

## Overview

This system treats ticket triage as a **deterministic state machine that happens to use LLM nodes**. The primary artifact is a JSON envelope that serves as a snapshot of what is known plus pointers to fetch what is missing.

### Key Differentiators

- **Auditability**: Every decision, tool call, and state change is recorded with evidence
- **Replay**: Re-run any case from the same input envelope with deterministic outputs
- **Safety**: Trust boundaries prevent prompt injection; permissions are enforced at orchestrator level

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INPUT ENVELOPE                               │
│  • Trust boundaries (untrusted customer text, trusted context)      │
│  • Provenance and freshness metadata                                │
│  • Permission constraints                                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     VALIDATION PHASE                                 │
│  ┌──────────────┐  ┌─────────────┐  ┌─────────────────┐            │
│  │ Schema       │─▶│ PII         │─▶│ Trust Boundary  │            │
│  │ Validation   │  │ Redaction   │  │ Check           │            │
│  └──────────────┘  └─────────────┘  └─────────────────┘            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     CLASSIFICATION PHASE                             │
│  ┌──────────────┐  ┌─────────────┐                                  │
│  │ Intent       │─▶│ Risk        │                                  │
│  │ Classification│  │ Assessment  │                                  │
│  └──────────────┘  └─────────────┘                                  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     EVIDENCE GATHERING                               │
│  ┌──────────────┐      ┌─────────────┐      ┌─────────────┐        │
│  │ Retrieval    │─────▶│ Fork:       │─────▶│ Join        │        │
│  │ Planning     │      │ KB + Billing│      │ Results     │        │
│  └──────────────┘      └─────────────┘      └─────────────┘        │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     SYNTHESIS & DRAFT                                │
│  ┌──────────────┐  ┌─────────────┐  ┌─────────────────┐            │
│  │ Synthesize   │─▶│ Draft       │─▶│ Decision        │            │
│  │ Evidence     │  │ Reply       │  │ Recording       │            │
│  └──────────────┘  └─────────────┘  └─────────────────┘            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     VERIFICATION & GATE                              │
│  ┌──────────────┐  ┌─────────────┐  ┌─────────────────┐            │
│  │ Output       │─▶│ Human       │─▶│ Execute         │            │
│  │ Verification │  │ Gate        │  │ Actions         │            │
│  └──────────────┘  └─────────────┘  └─────────────────┘            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         OUTPUT ENVELOPE                              │
│  • Classification and risk assessment                                │
│  • Action plan with citations                                        │
│  • Draft reply                                                       │
│  • Trace events for replay                                           │
└─────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Activate the Feature

The support triage system uses custom agents that need to be registered. You can do this in three ways:

**Option A: Environment Variable (Recommended)**
```bash
# Set ORKA_FEATURES to auto-load agents
export ORKA_FEATURES=support_triage  # Linux/Mac
$env:ORKA_FEATURES="support_triage"  # Windows PowerShell
```

**Option B: Programmatic Registration**
```python
from orka.support_triage import register_agents
register_agents()

# Then use Orchestrator normally
from orka.orchestrator import Orchestrator
orchestrator = Orchestrator("examples/support_triage/support_ticket_triage.yml")
```

**Option C: Entry Points (for packages)**
```toml
# In your pyproject.toml
[project.entry-points."orka.features"]
support_triage = "orka.support_triage:register_agents"
```

### 2. Run the Triage Workflow

```bash
# Start Redis (required for memory)
orka-start

# Run with example input (note: --json-input flag for JSON files)
ORKA_FEATURES=support_triage orka --json-input run \
  examples/support_triage/support_ticket_triage.yml \
  examples/support_triage/inputs/refund_with_injection.json
```

### 3. Run Self-Assessment

```bash
ORKA_FEATURES=support_triage orka run examples/support_triage/self_assessment.yml
```

## Input Envelope Schema

The canonical object you store for replay:

```json
{
  "schema_version": "1.0",
  "request_id": "req_2026_01_06_0001",
  "tenant": {
    "id": "acme_eu",
    "environment": "prod"
  },
  "task": {
    "type": "support_ticket",
    "goal": "draft_reply_and_plan",
    "locale": "en-GB",
    "priority_hint": "normal"
  },
  "case": {
    "ticket_id": "ZD-12345",
    "channel": "email",
    "subject": "Refund request",
    "customer_message": {
      "text": "Customer text here...",
      "source": "zendesk",
      "trust": "untrusted",  // ALWAYS untrusted
      "received_at": "2026-01-06T10:12:00Z"
    }
  },
  "context": {
    "customer_profile": { ... },  // trusted CRM data
    "entitlements": { ... }       // trusted billing data
  },
  "constraints": {
    "policy_id": "support_policy_v3",
    "privacy": { "pii_redacted": true },
    "token_budgets": { "max_input_tokens": 8000 }
  },
  "permissions": {
    "allowed_actions": ["draft_reply", "escalate"],
    "blocked_actions": ["issue_refund", "close_ticket"]
  }
}
```

## Trust Boundary Rules

**CRITICAL**: These rules prevent prompt injection attacks.

1. **Customer messages are ALWAYS untrusted** - The `trust` field is enforced by schema validation
2. **Untrusted content is NEVER instruction** - It's data to analyze, not commands to follow
3. **All tool permissions come from policy** - Not from ticket text
4. **Blocked actions are enforced at orchestrator level** - LLM cannot override

## Agent Types

### Deterministic Agents (No LLM)

| Agent | Type | Purpose |
|-------|------|---------|
| `EnvelopeValidatorAgent` | `envelope_validator` | Schema validation, size checks, freshness |
| `RedactionAgent` | `redaction` | PII redaction before LLM processing |
| `TrustBoundaryAgent` | `trust_boundary` | Injection detection, trust enforcement |
| `PermissionGateAgent` | `permission_gate` | Action permission validation |
| `OutputVerificationAgent` | `output_verification` | Output schema and citation validation |
| `DecisionRecorderAgent` | `decision_recorder` | Creates audit trail with evidence |

### LLM Agents

Standard OrKa LLM agents are used for:
- Intent classification
- Risk assessment
- Retrieval planning
- Synthesis
- Reply drafting

## Trace Events

Every node emits trace events for observability:

```json
{
  "trace_event": {
    "event_id": "ev_0009",
    "request_id": "req_2026_01_06_0001",
    "node_id": "verify_output",
    "event_type": "node_completed",
    "status": "ok",
    "timing_ms": 842,
    "inputs_hash": "sha256:...",
    "outputs_hash": "sha256:...",
    "writes": [{ "path": "output", "op": "replace" }]
  }
}
```

## Evaluation Framework

### Running Evaluations

```python
from orka.support_triage.evaluation import EvalRunner, EvalReporter

runner = EvalRunner(workflow_runner=my_runner)
report = runner.run_suite(cases, envelopes)

reporter = EvalReporter()
print(reporter.to_markdown(report))

# CI exit code
sys.exit(reporter.exit_code(report))
```

### Golden Case Testing

```python
from orka.support_triage.evaluation import GoldenCaseRegistry

registry = GoldenCaseRegistry("./golden_cases")

# Register known-good output
registry.register_golden(
    eval_id="ec_refund",
    envelope=envelope,
    output=output,
    output_hash=compute_hash(output.model_dump())
)

# Check for regressions
regression = registry.check_regression(eval_id, new_output, new_hash)
if regression:
    print(f"REGRESSION: {regression['diff']}")
```

### Invariant Checking

```python
from orka.support_triage.evaluation import InvariantChecker

checker = InvariantChecker()
passed = checker.check_all(envelope, output, trace_events, expected)

for violation in checker.violations:
    print(f"{violation['invariant']}: {violation['message']}")
```

## Success Metrics

| Metric | Description |
|--------|-------------|
| **Time to First Response** | How quickly a draft is generated |
| **Deflection Rate** | % of low-risk cases auto-resolved |
| **Escalation Rate** | % requiring human intervention |
| **Policy Compliance Rate** | % adhering to permission constraints |
| **Replayability** | Same input → same tool plan and outputs |

## Implementation Phases

### Phase 1: Ingestion & Replay (Current)
- ✅ Envelope schema and validators
- ✅ Redaction service
- ✅ Trace events and storage
- ✅ One ticket source, one KB tool
- ✅ Mutating actions disabled

### Phase 2: Minimal Orchestration
- Classification, risk assessment
- Retrieval planning and evidence gathering
- Synthesis and draft
- Human gate UI/API

### Phase 3: Reliability
- Idempotency, retries, timeouts
- Circuit breakers
- Deterministic fallbacks
- Per-tenant config

### Phase 4: Controlled Actions
- Low-risk actions (tagging, status)
- Hard permission enforcement
- Financial actions blocked

### Phase 5: Evals & Self-Assessment
- Sanitized dataset pipeline
- Golden cases and regression diffs
- Daily and release-triggered runs

### Phase 6: Scale
- Multi-tenant isolation
- Rate limiting
- Queue backpressure
- SLA monitoring

## File Structure

```
orka/support_triage/
├── __init__.py           # Package exports
├── schemas.py            # Pydantic models for all data structures
├── validators.py         # Deterministic validation logic
├── agents.py             # Support triage agent implementations
├── trace.py              # Trace event system
└── evaluation.py         # Eval runner and reporting

examples/support_triage/
├── support_ticket_triage.yml    # Main triage workflow
├── self_assessment.yml          # Self-assessment workflow
├── eval_cases.json              # Evaluation case definitions
└── inputs/
    ├── refund_with_injection.json
    ├── account_lockout_urgent.json
    └── injection_variants.json
```

## Security Considerations

1. **Never** pass untrusted text as instruction to LLM
2. **Always** redact PII before LLM processing
3. **Enforce** permissions at orchestrator level, not prompt level
4. **Log** all tool calls with idempotency keys
5. **Gate** high-risk actions with human approval
6. **Validate** outputs against schema before execution
