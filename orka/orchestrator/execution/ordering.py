# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0

"""
Execution Ordering
==================

Reorders the orchestrator's agent queue so that an agent declared in another
agent's ``depends_on`` runs first. The sort is **stable**: when dependencies do
not force a change, the original ``agents:`` list order is preserved exactly, so
existing workflows are unaffected.

Only ``depends_on`` entries that reference agents *within the orchestrator's
top-level agent list* constrain ordering. References to agents outside that list
(e.g. fork branch targets, which are scheduled dynamically) are ignored here.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _deps_of(cfg: Dict[str, Any]) -> List[str]:
    raw = cfg.get("depends_on") or []
    if isinstance(raw, str):
        raw = [raw]
    return [d for d in raw if isinstance(d, str)]


def topological_queue(agent_ids: List[str], cfg_by_id: Dict[str, Dict[str, Any]]) -> List[str]:
    """Return ``agent_ids`` reordered to honor ``depends_on``.

    Args:
        agent_ids: The orchestrator's ordered list of agent ids.
        cfg_by_id: Map of agent id -> its config dict (carrying ``depends_on``).

    Returns:
        A list containing exactly the same ids, reordered so each agent follows
        the agents it depends on. Stable w.r.t. the input order.

    Raises:
        ValueError: if ``depends_on`` forms a cycle among the listed agents.
    """
    id_set = set(agent_ids)
    index = {aid: i for i, aid in enumerate(agent_ids)}

    deps: Dict[str, List[str]] = {}
    for aid in agent_ids:
        cfg = cfg_by_id.get(aid, {})
        deps[aid] = [d for d in _deps_of(cfg) if d in id_set and d != aid]

    # Fast path: no in-list dependencies -> order is unchanged.
    if not any(deps.values()):
        return list(agent_ids)

    remaining = set(agent_ids)
    satisfied: set[str] = set()
    result: List[str] = []

    while remaining:
        ready = sorted(
            (aid for aid in remaining if all(d in satisfied for d in deps[aid])),
            key=lambda a: index[a],
        )
        if not ready:
            cycle = sorted(remaining, key=lambda a: index[a])
            raise ValueError(
                f"depends_on cycle detected among agents: {cycle}. "
                "Remove the circular dependency or list these agents without depends_on."
            )
        nxt = ready[0]
        result.append(nxt)
        satisfied.add(nxt)
        remaining.discard(nxt)

    return result


def ordered_initial_queue(agent_ids: List[Any], agent_cfgs: Any) -> List[Any]:
    """Reorder an initial queue by ``depends_on``, safely passing through edge cases.

    Leaves the list untouched if it contains non-string entries (e.g. nested
    decision-tree branches), since ordering only applies to a flat agent list.

    Args:
        agent_ids: The orchestrator's ``agents`` list.
        agent_cfgs: Iterable of agent config dicts (each with ``id``/``depends_on``).

    Raises:
        ValueError: if ``depends_on`` forms a cycle (surfaced to fail the run).
    """
    if not agent_ids or not all(isinstance(a, str) for a in agent_ids):
        return list(agent_ids)
    cfg_by_id: Dict[str, Dict[str, Any]] = {}
    for c in agent_cfgs or []:
        if isinstance(c, dict) and c.get("id"):
            cfg_by_id[c["id"]] = c
    return topological_queue(list(agent_ids), cfg_by_id)
