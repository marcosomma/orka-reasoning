"""Unit tests for orka.streaming.runtime (StreamingOrchestrator)."""

import asyncio
import os
from unittest.mock import AsyncMock, Mock, patch

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


class TestRefreshConfig:
    """Test suite for RefreshConfig dataclass."""

    def test_default_values(self):
        """Test RefreshConfig default values."""
        config = RefreshConfig()
        
        assert config.cadence_seconds == 3
        assert config.debounce_ms == 500
        assert config.max_refresh_per_min == 10

    def test_custom_values(self):
        """Test RefreshConfig with custom values."""
        config = RefreshConfig(
            cadence_seconds=5,
            debounce_ms=1000,
            max_refresh_per_min=20
        )
        
        assert config.cadence_seconds == 5
        assert config.debounce_ms == 1000
        assert config.max_refresh_per_min == 20


class TestStreamingOrchestrator:
    """Test suite for StreamingOrchestrator class."""

    def test_init_with_minimal_args(self):
        """Test StreamingOrchestrator initialization with minimal arguments."""
        bus = EventBus()
        composer = _make_composer()
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer
        )
        
        assert orch.session_id == "test-session"
        assert orch.bus == bus
        assert orch.composer == composer
        assert isinstance(orch.refresh, RefreshConfig)
        assert isinstance(orch.state, StreamingState)
        assert orch._last_refresh_ms == 0
        assert orch._last_executed_version == -1
        assert orch._last_sat_version == -1
        assert isinstance(orch._trace, list)
        assert len(orch._trace) == 0

    def test_init_with_custom_invariants(self):
        """Test initialization with custom invariants."""
        bus = EventBus()
        composer = _make_composer()
        invariants = Invariants(
            identity="Test Bot",
            voice="Professional",
            refusal="I cannot help with that"
        )
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            invariants=invariants
        )
        
        assert orch.state.invariants.identity == "Test Bot"

    def test_init_with_custom_refresh_config(self):
        """Test initialization with custom refresh configuration."""
        bus = EventBus()
        composer = _make_composer()
        refresh = RefreshConfig(cadence_seconds=10, debounce_ms=2000)
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=refresh
        )
        
        assert orch.refresh.cadence_seconds == 10
        assert orch.refresh.debounce_ms == 2000

    def test_init_with_executor_config(self):
        """Test initialization with executor configuration."""
        bus = EventBus()
        composer = _make_composer()
        executor = {
            "provider": "openai",
            "model": "gpt-4",
            "base_url": "https://api.openai.com",
            "api_key": "test-key"
        }
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            executor=executor
        )
        
        assert orch._executor_cfg["provider"] == "openai"
        assert orch._executor_cfg["model"] == "gpt-4"

    def test_init_with_satellites_config(self):
        """Test initialization with satellites configuration."""
        bus = EventBus()
        composer = _make_composer()
        satellites = {
            "roles": ["summarizer", "intent"],
            "defs": [
                {"role": "summarizer", "model": "gpt-3.5-turbo"}
            ]
        }
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            satellites=satellites
        )
        
        assert "summarizer" in orch._satellite_roles
        assert "intent" in orch._satellite_roles
        assert len(orch._sat_defs) == 1

    def test_new_executor_id(self):
        """Test that _new_executor_id generates unique IDs."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer
        )
        
        id1 = orch._new_executor_id()
        id2 = orch._new_executor_id()
        
        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert len(id1) == 12
        assert len(id2) == 12
        assert id1 != id2

    def test_history_max_chars_default(self):
        """Test default history max chars."""
        bus = EventBus()
        composer = _make_composer()
        
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer
        )
        
        assert orch._history_max_chars == 2000

    def test_history_max_chars_from_env(self):
        """Test history max chars from environment variable."""
        bus = EventBus()
        composer = _make_composer()
        
        with patch.dict(os.environ, {"ORKA_STREAMING_HISTORY_MAX_CHARS": "5000"}):
            orch = StreamingOrchestrator(
                session_id="test-session",
                bus=bus,
                composer=composer
            )
            assert orch._history_max_chars == 5000

    def test_history_max_chars_invalid_env(self):
        """Test history max chars with invalid environment variable."""
        bus = EventBus()
        composer = _make_composer()
        
        with patch.dict(os.environ, {"ORKA_STREAMING_HISTORY_MAX_CHARS": "invalid"}):
            orch = StreamingOrchestrator(
                session_id="test-session",
                bus=bus,
                composer=composer
            )
            assert orch._history_max_chars == 2000

    def test_append_history_line(self):
        """Test appending a line to history."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer
        )
        
        orch._append_history_line("User: Hello")
        assert len(orch._history_lines) == 1
        assert orch._history_lines[0] == "User: Hello"

    def test_append_history_line_strips_whitespace(self):
        """Test that append_history_line strips whitespace."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer
        )
        
        orch._append_history_line("  User: Hello  ")
        assert orch._history_lines[0] == "User: Hello"

    def test_append_history_line_ignores_empty(self):
        """Test that empty lines are not appended."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer
        )
        
        orch._append_history_line("")
        orch._append_history_line("   ")
        assert len(orch._history_lines) == 0

    def test_append_history_line_trimming(self):
        """Test that history is trimmed when exceeding max chars."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer
        )
        orch._history_max_chars = 50
        
        orch._append_history_line("Line 1: " + "x" * 30)
        orch._append_history_line("Line 2: " + "y" * 30)
        
        # Should drop oldest lines to stay under limit
        assert len("\n".join(orch._history_lines)) <= 50

    def test_current_history_text(self):
        """Test getting current history text."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer
        )
        
        orch._append_history_line("Line 1")
        orch._append_history_line("Line 2")
        
        history = orch._current_history_text()
        assert history == "Line 1\nLine 2"

    def test_current_history_text_truncates(self):
        """Test that history text is truncated to max chars."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer
        )
        orch._history_max_chars = 20
        
        orch._append_history_line("Short line")
        orch._append_history_line("Another line here")
        
        history = orch._current_history_text()
        assert len(history) <= 20
        # Should keep the end (most recent)
        assert history.endswith("here")

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test shutdown method."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer
        )
        
        await orch.shutdown(reason="test shutdown")
        
        assert orch._shutdown.is_set()

    @pytest.mark.asyncio
    async def test_maybe_refresh_skips_cadence_tick(self):
        """Test that _maybe_refresh skips cadence_tick refreshes."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer
        )
        
        initial_version = orch._last_executed_version
        await orch._maybe_refresh(reason="cadence_tick")
        
        # Should not have executed anything
        assert orch._last_executed_version == initial_version

    @pytest.mark.asyncio
    async def test_maybe_refresh_debounce(self):
        """Test that _maybe_refresh respects debounce."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(debounce_ms=10000)
        )
        
        # Set a recent refresh time
        import time
        orch._last_refresh_ms = int(time.time() * 1000)
        
        initial_version = orch._last_executed_version
        await orch._maybe_refresh(reason="state_delta_threshold")
        
        # Should have been debounced
        assert orch._last_executed_version == initial_version

    @pytest.mark.asyncio
    async def test_maybe_refresh_rate_limit(self):
        """Test that _maybe_refresh enforces rate limiting."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(max_refresh_per_min=2, debounce_ms=0)
        )
        
        # Simulate many recent refreshes
        import time
        current_time = time.time()
        orch._refresh_count_window = [current_time - 10, current_time - 5, current_time - 1]
        
        initial_version = orch._last_executed_version
        await orch._maybe_refresh(reason="test")
        
        # Should have been rate limited
        assert orch._last_executed_version == initial_version

    @pytest.mark.asyncio
    async def test_maybe_refresh_no_context_guard(self):
        """Test that _maybe_refresh guards against empty prompts."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(debounce_ms=0)
        )
        
        # Mock composer to return empty sections
        with patch.object(composer, 'compose') as mock_compose:
            mock_compose.return_value = {
                "sections": {
                    "intent": "",
                    "summary": "",
                    "history": ""
                },
                "state_version_used": 1
            }
            
            initial_version = orch._last_executed_version
            await orch._maybe_refresh(reason="test")
            
            # Should not execute without context
            assert orch._last_executed_version == initial_version

    @pytest.mark.asyncio
    async def test_maybe_refresh_avoids_duplicate_version(self):
        """Test that _maybe_refresh skips if version hasn't changed."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(debounce_ms=0)
        )
        
        orch._last_executed_version = 5
        
        with patch.object(composer, 'compose') as mock_compose:
            mock_compose.return_value = {
                "sections": {"intent": "test"},
                "state_version_used": 5
            }
            
            await orch._maybe_refresh(reason="test")
            
            # Should have exited early
            mock_compose.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_satellites_bg_exception_handling(self):
        """Test that _run_satellites_bg handles exceptions gracefully."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer
        )
        
        with patch.object(orch, '_run_satellites', side_effect=Exception("Test error")):
            # Should not raise
            await orch._run_satellites_bg()

    def test_naive_satellites_env_var(self):
        """Test naive satellites enabled from environment variable."""
        bus = EventBus()
        composer = _make_composer()
        
        with patch.dict(os.environ, {"ORKA_STREAMING_SATELLITES_NAIVE": "1"}):
            orch = StreamingOrchestrator(
                session_id="test-session",
                bus=bus,
                composer=composer
            )
            assert orch._naive_satellites is True

    def test_satellites_enable_env_var(self):
        """Test satellites enabled from environment variable."""
        bus = EventBus()
        composer = _make_composer()
        
        with patch.dict(os.environ, {"ORKA_STREAMING_SATELLITES_ENABLE": "1"}):
            orch = StreamingOrchestrator(
                session_id="test-session",
                bus=bus,
                composer=composer
            )
            assert orch._sat_enabled is True

    @pytest.mark.asyncio
    async def test_maybe_refresh_publishes_egress(self):
        """Test that _maybe_refresh publishes to egress channel."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(debounce_ms=0)
        )
        
        with patch.object(composer, 'compose') as mock_compose:
            mock_compose.return_value = {
                "sections": {"intent": "test query"},
                "state_version_used": 1
            }
            
            with patch.object(bus, 'publish', new_callable=AsyncMock) as mock_publish:
                await orch._maybe_refresh(reason="test")
                
                # Should have published to alerts and egress channels
                assert mock_publish.call_count >= 2
                
                # Check egress publish
                egress_calls = [c for c in mock_publish.call_args_list if 'egress' in str(c)]
                assert len(egress_calls) > 0

    @pytest.mark.asyncio
    async def test_maybe_refresh_updates_trace(self):
        """Test that _maybe_refresh updates trace."""
        bus = EventBus()
        composer = _make_composer()
        orch = StreamingOrchestrator(
            session_id="test-session",
            bus=bus,
            composer=composer,
            refresh=RefreshConfig(debounce_ms=0)
        )
        
        with patch.object(composer, 'compose') as mock_compose:
            mock_compose.return_value = {
                "sections": {"intent": "test"},
                "state_version_used": 1
            }
            
            initial_trace_len = len(orch._trace)
            await orch._maybe_refresh(reason="test")
            
            # Trace should have new entries
            assert len(orch._trace) > initial_trace_len
