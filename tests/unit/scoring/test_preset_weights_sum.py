"""POC ③: guard that every scoring preset is well-formed.

The presets are hand-tuned constants; nothing previously asserted that each
context/severity's criterion weights actually sum to 1.0 or that thresholds are
sane. This test pins both so a future edit can't silently unbalance the scoring.
"""

from __future__ import annotations

import pytest

from orka.scoring.presets import PRESETS


def _all_presets():
    for context, severities in PRESETS.items():
        for severity, preset in severities.items():
            yield context, severity, preset


@pytest.mark.parametrize("context,severity,preset", list(_all_presets()))
def test_preset_weights_sum_to_one(context, severity, preset):
    weights = preset.get("weights", {})
    assert weights, f"{context}/{severity} has no weights"
    total = sum(v for dim in weights.values() for v in dim.values())
    assert abs(total - 1.0) < 0.01, f"{context}/{severity} weights sum to {total:.4f}, expected 1.0"


@pytest.mark.parametrize("context,severity,preset", list(_all_presets()))
def test_preset_weights_are_nonnegative(context, severity, preset):
    for dim, criteria in preset.get("weights", {}).items():
        for crit, w in criteria.items():
            assert isinstance(w, (int, float)) and w >= 0, f"{context}/{severity}.{dim}.{crit}={w}"


@pytest.mark.parametrize("context,severity,preset", list(_all_presets()))
def test_preset_thresholds_ordered(context, severity, preset):
    th = preset.get("thresholds")
    if not th:
        pytest.skip(f"{context}/{severity} has no thresholds")
    approved = th.get("approved")
    needs = th.get("needs_improvement")
    if approved is not None and needs is not None:
        assert 0.0 <= needs <= approved <= 1.0, (
            f"{context}/{severity} thresholds not ordered: needs={needs}, approved={approved}"
        )
