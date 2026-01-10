# OrKa: Orchestrator Kit Agents
# Test suite for support triage trace system

"""
Unit tests for support triage trace event system.

Tests cover:
- TraceEventEmitter: Event emission and collection
- TraceStore: Storage backends (in-memory, file)
- TracingContextManager: Context-managed tracing
- Hash computation for replay verification
"""

import pytest
import tempfile
import time
from datetime import datetime

from orka.support_triage.trace import (
    compute_hash,
    FileTraceStore,
    InMemoryTraceStore,
    TraceEventEmitter,
    TracingContextManager,
)
from orka.support_triage.schemas import TraceEventType


class TestComputeHash:
    """Test hash computation for replay verification."""

    def test_hash_format(self):
        """Hash should have sha256 prefix."""
        data = {"key": "value"}
        result = compute_hash(data)
        assert result.startswith("sha256:")

    def test_deterministic(self):
        """Same data should produce same hash."""
        data = {"key": "value", "number": 42}
        hash1 = compute_hash(data)
        hash2 = compute_hash(data)
        assert hash1 == hash2

    def test_different_data_different_hash(self):
        """Different data should produce different hash."""
        hash1 = compute_hash({"key": "value1"})
        hash2 = compute_hash({"key": "value2"})
        assert hash1 != hash2

    def test_handles_none(self):
        """Should handle None input."""
        result = compute_hash(None)
        assert result == "sha256:null"

    def test_handles_datetime(self):
        """Should handle datetime objects."""
        data = {"timestamp": datetime.now()}
        result = compute_hash(data)
        assert result.startswith("sha256:")


class TestTraceEventEmitter:
    """Test trace event emission."""

    @pytest.fixture
    def emitter(self):
        return TraceEventEmitter(request_id="req_001")

    def test_emit_creates_event(self, emitter):
        """Should create event with all fields."""
        event = emitter.emit(
            node_id="test_node",
            event_type=TraceEventType.NODE_COMPLETED,
            status="ok",
            timing_ms=100,
        )

        assert event.request_id == "req_001"
        assert event.node_id == "test_node"
        assert event.timing_ms == 100

    def test_emit_generates_unique_ids(self, emitter):
        """Each event should have unique ID."""
        event1 = emitter.emit(
            node_id="node1",
            event_type=TraceEventType.NODE_STARTED,
            status="ok",
            timing_ms=0,
        )
        event2 = emitter.emit(
            node_id="node2",
            event_type=TraceEventType.NODE_STARTED,
            status="ok",
            timing_ms=0,
        )

        assert event1.event_id != event2.event_id

    def test_emit_node_started(self, emitter):
        """Should emit node started event."""
        event = emitter.emit_node_started(
            node_id="classify",
            inputs={"text": "hello"},
        )

        assert event.event_type == TraceEventType.NODE_STARTED
        assert event.inputs_hash is not None

    def test_emit_node_completed(self, emitter):
        """Should emit node completed event."""
        event = emitter.emit_node_completed(
            node_id="classify",
            timing_ms=150,
            outputs={"intent": "refund"},
            writes=[{"path": "classification", "op": "replace"}],
        )

        assert event.event_type == TraceEventType.NODE_COMPLETED
        assert event.outputs_hash is not None
        assert len(event.writes) == 1

    def test_emit_node_failed(self, emitter):
        """Should emit node failed event."""
        event = emitter.emit_node_failed(
            node_id="classify",
            timing_ms=50,
            error="Connection timeout",
        )

        assert event.event_type == TraceEventType.NODE_FAILED
        assert event.status == "error"
        assert event.metadata["error"] == "Connection timeout"

    def test_emit_tool_call(self, emitter):
        """Should emit tool call events."""
        started = emitter.emit_tool_call_started(
            node_id="retrieval",
            tool_name="kb_search",
            tool_call_id="tc_001",
            idempotency_key="req_001:kb_search:rh_01",
        )

        assert started.event_type == TraceEventType.TOOL_CALL_STARTED
        assert started.metadata["tool_name"] == "kb_search"

    def test_emit_decision(self, emitter):
        """Should emit decision event."""
        event = emitter.emit_decision_made(
            node_id="router",
            decision_id="d_001",
            decision_type="routing",
            chosen_path="refund_flow",
            confidence=0.85,
            timing_ms=50,
        )

        assert event.event_type == TraceEventType.DECISION_MADE
        assert event.metadata["confidence"] == 0.85

    def test_get_all_events(self, emitter):
        """Should return all emitted events."""
        emitter.emit_node_started("node1", None)
        emitter.emit_node_completed("node1", 100, None)
        emitter.emit_node_started("node2", None)

        events = emitter.get_all_events()
        assert len(events) == 3

    def test_get_events_by_node(self, emitter):
        """Should filter events by node."""
        emitter.emit_node_started("node1", None)
        emitter.emit_node_completed("node1", 100, None)
        emitter.emit_node_started("node2", None)

        node1_events = emitter.get_events_by_node("node1")
        assert len(node1_events) == 2

    def test_get_summary(self, emitter):
        """Should generate summary."""
        emitter.emit_node_started("node1", None)
        emitter.emit_node_completed("node1", 100, None)
        emitter.emit_node_failed("node2", 50, "Error")

        summary = emitter.get_summary()

        assert summary["total_events"] == 3
        assert summary["error_count"] == 1
        assert "node1" in summary["nodes_executed"]

    def test_callback_invoked(self):
        """Should invoke callback on emit."""
        callback_events = []

        def callback(event):
            callback_events.append(event)

        emitter = TraceEventEmitter(
            request_id="req_001",
            event_callback=callback,
        )

        emitter.emit_node_started("node1", None)

        assert len(callback_events) == 1


