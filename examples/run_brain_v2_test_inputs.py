#!/usr/bin/env python3
"""
Brain v2 Test-Input Runner
===========================

Runs brain_v2_recipe_transfer.yml and brain_v2_graphscout_integration.yml
with 12 curated inputs each. Prints a summary table showing which skills
were created, transfer scores, and routing decisions.

Usage:
    python examples/run_brain_v2_test_inputs.py recipe       # 12 recipe runs
    python examples/run_brain_v2_test_inputs.py graphscout   # 12 graphscout runs
    python examples/run_brain_v2_test_inputs.py all          # both suites
    python examples/run_brain_v2_test_inputs.py recipe --id 3   # single run

Prerequisites:
    - Redis running (orka-start)
    - Local LLM available (LM Studio / Ollama)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from orka.orchestrator import Orchestrator  # noqa: E402


# ──────────────────────────────────────────────────────────────────────
# Recipe Transfer Inputs — 12 diverse inputs
# ──────────────────────────────────────────────────────────────────────
# Each run creates/updates 3 skills:
#   recipe:code-review:sequential-code_linter+code_analyzer
#   recipe:data-pipeline:sequential-data_validator+data_transformer
#   anti:code-review:running-full-analysis-on-trivial
# Then tests cross-domain transfer to compliance-audit.

RECIPE_INPUTS: list[dict[str, str]] = [
    {
        "id": "1",
        "label": "Python function — pricing module",
        "input": (
            "Review this pull request that adds a 'calculate_discount' function "
            "to the pricing module. It takes base_price and discount_code, "
            "looks up the code in a database, returns the discounted price."
        ),
    },
    {
        "id": "2",
        "label": "Strategy pattern refactor + schema change",
        "input": (
            "Review this refactoring that replaces the PaymentProcessor class "
            "hierarchy with a Strategy pattern. Removes CreditCardProcessor, "
            "PayPalProcessor, StripeProcessor subclasses. Introduces injectable "
            "PaymentStrategy objects. Also updates the payment_transactions "
            "table schema to add a strategy_type column."
        ),
    },
    {
        "id": "3",
        "label": "REST API with data validation",
        "input": (
            "Review this PR adding POST /api/v2/orders endpoint. Validates "
            "order items against the product catalog (schema check), transforms "
            "prices to base currency using exchange rate lookups, and stores "
            "the normalized order in the orders table."
        ),
    },
    {
        "id": "4",
        "label": "Database migration with code changes",
        "input": (
            "Review this PR: adds an audit_log table with (id, user_id, action, "
            "entity_type, entity_id, old_value JSON, new_value JSON, timestamp). "
            "Python code adds AuditLogger class that intercepts ORM saves and "
            "writes diffs. Includes data migration backfilling existing records."
        ),
    },
    {
        "id": "5",
        "label": "ETL pipeline configuration",
        "input": (
            "Review this ETL pipeline config: extracts CSV from S3, validates "
            "schema (column types, null constraints, value ranges), transforms "
            "dates from US to ISO format, normalizes phone numbers to E.164, "
            "deduplicates on customer_id, and loads into Redshift."
        ),
    },
    {
        "id": "6",
        "label": "Data quality framework",
        "input": (
            "Review this PR adding a data quality framework. Includes schema "
            "validators for JSON payloads, null-rate checkers, freshness monitors, "
            "and drift detectors comparing current distributions to baseline. "
            "Also adds a DataQualityReport class for generating reports."
        ),
    },
    {
        "id": "7",
        "label": "Terraform infrastructure",
        "input": (
            "Review this Terraform PR: provisions EKS cluster with 3 node groups, "
            "VPC peering to shared-services, ALB ingress controller, Datadog "
            "monitoring as DaemonSet. Includes variable validation rules for "
            "CIDR blocks and instance types."
        ),
    },
    {
        "id": "8",
        "label": "ML model training pipeline",
        "input": (
            "Review this ML pipeline: loads training data from Parquet, validates "
            "feature distributions against expected ranges, applies feature "
            "engineering transforms (normalization, one-hot encoding), trains "
            "a gradient boosted classifier, and validates predictions against "
            "a holdout set. Code uses scikit-learn with custom estimators."
        ),
    },
    {
        "id": "9",
        "label": "Event-driven microservice",
        "input": (
            "Review this Kafka consumer microservice: deserializes Avro messages, "
            "validates against the schema registry, transforms events into "
            "normalized domain objects, enriches with customer data from gRPC "
            "service, and publishes transformed events to output topic."
        ),
    },
    {
        "id": "10",
        "label": "GraphQL API with input validation",
        "input": (
            "Review this GraphQL schema and resolvers: adds mutations for "
            "creating and updating user profiles. Includes input type validation "
            "(email format, phone E.164, date ranges), transforms nested input "
            "objects into flat database records, and handles partial updates "
            "with field-level merge logic."
        ),
    },
    {
        "id": "11",
        "label": "Trivial fix — success rate check",
        "input": "Fix typo: changed 'recieve' to 'receive' in error message string.",
    },
    {
        "id": "12",
        "label": "Large rewrite — cumulative degradation",
        "input": (
            "Complete rewrite of authentication from sessions to JWT. Touches "
            "47 files, removes sessions table, adds token refresh, updates all "
            "middleware, changes login/logout API contracts, migrates existing "
            "session data to token format."
        ),
    },
]


# ──────────────────────────────────────────────────────────────────────
# GraphScout Inputs — 12 diverse tickets
# ──────────────────────────────────────────────────────────────────────
# Each run creates/updates 5 skills (3 anti-patterns + 2 paths).
# Then GraphScout routes with brain boost/penalty.

GRAPHSCOUT_INPUTS: list[dict[str, str]] = [
    {
        "id": "1",
        "label": "Trivial — business hours",
        "input": "What are your business hours for phone support?",
    },
    {
        "id": "2",
        "label": "Simple billing — wrong charge",
        "input": (
            "I was charged $49.99 but my plan is Basic at $19.99/month. "
            "Please refund the $30 difference."
        ),
    },
    {
        "id": "3",
        "label": "FAQ — password reset",
        "input": "How do I reset my password?",
    },
    {
        "id": "4",
        "label": "Technical — API 503 errors",
        "input": (
            "Our integration gets HTTP 503 from /api/v2/users since 3am UTC. "
            "API key is valid, request format unchanged. Blocking production."
        ),
    },
    {
        "id": "5",
        "label": "Account — update payment method",
        "input": (
            "My credit card expired and I can't update payment. Keep getting "
            "'payment failed' emails but settings page has no option to change card."
        ),
    },
    {
        "id": "6",
        "label": "Technical — webhook duplicates",
        "input": (
            "Webhook at https://hooks.ourapp.com/sync receives duplicate events. "
            "Same order_created event delivered 3-4 times in 10 seconds. "
            "Transaction IDs are unique but payload identical."
        ),
    },
    {
        "id": "7",
        "label": "Security — account breach",
        "input": (
            "Someone logged into my account from a foreign country. I changed "
            "my password but worried about data access. I need a full audit log "
            "of all account activity for the past 30 days immediately."
        ),
    },
    {
        "id": "8",
        "label": "Critical — data leak between customers",
        "input": (
            "URGENT: Our API export contains records from OTHER customers. "
            "Serious data isolation breach. Affected: EXP-92831, EXP-92832. "
            "We are SOC2-certified — this triggers our incident response. "
            "Need your security team NOW."
        ),
    },
    {
        "id": "9",
        "label": "Critical — production outage enterprise",
        "input": (
            "PRODUCTION DOWN. Your entire platform is unreachable for our 50,000 "
            "users since 14:00 UTC. We're an enterprise customer paying $200k/year. "
            "Our SLA guarantees 99.99% uptime. Every minute costs us $10,000. "
            "Need executive escalation immediately."
        ),
    },
    {
        "id": "10",
        "label": "Multi-issue ticket",
        "input": (
            "Three problems: (1) double-charged in February, (2) export feature "
            "throws 500 for date ranges over 90 days, (3) team member can't "
            "access shared workspace though I added them as editor."
        ),
    },
    {
        "id": "11",
        "label": "Churn risk — feature complaint",
        "input": (
            "Your product doesn't support Okta SSO. Every competitor has it. "
            "We're an enterprise customer at $50k/year and this is a dealbreaker. "
            "If not on Q2 roadmap, we switch to CompetitorX. Escalate to product."
        ),
    },
    {
        "id": "12",
        "label": "Mobile crash with workaround",
        "input": (
            "iOS app crashes on launch after update v3.2.1 on iPhone 14 Pro "
            "(iOS 17.4). Crash: EXC_BAD_ACCESS in AuthModule. Tried reinstall, "
            "cache clear, restart. But I can use the web app as workaround."
        ),
    },
]


# ── Workflow paths ───────────────────────────────────────────────────

WORKFLOWS = {
    "recipe": {
        "config": "examples/brain_v2_recipe_transfer.yml",
        "inputs": RECIPE_INPUTS,
        "description": "Multi-Skill Recipe Learning & Cross-Domain Transfer",
    },
    "graphscout": {
        "config": "examples/brain_v2_graphscout_integration.yml",
        "inputs": GRAPHSCOUT_INPUTS,
        "description": "Multi-Skill Anti-Pattern + Brain-Assisted GraphScout",
    },
}


# ── Result extraction ────────────────────────────────────────────────


def _build_agent_outputs(logs: list[dict]) -> dict[str, Any]:
    """Build a dict of agent_id -> output from full execution logs."""
    outputs: dict[str, Any] = {}
    for log in logs:
        if not isinstance(log, dict):
            continue
        agent_id = log.get("agent_id", "")
        if not agent_id or log.get("event_type") == "MetaReport":
            continue
        payload = log.get("payload", {})
        if not isinstance(payload, dict):
            continue
        if "result" in payload:
            outputs[agent_id] = payload["result"]
        elif "response" in payload:
            outputs[agent_id] = {
                "response": payload["response"],
                "confidence": payload.get("confidence", "0.0"),
                "internal_reasoning": payload.get("internal_reasoning", ""),
            }
    return outputs


def _extract_skill_name(agent_output: Any) -> str:
    """Extract skill name from agent output (dict or response string)."""
    if isinstance(agent_output, dict):
        name = agent_output.get("skill_name")
        if name:
            return str(name)
        resp = agent_output.get("response", "")
    elif isinstance(agent_output, str):
        resp = agent_output
    else:
        return "?"
    # Parse from response string pattern: "Learned skill: <name>"
    if "Learned skill:" in resp:
        return resp.split("Learned skill:", 1)[1].strip()
    if "Learned anti-pattern:" in resp:
        return resp.split("Learned anti-pattern:", 1)[1].strip()
    return "?"


def _extract_key_results(result: dict | str | list | None, wtype: str) -> dict:
    """Pull out relevant fields for the summary."""
    info: dict[str, str] = {}
    if not isinstance(result, dict):
        info["raw"] = str(result)[:200]
        return info

    if wtype == "recipe":
        # Skill 1: code recipe
        r1 = result.get("brain_learn_recipe_code")
        info["skill1_name"] = _extract_skill_name(r1)

        # Skill 2: data recipe
        r2 = result.get("brain_learn_recipe_data")
        info["skill2_name"] = _extract_skill_name(r2)

        # Skill 3: anti-pattern
        r3 = result.get("brain_learn_anti_trivial")
        info["skill3_name"] = _extract_skill_name(r3)

        # Transfer
        recall = result.get("brain_recall_all", {})
        if isinstance(recall, dict):
            info["transfer_score"] = str(recall.get("combined_score", "?"))
            info["recalled_skill"] = str(recall.get("skill_name", "?"))
            candidates = recall.get("all_candidates", [])
            info["num_candidates"] = str(len(candidates) if isinstance(candidates, list) else 0)

        # Degradation
        fail = result.get("brain_fail_code_recipe", {})
        if isinstance(fail, dict):
            info["degradation"] = str(fail.get("response", "?"))[:80]

    elif wtype == "graphscout":
        # Anti-patterns created
        for key, label in [
            ("brain_anti_expensive", "anti1"),
            ("brain_anti_no_classify", "anti2"),
            ("brain_anti_auto_escalate", "anti3"),
        ]:
            info[label] = _extract_skill_name(result.get(key))

        # Paths created
        for key, label in [
            ("brain_path_standard", "path1"),
            ("brain_path_escalation", "path2"),
        ]:
            info[label] = _extract_skill_name(result.get(key))

        # Router decision
        router = result.get("smart_router", {})
        if isinstance(router, dict):
            info["target"] = str(router.get("target", "?"))
            info["confidence"] = str(router.get("confidence", "?"))
            info["decision"] = str(router.get("decision", "?"))[:40]
            info["status"] = str(router.get("status", ""))[:30]

        # Learned path
        learned = result.get("brain_learn_executed_path")
        info["learned"] = _extract_skill_name(learned) if learned else "?"

    return info


async def run_single(wtype: str, test_input: dict) -> dict:
    """Execute a single workflow input and return the summary."""
    wf = WORKFLOWS[wtype]
    config = str(project_root / wf["config"])
    input_text = test_input["input"]

    print(f"\n{'─' * 72}")
    print(f"  [{test_input['id']:>2}] {test_input['label']}")
    print(f"  Input: {input_text[:85]}...")
    print(f"{'─' * 72}")

    t0 = time.time()
    try:
        orchestrator = Orchestrator(config)
        logs = await orchestrator.run(input_text, return_logs=True)
        elapsed = time.time() - t0
        result = _build_agent_outputs(logs if isinstance(logs, list) else [])
        key = _extract_key_results(result, wtype)
        status = "PASS"
    except Exception as exc:
        elapsed = time.time() - t0
        key = {"error": str(exc)[:200]}
        status = "FAIL"

    print(f"  Status: {status}  ({elapsed:.1f}s)")
    for k, v in key.items():
        print(f"    {k}: {v}")

    return {
        "id": test_input["id"],
        "label": test_input["label"],
        "status": status,
        "elapsed": round(elapsed, 1),
        **key,
    }


async def run_workflow_suite(wtype: str, single_id: str | None = None) -> None:
    """Run all (or one) inputs for a workflow type and print a summary."""
    wf = WORKFLOWS[wtype]
    inputs = wf["inputs"]
    if single_id:
        inputs = [i for i in inputs if str(i["id"]) == str(single_id)]
        if not inputs:
            print(f"No input with id={single_id} found.")
            return

    print(f"\n{'═' * 72}")
    print(f"  WORKFLOW: {wf['description']}")
    print(f"  Config:   {wf['config']}")
    print(f"  Inputs:   {len(inputs)}")
    print(f"{'═' * 72}")

    results = []
    for test_input in inputs:
        summary = await run_single(wtype, test_input)
        results.append(summary)

    # ── Final summary ────────────────────────────────────────────────
    print(f"\n{'═' * 72}")
    print(f"  SUMMARY — {wf['description']}")
    print(f"{'═' * 72}")
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = len(results) - passed
    print(f"  Total: {len(results)}  |  Passed: {passed}  |  Failed: {failed}\n")

    for r in results:
        mark = "✓" if r["status"] == "PASS" else "✗"
        line = f"  {mark} [{r['id']:>2}] {r['label']:<45} {r['elapsed']:>6.1f}s"
        if wtype == "recipe":
            line += f"  xfer={r.get('transfer_score', '?')}"
            line += f"  cands={r.get('num_candidates', '?')}"
        elif wtype == "graphscout":
            line += f"  path={r.get('target', '?')}"
            line += f"  conf={r.get('confidence', '?')}"
        print(line)

    # Unique skills across runs
    if wtype == "recipe":
        unique = set()
        for r in results:
            for k in ("skill1_name", "skill2_name", "skill3_name"):
                v = r.get(k, "?")
                if v != "?":
                    unique.add(v)
        print(f"\n  Unique skills created: {len(unique)}")
        for s in sorted(unique):
            print(f"    • {s}")

    elif wtype == "graphscout":
        unique = set()
        for r in results:
            for k in ("anti1", "anti2", "anti3", "path1", "path2", "learned"):
                v = r.get(k, "?")
                if v != "?" and "No path" not in v:
                    unique.add(v)
        print(f"\n  Unique skills created: {len(unique)}")
        for s in sorted(unique):
            print(f"    • {s}")

    out_file = project_root / f"brain_v2_{wtype}_results.json"
    out_file.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n  Results saved to {out_file.name}")


# ── CLI ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Brain v2 test-input runner")
    parser.add_argument(
        "suite",
        choices=["recipe", "graphscout", "all"],
        help="Which workflow suite to run",
    )
    parser.add_argument("--id", type=str, default=None, help="Run only one input by ID")
    args = parser.parse_args()

    suites = ["recipe", "graphscout"] if args.suite == "all" else [args.suite]
    for suite in suites:
        asyncio.run(run_workflow_suite(suite, args.id))


if __name__ == "__main__":
    main()
