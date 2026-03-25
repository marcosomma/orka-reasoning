#!/usr/bin/env python3
"""
OrKa Brain — Skill Transfer Demo
=================================

Demonstrates the Brain's core capability: learning skills in one context
and re-applying them in completely different domains.

This demo runs through 10 scenarios:
  - Scenarios 1-3: LEARN phase — the Brain learns 3 distinct patterns
      1. Decompose-Analyze-Synthesize (from text analysis)
      2. Validate-Classify-Route (from customer support)
      3. Iterative Refinement (from creative writing)

  - Scenarios 4-10: RECALL phase — the Brain is given tasks in wildly
    different domains and must recognize which learned skill applies:
      4. Code Review           → should recall Decompose-Analyze-Synthesize
      5. Content Moderation    → should recall Validate-Classify-Route
      6. Code Optimization     → should recall Iterative Refinement
      7. Financial Analysis    → should recall Decompose-Analyze-Synthesize
      8. API Gateway           → should recall Validate-Classify-Route
      9. Essay Grading         → should recall Iterative Refinement
     10. Incident Response     → should recall Decompose-Analyze-Synthesize

Usage:
    python examples/brain_skill_transfer_demo.py

No Redis or LLM required — uses in-memory storage for demonstration.
"""

import asyncio
import json
import os
import sys

# Ensure orka is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orka.brain import Brain


# ── In-memory fake memory (no Redis needed for demo) ────────────────────────

class InMemoryStore:
    """Minimal in-memory Redis-like store for the demo."""

    def __init__(self):
        self._kv: dict[str, str] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._sets: dict[str, set[str]] = {}

    def get(self, key):
        return self._kv.get(key)

    def set(self, key, value):
        self._kv[key] = value
        return True

    def delete(self, *keys):
        return sum(1 for k in keys if self._kv.pop(k, None) is not None)

    def hset(self, name, key, value):
        self._hashes.setdefault(name, {})[key] = value
        return 1

    def hget(self, name, key):
        return self._hashes.get(name, {}).get(key)

    def hkeys(self, name):
        return list(self._hashes.get(name, {}).keys())

    def hdel(self, name, *keys):
        h = self._hashes.get(name, {})
        return sum(1 for k in keys if h.pop(k, None) is not None)

    def sadd(self, name, *values):
        s = self._sets.setdefault(name, set())
        before = len(s)
        s.update(values)
        return len(s) - before

    def srem(self, name, *values):
        s = self._sets.get(name, set())
        return sum(1 for v in values if v in s and not s.discard(v) and True)

    def smembers(self, name):
        return list(self._sets.get(name, set()))

    def log(self, agent_id, event_type, payload, **kwargs):
        pass  # Silently accept log calls


# ── Formatting helpers ──────────────────────────────────────────────────────

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def header(text: str) -> None:
    print(f"\n{'═' * 72}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{'═' * 72}")


def section(text: str) -> None:
    print(f"\n{BOLD}{text}{RESET}")


def info(label: str, value: str) -> None:
    print(f"  {DIM}{label}:{RESET} {value}")


def score_bar(score: float, width: int = 30) -> str:
    filled = int(score * width)
    bar = "█" * filled + "░" * (width - filled)
    color = GREEN if score >= 0.6 else YELLOW if score >= 0.4 else RED
    return f"{color}{bar}{RESET} {score:.2f}"


# ── Main demo ───────────────────────────────────────────────────────────────

