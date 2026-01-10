# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

"""
Trace Event System
==================

Event-level observability for the ticket triage system. This is the OrKa product
surface - you want event-level observability, not just logs.

Features:
- Structured trace events for every node execution
- Hash computation for replay verification
- Trace storage with multiple backends
- Correlation across request lifecycle
"""

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .schemas import TraceEvent, TraceEventType, TraceWrite
logger = logging.getLogger(__name__)


def compute_hash(data: Any) -> str:
    """
    Compute SHA256 hash of data for replay verification.

    Args:
        data: Data to hash (will be JSON serialized)

    Returns:
        SHA256 hash string prefixed with 'sha256:'
    """
    if data is None:
        return "sha256:null"

    try:
        # Serialize with sorted keys for determinism
        json_str = json.dumps(data, sort_keys=True, default=str)
        hash_value = hashlib.sha256(json_str.encode()).hexdigest()
        return f"sha256:{hash_value}"
    except Exception as e:
        logger.warning(f"Failed to compute hash: {e}")
        return f"sha256:error:{str(e)[:20]}"


class TraceEventEmitter:
    """
    Emits trace events for observability.

    Each event captures:
    - What node executed
    - How long it took
    - What inputs it received (hashed)
    - What outputs it produced (hashed)
    - What state writes it made
    """

    def __init__(
        self,
        request_id: str,
        store: Optional["TraceStore"] = None,
        event_callback: Optional[Callable[[TraceEvent], None]] = None,
    ):
        """
        Initialize emitter.

        Args:
            request_id: Request ID for correlation
            store: Optional trace store for persistence
            event_callback: Optional callback for each event
        """
        self.request_id = request_id
        self.store = store
        self.event_callback = event_callback
        self.events: List[TraceEvent] = []
        self._event_counter = 0

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        self._event_counter += 1
        return f"ev_{self._event_counter:04d}"

    def emit(
        self,
        node_id: str,
        event_type: TraceEventType,
        status: str,
        timing_ms: int,
        inputs: Optional[Any] = None,
        outputs: Optional[Any] = None,
        writes: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceEvent:
        """
        Emit a trace event.

        Args:
            node_id: ID of the node emitting the event
            event_type: Type of event
            status: Status ('ok', 'error', 'warning')
            timing_ms: Timing in milliseconds
            inputs: Optional inputs (will be hashed)
            outputs: Optional outputs (will be hashed)
            writes: Optional list of state writes
            metadata: Optional additional metadata

        Returns:
            The emitted TraceEvent
        """
        event = TraceEvent(
            event_id=self._generate_event_id(),
            request_id=self.request_id,
            node_id=node_id,
            event_type=event_type,
            status=status,
            timing_ms=timing_ms,
            inputs_hash=compute_hash(inputs) if inputs else None,
            outputs_hash=compute_hash(outputs) if outputs else None,
            writes=[TraceWrite(**w) for w in (writes or [])],
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

        self.events.append(event)

        # Persist if store available
        if self.store:
            self.store.store_event(event)

        # Call callback if provided
        if self.event_callback:
            try:
                self.event_callback(event)
            except Exception as e:
                logger.warning(f"Event callback failed: {e}")

        logger.debug(
            f"Trace event: {event.event_type.value} for {event.node_id} "
            f"[{event.status}] {event.timing_ms}ms"
        )

        return event

    def emit_node_started(
        self, node_id: str, inputs: Optional[Any] = None, metadata: Optional[Dict[str, Any]] = None
    ) -> TraceEvent:
        """Emit node started event."""
        return self.emit(
            node_id=node_id,
            event_type=TraceEventType.NODE_STARTED,
            status="ok",
            timing_ms=0,
            inputs=inputs,
            metadata=metadata,
        )

    def emit_node_completed(
        self,
        node_id: str,
        timing_ms: int,
        outputs: Optional[Any] = None,
        writes: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceEvent:
        """Emit node completed event."""
        return self.emit(
            node_id=node_id,
            event_type=TraceEventType.NODE_COMPLETED,
            status="ok",
            timing_ms=timing_ms,
            outputs=outputs,
            writes=writes,
            metadata=metadata,
        )

    def emit_node_failed(
        self,
        node_id: str,
        timing_ms: int,
        error: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceEvent:
        """Emit node failed event."""
        meta = metadata or {}
        meta["error"] = error
        return self.emit(
            node_id=node_id,
            event_type=TraceEventType.NODE_FAILED,
            status="error",
            timing_ms=timing_ms,
            metadata=meta,
        )

    def emit_tool_call_started(
        self,
        node_id: str,
        tool_name: str,
        tool_call_id: str,
        idempotency_key: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceEvent:
        """Emit tool call started event."""
        meta = metadata or {}
        meta.update(
            {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "idempotency_key": idempotency_key,
            }
        )
        return self.emit(
            node_id=node_id,
            event_type=TraceEventType.TOOL_CALL_STARTED,
            status="ok",
            timing_ms=0,
            metadata=meta,
        )

    def emit_tool_call_completed(
        self,
        node_id: str,
        tool_name: str,
        tool_call_id: str,
        timing_ms: int,
        result_ref: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceEvent:
        """Emit tool call completed event."""
        meta = metadata or {}
        meta.update(
            {
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "result_ref": result_ref,
            }
        )
        return self.emit(
            node_id=node_id,
            event_type=TraceEventType.TOOL_CALL_COMPLETED,
            status="ok",
            timing_ms=timing_ms,
            metadata=meta,
        )

    def emit_decision_made(
        self,
        node_id: str,
        decision_id: str,
        decision_type: str,
        chosen_path: str,
        confidence: float,
        timing_ms: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceEvent:
        """Emit decision made event."""
        meta = metadata or {}
        meta.update(
            {
                "decision_id": decision_id,
                "decision_type": decision_type,
                "chosen_path": chosen_path,
                "confidence": confidence,
            }
        )
        return self.emit(
            node_id=node_id,
            event_type=TraceEventType.DECISION_MADE,
            status="ok",
            timing_ms=timing_ms,
            metadata=meta,
        )

    def emit_human_gate(
        self,
        node_id: str,
        gate_type: TraceEventType,
        timing_ms: int,
        approver: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceEvent:
        """Emit human gate event."""
        meta = metadata or {}
        if approver:
            meta["approver"] = approver
        if reason:
            meta["reason"] = reason

        status = "ok" if gate_type != TraceEventType.HUMAN_GATE_REJECTED else "warning"
        return self.emit(
            node_id=node_id,
            event_type=gate_type,
            status=status,
            timing_ms=timing_ms,
            metadata=meta,
        )

    def emit_validation(
        self,
        node_id: str,
        passed: bool,
        timing_ms: int,
        violations: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TraceEvent:
        """Emit validation event."""
        meta = metadata or {}
        if violations:
            meta["violations"] = violations

        return self.emit(
            node_id=node_id,
            event_type=(
                TraceEventType.VALIDATION_PASSED if passed else TraceEventType.VALIDATION_FAILED
            ),
            status="ok" if passed else "error",
            timing_ms=timing_ms,
            metadata=meta,
        )

    def get_all_events(self) -> List[TraceEvent]:
        """Get all emitted events."""
        return self.events.copy()

    def get_events_by_node(self, node_id: str) -> List[TraceEvent]:
        """Get events for a specific node."""
        return [e for e in self.events if e.node_id == node_id]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of trace events."""
        total_timing = sum(e.timing_ms for e in self.events)
        errors = [e for e in self.events if e.status == "error"]
        nodes = set(e.node_id for e in self.events)

        return {
            "request_id": self.request_id,
            "total_events": len(self.events),
            "total_timing_ms": total_timing,
            "nodes_executed": list(nodes),
            "error_count": len(errors),
            "event_types": {
                event_type.value: len([e for e in self.events if e.event_type == event_type])
                for event_type in TraceEventType
                if any(e.event_type == event_type for e in self.events)
            },
        }


class TraceStore:
    """
    Abstract trace store for persistence.

    Implementations can store to:
    - Redis (for real-time access)
    - S3/GCS (for long-term storage)
    - Local filesystem (for development)
    """

    def store_event(self, event: TraceEvent) -> None:
        """Store a trace event."""
        raise NotImplementedError

    def store_envelope(self, request_id: str, envelope: Dict[str, Any]) -> None:
        """Store an input envelope for replay."""
        raise NotImplementedError

    def get_events(self, request_id: str) -> List[TraceEvent]:
        """Get all events for a request."""
        raise NotImplementedError

    def get_envelope(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get stored envelope for replay."""
        raise NotImplementedError


class InMemoryTraceStore(TraceStore):
    """In-memory trace store for development and testing."""

    def __init__(self):
        self.events: Dict[str, List[TraceEvent]] = {}
        self.envelopes: Dict[str, Dict[str, Any]] = {}

    def store_event(self, event: TraceEvent) -> None:
        """Store a trace event."""
        if event.request_id not in self.events:
            self.events[event.request_id] = []
        self.events[event.request_id].append(event)

    def store_envelope(self, request_id: str, envelope: Dict[str, Any]) -> None:
        """Store an input envelope."""
        self.envelopes[request_id] = envelope

    def get_events(self, request_id: str) -> List[TraceEvent]:
        """Get all events for a request."""
        return self.events.get(request_id, [])

    def get_envelope(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get stored envelope."""
        return self.envelopes.get(request_id)

    def clear(self) -> None:
        """Clear all stored data."""
        self.events.clear()
        self.envelopes.clear()


class FileTraceStore(TraceStore):
    """File-based trace store for local development."""

    def __init__(self, base_path: str = "./traces"):
        import os

        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def _get_request_dir(self, request_id: str) -> str:
        import os

        dir_path = os.path.join(self.base_path, request_id)
        os.makedirs(dir_path, exist_ok=True)
        return dir_path

    def store_event(self, event: TraceEvent) -> None:
        """Store a trace event to file."""
        import os

        dir_path = self._get_request_dir(event.request_id)
        events_file = os.path.join(dir_path, "events.jsonl")

        with open(events_file, "a") as f:
            f.write(event.model_dump_json() + "\n")

    def store_envelope(self, request_id: str, envelope: Dict[str, Any]) -> None:
        """Store an input envelope."""
        import os

        dir_path = self._get_request_dir(request_id)
        envelope_file = os.path.join(dir_path, "envelope.json")

        with open(envelope_file, "w") as f:
            json.dump(envelope, f, indent=2, default=str)

    def get_events(self, request_id: str) -> List[TraceEvent]:
        """Get all events for a request."""
        import os

        dir_path = self._get_request_dir(request_id)
        events_file = os.path.join(dir_path, "events.jsonl")

        if not os.path.exists(events_file):
            return []

        events = []
        with open(events_file, "r") as f:
            for line in f:
                if line.strip():
                    events.append(TraceEvent.model_validate_json(line))
        return events

    def get_envelope(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get stored envelope."""
        import os

        dir_path = self._get_request_dir(request_id)
        envelope_file = os.path.join(dir_path, "envelope.json")

        if not os.path.exists(envelope_file):
            return None

        with open(envelope_file, "r") as f:
            return json.load(f)


class TracingContextManager:
    """
    Context manager for tracing node execution.

    Usage:
        with TracingContextManager(emitter, "my_node") as ctx:
            result = do_work(inputs)
            ctx.set_outputs(result)
            ctx.add_write("output", "replace")
    """

    def __init__(
        self,
        emitter: TraceEventEmitter,
        node_id: str,
        inputs: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.emitter = emitter
        self.node_id = node_id
        self.inputs = inputs
        self.metadata = metadata or {}
        self.outputs: Optional[Any] = None
        self.writes: List[Dict[str, str]] = []
        self.start_time: float = 0
        self.error: Optional[str] = None

    def __enter__(self) -> "TracingContextManager":
        self.start_time = time.time()
        self.emitter.emit_node_started(
            node_id=self.node_id,
            inputs=self.inputs,
            metadata=self.metadata,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        timing_ms = int((time.time() - self.start_time) * 1000)

        if exc_type is not None:
            # Exception occurred
            self.emitter.emit_node_failed(
                node_id=self.node_id,
                timing_ms=timing_ms,
                error=str(exc_val),
                metadata=self.metadata,
            )
            return False  # Re-raise exception

        if self.error:
            # Explicit error set
            self.emitter.emit_node_failed(
                node_id=self.node_id,
                timing_ms=timing_ms,
                error=self.error,
                metadata=self.metadata,
            )
        else:
            # Success
            self.emitter.emit_node_completed(
                node_id=self.node_id,
                timing_ms=timing_ms,
                outputs=self.outputs,
                writes=self.writes,
                metadata=self.metadata,
            )

        return False

    def set_outputs(self, outputs: Any) -> None:
        """Set outputs for the trace."""
        self.outputs = outputs

    def add_write(self, path: str, op: str = "replace") -> None:
        """Add a state write to the trace."""
        self.writes.append({"path": path, "op": op})

    def set_error(self, error: str) -> None:
        """Set error for the trace."""
        self.error = error

    def update_metadata(self, **kwargs: Any) -> None:
        """Update metadata."""
        self.metadata.update(kwargs)
