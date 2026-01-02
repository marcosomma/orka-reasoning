"""
StreamingOrchestrator runtime skeleton.

This executor wires the EventBus, StreamingState, and PromptComposer together
and provides a minimal, deterministic refresh loop with debounce. It is safe to
import and run in offline unit tests thanks to the in-memory EventBus.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..observability.structured_logging import StructuredLogger
from .event_bus import EventBus
from .prompt_composer import PromptComposer
from .state import Invariants, StreamingState
from .executor_client import OpenAICompatClient
from pathlib import Path
import json


@dataclass
class RefreshConfig:
    cadence_seconds: int = 3
    debounce_ms: int = 500
    max_refresh_per_min: int = 10


class StreamingOrchestrator:
    """Event-driven streaming runtime with deterministic refresh."""

    def __init__(
        self,
        session_id: str,
        bus: EventBus,
        composer: PromptComposer,
        invariants: Optional[Invariants] = None,
        refresh: Optional[RefreshConfig] = None,
        executor: Optional[Dict[str, Any]] = None,
        satellites: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.session_id = session_id
        self.bus = bus
        self.composer = composer
        self.refresh = refresh or RefreshConfig()
        self.logger = StructuredLogger(__name__)
        self.state = StreamingState(invariants=invariants or Invariants())
        self._shutdown = asyncio.Event()
        self._last_refresh_ms = 0
        self._refresh_count_window: list[float] = []
        self._executor_instance_id = self._new_executor_id()
        self._executor_cfg = executor or {}
        self._last_executed_version: int = -1
        self._satellite_roles = (satellites or {}).get("roles", [])
        self._sat_defs: list[dict] = (satellites or {}).get("defs", [])
        self._naive_satellites = os.environ.get("ORKA_STREAMING_SATELLITES_NAIVE", "0") == "1"
        self._sat_enabled = os.environ.get("ORKA_STREAMING_SATELLITES_ENABLE", "0") == "1"
        self._last_sat_version: int = -1
        self._trace: list[dict] = []
        # Background satellite task handle
        self._sat_task: Optional[asyncio.Task] = None
        # Lightweight rolling conversation history (for context carry)
        self._history_lines: list[str] = []
        try:
            self._history_max_chars = int(os.environ.get("ORKA_STREAMING_HISTORY_MAX_CHARS", "2000"))
        except Exception:
            self._history_max_chars = 2000

    def _new_executor_id(self) -> str:
        return uuid.uuid4().hex[:12]

    async def run(self) -> None:
        """Run the streaming loops until shutdown is requested."""
        # Beta warning
        self.logger.warning(
            "⚠️ BETA: Streaming runtime has known limitations including context loss across turns. "
            "See docs/STREAMING_GUIDE.md for details.",
            session_id=self.session_id
        )
        self.logger.info("streaming_started", session_id=self.session_id)
        try:
            await self._main_loop()
        finally:
            self.logger.info("streaming_stopped", session_id=self.session_id)

    async def shutdown(self, reason: str = "") -> None:
        self.logger.info("streaming_shutdown", reason=reason)
        self._shutdown.set()
        # Persist trace for replay/debug
        try:
            logs_dir = Path(__file__).resolve().parents[2] / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            trace_path = logs_dir / f"stream_trace_{self.session_id}_{int(time.time())}.json"
            with open(trace_path, "w", encoding="utf-8") as f:
                json.dump(self._trace, f)
        except Exception:
            pass

    async def _main_loop(self) -> None:
        # Minimal ingress-consume + compose + egress loop
        ingress_ch = f"{self.session_id}.ingress"
        egress_ch = f"{self.session_id}.egress"
        block_ms = 200
        cadence_ms = max(100, int(self.refresh.cadence_seconds * 1000))
        while not self._shutdown.is_set():
            # Read ingress with short block
            msgs = await self.bus.read([ingress_ch], count=50, block_ms=block_ms)
            if not msgs:
                # Cadence tick only if enough time has passed since last refresh
                now_ms = int(time.time() * 1000)
                if now_ms - self._last_refresh_ms >= cadence_ms:
                    await self._maybe_refresh(reason="cadence_tick")
                continue
            # Apply incoming patches or text as intent
            changed = False
            for item in msgs:
                env = item.get("envelope", {})
                payload = env.get("payload", {})
                if isinstance(payload, dict) and payload.get("state_patch"):
                    prov = payload.get("provenance", {"timestamp_ms": int(time.time() * 1000)})
                    patch = payload.get("state_patch", {})
                    try:
                        self.state.apply_patch(patch, prov)
                        changed = True
                    except Exception as exc:  # emit alert
                        await self.bus.to_dlq(ingress_ch, env, reason=str(exc))
                        # Also emit alert event for chat UI visibility
                        await self.bus.publish(
                            f"{self.session_id}.alerts",
                            {
                                "session_id": self.session_id,
                                "channel": f"{self.session_id}.alerts",
                                "type": "alerts",
                                "payload": {
                                    "severity": "error",
                                    "event": "state_patch_failed",
                                    "reason": str(exc),
                                },
                                "timestamp_ms": int(time.time() * 1000),
                                "source": "streaming_orchestrator",
                                "state_version": self.state.version,
                            },
                        )
                elif isinstance(payload, dict) and "text" in payload:
                    # Treat as raw user text -> intent section update
                    prov = {"timestamp_ms": int(time.time() * 1000), "source": "user"}
                    self.state.apply_patch({"intent": str(payload["text"])}, prov)
                    # Update rolling history with the new user turn
                    self._append_history_line(f"User: {str(payload['text']).strip()}")
                    self.state.apply_patch({"history": self._current_history_text()}, prov)
                    # Naive satellites (optional): produce a summary patch
                    if self._naive_satellites and ("summarizer" in self._satellite_roles):
                        intent_text = str(payload["text"]) or ""
                        summary = " ".join(intent_text.split()[:50])  # clip first 50 tokens approx
                        sat_prov = {"timestamp_ms": int(time.time() * 1000), "source": "sat_summarizer"}
                        self.state.apply_patch({"summary": summary}, sat_prov)
                        # Alert for visibility
                        await self.bus.publish(
                            f"{self.session_id}.alerts",
                            {
                                "session_id": self.session_id,
                                "channel": f"{self.session_id}.alerts",
                                "type": "alerts",
                                "payload": {"severity": "info", "event": "satellite_summary_applied"},
                                "timestamp_ms": int(time.time() * 1000),
                                "source": "streaming_orchestrator",
                                "state_version": self.state.version,
                            },
                        )
                    changed = True
                # Ack best-effort
                await self.bus.ack(group="default", channel=item["channel"], message_id=item["message_id"])

            if changed:
                # Kick off satellites in background if enabled and no run in-flight
                if self._sat_enabled and self.state.version != self._last_sat_version:
                    if self._sat_task is None or self._sat_task.done():
                        self._sat_task = asyncio.create_task(self._run_satellites_bg())
                # Immediately refresh executor for fast time-to-first-token
                await self._maybe_refresh(reason="state_delta_threshold")

    async def _maybe_refresh(self, reason: str) -> None:
        now_ms = int(time.time() * 1000)
        # Skip periodic cadence refreshes; only refresh on state changes or satellite patches
        if reason == "cadence_tick":
            self.logger.debug("skip_cadence_refresh", reason=reason)
            return
        # Debounce
        if now_ms - self._last_refresh_ms < self.refresh.debounce_ms and reason != "critical_alert":
            self.logger.debug("debounce_hit", reason=reason)
            # Emit informational alert for chat UI
            await self.bus.publish(
                f"{self.session_id}.alerts",
                {
                    "session_id": self.session_id,
                    "channel": f"{self.session_id}.alerts",
                    "type": "alerts",
                    "payload": {"severity": "info", "event": "debounce_hit", "reason": reason},
                    "timestamp_ms": now_ms,
                    "source": "streaming_orchestrator",
                    "state_version": self.state.version,
                },
            )
            return

        # Rate limit per minute
        window = self._refresh_count_window
        window.append(time.time())
        one_min_ago = time.time() - 60.0
        while window and window[0] < one_min_ago:
            window.pop(0)
        if len(window) > self.refresh.max_refresh_per_min:
            self.logger.warning("refresh_rate_limited", count=len(window))
            # Emit warning alert
            await self.bus.publish(
                f"{self.session_id}.alerts",
                {
                    "session_id": self.session_id,
                    "channel": f"{self.session_id}.alerts",
                    "type": "alerts",
                    "payload": {"severity": "warning", "event": "refresh_rate_limited", "count": len(window)},
                    "timestamp_ms": now_ms,
                    "source": "streaming_orchestrator",
                    "state_version": self.state.version,
                },
            )
            # Back off to avoid log spam; treat as a logical refresh attempt
            self._last_refresh_ms = now_ms
            return

        # Compose prompt and emit a single synthetic egress message
        composed = self.composer.compose(self.state)
        self._last_refresh_ms = now_ms
        current_version = int(composed.get("state_version_used", 0))
        # Avoid repeatedly invoking executor when state did not change
        if current_version == self._last_executed_version:
            return

        # Guard: avoid empty prompts (no user/satellite context yet)
        sections_guard = composed.get("sections", {})
        has_any_context = bool(
            (sections_guard.get("intent") or "").strip()
            or (sections_guard.get("summary") or "").strip()
            or (sections_guard.get("history") or "").strip()
        )
        if not has_any_context:
            # Do not rotate executor or publish any egress until there is context
            return

        # Executor replacement: emit replacement event and rotate instance id
        old_id = self._executor_instance_id
        self._executor_instance_id = self._new_executor_id()
        await self.bus.publish(
            f"{self.session_id}.alerts",
            {
                "session_id": self.session_id,
                "channel": f"{self.session_id}.alerts",
                "type": "alerts",
                "payload": {
                    "severity": "info",
                    "event": "executor_replacement",
                    "executor_instance_id_old": old_id,
                    "executor_instance_id_new": self._executor_instance_id,
                    "reason": reason,
                    "state_version_before": self._last_executed_version,
                    "state_version_after": current_version,
                },
                "timestamp_ms": now_ms,
                "source": "streaming_orchestrator",
                "state_version": current_version,
            },
        )
        self._trace.append({
            "type": "replacement",
            "old": old_id,
            "new": self._executor_instance_id,
            "reason": reason,
            "before": self._last_executed_version,
            "after": current_version,
            "ts": now_ms,
        })
        self._last_executed_version = current_version
        env = {
            "session_id": self.session_id,
            "channel": f"{self.session_id}.egress",
            "type": "egress",
            "payload": {
                "composed": composed,
                "executor_instance_id": self._executor_instance_id,
            },
            "timestamp_ms": now_ms,
            "source": "streaming_orchestrator",
            "state_version": self.state.version,
        }
        await self.bus.publish(env["channel"], env)
        self._trace.append({"type": "egress", "payload": env.get("payload", {}), "ts": now_ms})

        # Optionally call OpenAI-compatible endpoint for a real completion
        if os.environ.get("ORKA_STREAMING_HTTP_ENABLE", "0") == "1":
            try:
                provider = str(self._executor_cfg.get("provider", "")).lower()
                model = str(self._executor_cfg.get("model", ""))
                base_url = str(self._executor_cfg.get("base_url", ""))
                api_key = self._executor_cfg.get("api_key")
                if provider and model and base_url:
                    # Emit start alert for visibility
                    await self.bus.publish(
                        f"{self.session_id}.alerts",
                        {
                            "session_id": self.session_id,
                            "channel": f"{self.session_id}.alerts",
                            "type": "alerts",
                            "payload": {
                                "severity": "info",
                                "event": "executor_http_start",
                                "provider": provider,
                                "model": model,
                                "base_url": base_url,
                            },
                            "timestamp_ms": int(time.time() * 1000),
                            "source": "streaming_orchestrator",
                            "state_version": self.state.version,
                        },
                    )
                    sections = composed["sections"]
                    inv_text = sections.get("invariants", "")
                    constraints_text = sections.get("constraints", "")
                    policy_text = sections.get("policy", "")
                    risk_text = sections.get("risk", "")
                    history_text = sections.get("history", "")
                    # Feed executor with invariants and any compliance/policy context as system
                    extra_rules = []
                    if constraints_text:
                        extra_rules.append(f"constraints: {constraints_text}")
                    if policy_text:
                        extra_rules.append(f"policy: {policy_text}")
                    if risk_text:
                        extra_rules.append(f"risk: {risk_text}")
                    system_text = inv_text if not extra_rules else (inv_text + "\n" + "\n".join(extra_rules))
                    # Build user message with rolling history + summary + latest intent
                    user_parts: list[str] = []
                    if (history_text or "").strip():
                        user_parts.append("Conversation so far:\n" + history_text.strip())
                    if (sections.get("summary") or "").strip():
                        user_parts.append("Summary:\n" + sections.get("summary", "").strip())
                    if (sections.get("intent") or "").strip():
                        user_parts.append("User:\n" + sections.get("intent", "").strip())
                    user_text = "\n\n".join(user_parts).strip()
                    # Optional prompt debug: emit exact system/user strings
                    if os.environ.get("ORKA_STREAMING_PROMPT_DEBUG", "0") == "1":
                        try:
                            await self.bus.publish(
                                f"{self.session_id}.alerts",
                                {
                                    "session_id": self.session_id,
                                    "channel": f"{self.session_id}.alerts",
                                    "type": "alerts",
                                    "payload": {
                                        "severity": "debug",
                                        "event": "prompt_debug",
                                        "system": system_text,
                                        "user": user_text,
                                    },
                                    "timestamp_ms": int(time.time() * 1000),
                                    "source": "streaming_orchestrator",
                                    "state_version": self.state.version,
                                },
                            )
                        except Exception:
                            pass

                    client = OpenAICompatClient(base_url=base_url, api_key=api_key)
                    is_first_chunk = True
                    assembled_chunks: list[str] = []
                    async for chunk in client.stream_complete(model=model, system=system_text, user=user_text):
                        # Emit incremental deltas to the bus (UI may ignore these if aggregating)
                        payload = {
                            "text": chunk,
                            "is_first": is_first_chunk,
                            "state_version_used": self.state.version,
                            "executor_instance_id": self._executor_instance_id,
                        }
                        assembled_chunks.append(chunk)
                        is_first_chunk = False
                        await self.bus.publish(
                            f"{self.session_id}.egress",
                            {
                                "session_id": self.session_id,
                                "channel": f"{self.session_id}.egress",
                                "type": "egress",
                                "payload": payload,
                                "timestamp_ms": int(time.time() * 1000),
                                "source": "executor_http_stream",
                                "state_version": self.state.version,
                            },
                        )
                        self._trace.append({"type": "egress", "payload": payload, "ts": int(time.time() * 1000)})

                    # After stream completes, emit a final aggregated message
                    final_text = "".join(assembled_chunks)
                    final_payload = {
                        "text": final_text,
                        "final": True,
                        "state_version_used": self.state.version,
                        "executor_instance_id": self._executor_instance_id,
                    }
                    await self.bus.publish(
                        f"{self.session_id}.egress",
                        {
                            "session_id": self.session_id,
                            "channel": f"{self.session_id}.egress",
                            "type": "egress",
                            "payload": final_payload,
                            "timestamp_ms": int(time.time() * 1000),
                            "source": "executor_http_stream",
                            "state_version": self.state.version,
                        },
                    )
                    self._trace.append({"type": "egress", "payload": final_payload, "ts": int(time.time() * 1000)})
                    # Append assistant turn to rolling history for future context
                    try:
                        prov_assist = {"timestamp_ms": int(time.time() * 1000), "source": "assistant"}
                        self._append_history_line(f"Assistant: {final_text.strip()}")
                        self.state.apply_patch({"history": self._current_history_text()}, prov_assist)
                    except Exception:
                        pass
            except Exception as exc:
                # Publish an alert for visibility
                await self.bus.publish(
                    f"{self.session_id}.alerts",
                    {
                        "session_id": self.session_id,
                        "channel": f"{self.session_id}.alerts",
                        "type": "alerts",
                        "payload": {"severity": "error", "event": "executor_http_failed", "reason": str(exc)},
                        "timestamp_ms": int(time.time() * 1000),
                        "source": "streaming_orchestrator",
                        "state_version": self.state.version,
                    },
                )
                self._trace.append({"type": "alert", "event": "executor_http_failed", "reason": str(exc), "ts": int(time.time() * 1000)})

    async def _run_satellites(self) -> None:
        """Invoke configured satellites (LLM-backed) to produce patches.

        Uses OpenAI-compatible HTTP (non-streaming) for simplicity.
        Gated by ORKA_STREAMING_SATELLITES_ENABLE=1.
        """
        tasks: list[asyncio.Task] = []
        now_ts = int(time.time() * 1000)
        # Prepare inputs
        inv = self.state.clone_invariants()
        intent = getattr(self.state.mutable, "intent", "")
        summary = getattr(self.state.mutable, "summary", "")

        async def run_one(defn: dict) -> tuple[str, Optional[str]]:
            role = str(defn.get("role", ""))
            provider = str(defn.get("provider", ""))
            model = str(defn.get("model", ""))
            base_url = str(defn.get("base_url", ""))
            api_key = defn.get("api_key")
            if not (provider and model and base_url):
                return role, None
            system_text = (
                f"identity: {inv.get('identity','')}\nvoice: {inv.get('voice','')}\nrefusal: {inv.get('refusal','')}"
            )
            if role == "summarizer":
                user_text = f"Summarize briefly this content for chat continuity:\n{intent or summary}"
            elif role == "intent":
                user_text = f"Extract the user's intent in one sentence:\n{intent or summary}"
            elif role == "compliance":
                user_text = f"Check risks/policy constraints for this message:\n{intent or summary}"
            else:
                user_text = f"Process:\n{intent or summary}"
            try:
                client = OpenAICompatClient(base_url=base_url, api_key=api_key)
                out = await client.complete(model=model, system=system_text, user=user_text)
                return role, out or ""
            except Exception as e:
                await self.bus.publish(
                    f"{self.session_id}.alerts",
                    {
                        "session_id": self.session_id,
                        "channel": f"{self.session_id}.alerts",
                        "type": "alerts",
                        "payload": {"severity": "warning", "event": "satellite_failed", "role": role, "reason": str(e)},
                        "timestamp_ms": int(time.time() * 1000),
                        "source": "streaming_orchestrator",
                        "state_version": self.state.version,
                    },
                )
                return role, None

        for d in self._sat_defs:
            tasks.append(asyncio.create_task(run_one(d)))

        results = await asyncio.gather(*tasks, return_exceptions=False)
        # Apply patches
        for role, text in results:
            if text is None:
                continue
            section = None
            if role == "summarizer":
                section = "summary"
            elif role == "intent":
                section = "intent"
            elif role == "compliance":
                # Generate actionable suggestions/constraints for executor
                section = "constraints"
            else:
                section = "constraints"
            try:
                self.state.apply_patch({section: text}, {"timestamp_ms": int(time.time() * 1000), "source": f"sat_{role}"})
                preview = (text or "")[:160]
                await self.bus.publish(
                    f"{self.session_id}.alerts",
                    {
                        "session_id": self.session_id,
                        "channel": f"{self.session_id}.alerts",
                        "type": "alerts",
                        "payload": {"severity": "info", "event": "satellite_patch_applied", "role": role, "section": section, "preview": preview},
                        "timestamp_ms": int(time.time() * 1000),
                        "source": "streaming_orchestrator",
                        "state_version": self.state.version,
                    },
                )
            except Exception:
                pass

    async def _run_satellites_bg(self) -> None:
        """Run satellites without blocking executor, then trigger a refresh."""
        try:
            await self._run_satellites()
            self._last_sat_version = self.state.version
            # Trigger a follow-up refresh so executor picks up new constraints/summary
            await self._maybe_refresh(reason="satellite_patch")
        except Exception:
            pass

    # History helpers
    def _current_history_text(self) -> str:
        text = "\n".join(self._history_lines)
        if len(text) <= self._history_max_chars:
            return text
        # Trim from the start to fit budget
        return text[-self._history_max_chars :]

    def _append_history_line(self, line: str) -> None:
        line = (line or "").strip()
        if not line:
            return
        self._history_lines.append(line)
        # Keep rough bound by characters
        cur = "\n".join(self._history_lines)
        if len(cur) > self._history_max_chars:
            # Drop oldest lines until under limit
            while self._history_lines and len("\n".join(self._history_lines)) > self._history_max_chars:
                self._history_lines.pop(0)