async def main():
    header("OrKa Brain — Skill Transfer Demo")
    print(f"\n  {DIM}Demonstrating cross-context skill learning and transfer.{RESET}")
    print(f"  {DIM}The Brain learns patterns in one domain, then recognizes them in others.{RESET}")

    # Load scenarios
    scenarios_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "inputs",
        "brain_skill_transfer_scenarios.json",
    )
    with open(scenarios_path, "r") as f:
        scenarios = json.load(f)

    # Create brain with in-memory store
    brain = Brain(memory=InMemoryStore())

    learned_skills = {}

    # ── Phase 1: Learning ───────────────────────────────────────────────
    header("PHASE 1: LEARNING")
    print(f"  {DIM}Teaching the Brain 3 distinct problem-solving patterns...{RESET}")

    for scenario in scenarios:
        if scenario["phase"] != "learn":
            continue

        section(f"📚 {scenario['title']}")
        info("Domain", scenario["context"]["domain"])
        info("Task", scenario["context"]["task"][:80] + "...")

        skill = await brain.learn(
            execution_trace=scenario["execution_trace"],
            context=scenario["context"],
            outcome=scenario["outcome"],
        )

        if skill:
            learned_skills[scenario["id"]] = skill
            info("Skill learned", f"{GREEN}{skill.name}{RESET}")
            info("Confidence", score_bar(skill.confidence))
            info("Steps", " → ".join(s.action for s in skill.procedure))
            info("Tags", ", ".join(skill.tags[:6]))
        else:
            print(f"  {RED}Failed to learn skill{RESET}")

    # Summary
    summary = await brain.get_skill_summary()
    section("Learning Summary")
    info("Total skills learned", str(summary["total_skills"]))
    info("Avg confidence", f"{summary['avg_confidence']:.2f}")

    # ── Phase 2: Recall & Transfer ──────────────────────────────────────
    header("PHASE 2: CROSS-CONTEXT TRANSFER")
    print(f"  {DIM}Now giving the Brain tasks in completely different domains.{RESET}")
    print(f"  {DIM}Can it recognize which learned pattern applies?{RESET}")

    # Map expected patterns to skill name keywords for accurate matching
    pattern_keywords = {
        "Decompose-Analyze-Synthesize": ["decomposition", "analysis"],
        "Validate-Classify-Route": ["classification", "sequential"],
        "Iterative Refinement": ["iteration", "evaluation"],
    }

    successes = 0
    total_recalls = 0

    for scenario in scenarios:
        if scenario["phase"] != "recall":
            continue

        total_recalls += 1
        expected = scenario.get("expected_skill_pattern", "")

        section(f"🔍 {scenario['title']}")
        info("Domain", scenario["context"]["domain"])
        info("Task", scenario["context"]["task"][:80] + "...")
        info("Expected pattern", f"{YELLOW}{expected}{RESET}")

        candidates = await brain.recall(
            context=scenario["context"],
            top_k=3,
            min_score=0.0,
        )

        if candidates:
            top = candidates[0]
            keywords = pattern_keywords.get(expected, [])
            name_lower = top.skill.name.lower()
            match = any(kw in name_lower for kw in keywords)

            if match:
                successes += 1
                status = f"{GREEN}✓ MATCH{RESET}"
            else:
                status = f"{YELLOW}~ PARTIAL{RESET}"

            info("Top match", f"{status}  {BOLD}{top.skill.name}{RESET}")
            info("Combined score", score_bar(top.combined_score))
            info("  Structural", score_bar(top.structural_score))
            info("  Semantic", score_bar(top.semantic_score))
            info("  Transfer", score_bar(top.transfer_score))
            info("  Confidence", score_bar(top.confidence_score))

            if top.reasoning:
                info("Reasoning", top.reasoning[:100])

            if top.adaptations:
                adapt_items = []
                if "input_adaptation" in top.adaptations:
                    a = top.adaptations["input_adaptation"]
                    adapt_items.append(f"input: {a['from']} → {a['to']}")
                if "output_adaptation" in top.adaptations:
                    a = top.adaptations["output_adaptation"]
                    adapt_items.append(f"output: {a['from']} → {a['to']}")
                if "add_structures" in top.adaptations:
                    adapt_items.append(f"add: {', '.join(top.adaptations['add_structures'])}")
                if adapt_items:
                    info("Adaptations", "; ".join(adapt_items))

            # Show runner-up if there is one
            if len(candidates) > 1:
                runner = candidates[1]
                info(
                    "Runner-up",
                    f"{runner.skill.name} (score: {runner.combined_score:.2f})",
                )

            # Give positive feedback to reinforce the transfer
            await brain.feedback(
                skill_id=top.skill.id,
                context=scenario["context"],
                success=match,
            )
        else:
            print(f"  {RED}No applicable skills found{RESET}")

    # ── Final Summary ───────────────────────────────────────────────────
    header("RESULTS")

    final_summary = await brain.get_skill_summary()
    info("Total skills", str(final_summary["total_skills"]))
    info("Transferable skills", str(final_summary["transferable_skills"]))
    info("Total transfers", str(final_summary["total_transfers"]))
    info("Avg confidence", f"{final_summary['avg_confidence']:.2f}")
    info(
        "Recall accuracy",
        f"{successes}/{total_recalls} ({successes/total_recalls:.0%})",
    )

    print(f"\n  {BOLD}Skill Details:{RESET}")
    for s in final_summary["top_skills"]:
        print(
            f"    • {s['name']:40s}  "
            f"confidence={s['confidence']:.2f}  "
            f"used={s['usage_count']}x  "
            f"transfers={s['transfer_count']}"
        )

    print(f"\n{'═' * 72}")
    print(f"{BOLD}{CYAN}  The same abstract patterns recognized across {total_recalls} different domains.{RESET}")
    print(f"{'═' * 72}\n")


if __name__ == "__main__":
    asyncio.run(main())
