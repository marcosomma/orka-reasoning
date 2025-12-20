"""
Guardrail: prevent drift between `examples/**` and the implemented scoring presets.

We specifically validate that any LoopNode configured with:
  scoring.context: loop_convergence
only references criteria keys that exist in `orka.scoring.presets`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pytest
import yaml

from orka.scoring.presets import load_preset


pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


def _iter_nodes(obj: Any) -> Iterable[dict[str, Any]]:
    """Yield every dict node within an arbitrarily nested YAML structure."""
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _iter_nodes(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _iter_nodes(item)


def _preset_criteria_keys(preset_name: str, context: str) -> set[str]:
    preset = load_preset(preset_name, context=context)
    weights = preset.get("weights", {})
    keys: set[str] = set()
    for dimension, criteria in weights.items():
        if not isinstance(criteria, dict):
            continue
        for criterion in criteria.keys():
            keys.add(f"{dimension}.{criterion}")
    return keys


def _example_files() -> list[Path]:
    root = Path(__file__).resolve().parents[3]  # repo root
    examples_dir = root / "examples"
    files: list[Path] = []
    for p in examples_dir.rglob("*.yml"):
        if "PRIVATE" in p.parts:
            continue
        files.append(p)
    for p in examples_dir.rglob("*.yaml"):
        if "PRIVATE" in p.parts:
            continue
        files.append(p)
    return sorted(set(files))


@pytest.mark.parametrize("example_path", _example_files(), ids=lambda p: str(p))
def test_loop_convergence_custom_weights_reference_known_criteria(example_path: Path) -> None:
    data = yaml.safe_load(example_path.read_text(encoding="utf-8"))
    assert data is not None

    errors: list[str] = []

    for node in _iter_nodes(data):
        if node.get("type") != "loop":
            continue

        scoring = node.get("scoring")
        if not isinstance(scoring, dict):
            continue

        context = scoring.get("context")
        if context != "loop_convergence":
            continue

        preset_name = scoring.get("preset", "moderate")
        if not isinstance(preset_name, str) or not preset_name.strip():
            preset_name = "moderate"

        custom_weights = scoring.get("custom_weights")
        if not isinstance(custom_weights, dict):
            continue

        known = _preset_criteria_keys(preset_name, context="loop_convergence")
        for key in custom_weights.keys():
            if key not in known:
                errors.append(
                    f"{example_path.as_posix()}: loop '{node.get('id', '<unknown>')}' "
                    f"scoring.custom_weights has unknown key '{key}' for preset='{preset_name}' "
                    f"context='loop_convergence'. Known keys: {sorted(known)}"
                )

    if errors:
        raise AssertionError("\n".join(errors))


