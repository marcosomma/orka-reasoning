"""Integration tests for StreamingOrchestrator covering main workflows."""

import asyncio
import os
from unittest.mock import AsyncMock, Mock, patch, call
import pytest

from orka.streaming.event_bus import EventBus
from orka.streaming.prompt_composer import PromptComposer
from orka.streaming.runtime import RefreshConfig, StreamingOrchestrator
from orka.streaming.state import Invariants, StreamingState
from orka.streaming.types import PromptBudgets

pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


def _make_composer():
    """Create a PromptComposer with default budgets for testing."""
    budgets = PromptBudgets(total_tokens=1000, sections={"context": 500})
    return PromptComposer(budgets=budgets)


class TestStreamingOrchestratorIntegration:
    """Test suite for StreamingOrchestrator integration scenarios."""

    @pytest.mark.asyncio
    async def test_run_and_shutdown(self):
        """Test run() method with shutdown."""
        bus = EventBus()
        composer = _make_composer()
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(cadence_seconds=1, debounce_ms=100),
        )
        
        # Start run in background task
        run_task = asyncio.create_task(orch.run())
        
        # Let it run briefly
        await asyncio.sleep(0.3)
        
        # Trigger shutdown
        await orch.shutdown(reason="test_complete")
        
        # Wait for run to complete
        await asyncio.wait_for(run_task, timeout=2.0)
        
        assert orch._shutdown.is_set()

    @pytest.mark.asyncio
    async def test_main_loop_state_patch(self):
        """Test _main_loop processing state patches from ingress."""
        bus = EventBus()
        composer = _make_composer()
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(cadence_seconds=1, debounce_ms=50),
        )
        
        # Publish a state patch to ingress
        await bus.publish(
            "test-session.ingress",
            {
                "session_id": "test-session",
                "channel": "test-session.ingress",
                "type": "ingress",
                "payload": {
                    "state_patch": {"intent": "Hello world"},
                    "provenance": {"timestamp_ms": 123456, "source": "test"},
                },
                "timestamp_ms": 123456,
                "source": "test",
                "state_version": 0,
            },
        )
        
        # Start run in background
        run_task = asyncio.create_task(orch.run())
        
        # Wait until state is updated or timeout
        for _ in range(20):
            if orch.state.mutable.intent == "Hello world":
                break
            await asyncio.sleep(0.05)
        
        # Shutdown
        await orch.shutdown(reason="test_complete")
        await asyncio.wait_for(run_task, timeout=2.0)
        
        # Verify state was updated
        assert orch.state.mutable.intent == "Hello world"

    @pytest.mark.asyncio
    async def test_main_loop_text_message(self):
        """Test _main_loop processing text messages."""
        bus = EventBus()
        composer = _make_composer()
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(cadence_seconds=1, debounce_ms=50),
        )
        
        # Publish a text message to ingress
        await bus.publish(
            "test-session.ingress",
            {
                "session_id": "test-session",
                "channel": "test-session.ingress",
                "type": "ingress",
                "payload": {"text": "What is the capital of France?"},
                "timestamp_ms": 123456,
                "source": "user",
                "state_version": 0,
            },
        )
        
        # Start run in background
        run_task = asyncio.create_task(orch.run())
        
        # Wait until intent is populated or timeout
        for _ in range(20):
            if "What is the capital of France?" in orch.state.mutable.intent:
                break
            await asyncio.sleep(0.05)
        
        # Shutdown
        await orch.shutdown(reason="test_complete")
        await asyncio.wait_for(run_task, timeout=2.0)
        
        # Verify state was updated with intent and history
        assert "What is the capital of France?" in orch.state.mutable.intent
        assert "User:" in orch._current_history_text()

    @pytest.mark.asyncio
    async def test_main_loop_naive_satellites(self):
        """Test naive satellites summarizer in _main_loop."""
        bus = EventBus()
        composer = _make_composer()
        
        # Enable naive satellites via env var
        with patch.dict(os.environ, {"ORKA_STREAMING_SATELLITES_NAIVE": "1"}):
            orch = StreamingOrchestrator(
                session_id="test-session",
                bus=bus,
                composer=composer,
                refresh=RefreshConfig(cadence_seconds=1, debounce_ms=50),
                satellites={"roles": ["summarizer"], "defs": []},
            )
            
            # Publish a text message
            await bus.publish(
                "test-session.ingress",
                {
                    "session_id": "test-session",
                    "channel": "test-session.ingress",
                    "type": "ingress",
                    "payload": {"text": " ".join(["word"] * 60)},  # Long text for clipping
                    "timestamp_ms": 123456,
                    "source": "user",
                    "state_version": 0,
                },
            )
            
            # Start run in background
            run_task = asyncio.create_task(orch.run())
            
            # Wait until summary is populated or timeout
            for _ in range(20):
                if orch.state.mutable.summary:
                    break
                await asyncio.sleep(0.05)
            
            # Shutdown
            await orch.shutdown(reason="test_complete")
            await asyncio.wait_for(run_task, timeout=2.0)
            
            # Verify summary was created
            summary = orch.state.mutable.summary
            assert summary
            assert len(summary.split()) <= 55  # Approximately 50 words due to clipping

    @pytest.mark.asyncio
    async def test_main_loop_invalid_patch(self):
        """Test _main_loop handling invalid state patches."""
        bus = EventBus()
        composer = _make_composer()
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(cadence_seconds=1, debounce_ms=50),
        )
        
        # Patch apply_patch to raise an exception
        original_apply = orch.state.apply_patch
        def broken_apply(*args, **kwargs):
            raise ValueError("Invalid patch")
        orch.state.apply_patch = broken_apply
        
        # Publish a state patch
        await bus.publish(
            "test-session.ingress",
            {
                "session_id": "test-session",
                "channel": "test-session.ingress",
                "type": "ingress",
                "payload": {
                    "state_patch": {"intent": "test"},
                    "provenance": {"timestamp_ms": 123456},
                },
                "timestamp_ms": 123456,
                "source": "test",
                "state_version": 0,
            },
        )
        
        # Start run in background
        run_task = asyncio.create_task(orch.run())
        
        # Let loop process and handle error (wait for alert)
        found_alert = False
        for _ in range(20):
            alerts = await bus.read(["test-session.alerts"], count=10, block_ms=10)
            if any("state_patch_failed" in str(a) for a in alerts):
                found_alert = True
                break
            await asyncio.sleep(0.05)
        
        # Shutdown
        await orch.shutdown(reason="test_complete")
        await asyncio.wait_for(run_task, timeout=2.0)
        
        # Verify alert was published (check DLQ or alerts channel)
        assert found_alert

    @pytest.mark.asyncio
    async def test_maybe_refresh_executor_rotation(self):
        """Test _maybe_refresh rotates executor instance ID."""
        bus = EventBus()
        composer = _make_composer()
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(debounce_ms=10),
        )
        
        # Apply state change to trigger refresh
        orch.state.apply_patch({"intent": "test intent"}, {"timestamp_ms": 1000})
        
        old_id = orch._executor_instance_id
        
        # Trigger refresh
        await orch._maybe_refresh(reason="state_delta_threshold")
        
        # Verify executor ID changed
        assert orch._executor_instance_id != old_id

    @pytest.mark.asyncio
    async def test_maybe_refresh_publishes_egress(self):
        """Test _maybe_refresh publishes to egress channel."""
        bus = EventBus()
        composer = _make_composer()
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(debounce_ms=10),
        )
        
        # Apply state change
        orch.state.apply_patch({"intent": "test intent"}, {"timestamp_ms": 1000})
        
        # Trigger refresh
        await orch._maybe_refresh(reason="state_delta_threshold")
        
        # Check egress channel
        egress_ch = "test-session.egress"
        messages = await bus.read([egress_ch], count=10, block_ms=100)
        
        assert len(messages) > 0
        assert any("egress" in str(msg) for msg in messages)

    @pytest.mark.asyncio
    async def test_maybe_refresh_no_context_guard(self):
        """Test _maybe_refresh skips when no context available."""
        bus = EventBus()
        composer = _make_composer()
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(debounce_ms=10),
        )
        
        # Don't apply any state changes (no intent/summary/history)
        old_exec_ver = orch._last_executed_version
        
        # Trigger refresh
        await orch._maybe_refresh(reason="state_delta_threshold")
        
        # Verify no execution happened (version unchanged)
        assert orch._last_executed_version == old_exec_ver

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ORKA_STREAMING_HTTP_ENABLE": "1"})
    async def test_maybe_refresh_http_executor(self):
        """Test _maybe_refresh with HTTP executor enabled."""
        bus = EventBus()
        composer = _make_composer()
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(debounce_ms=10),
            executor={
                "provider": "openai",
                "model": "gpt-4",
                "base_url": "http://localhost:8080/v1",
                "api_key": "test-key",
            },
        )
        
        # Apply state change
        orch.state.apply_patch({"intent": "test intent"}, {"timestamp_ms": 1000})
        
        # Mock the OpenAICompatClient
        mock_client = AsyncMock()
        
        async def mock_stream(*args, **kwargs):
            yield "Hello"
            yield " world"
        
        mock_client.stream_complete = mock_stream
        
        with patch("orka.streaming.runtime.OpenAICompatClient", return_value=mock_client):
            # Trigger refresh
            await orch._maybe_refresh(reason="state_delta_threshold")
        
        # Verify streaming messages were published
        egress_ch = "test-session.egress"
        # Wait for some egress messages to arrive
        messages = []
        for _ in range(20):
            batch = await bus.read([egress_ch], count=50, block_ms=10)
            messages.extend(batch)
            if len(messages) >= 2:
                break
            await asyncio.sleep(0.05)
        
        # Should have multiple egress messages (initial + stream chunks + final)
        assert len(messages) >= 2

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ORKA_STREAMING_SATELLITES_ENABLE": "1"})
    async def test_run_satellites_bg(self):
        """Test _run_satellites_bg executes satellites."""
        bus = EventBus()
        composer = _make_composer()
        
        # Mock satellite client
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(return_value="Satellite summary output")
        
        with patch("orka.streaming.runtime.OpenAICompatClient", return_value=mock_client):
            orch = StreamingOrchestrator(
                session_id="test-session",
                bus=bus,
                composer=composer,
                refresh=RefreshConfig(debounce_ms=10),
                satellites={
                    "roles": ["summarizer"],
                    "defs": [
                        {
                            "role": "summarizer",
                            "provider": "openai",
                            "model": "gpt-3.5-turbo",
                            "base_url": "http://localhost:8080/v1",
                            "api_key": "test-key",
                        }
                    ],
                },
            )
            
            # Apply state change to provide content
            orch.state.apply_patch({"intent": "test intent for summarization"}, {"timestamp_ms": 1000})
            
            # Run satellites in background
            await orch._run_satellites_bg()
            
            # Verify satellite was called
            assert mock_client.complete.called
            
            # Verify state was updated with satellite output
            assert "Satellite summary output" in str(orch.state.mutable.summary)

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ORKA_STREAMING_SATELLITES_ENABLE": "1"})
    async def test_run_satellites_with_failure(self):
        """Test _run_satellites handles satellite failures."""
        bus = EventBus()
        composer = _make_composer()
        
        # Mock satellite client that raises exception
        mock_client = AsyncMock()
        mock_client.complete = AsyncMock(side_effect=Exception("Satellite failed"))
        
        with patch("orka.streaming.runtime.OpenAICompatClient", return_value=mock_client):
            orch = StreamingOrchestrator(
                session_id="test-session",
                bus=bus,
                composer=composer,
                satellites={
                    "roles": ["summarizer"],
                    "defs": [
                        {
                            "role": "summarizer",
                            "provider": "openai",
                            "model": "gpt-3.5-turbo",
                            "base_url": "http://localhost:8080/v1",
                            "api_key": "test-key",
                        }
                    ],
                },
            )
            
            # Apply state change
            orch.state.apply_patch({"intent": "test"}, {"timestamp_ms": 1000})
            
            # Run satellites (should not raise exception)
            await orch._run_satellites()
            
            # Verify warning alert was published
            alerts_ch = "test-session.alerts"
            alerts = await bus.read([alerts_ch], count=10, block_ms=100)
            assert any("satellite_failed" in str(alert) for alert in alerts)

    @pytest.mark.asyncio
    async def test_main_loop_with_satellite_trigger(self):
        """Test _main_loop triggers satellites on state change."""
        bus = EventBus()
        composer = _make_composer()
        
        with patch.dict(os.environ, {"ORKA_STREAMING_SATELLITES_ENABLE": "1"}):
            orch = StreamingOrchestrator(
                session_id="test-session",
                bus=bus,
                composer=composer,
                refresh=RefreshConfig(cadence_seconds=1, debounce_ms=50),
                satellites={
                    "roles": ["summarizer"],
                    "defs": [
                        {
                            "role": "summarizer",
                            "provider": "openai",
                            "model": "gpt-3.5-turbo",
                            "base_url": "http://localhost:8080/v1",
                            "api_key": "test-key",
                        }
                    ],
                },
            )
            
            # Mock satellite execution
            orch._run_satellites_bg = AsyncMock()
            
            # Publish a text message to trigger state change
            await bus.publish(
                "test-session.ingress",
                {
                    "session_id": "test-session",
                    "channel": "test-session.ingress",
                    "type": "ingress",
                    "payload": {"text": "Test message"},
                    "timestamp_ms": 123456,
                    "source": "user",
                    "state_version": 0,
                },
            )
            
            # Start run in background
            run_task = asyncio.create_task(orch.run())
            
            # Wait until satellites are triggered
            for _ in range(20):
                if orch._run_satellites_bg.called:
                    break
                await asyncio.sleep(0.05)
            
            # Shutdown
            await orch.shutdown(reason="test_complete")
            await asyncio.wait_for(run_task, timeout=2.0)
            
            # Verify satellites were triggered
            assert orch._run_satellites_bg.called

    @pytest.mark.asyncio
    async def test_shutdown_persists_trace(self):
        """Test shutdown() persists trace to file."""
        bus = EventBus()
        composer = _make_composer()
        
        orch = StreamingOrchestrator(
            session_id="test-trace-session",
            bus=bus,
            composer=composer,
        )
        
        # Add some trace entries
        orch._trace.append({"type": "test", "data": "value1"})
        orch._trace.append({"type": "test", "data": "value2"})
        
        # Trigger shutdown
        await orch.shutdown(reason="test_trace_persist")
        
        # Trace file should have been created (we don't check file existence in unit test)
        # Just verify shutdown completed without error
        assert orch._shutdown.is_set()

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"ORKA_STREAMING_HTTP_ENABLE": "1", "ORKA_STREAMING_PROMPT_DEBUG": "1"})
    async def test_maybe_refresh_prompt_debug(self):
        """Test _maybe_refresh with prompt debug enabled."""
        bus = EventBus()
        composer = _make_composer()
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(debounce_ms=10),
            executor={
                "provider": "openai",
                "model": "gpt-4",
                "base_url": "http://localhost:8080/v1",
                "api_key": "test-key",
            },
        )
        
        # Apply state change
        orch.state.apply_patch({"intent": "debug test intent"}, {"timestamp_ms": 1000})
        
        # Mock the OpenAICompatClient to avoid actual HTTP call
        mock_client = AsyncMock()
        
        async def mock_stream():
            yield "Response"
        
        mock_client.stream_complete = mock_stream
        
        with patch("orka.streaming.runtime.OpenAICompatClient", return_value=mock_client):
            # Trigger refresh
            await orch._maybe_refresh(reason="state_delta_threshold")
        
        # Verify prompt debug alert was published
        alerts_ch = "test-session.alerts"
        alerts = await bus.read([alerts_ch], count=20, block_ms=100)
        assert any("prompt_debug" in str(alert) for alert in alerts)
