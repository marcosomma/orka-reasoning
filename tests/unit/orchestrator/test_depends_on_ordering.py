"""Tests for P2b: agent-level depends_on driving execution order."""

from __future__ import annotations

import pytest

from orka.orchestrator.execution.ordering import ordered_initial_queue, topological_queue


def _cfgs(*specs):
    """specs: (id, [deps]) -> list of config dicts."""
    return [{"id": i, "depends_on": d} for i, d in specs]


def test_no_deps_preserves_order():
    ids = ["a", "b", "c", "d"]
    cfg = {i: {"id": i} for i in ids}
    assert topological_queue(ids, cfg) == ids


def test_dependency_moves_before_dependent():
    # c depends on d, but d is listed after c -> d must move before c.
    ids = ["a", "c", "b", "d"]
    cfg = {"a": {"id": "a"}, "b": {"id": "b"}, "c": {"id": "c", "depends_on": ["d"]}, "d": {"id": "d"}}
    out = topological_queue(ids, cfg)
    assert out.index("d") < out.index("c")
    # stable: untouched agents keep relative order
    assert out.index("a") < out.index("b")


def test_chain_orders_fully():
    ids = ["c", "b", "a"]
    cfg = {"a": {"id": "a"}, "b": {"id": "b", "depends_on": ["a"]}, "c": {"id": "c", "depends_on": ["b"]}}
    assert topological_queue(ids, cfg) == ["a", "b", "c"]


def test_external_deps_ignored():
    # depends_on referencing an agent NOT in the list (e.g. a fork target) is ignored.
    ids = ["a", "b"]
    cfg = {"a": {"id": "a"}, "b": {"id": "b", "depends_on": ["fork_x"]}}
    assert topological_queue(ids, cfg) == ["a", "b"]


def test_string_depends_on_supported():
    ids = ["x", "y"]
    cfg = {"x": {"id": "x", "depends_on": "y"}, "y": {"id": "y"}}
    assert topological_queue(ids, cfg) == ["y", "x"]


def test_cycle_raises():
    ids = ["a", "b"]
    cfg = {"a": {"id": "a", "depends_on": ["b"]}, "b": {"id": "b", "depends_on": ["a"]}}
    with pytest.raises(ValueError, match="cycle"):
        topological_queue(ids, cfg)


def test_self_dependency_ignored():
    ids = ["a", "b"]
    cfg = {"a": {"id": "a", "depends_on": ["a"]}, "b": {"id": "b"}}
    assert topological_queue(ids, cfg) == ["a", "b"]


def test_ordered_initial_queue_passes_through_nested_lists():
    # decision-tree style nested entries must not be reordered.
    ids = ["a", ["b", "c"], "d"]
    assert ordered_initial_queue(ids, _cfgs(("a", []), ("d", []))) == ids


def test_ordered_initial_queue_with_list_cfgs():
    ids = ["second", "first"]
    cfgs = _cfgs(("second", ["first"]), ("first", []))
    assert ordered_initial_queue(ids, cfgs) == ["first", "second"]


def test_real_temporal_example_correction():
    # Mirrors examples/temporal_change_search_synthesis.yml: searches listed after
    # the join/synthesize that depend on them -> must be reordered before.
    ids = ["fork_detect", "join_detect", "fork_temporal", "join_paths",
           "synthesize_timeline_answer", "search_before", "search_after"]
    cfgs = _cfgs(
        ("fork_detect", []), ("join_detect", []), ("fork_temporal", ["join_detect"]),
        ("join_paths", ["search_before", "search_after"]),
        ("synthesize_timeline_answer", ["join_paths"]),
        ("search_before", ["generate_before_query"]),  # external dep ignored
        ("search_after", ["generate_after_query"]),
    )
    out = ordered_initial_queue(ids, cfgs)
    assert out.index("search_before") < out.index("join_paths")
    assert out.index("search_after") < out.index("join_paths")
    assert out.index("join_paths") < out.index("synthesize_timeline_answer")
