"""
Typed state model for OrKa streaming runtime.

StreamingState = Invariants (immutable) + MutableState (rolling, bounded).
Deterministic merge with last-write-wins per field keyed by monotonic
timestamp in provenance; stable lexical ordering for joins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, MutableMapping, Optional, Tuple


ImmutableKeys = ("identity", "voice", "refusal", "tool_permissions", "safety_policies")


@dataclass(frozen=True)
class Invariants:
    identity: str = ""
    voice: str = ""
    refusal: str = ""
    tool_permissions: Tuple[str, ...] = tuple()
    safety_policies: Tuple[str, ...] = tuple()


@dataclass
class MutableState:
    summary: str = ""
    intent: str = ""
    constraints: str = ""
    policy: str = ""
    risk: str = ""


@dataclass
class StreamingState:
    """Holds invariants and mutable state with versioning and provenance."""

    invariants: Invariants
    mutable: MutableState = field(default_factory=MutableState)
    version: int = 0
    _provenance: Dict[str, Dict[str, Any]] = field(default_factory=dict, repr=False)

    def clone_invariants(self) -> Dict[str, Any]:
        """Return an immutable copy of invariants as dict."""
        inv = self.invariants
        return {
            "identity": inv.identity,
            "voice": inv.voice,
            "refusal": inv.refusal,
            "tool_permissions": list(inv.tool_permissions),
            "safety_policies": list(inv.safety_policies),
        }

    def apply_patch(self, patch: Mapping[str, Any], provenance: Mapping[str, Any]) -> int:
        """Apply a state patch to mutable fields and bump version.

        Invariant fields cannot be mutated; attempts raise ValueError.
        Returns new version number.
        """
        self._assert_no_invariant_mutation(patch)

        # Determine ordering: lexical field name order for stability
        for key in sorted(patch.keys()):
            value = patch[key]
            # Treat None as a delete to empty string for safety and determinism
            if value is None:
                value = ""
            self._apply_field(key, value, provenance)

        self.version += 1
        return self.version

    def _apply_field(self, key: str, value: Any, provenance: Mapping[str, Any]) -> None:
        # Last-write-wins using timestamp_ms from provenance; missing ts treated as 0
        ts = int(provenance.get("timestamp_ms", 0))
        prev = self._provenance.get(key, {})
        prev_ts = int(prev.get("timestamp_ms", -1))
        if ts < prev_ts:
            # Older write; ignore to preserve determinism
            return

        # Assign
        if hasattr(self.mutable, key):
            setattr(self.mutable, key, value)
        else:
            # Allow new sections but keep them JSON-serializable
            setattr(self.mutable, key, value)
        self._provenance[key] = dict(provenance)

    def _assert_no_invariant_mutation(self, patch: Mapping[str, Any]) -> None:
        for key in patch.keys():
            if key in ImmutableKeys:
                raise ValueError(f"Attempted to mutate invariant field: {key}")