class TestInMemoryTraceStore:
    """Test in-memory trace store."""

    @pytest.fixture
    def store(self):
        return InMemoryTraceStore()

    def test_store_and_retrieve_events(self, store):
        """Should store and retrieve events."""
        emitter = TraceEventEmitter(request_id="req_001", store=store)
        emitter.emit_node_started("node1", None)
        emitter.emit_node_completed("node1", 100, None)

        events = store.get_events("req_001")
        assert len(events) == 2

    def test_store_envelope(self, store):
        """Should store and retrieve envelopes."""
        envelope = {"request_id": "req_001", "data": "test"}
        store.store_envelope("req_001", envelope)

        retrieved = store.get_envelope("req_001")
        assert retrieved == envelope

    def test_get_nonexistent_events(self, store):
        """Should return empty list for nonexistent request."""
        events = store.get_events("nonexistent")
        assert events == []

    def test_clear(self, store):
        """Should clear all data."""
        store.store_envelope("req_001", {"data": "test"})
        store.clear()

        assert store.get_envelope("req_001") is None


class TestFileTraceStore:
    """Test file-based trace store."""

    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield FileTraceStore(base_path=tmpdir)

    def test_store_and_retrieve_events(self, store):
        """Should store and retrieve events from files."""
        emitter = TraceEventEmitter(request_id="req_001", store=store)
        emitter.emit_node_started("node1", None)

        events = store.get_events("req_001")
        assert len(events) == 1

    def test_store_envelope(self, store):
        """Should store and retrieve envelope from file."""
        envelope = {"request_id": "req_001", "data": "test"}
        store.store_envelope("req_001", envelope)

        retrieved = store.get_envelope("req_001")
        assert retrieved["request_id"] == "req_001"


class TestTracingContextManager:
    """Test tracing context manager."""

    @pytest.fixture
    def emitter(self):
        return TraceEventEmitter(request_id="req_001")

    def test_success_path(self, emitter):
        """Should emit start and complete events on success."""
        with TracingContextManager(emitter, "test_node") as ctx:
            ctx.set_outputs({"result": "success"})
            ctx.add_write("output", "replace")

        events = emitter.get_all_events()
        assert len(events) == 2
        assert events[0].event_type == TraceEventType.NODE_STARTED
        assert events[1].event_type == TraceEventType.NODE_COMPLETED

    def test_exception_path(self, emitter):
        """Should emit failed event on exception."""
        with pytest.raises(ValueError):
            with TracingContextManager(emitter, "test_node"):
                raise ValueError("Test error")

        events = emitter.get_all_events()
        assert len(events) == 2
        assert events[1].event_type == TraceEventType.NODE_FAILED
        assert events[1].status == "error"

    def test_explicit_error(self, emitter):
        """Should handle explicit error setting."""
        with TracingContextManager(emitter, "test_node") as ctx:
            ctx.set_error("Something went wrong")

        events = emitter.get_all_events()
        assert events[1].event_type == TraceEventType.NODE_FAILED

    def test_timing_captured(self, emitter):
        """Should capture execution timing."""
        with TracingContextManager(emitter, "test_node") as ctx:
            time.sleep(0.01)  # 10ms
            ctx.set_outputs({})

        events = emitter.get_all_events()
        completed = events[1]
        assert completed.timing_ms >= 10
