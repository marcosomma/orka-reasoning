"""Scan examples for graph-scout agents missing provider/model_url in params.

Usage: python scripts/check_graphscout_configs.py
Exits with code 1 if any issues are found.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


def scan_examples() -> dict[str, list[tuple[str, list[str]]]]:
    """Returns a mapping of file -> list of (agent_id, missing_keys)."""
    problems: dict[str, list[tuple[str, list[str]]]] = {}

    for path in EXAMPLES.rglob("*.yml"):
        try:
            data = yaml.safe_load(path.read_text()) or {}
        except Exception:
            # skip files that aren't valid yaml for now
            continue

        agents = data.get("agents") or []
        for agent in agents:
            if not isinstance(agent, dict):
                continue
            if agent.get("type") != "graph-scout":
                continue

            params = agent.get("params") or {}
            missing = []
            if "provider" not in params:
                missing.append("provider")
            if "model_url" not in params:
                missing.append("model_url")

            if missing:
                problems.setdefault(str(path), []).append((agent.get("id", "<no-id>"), missing))

    return problems


def main() -> int:
    problems = scan_examples()
    if not problems:
        print("No issues found: all graph-scout agents specify provider and model_url")
        return 0

    print("Found graph-scout agents missing required params:")
    for path, entries in problems.items():
        print(f"\n{path}")
        for agent_id, missing in entries:
            print(f" - agent id={agent_id} missing={missing}")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
